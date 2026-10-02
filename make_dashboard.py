"""Embed the processed tables into a standalone, GitHub Pages-ready dashboard."""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TABLES = {
    "monthly": "market_month.csv",
    "leaders": "leaders_month.csv",
    "apps": "app_month.csv",
    "yearly": "leaders_year.csv",
}


def read_table(file_name):
    with (ROOT / "data" / "processed" / file_name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main():
    data = {key: read_table(file_name) for key, file_name in TABLES.items()}
    template = (ROOT / "dashboard" / "template.html").read_text(encoding="utf-8")
    output = template.replace("/* DATA_GOES_HERE */", "const DATA = " + json.dumps(data, separators=(",", ":")) + ";")
    target = ROOT / "dashboard" / "index.html"
    target.write_text(output, encoding="utf-8")
    pages = ROOT / "docs" / "index.html"
    pages.parent.mkdir(parents=True, exist_ok=True)
    pages.write_text(output, encoding="utf-8")
    print(f"Built {target}")
    print(f"Built {pages} for GitHub Pages")


if __name__ == "__main__":
    main()
