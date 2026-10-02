"""Checks that the source parsing and dashboard figures agree."""

import csv
import sqlite3
import unittest
from collections import defaultdict
from pathlib import Path


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

    def test_sql_queries_run(self):
        with sqlite3.connect(DATA / "upi_market.sqlite") as connection:
            text = (ROOT / "analysis.sql").read_text(encoding="utf-8")
            queries = [part for part in text.split(";") if "SELECT" in part.upper()]
            self.assertEqual(len(queries), 7)
            for query in queries:
                self.assertTrue(connection.execute(query).fetchall())


if __name__ == "__main__":
    unittest.main()
