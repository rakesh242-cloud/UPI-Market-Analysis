"""Load the prepared NPCI tables into MySQL for the Power BI report.

Set UPI_MYSQL_PASSWORD in your environment, then run python load_mysql.py.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import os
import re
from datetime import date
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"
TABLES = (
    ("app_month", "app_month.csv"),
    ("market_month", "market_month.csv"),
    ("leaders_month", "leaders_month.csv"),
    ("leaders_year", "leaders_year.csv"),
    ("seasonality", "seasonality.csv"),
)
INTEGER_FIELDS = {"year", "month", "value_complete", "listed_apps", "missing_value_apps", "years_observed"}
DECIMAL_FIELDS = {"volume_mn", "value_cr", "reported_volume_mn", "top3_share", "phonepe_share",
                  "googlepay_share", "paytm_share", "share", "mean_reported_volume_mn"}


def typed_value(field: str, value: str):
    if value == "":
        return None
    if field == "date":
        return date.fromisoformat(value)
    if field in INTEGER_FIELDS:
        return int(value)
    if field in DECIMAL_FIELDS:
        return Decimal(value)
    return value


def rows_from_csv(path: Path) -> tuple[list[str], list[tuple]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields:
            raise ValueError(f"Missing columns: {path}")
        rows = [tuple(typed_value(field, row[field]) for field in fields) for row in reader]
    if not rows:
        raise ValueError(f"No data rows: {path}")
    return fields, rows


def load(connection, data_dir: Path = DATA) -> dict[str, int]:
    """Create the five tables and replace their rows as one transaction."""
    ddl = (ROOT / "schema.sql").read_text(encoding="utf-8")
    cursor = connection.cursor()
    try:
        for statement in ddl.split(";"):
            if statement.strip():
                cursor.execute(statement)
        counts = {}
        for table, file_name in TABLES:
            fields, rows = rows_from_csv(data_dir / file_name)
            columns = ", ".join(f"`{field}`" for field in fields)
            placeholders = ", ".join("%s" for _ in fields)
            cursor.execute(f"DELETE FROM `{table}`")
            cursor.executemany(f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})", rows)
            counts[table] = len(rows)
        connection.commit()
        return counts
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--database", default="upi_market_analysis")
    parser.add_argument("--user", default="root")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.database):
        parser.error("Database name must contain only letters, numbers, and underscores")
    password = os.environ.get("UPI_MYSQL_PASSWORD")
    if password is None:
        password = getpass.getpass("MySQL password: ")
    import mysql.connector

    connection = mysql.connector.connect(host=args.host, port=args.port, user=args.user, password=password)
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{args.database}` CHARACTER SET utf8mb4")
            cursor.execute(f"USE `{args.database}`")
        finally:
            cursor.close()
        counts = load(connection)
    finally:
        connection.close()
    for table, count in counts.items():
        print(f"{table}: {count:,} rows")
    print(f"Loaded MySQL database: {args.database}")


if __name__ == "__main__":
    main()
