"""Checks the prepared data and MySQL input types."""

import csv
import re
import unittest
import zipfile
from collections import defaultdict
from pathlib import Path
from datetime import date
from decimal import Decimal

from load_mysql import rows_from_csv
from build_powerbi import DATASETS


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"


def read_csv(name):
    with (DATA / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class ProjectChecks(unittest.TestCase):
    def test_months_and_latest_volume(self):
        months = read_csv("market_month.csv")
        self.assertEqual(len(months), 48)
        self.assertEqual(months[0]["date"], "2022-01-01")
        self.assertEqual(months[-1]["date"], "2025-12-01")
        self.assertGreater(float(months[-1]["reported_volume_mn"]), 20000)

    def test_app_rows_reconcile_to_market(self):
        app_totals = defaultdict(float)
        for row in read_csv("app_month.csv"):
            app_totals[row["date"]] += float(row["volume_mn"])
        for month in read_csv("market_month.csv"):
            self.assertAlmostEqual(app_totals[month["date"]], float(month["reported_volume_mn"]), places=2)

    def test_market_share_is_complete(self):
        shares = defaultdict(float)
        for row in read_csv("leaders_month.csv"):
            shares[row["date"]] += float(row["share"])
        self.assertEqual(len(shares), 48)
        for share in shares.values():
            self.assertAlmostEqual(share, 1, delta=.000003)

    def test_mysql_loader_preserves_types_and_missing_values(self):
        fields, rows = rows_from_csv(DATA / "app_month.csv")
        self.assertEqual(len(rows), 3509)
        first = dict(zip(fields, rows[0]))
        self.assertIsInstance(first["date"], date)
        self.assertIsInstance(first["volume_mn"], Decimal)
        self.assertTrue(any(row[fields.index("value_cr")] is None for row in rows))

    def test_powerbi_snapshot_contains_the_prepared_rows(self):
        tables = ROOT / "powerbi" / "UPI Market Analysis.SemanticModel" / "definition" / "tables"
        archive = ROOT / "powerbi" / "UPI Market Analysis - Power BI project.zip"
        for dataset in DATASETS:
            with self.subTest(table=dataset.name):
                path = tables / f"{dataset.name}.tmdl"
                if path.is_file():
                    definition = path.read_text(encoding="utf-8")
                else:
                    with zipfile.ZipFile(archive) as package:
                        definition = package.read(
                            f"UPI Market Analysis.SemanticModel/definition/tables/{dataset.name}.tmdl"
                        ).decode("utf-8").replace("\r\n", "\n")
                self.assertNotIn("MySQL.Database", definition)
                csv_expression = definition.split("CsvText = ", 1)[1].split(",\n\t\t\t\t    Rows =", 1)[0]
                chunks = re.findall(r'"((?:[^"]|"")*)"', csv_expression)
                actual = "".join(chunk.replace('""', '"') for chunk in chunks).replace("#(lf)", "\n")
                expected = (DATA / f"{dataset.sql_table}.csv").read_text(encoding="utf-8").replace("\r\n", "\n")
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
