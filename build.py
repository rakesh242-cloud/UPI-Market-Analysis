"""Prepare month, app, ranking and seasonality tables from NPCI UPI Apps files."""
from __future__ import annotations

import argparse
import csv
import re
from calendar import month_abbr
from collections import defaultdict
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

HOME = Path(__file__).resolve().parent
DEST = HOME / "data" / "processed"
APP_ALIASES = {"phone pe": "PhonePe", "phonepe": "PhonePe", "paytm payments bank app": "Paytm",
               "paytm (ocl)": "Paytm", "paytm (ocl )": "Paytm",
               "cred": "CRED", "whatsapp": "WhatsApp Pay"}
LEADERS = ("PhonePe", "Google Pay", "Paytm")


def as_number(value):
    text = "" if value is None else str(value).strip().replace(",", "")
    if not text or set(text) == {"#"}:
        return None
    return 0.0 if text in {"-", "–", "—"} else float(text)


def read_month(path):
    match = re.search(r"(20\d{2})-([A-Za-z]{3})\.xlsx$", path.name, re.I)
    if not match:
        raise ValueError(f"Expected YYYY-Mon in {path.name}")
    month_codes = {label.lower(): i for i, label in enumerate(month_abbr) if label}
    period = date(int(match[1]), month_codes[match[2].lower()], 1)
    book = load_workbook(path, read_only=True, data_only=True)
    found = []
    total_at = None
    try:
        for line, cells in enumerate(book.active.iter_rows(values_only=True), 1):
            if total_at is None:
                labels = [str(cell).strip() if cell is not None else "" for cell in cells]
                if "Application Name" in labels:
                    total_at = labels.index("Total")
                continue
            if not cells or cells[0] is None or not re.fullmatch(r"\d+(?:\.0)?", str(cells[0]).strip()):
                continue
            if len(cells) <= total_at + 1 or cells[1] is None:
                raise ValueError(f"Incomplete source row {path.name}:{line}")
            volume = as_number(cells[total_at])
            if volume is None:
                raise ValueError(f"Unreadable volume at {path.name}:{line}")
            label = re.sub(r"\s*#\s*$", "", str(cells[1]).strip())
            found.append((period, APP_ALIASES.get(label.lower(), label), volume,
                          as_number(cells[total_at + 1])))
    finally:
        book.close()
    if not found:
        raise ValueError(f"No app entries in {path.name}")
    return found


def prepare(files):
    records = defaultdict(list)
    for path in files:
        for period, app, volume, value in read_month(path):
            records[(period, app)].append((volume, value))
    periods = {period for period, _ in records}
    if len(periods) != len(files):
        raise ValueError("Expected one workbook for each month")

    app_rows = []
    by_period = defaultdict(list)
    for (period, app), amounts in sorted(records.items()):
        complete = all(value is not None for _, value in amounts)
        row = {"date": period.isoformat(), "year": period.year, "month": period.month,
               "app": app, "volume_mn": round(sum(volume for volume, _ in amounts), 2),
               "value_cr": round(sum(value for _, value in amounts if value is not None), 2) if complete else None,
               "value_complete": int(complete)}
        app_rows.append(row)
        by_period[period].append(row)

    monthly, leader_rows = [], []
    for period, members in sorted(by_period.items()):
        total = sum(row["volume_mn"] for row in members)
        if total <= 0:
            raise ValueError(f"No reported volume for {period}")
        volumes = {row["app"]: row["volume_mn"] for row in members}
        named = sorted((row["volume_mn"] for row in members
                        if row["app"].lower() not in {"other", "others"}), reverse=True)
        monthly.append({"date": period.isoformat(), "year": period.year, "month": period.month,
                        "reported_volume_mn": round(total, 2), "listed_apps": len(named),
                        "top3_share": round(sum(named[:3]) / total, 6),
                        "phonepe_share": round(volumes.get("PhonePe", 0) / total, 6),
                        "googlepay_share": round(volumes.get("Google Pay", 0) / total, 6),
                        "paytm_share": round(volumes.get("Paytm", 0) / total, 6),
                        "missing_value_apps": sum(1 for row in members if not row["value_complete"])})
        leader_total = 0
        for app in LEADERS:
            amount = volumes.get(app, 0)
            leader_total += amount
            leader_rows.append({"date": period.isoformat(), "year": period.year,
                                "app_group": app, "volume_mn": round(amount, 2),
                                "share": round(amount / total, 6)})
        remainder = total - leader_total
        leader_rows.append({"date": period.isoformat(), "year": period.year,
                            "app_group": "All other apps", "volume_mn": round(remainder, 2),
                            "share": round(remainder / total, 6)})

    annual_groups = defaultdict(float)
    annual_totals = defaultdict(float)
    for row in leader_rows:
        annual_groups[(row["year"], row["app_group"])] += row["volume_mn"]
        annual_totals[row["year"]] += row["volume_mn"]
    annual = [{"year": year, "app_group": app, "volume_mn": round(amount, 2),
               "share": round(amount / annual_totals[year], 6)}
              for (year, app), amount in sorted(annual_groups.items())]

    seasonal_groups = defaultdict(list)
    for row in monthly:
        seasonal_groups[row["month"]].append(row["reported_volume_mn"])
    seasonal = [{"month": month, "month_name": month_abbr[month],
                 "mean_reported_volume_mn": round(sum(values) / len(values), 2),
                 "years_observed": len(values)}
                for month, values in sorted(seasonal_groups.items())]
    newest = max(by_period)
    ranked = sorted(by_period[newest], key=lambda row: row["volume_mn"], reverse=True)[:20]
    total = next(row["reported_volume_mn"] for row in monthly if row["date"] == newest.isoformat())
    top20 = [{"rank": rank, "app": row["app"], "volume_mn": row["volume_mn"],
              "share": round(row["volume_mn"] / total, 6), "date": newest.isoformat()}
             for rank, row in enumerate(ranked, 1)]
    return {"app_month.csv": app_rows, "market_month.csv": monthly,
            "leaders_month.csv": leader_rows, "leaders_year.csv": annual,
            "seasonality.csv": seasonal, "latest_top20.csv": top20}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=HOME / "data" / "raw")
    paths = sorted(parser.parse_args().source.glob("*.xlsx"))
    if not paths:
        raise FileNotFoundError("No NPCI .xlsx workbooks found")
    DEST.mkdir(parents=True, exist_ok=True)
    for filename, rows in prepare(paths).items():
        with (DEST / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=tuple(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(f"Prepared {len(paths)} months from NPCI workbooks")


if __name__ == "__main__":
    main()
