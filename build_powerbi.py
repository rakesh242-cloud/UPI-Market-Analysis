"""Create Rakesh's UPI Market Analysis Power BI project from MySQL tables."""
from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "powerbi"
TITLE = "UPI Market Analysis"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item"
NAMESPACE = uuid.UUID("ce1270df-ec51-47f8-8d90-b516757b70ae")


def stable_id(label: str) -> str:
    return uuid.uuid5(NAMESPACE, label).hex[:20]


def put_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def schema(kind: str, version: str) -> str:
    return f"{SCHEMA}/{kind}/{version}/schema.json"


@dataclass(frozen=True)
class Dataset:
    name: str
    sql_table: str
    columns: tuple[tuple[str, str, str], ...]
    measures: tuple[tuple[str, str, str], ...]


DATASETS = (
    Dataset("Market", "market_month", (
        ("date", "dateTime", "type date"), ("year", "int64", "Int64.Type"),
        ("month", "int64", "Int64.Type"), ("reported_volume_mn", "double", "type number"),
        ("listed_apps", "int64", "Int64.Type"), ("top3_share", "double", "type number"),
        ("phonepe_share", "double", "type number"),
        ("googlepay_share", "double", "type number"),
        ("paytm_share", "double", "type number"),
        ("missing_value_apps", "int64", "Int64.Type"),
    ), (
        ("Transactions (Mn)", "SUM(Market[reported_volume_mn])", "#,0"),
        ("Peak Month (Mn)", "MAX(Market[reported_volume_mn])", "#,0"),
        ("Top Three %", "AVERAGE(Market[top3_share])", "0.0%"),
        ("Active Apps", "AVERAGE(Market[listed_apps])", "#,0"),
    )),
    Dataset("Competitors", "leaders_month", (
        ("date", "dateTime", "type date"), ("year", "int64", "Int64.Type"),
        ("app_group", "string", "type text"), ("volume_mn", "double", "type number"),
        ("share", "double", "type number"),
    ), (
        ("App Transactions (Mn)", "SUM(Competitors[volume_mn])", "#,0"),
        ("Average Share", "AVERAGE(Competitors[share])", "0.0%"),
    )),
    Dataset("AppLedger", "app_month", (
        ("date", "dateTime", "type date"), ("year", "int64", "Int64.Type"),
        ("month", "int64", "Int64.Type"), ("app", "string", "type text"),
        ("volume_mn", "double", "type number"), ("value_cr", "double", "type number"),
        ("value_complete", "int64", "Int64.Type"),
    ), (("App Volume (Mn)", "SUM(AppLedger[volume_mn])", "#,0"),)),
    Dataset("SeasonalPattern", "seasonality", (
        ("month", "int64", "Int64.Type"), ("month_name", "string", "type text"),
        ("mean_reported_volume_mn", "double", "type number"),
        ("years_observed", "int64", "Int64.Type"),
    ), (("Typical Month (Mn)", "SUM(SeasonalPattern[mean_reported_volume_mn])", "#,0"),)),
)


def tmdl(dataset: Dataset, server: str, database: str) -> str:
    lines = [f"table {dataset.name}", ""]
    for label, dax, display in dataset.measures:
        lines.extend((f"\tmeasure '{label}' = {dax}", f"\t\tformatString: {display}", ""))
    for label, dtype, _ in dataset.columns:
        lines.extend((f"\tcolumn {label}", f"\t\tdataType: {dtype}",
                      "\t\tsummarizeBy: none", f"\t\tsourceColumn: {label}", ""))
    types = ", ".join(f'{{"{name}", {mtype}}}' for name, _, mtype in dataset.columns)
    lines.extend((f"\tpartition {dataset.name} = m", "\t\tmode: import", "\t\tsource =",
                  "\t\t\t\tlet",
                  f'\t\t\t\t    Rows = MySQL.Database({json.dumps(server)}, {json.dumps(database)}, [Query="SELECT * FROM {dataset.sql_table}"]),',
                  f"\t\t\t\t    Columns = Table.TransformColumnTypes(Rows, {{{types}}})",
                  "\t\t\t\tin", "\t\t\t\t    Columns", ""))
    return "\n".join(lines)


