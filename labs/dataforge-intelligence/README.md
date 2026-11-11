# DataForge Intelligence — deterministic ETL lab

A standalone data-engineering module inside the existing VectorHarbor repository. It turns transactional CSV events into UTC daily revenue per tenant and currency, with validation, quarantine, duplicate detection, deterministic replay, atomic CSV exports and tests.

## Quick verification

From this folder (Python 3.11+):

    PYTHONPATH=. python -m unittest discover -s tests -v

To execute:

    PYTHONPATH=. python -m dataforge.pipeline --input examples/events.csv --output /tmp/dataforge-output

The pipeline uses only the Python standard library. The separate Airflow DAG is optional orchestration; the Spark script is an *illustrative batch alternative*, not a claim of identical conflict handling. Its input must be prevalidated before production use. PostgreSQL warehouse DDL is included as a deployment starting point.

## Data contract

Input header: event_id,tenant_id,occurred_at,amount,currency,status

- status: paid / refunded; currencies MXN or USD
- occurred_at: ISO-8601 with explicit timezone
- amount: positive decimal with no more than two fractional digits
- identical duplicate event IDs are ignored, conflicting duplicates quarantined
- outputs: daily_revenue.csv, quarantine.csv, metrics.json
- outputs are replay-safe for a static input; incremental ingestion and global idempotency require a durable event ledger.

Never mix currencies in a single sum. No sample records represent real customer data.
