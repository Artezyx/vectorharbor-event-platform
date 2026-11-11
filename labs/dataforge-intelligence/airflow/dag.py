"""Optional Airflow orchestration; install Airflow separately in an Airflow environment."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dataforge.pipeline import run_pipeline  # noqa: E402

INPUT = os.getenv("DATAFORGE_INPUT", "/opt/airflow/data/events.csv")
OUTPUT = os.getenv("DATAFORGE_OUTPUT", "/opt/airflow/data/output")

with DAG(
    dag_id="dataforge_daily_revenue",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    schedule="@daily",
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["portfolio", "etl"],
) as dag:
    transform = PythonOperator(
        task_id="validate_dedupe_aggregate",
        python_callable=run_pipeline,
        op_kwargs={"input_csv": INPUT, "output_dir": OUTPUT},
    )