def semantic_model(server: str, database: str) -> None:
    folder = OUTPUT / f"{TITLE}.SemanticModel"
    put_json(folder / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": TITLE},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(NAMESPACE, "model"))},
    })
    put_json(folder / "definition.pbism", {"$schema": schema("semanticModel/definitionProperties", "1.0.0"),
                                           "version": "4.2", "settings": {}})
    definition = folder / "definition"
    definition.mkdir(parents=True, exist_ok=True)
    (definition / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1550\n", encoding="utf-8")
    references = "\n".join(f"ref table {dataset.name}" for dataset in DATASETS)
    (definition / "model.tmdl").write_text(
        "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        f"\tsourceQueryCulture: en-US\n\n{references}\n", encoding="utf-8")
    for dataset in DATASETS:
        path = definition / "tables" / f"{dataset.name}.tmdl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(tmdl(dataset, server, database), encoding="utf-8")


def binding(table: str, item: str, is_measure: bool = False) -> dict:
    kind = "Measure" if is_measure else "Column"
    return {"field": {kind: {"Expression": {"SourceRef": {"Entity": table}}, "Property": item}},
            "queryRef": f"{table}.{item}", "nativeQueryRef": item}


@dataclass
class Sheet:
    name: str
    slug: str
    visuals: list[dict] = field(default_factory=list)

    def add(self, label: str, kind: str, box: tuple[int, int, int, int],
            *, category=None, value=None, series=None, text=None, size=13) -> None:
        x, y, width, height = box
        visual = {"visualType": kind}
        roles = {}
        if category:
            roles["Category" if kind != "slicer" else "Values"] = {"projections": [binding(*category)]}
        if value:
            roles["Values" if kind == "card" else "Y"] = {"projections": [binding(*value)]}
        if series:
            roles["Series"] = {"projections": [binding(*series)]}
        if roles:
            visual["query"] = {"queryState": roles}
            visual["drillFilterOtherVisuals"] = True
        if text is not None:
            visual["objects"] = {"general": [{"properties": {"paragraphs": [{
                "textRuns": [{"value": text, "textStyle": {
                    "fontFamily": "Aptos Display", "fontSize": f"{size}pt",
                    "fontWeight": "bold" if size >= 18 else "normal"}}],
                "horizontalTextAlignment": "left"}]}}]}
        self.visuals.append({
            "$schema": schema("report/definition/visualContainer", "2.2.0"),
            "name": stable_id(f"{self.slug}/{label}"),
            "position": {"x": x, "y": y, "z": len(self.visuals) + 1,
                         "height": height, "width": width},
            "visual": visual,
        })


def report_pages() -> list[Sheet]:
    momentum = Sheet("01  |  Market Momentum", "momentum")
    momentum.add("headline", "textbox", (38, 20, 900, 52), text="UPI Market Analysis", size=30)
    momentum.add("deck", "textbox", (40, 78, 930, 35), text="UPI app transactions from 2022 to 2025", size=13)
    momentum.add("year", "slicer", (1035, 28, 195, 80), category=("Market", "year"))
    momentum.add("total label", "textbox", (45, 130, 340, 30), text="TRANSACTIONS · MILLION", size=12)
    momentum.add("total", "card", (45, 162, 350, 103), value=("Market", "Transactions (Mn)", True))
    momentum.add("peak label", "textbox", (445, 130, 340, 30), text="PEAK MONTH · MILLION", size=12)
    momentum.add("peak", "card", (445, 162, 350, 103), value=("Market", "Peak Month (Mn)", True))
    momentum.add("apps label", "textbox", (845, 130, 350, 30), text="AVERAGE LISTED APPS", size=12)
    momentum.add("apps", "card", (845, 162, 350, 103), value=("Market", "Active Apps", True))
    momentum.add("chart label", "textbox", (45, 293, 950, 36), text="Monthly transactions", size=18)
    momentum.add("volume trend", "areaChart", (45, 336, 1160, 320),
                 category=("Market", "date"), value=("Market", "Transactions (Mn)", True))
    momentum.add("foot", "textbox", (45, 672, 1150, 25),
                 text="Source: NPCI UPI Apps data  •  Transactions shown in millions", size=10)

    landscape = Sheet("02  |  Competitive Landscape", "landscape")
    landscape.add("headline", "textbox", (38, 20, 940, 52), text="The competitive landscape", size=29)
    landscape.add("deck", "textbox", (40, 78, 950, 32),
                  text="Select an app or year to examine how the mix changes", size=13)
    landscape.add("year", "slicer", (1035, 28, 195, 80), category=("Competitors", "year"))
    landscape.add("share label", "textbox", (45, 132, 700, 32), text="Share of reported app volume", size=18)
    landscape.add("share trend", "lineChart", (45, 173, 740, 285),
                  category=("Competitors", "date"), value=("Competitors", "Average Share", True),
                  series=("Competitors", "app_group"))
    landscape.add("mix label", "textbox", (825, 132, 380, 32), text="Volume by app group", size=18)
    landscape.add("app mix", "barChart", (825, 173, 380, 285),
                  category=("Competitors", "app_group"), value=("Competitors", "App Transactions (Mn)", True))
    landscape.add("yearly label", "textbox", (45, 481, 800, 32), text="Annual contribution", size=18)
    landscape.add("annual bars", "clusteredColumnChart", (45, 522, 1160, 151),
                  category=("Competitors", "year"), value=("Competitors", "App Transactions (Mn)", True),
                  series=("Competitors", "app_group"))
    landscape.add("foot", "textbox", (45, 680, 1140, 22),
                  text="Shares use the sum of the apps listed by NPCI each month.", size=10)

    explorer = Sheet("03  |  App Explorer", "explorer")
    explorer.add("headline", "textbox", (38, 20, 900, 52), text="Explore every listed app", size=29)
    explorer.add("deck", "textbox", (40, 78, 950, 32),
                 text="Use the app and year controls to focus the view", size=13)
    explorer.add("year", "slicer", (45, 127, 255, 88), category=("AppLedger", "year"))
    explorer.add("app", "slicer", (328, 127, 410, 88), category=("AppLedger", "app"))
    explorer.add("total", "card", (830, 127, 360, 92), value=("AppLedger", "App Volume (Mn)", True))
    explorer.add("trend label", "textbox", (45, 241, 700, 35), text="Monthly volume for the selected app", size=18)
    explorer.add("trend", "lineChart", (45, 282, 760, 370),
                 category=("AppLedger", "date"), value=("AppLedger", "App Volume (Mn)", True))
    explorer.add("ranking label", "textbox", (840, 241, 350, 35), text="App volume ranking", size=18)
    explorer.add("ranking", "barChart", (840, 282, 355, 370),
                 category=("AppLedger", "app"), value=("AppLedger", "App Volume (Mn)", True))
    explorer.add("foot", "textbox", (45, 670, 1140, 25),
                 text="App names have been standardized for easier comparison. Source: NPCI.", size=10)

    rhythm = Sheet("04  |  Monthly Rhythm", "rhythm")
    rhythm.add("headline", "textbox", (38, 20, 900, 52), text="The monthly rhythm", size=29)
    rhythm.add("deck", "textbox", (40, 78, 1100, 32),
               text="Average reported transactions for each calendar month, 2022–2025", size=13)
    rhythm.add("chart label", "textbox", (45, 135, 950, 35), text="Average volume by month", size=18)
    rhythm.add("bars", "clusteredColumnChart", (45, 185, 1150, 362),
               category=("SeasonalPattern", "month"),
               value=("SeasonalPattern", "Typical Month (Mn)", True))
    rhythm.add("note one", "textbox", (48, 574, 1120, 36),
               text="Each bar averages that month across the four years.", size=13)
    rhythm.add("note two", "textbox", (48, 618, 1120, 36),
               text="These are reported app totals, not NPCI's separate network-wide UPI total.", size=13)
    rhythm.add("foot", "textbox", (45, 674, 1100, 24), text="Data: NPCI  •  Preparation, analysis and report: Rakesh", size=10)
    return [momentum, landscape, explorer, rhythm]


def report_definition() -> None:
    report = OUTPUT / f"{TITLE}.Report"
    definition = report / "definition"
    put_json(OUTPUT / f"{TITLE}.pbip", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{TITLE}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })
    put_json(report / ".platform", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": TITLE},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid5(NAMESPACE, "report"))},
    })
    put_json(report / "definition.pbir", {
        "$schema": schema("report/definitionProperties", "2.0.0"), "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{TITLE}.SemanticModel"}},
    })
    theme_name = "RakeshUPIStudio.json"
    put_json(report / "StaticResources" / "RegisteredResources" / theme_name, {
        "name": theme_name, "dataColors": ["#0A7F86", "#E56D4E", "#334F89", "#E5AF40",
                                            "#48A6A0", "#8D70B1", "#18334B", "#C77759"],
        "background": "#F7F9F9", "foreground": "#17334A", "tableAccent": "#0A7F86",
        "firstLevelElements": "#17334A", "secondLevelElements": "#456171",
        "thirdLevelElements": "#DCE8E8", "fourthLevelElements": "#66808D",
        "secondaryBackground": "#EAF2F1", "good": "#0A7F86",
        "neutral": "#E5AF40", "bad": "#D6645A",
        "textClasses": {
            "title": {"fontFace": "Aptos Display", "fontSize": 14, "color": "#17334A"},
            "label": {"fontFace": "Aptos", "fontSize": 10, "color": "#456171"},
            "callout": {"fontFace": "Aptos Display", "fontSize": 34, "color": "#0A7F86"},
            "header": {"fontFace": "Aptos", "fontSize": 11, "color": "#17334A"},
        },
    })
    put_json(definition / "version.json", {
        "$schema": schema("report/definition/versionMetadata", "1.0.0"), "version": "2.0.0"})
    put_json(definition / "report.json", {
        "$schema": schema("report/definition/report", "3.0.0"),
        "themeCollection": {"customTheme": {"name": theme_name, "type": "RegisteredResources"}},
        "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                              "items": [{"name": theme_name, "path": theme_name,
                                         "type": "CustomTheme"}]}],
        "settings": {"defaultFilterActionIsDataFilter": True,
                     "useStylableVisualContainerHeader": True, "useEnhancedTooltips": True},
    })
    pages = report_pages()
    put_json(definition / "pages" / "pages.json", {
        "$schema": schema("report/definition/pagesMetadata", "1.0.0"),
        "pageOrder": [stable_id(page.slug) for page in pages],
        "activePageName": stable_id(pages[0].slug),
    })
    for page in pages:
        base = definition / "pages" / stable_id(page.slug)
        put_json(base / "page.json", {
            "$schema": schema("report/definition/page", "2.0.0"),
            "name": stable_id(page.slug), "displayName": page.name,
            "displayOption": "FitToPage", "height": 720, "width": 1280,
        })
        for item in page.visuals:
            put_json(base / "visuals" / item["name"] / "visual.json", item)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--database", default="upi_market_analysis")
    args = parser.parse_args()
    for dataset in DATASETS:
        if not (ROOT / "data" / "processed" / f"{dataset.sql_table}.csv").is_file():
            parser.error(f"Run build.py first: missing {dataset.sql_table}.csv")
    semantic_model(f"{args.host}:{args.port}", args.database)
    report_definition()
    archive = OUTPUT / f"{TITLE} - Power BI project.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as zip_file:
        for path in sorted(OUTPUT.rglob("*")):
            if path.is_file() and path != archive:
                zip_file.write(path, path.relative_to(OUTPUT))
        zip_file.write(ROOT / "LICENSE", "LICENSE")
    print(f"Created {OUTPUT / (TITLE + '.pbip')} and {archive}")
    print("Refresh and review the four report pages in Power BI Desktop.")


if __name__ == "__main__":
    main()
