"""Generate an editable Power BI Project (PBIP) backed by MySQL."""

from __future__ import annotations

import json
import uuid
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
BASE = ROOT / "powerbi"
NAME = "UPI Market Analysis"
REPORT = BASE / f"{NAME}.Report"
MODEL = BASE / f"{NAME}.SemanticModel"
SCHEMA_ROOT = "https://developer.microsoft.com/json-schemas/fabric/item"
TABLES = {
    "MarketMonthly": (
        "market_month.csv",
        [("date", "dateTime", "type date"), ("year", "int64", "Int64.Type"),
         ("month", "int64", "Int64.Type"), ("reported_volume_mn", "double", "type number"),
         ("listed_apps", "int64", "Int64.Type"), ("top3_share", "double", "type number"),
         ("phonepe_share", "double", "type number"), ("googlepay_share", "double", "type number"),
         ("paytm_share", "double", "type number"), ("missing_value_apps", "int64", "Int64.Type")],
        [
            ("Reported Volume (Mn)", "SUM(MarketMonthly[reported_volume_mn])", "#,0"),
            ("Top Three Share", "MAX(MarketMonthly[top3_share])", "0.0%"),
            ("Latest Reported Volume (Mn)", "CALCULATE(MAX(MarketMonthly[reported_volume_mn]), MarketMonthly[date] = MAXX(ALL(MarketMonthly), MarketMonthly[date]))", "#,0"),
            ("Latest Top Three Share", "CALCULATE(MAX(MarketMonthly[top3_share]), MarketMonthly[date] = MAXX(ALL(MarketMonthly), MarketMonthly[date]))", "0.0%"),
            ("Latest PhonePe Share", "CALCULATE(MAX(MarketMonthly[phonepe_share]), MarketMonthly[date] = MAXX(ALL(MarketMonthly), MarketMonthly[date]))", "0.0%"),
            ("Latest Google Pay Share", "CALCULATE(MAX(MarketMonthly[googlepay_share]), MarketMonthly[date] = MAXX(ALL(MarketMonthly), MarketMonthly[date]))", "0.0%"),
        ],
    ),
    "LeadersMonthly": (
        "leaders_month.csv",
        [("date", "dateTime", "type date"), ("year", "int64", "Int64.Type"),
         ("app_group", "string", "type text"), ("volume_mn", "double", "type number"),
         ("share", "double", "type number")],
        [("App Share", "MAX(LeadersMonthly[share])", "0.0%")],
    ),
    "LeadersYear": (
        "leaders_year.csv",
        [("year", "int64", "Int64.Type"), ("app_group", "string", "type text"),
         ("volume_mn", "double", "type number"), ("share", "double", "type number")],
        [("Annual App Volume (Mn)", "SUM(LeadersYear[volume_mn])", "#,0")],
    ),
    "Seasonality": (
        "seasonality.csv",
        [("month", "int64", "Int64.Type"), ("month_name", "string", "type text"),
         ("mean_reported_volume_mn", "double", "type number"),
         ("years_observed", "int64", "Int64.Type")],
        [("Mean Monthly Volume (Mn)", "SUM(Seasonality[mean_reported_volume_mn])", "#,0")],
    ),
}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def q(value: str) -> str:
    return f"'{value}'" if " " in value or "-" in value else value


def table_tmdl(name: str, table_name: str, columns: list, measures: list,
               server: str, database: str) -> str:
    lines = [f"table {name}", ""]
    for label, expression, fmt in measures:
        lines += [f"\tmeasure {q(label)} = {expression}", f"\t\tformatString: {fmt}", ""]
    for field, kind, _ in columns:
        lines += [f"\tcolumn {field}", f"\t\tdataType: {kind}",
                  f"\t\tsummarizeBy: {'none' if kind in ('string', 'dateTime') else 'sum'}",
                  f"\t\tsourceColumn: {field}", ""]
    column_types = ", ".join(f'{{"{field}", {power_type}}}' for field, _, power_type in columns)
    mysql_query = f"SELECT * FROM {table_name}"
    lines += [f"\tpartition {name} = m", "\t\tmode: import", "\t\tsource =",
              "\t\t\t\tlet",
              f'\t\t\t\t    Source = MySQL.Database({json.dumps(server)}, {json.dumps(database)}, [Query={json.dumps(mysql_query)}]),',
              f'\t\t\t\t    Typed = Table.TransformColumnTypes(Source, {{{column_types}}})',
              "\t\t\t\tin", "\t\t\t\t    Typed", ""]
    return "\n".join(lines)


