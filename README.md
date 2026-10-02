# UPI Market Analysis

**Python · MySQL · Power BI**

This project looks at how India's UPI app market changed from January 2022 to December 2025. Python prepares the monthly app data published by [NPCI](https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics), MySQL holds the analysis tables, and Power BI brings the results together in an interactive report.

## In the report

- **Market Momentum** tracks monthly transaction volume.
- **Competitive Landscape** compares the leading apps and their market shares.
- **App Explorer** lets you filter by app and year.
- **Monthly Rhythm** shows how volume varies across the calendar year.

The report has year and app filters, and charts on the same page respond to selections. Download the [Power BI project](powerbi/UPI%20Market%20Analysis%20-%20Power%20BI%20project.zip), extract it, and open `UPI Market Analysis.pbip` in Power BI Desktop.

## Data notes

The dataset covers 48 monthly NPCI **UPI Apps** workbooks. Monthly volume is the sum of the apps listed in each workbook, which can differ from NPCI's separate network-wide UPI total. App shares use that monthly app sum as the denominator.

The preparation step combines duplicate app rows and standardizes a few name variants. A dash in the source is read as zero; an unreadable value cell stays missing. The original NPCI workbooks are not included here.

## Files

| File | What it does |
| --- | --- |
| [Complete project download](UPI%20Market%20Analysis%20-%20Source.zip) | All project files in one ZIP |
| [`build.py`](build.py) | Prepares six CSV tables from the monthly workbooks |
| [`load_mysql.py`](load_mysql.py) and [`schema.sql`](schema.sql) | Loads five analysis tables into MySQL |
| [`analysis.sql`](analysis.sql) | Queries for volume, app share, and trends |
| [`build_powerbi.py`](build_powerbi.py) | Creates the Power BI project and its MySQL connection |
| [`data/processed/`](data/processed/) | Prepared CSV data |
| [`test_project.py`](test_project.py) | Checks the prepared data |

## Getting started

1. Install Python 3.10+, MySQL Server 8.0+, Power BI Desktop, and [MySQL Connector/NET](https://learn.microsoft.com/en-us/power-query/connectors/mysql-database#prerequisites). Install the Python packages with `python -m pip install -r requirements.txt`.
2. The prepared CSVs are included. To rebuild them, download the monthly UPI Apps workbooks from [NPCI](https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics) into `data/raw/`. Keep filenames ending in `YYYY-Mon.xlsx`, then run `python build.py --source data/raw`.
3. Set `UPI_MYSQL_PASSWORD` in your environment, or enter the password when prompted. Run `python load_mysql.py --host localhost --port 3306 --database upi_market_analysis --user root`.
4. Run `python build_powerbi.py --host localhost --port 3306 --database upi_market_analysis` if you need to change the connection settings. Otherwise, use the included Power BI project ZIP.
5. Open the extracted `.pbip` file in Power BI Desktop, sign in to MySQL with **Database** authentication, and refresh the report.
6. Run `python -m unittest -v test_project.py` to check the prepared data.

Keep MySQL passwords out of the project files. The Python loader reads a password from the environment or a hidden prompt; Power BI Desktop stores its connection credentials separately.

## Source and license

Project owner: **Rakesh**. The code and report files are covered by the [MIT license](LICENSE). The underlying UPI statistics come from [NPCI](https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics).

The Power BI project files were generated and checked for structure, but the report still needs a refresh and visual review in Power BI Desktop with a live MySQL connection.
