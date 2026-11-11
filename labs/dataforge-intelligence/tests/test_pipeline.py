import csv
import tempfile
import unittest
from pathlib import Path

from dataforge.pipeline import run_pipeline


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / "source.csv"
        self.out = self.root / "out"

    def load(self, rows):
        with self.src.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "event_id", "tenant_id", "occurred_at", "amount", "currency", "status"
            ])
            writer.writeheader()
            writer.writerows(rows)

    def test_dedup_refunds_and_idempotent_reruns(self):
        basic = {"tenant_id": "alpha", "occurred_at": "2026-11-11T01:00:00+00:00", "currency": "MXN"}
        self.load([
            {**basic, "event_id": "one", "amount": "100.50", "status": "paid"},
            {**basic, "event_id": "one", "amount": "100.50", "status": "paid"},
            {**basic, "event_id": "two", "amount": "20.25", "status": "refunded"},
            {**basic, "event_id": "one", "amount": "90.00", "status": "paid"},
            {**basic, "event_id": "bad", "amount": "NaN", "status": "paid"},
        ])
        self.assertEqual(run_pipeline(self.src, self.out), {"accepted": 2, "quarantined": 2, "groups": 1})
        first = (self.out / "daily_revenue.csv").read_bytes()
        with (self.out / "daily_revenue.csv").open() as handle:
            result = next(csv.DictReader(handle))
        self.assertEqual(result["net_cents"], "8025")
        self.assertEqual(result["paid_count"], "1")
        self.assertEqual(result["refund_count"], "1")
        run_pipeline(self.src, self.out)
        self.assertEqual((self.out / "daily_revenue.csv").read_bytes(), first)

    def test_invalid_time_and_negative_amount_are_quarantined(self):
        self.load([
            {"event_id": "x", "tenant_id": "t", "occurred_at": "2026-11-11",
             "amount": "2", "currency": "MXN", "status": "paid"},
            {"event_id": "y", "tenant_id": "t", "occurred_at": "2026-11-11T00:00:00Z",
             "amount": "-3", "currency": "USD", "status": "paid"},
        ])
        self.assertEqual(run_pipeline(self.src, self.out)["quarantined"], 2)

    def test_rejects_missing_columns(self):
        self.src.write_text("event_id,tenant_id\nx,t\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "headers"):
            run_pipeline(self.src, self.out)


if __name__ == "__main__":
    unittest.main()