def build_model(server: str, database: str) -> None:
    write_json(MODEL / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(uuid.NAMESPACE_DNS, "upi.market.analysis.model"))},
    })
    write_json(MODEL / "definition.pbism", {
        "$schema": f"{SCHEMA_ROOT}/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {},
    })
    definition = MODEL / "definition"
    definition.mkdir(parents=True, exist_ok=True)
    (definition / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1550\n", encoding="utf-8")
    model = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
             "\tsourceQueryCulture: en-US", ""]
    model += [f"ref table {name}" for name in TABLES]
    (definition / "model.tmdl").write_text("\n".join(model) + "\n", encoding="utf-8")
    for name, (file_name, columns, measures) in TABLES.items():
        path = definition / "tables" / f"{name}.tmdl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(table_tmdl(name, file_name.removesuffix(".csv"), columns, measures,
                                   server, database), encoding="utf-8")


def field(table: str, property_name: str, kind: str) -> dict:
    return {kind: {"Expression": {"SourceRef": {"Entity": table}}, "Property": property_name}}


def projection(table: str, property_name: str, kind: str) -> dict:
    query_ref = f"{table}.{property_name}"
    return {"field": field(table, property_name, kind), "queryRef": query_ref,
            "nativeQueryRef": property_name}


def visual(name: str, visual_type: str, x: int, y: int, w: int, h: int,
           category: tuple | None = None, measure: tuple | None = None,
           series: tuple | None = None) -> dict:
    item = {
        "$schema": f"{SCHEMA_ROOT}/report/definition/visualContainer/2.2.0/schema.json",
        "name": name, "position": {"x": x, "y": y, "z": 1, "height": h, "width": w},
        "visual": {"visualType": visual_type},
    }
    state = {}
    if category:
        state["Category"] = {"projections": [projection(*category)]}
    if measure:
        state["Values" if visual_type == "card" else "Y"] = {"projections": [projection(*measure)]}
    if series:
        state["Series"] = {"projections": [projection(*series)]}
    if state:
        item["visual"]["query"] = {"queryState": state}
    return item


def textbox(name: str, text: str, x: int, y: int, w: int, h: int, size: int) -> dict:
    item = visual(name, "textbox", x, y, w, max(h, int(size * 1.6 + 17)))
    item["visual"]["objects"] = {"general": [{"properties": {"paragraphs": [{
        "textRuns": [{"value": text, "textStyle": {
            "fontFamily": "Segoe UI", "fontSize": f"{size}pt",
            "fontStyle": "normal", "fontWeight": "bold" if size >= 18 else "normal",
        }}], "horizontalTextAlignment": "left",
    }]}}]}
    return item


