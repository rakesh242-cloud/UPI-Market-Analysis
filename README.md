# Rakesh UPI Market Pulse

An interactive analysis of India's UPI app market by **Rakesh**. The project turns monthly app statistics from the [National Payments Corporation of India (NPCI)](https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics) into a browser dashboard, a Power BI project, reusable data tables, and SQL analysis.

**Explore the dashboard:** open [`docs/index.html`](docs/index.html) in a browser. It is a single, self-contained file and also works with GitHub Pages.

Use the period selector and month slider to change the entire view. Play the timeline, click a chart month, toggle app lines, or click an annual bar to jump to that year. The ranking follows the selected month.

## What the analysis shows

- Reported monthly transaction volume from January 2022 through December 2025
- Monthly share of PhonePe, Google Pay, and Paytm, plus their combined share
- Annual app mix, a ranking that follows the selected month, and normalized seasonality
- Seven SQL queries covering year-over-year growth, concentration, rankings, seasonality, and data quality

The dashboard uses the transaction **volume** reported in the app-level NPCI workbooks. Its totals are sums of listed apps, so they should not be read as the entire UPI network total. A dash in the source is treated as zero; unreadable value cells stay missing. App names with obvious variations are normalized, and repeated app rows within a month are combined. Share is calculated against all listed apps in that month. The source workbooks remain available from NPCI; they are not redistributed in this repository.

## Contents

| Path | Purpose |
| --- | --- |
| [`docs/index.html`](docs/index.html) | Standalone interactive dashboard for GitHub Pages |
| [`dashboard/template.html`](dashboard/template.html) | Dashboard source |
| [`powerbi/Rakesh UPI Market Pulse.pbip`](powerbi/Rakesh%20UPI%20Market%20Pulse.pbip) | Power BI Desktop project with three report pages |
| [`data/processed/`](data/processed/) | Clean CSV tables and SQLite database |
| [`analysis.sql`](analysis.sql) | Reusable analytical queries |
| [`build.py`](build.py), [`make_dashboard.py`](make_dashboard.py), [`build_powerbi.py`](build_powerbi.py) | Rebuild scripts |
| [`test_project.py`](test_project.py) | Data reconciliation and query checks |

## Rebuild from NPCI workbooks

1. Download the monthly **UPI Apps** Excel workbooks from the [NPCI UPI ecosystem statistics page](https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics) into one folder. This edition uses the 48 months from January 2022 to December 2025. Preserve filenames ending in `YYYY-Mon.xlsx` (for example, `2025-Dec.xlsx`).
2. Install Python 3.10+ and the dependency: `python -m pip install -r requirements.txt`.
3. Run `python build.py --source path/to/workbooks`.
4. Run `python make_dashboard.py` and `python build_powerbi.py`.
5. Run `python -m unittest -v test_project.py` to check the output.

The processed data and ready-to-use dashboard are included for readers who just want to explore the results. After moving the project to a different computer, rerun `build_powerbi.py` before opening the `.pbip` file so its CSV paths point to the new location. Open the `.pbip` file in Power BI Desktop and refresh the model.

## Publish the dashboard with GitHub Pages

In the GitHub repository, choose **Settings → Pages → Deploy from a branch**, select the default branch and the `/docs` folder, then save. The published site uses `docs/index.html`.

## Authorship and source

Analysis, data preparation, SQL, dashboard, and Power BI report by **Rakesh**. Source data: [NPCI UPI ecosystem statistics](https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics). See [LICENSE](LICENSE) for the license on this project's original code and report assets.
