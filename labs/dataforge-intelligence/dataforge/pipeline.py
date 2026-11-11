"""Revenue ETL: validation, deduplication, quarantine, daily rollups and atomic writes."""
from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED = {"event_id", "tenant_id", "occurred_at", "amount", "currency", "status"}
CURRENCIES = {"MXN", "USD"}
STATUSES = {"paid", "refunded"}


def parse_record(row: dict[str, str]) -> dict:
    if not REQUIRED.issubset(row):
        raise ValueError("missing required columns")
    event_id, tenant = row["event_id"].strip(), row["tenant_id"].strip()
    if not event_id or not tenant:
        raise ValueError("event_id and tenant_id are required")
    try:
        when = datetime.fromisoformat(row["occurred_at"].strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError) as error:
        raise ValueError("invalid occurred_at") from error
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("occurred_at must include timezone")
    currency, status = row["currency"].strip().upper(), row["status"].strip().lower()
    if currency not in CURRENCIES or status not in STATUSES:
        raise ValueError("unsupported currency or status")
    try:
        amount = Decimal(row["amount"].strip())
    except (InvalidOperation, AttributeError) as error:
        raise ValueError("invalid amount") from error
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
        raise ValueError("amount must be positive with at most 2 decimals")
    return {
        "event_id": event_id,
        "tenant_id": tenant,
        "day": when.astimezone(timezone.utc).date().isoformat(),
        "amount_cents": int(amount * 100),
        "currency": currency,
        "status": status,
    }


def atomic_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def run_pipeline(input_csv: str | Path, output_dir: str | Path) -> dict[str, int]:
    """Exactly-once per event ID within this input; reruns replace deterministic outputs."""
    source, target = Path(input_csv), Path(output_dir)
    if not source.is_file():
        raise FileNotFoundError(source)
    accepted: dict[str, dict] = {}
    rejected: list[dict[str, str]] = []
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError("input CSV missing required headers")
        for line, row in enumerate(reader, 2):
            try:
                item = parse_record(row)
                current = accepted.get(item["event_id"])
                if current:
                    if current != item:
                        rejected.append({"line": str(line), "event_id": item["event_id"], "reason": "conflicting duplicate"})
                    continue
                accepted[item["event_id"]] = item
            except ValueError as error:
                rejected.append({"line": str(line), "event_id": row.get("event_id", ""), "reason": str(error)})
    totals: dict[tuple[str, str, str], dict[str, int]] = defaultdict(
        lambda: {"paid_count": 0, "refund_count": 0, "net_cents": 0}
    )
    for item in accepted.values():
        key = item["day"], item["tenant_id"], item["currency"]
        value = totals[key]
        if item["status"] == "paid":
            value["paid_count"] += 1
            value["net_cents"] += item["amount_cents"]
        else:
            value["refund_count"] += 1
            value["net_cents"] -= item["amount_cents"]
    summaries = [
        {"day": day, "tenant_id": tenant, "currency": currency, **totals[(day, tenant, currency)]}
        for day, tenant, currency in sorted(totals)
    ]
    atomic_csv(target / "daily_revenue.csv",
               ["day", "tenant_id", "currency", "paid_count", "refund_count", "net_cents"], summaries)
    atomic_csv(target / "quarantine.csv", ["line", "event_id", "reason"], rejected)
    metrics = {"accepted": len(accepted), "quarantined": len(rejected), "groups": len(summaries)}
    (target / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic CSV revenue pipeline")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(run_pipeline(args.input, args.output)))


if __name__ == "__main__":
    main()