PAGES = [
    ("pulse", "Market Overview", [
        textbox("pulse_title", "UPI Market Analysis", 40, 24, 700, 55, 28),
        textbox("pulse_note", "Reported UPI app volumes, January 2022 to December 2025", 42, 90, 1100, 35, 12),
        textbox("pulse_volume_label", "December 2025 volume (million)", 45, 130, 400, 35, 13),
        visual("pulse_volume_card", "card", 45, 168, 350, 110, measure=("MarketMonthly", "Latest Reported Volume (Mn)", "Measure")),
        textbox("pulse_top3_label", "December 2025 top-three share", 445, 130, 400, 35, 13),
        visual("pulse_top3_card", "card", 445, 168, 350, 110, measure=("MarketMonthly", "Latest Top Three Share", "Measure")),
        textbox("pulse_volume_chart_label", "Reported app transactions (million)", 45, 300, 560, 35, 15),
        visual("pulse_volume_chart", "lineChart", 45, 345, 560, 312, category=("MarketMonthly", "date", "Column"), measure=("MarketMonthly", "Reported Volume (Mn)", "Measure")),
        textbox("pulse_concentration_label", "Top-three share over time", 660, 300, 570, 35, 15),
        visual("pulse_concentration", "lineChart", 660, 345, 570, 312, category=("MarketMonthly", "date", "Column"), measure=("MarketMonthly", "Top Three Share", "Measure")),
    ]),
    ("competition", "Competition", [
        textbox("competition_title", "App competition", 40, 24, 700, 55, 28),
        textbox("competition_note", "Share of reported app volume", 42, 90, 750, 35, 12),
        textbox("competition_phonepe_label", "PhonePe share, December 2025", 45, 130, 400, 35, 13),
        visual("competition_phonepe_card", "card", 45, 170, 350, 110, measure=("MarketMonthly", "Latest PhonePe Share", "Measure")),
        textbox("competition_google_label", "Google Pay share, December 2025", 445, 130, 400, 35, 13),
        visual("competition_google_card", "card", 445, 170, 350, 110, measure=("MarketMonthly", "Latest Google Pay Share", "Measure")),
        textbox("competition_share_label", "Leading app shares by month", 45, 300, 550, 35, 15),
        visual("competition_share", "lineChart", 45, 345, 560, 312, category=("LeadersMonthly", "date", "Column"), measure=("LeadersMonthly", "App Share", "Measure"), series=("LeadersMonthly", "app_group", "Column")),
        textbox("competition_volume_label", "Annual app volume by group (million)", 660, 300, 580, 35, 15),
        visual("competition_volume", "clusteredColumnChart", 660, 345, 570, 312, category=("LeadersYear", "year", "Column"), measure=("LeadersYear", "Annual App Volume (Mn)", "Measure"), series=("LeadersYear", "app_group", "Column")),
    ]),
    ("seasonality", "Seasonality", [
        textbox("seasonality_title", "Seasonality", 40, 24, 900, 55, 28),
        textbox("seasonality_note", "Average reported app volume across the four complete years", 42, 90, 900, 35, 12),
        textbox("seasonality_chart_label", "Mean monthly transactions (million)", 45, 140, 700, 35, 15),
        visual("seasonality_chart", "clusteredColumnChart", 45, 180, 1170, 365, category=("Seasonality", "month", "Column"), measure=("Seasonality", "Mean Monthly Volume (Mn)", "Measure")),
        textbox("seasonality_caution1", "Shares use the sum of reported app volumes, not the separate official UPI total.", 45, 570, 1150, 35, 12),
        textbox("seasonality_caution2", "Source: NPCI UPI Ecosystem Statistics. Analysis and report by Rakesh.", 45, 610, 1150, 35, 12),
    ]),
]


def build_report() -> None:
    page_ids = {
        short_name: "ReportSection" + uuid.uuid5(uuid.NAMESPACE_DNS, f"upi.market.analysis.{short_name}").hex[:20]
        for short_name, _, _ in PAGES
    }
    write_json(BASE / f"{NAME}.pbip", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })
    write_json(REPORT / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(uuid.NAMESPACE_DNS, "upi.market.analysis.report"))},
    })
    write_json(REPORT / "definition.pbir", {
        "$schema": f"{SCHEMA_ROOT}/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
    })
    definition = REPORT / "definition"
    write_json(definition / "version.json", {
        "$schema": f"{SCHEMA_ROOT}/report/definition/versionMetadata/1.0.0/schema.json",
        "version": "2.0.0",
    })
    write_json(definition / "report.json", {
        "$schema": f"{SCHEMA_ROOT}/report/definition/report/3.0.0/schema.json",
        "themeCollection": {}, "settings": {"useStylableVisualContainerHeader": True},
    })
    write_json(definition / "pages" / "pages.json", {
        "$schema": f"{SCHEMA_ROOT}/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [page_ids[short_name] for short_name, _, _ in PAGES],
        "activePageName": page_ids["pulse"],
    })
    for short_name, title, visuals in PAGES:
        page_id = page_ids[short_name]
        page_dir = definition / "pages" / page_id
        write_json(page_dir / "page.json", {
            "$schema": f"{SCHEMA_ROOT}/report/definition/page/2.0.0/schema.json",
            "name": page_id, "displayName": title, "displayOption": "FitToPage",
            "height": 720, "width": 1280,
        })
        for item in visuals:
            item["name"] = uuid.uuid5(uuid.NAMESPACE_DNS, f"upi.market.analysis.{short_name}.{item['name']}").hex[:20]
            write_json(page_dir / "visuals" / item["name"] / "visual.json", item)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--database", default="upi_market_analysis")
    args = parser.parse_args()
    server = f"{args.host}:{args.port}"
    for file_name, _, _ in TABLES.values():
        if not (ROOT / "data" / "processed" / file_name).exists():
            raise FileNotFoundError(f"Run build.py first: {file_name}")
    build_model(server, args.database)
    build_report()
    archive = BASE / f"{NAME} - Power BI project.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        for file in BASE.rglob("*"):
            if file.is_file() and file != archive:
                bundle.write(file, file.relative_to(BASE))
    print(f"Built {BASE / (NAME + '.pbip')}")
    print(f"Packaged {archive}")
    print("Power BI Desktop is required to refresh and visually validate the report.")


if __name__ == "__main__":
    main()
