# UPI Market Analysis

**Python · MySQL · Power BI**

An analysis of India's UPI app market by Rakesh. Python prepares monthly app statistics from the [National Payments Corporation of India (NPCI)](https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics), loads five tables into MySQL, and feeds an interactive four-page Power BI report. The report is the only dashboard in this project.

## What the report shows

- **Market Momentum:** monthly volume and yearly selection
- **Competitive Landscape:** app shares, annual contributions, and cross-filtered selections
- **App Explorer:** app and year controls with volume trends and rankings
- **Monthly Rhythm:** four-year calendar-month averages

The figures are sums of the apps listed in NPCI's monthly workbooks, **not** the separate UPI network total. A dash in the source is treated as zero; unreadable value cells stay missing. Obvious app-name variants are normalized, and repeated app rows within a month are combined. Share uses all listed apps in that month as its denominator.

## Project files

| Path | Purpose |
| --- | --- |
| [Complete project ZIP](UPI%20Market%20Analysis%20-%20Rakesh%20Source.zip) | Clean source snapshot without prior Git history |
| [Power BI project ZIP](powerbi/UPI%20Market%20Analysis%20-%20Power%20BI%20project.zip) | Downloadable Power BI project; extract it before opening the `.pbip` file |
| [`build.py`](build.py) | Clean NPCI Excel workbooks into six reusable CSV tables |
| [`load_mysql.py`](load_mysql.py) and [`schema.sql`](schema.sql) | Create and populate the MySQL database |
| [`build_powerbi.py`](build_powerbi.py) | Generate Rakesh's four-page Power BI report and color theme with a MySQL connection |
| [`analysis.sql`](analysis.sql) | Seven MySQL analytical queries |
| [`data/processed/`](data/processed/) | Prepared CSV data for reproducibility |
| [`test_project.py`](test_project.py) | Data reconciliation and loader checks |

## Run the project

1. Install Python 3.10+, MySQL Server 8.0+, Power BI Desktop, and [Oracle MySQL Connector/NET](https://learn.microsoft.com/en-us/power-query/connectors/mysql-database#prerequisites). Install Python packages with `python -m pip install -r requirements.txt`.
2. The prepared CSVs are included. To rebuild them, download the monthly **UPI Apps** workbooks from [NPCI](https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics) into `data/raw/` and run `python build.py --source data/raw`. This edition uses 48 months; keep filenames ending in `YYYY-Mon.xlsx`.
3. Set your MySQL password in the `UPI_MYSQL_PASSWORD` environment variable, or let the loader prompt for it. Run `python load_mysql.py --host localhost --port 3306 --database upi_market_analysis --user root`. The loader creates the database and tables, then replaces the table rows in one transaction. Use a MySQL account with database-creation rights on the first run.
4. Run `python build_powerbi.py --host localhost --port 3306 --database upi_market_analysis`. The script creates the project and ZIP in `powerbi/`. If the files already exist, this step is needed only when changing the MySQL host, port, or database name.
5. Open `powerbi/UPI Market Analysis.pbip` in Power BI Desktop. Choose **Database** authentication for the MySQL connection, enter your MySQL credentials, and refresh the report. Browse **Market Momentum**, **Competitive Landscape**, **App Explorer**, and **Monthly Rhythm**. Use slicers and select chart marks to filter related visuals on a page.
6. Run `python -m unittest -v test_project.py` to check the prepared data.

Do not put a MySQL password into the project files. The Python loader reads it from the environment or a hidden prompt; Power BI Desktop stores its connection credentials separately. For a MySQL server on another computer, use its hostname in both commands.

## Data and authorship

The Python pipeline, MySQL workflow, SQL analysis, Power BI generator, report structure, and theme in this version were created for **Rakesh**. This project's code is licensed under [MIT](LICENSE) in Rakesh's name. The underlying UPI statistics are from [NPCI UPI ecosystem statistics](https://www.npci.org.in/what-we-do/upi/upi-ecosystem-statistics); Rakesh does not claim ownership of NPCI's source data. The original workbooks are not redistributed.

The Power BI project uses Microsoft's public [PBIR report format](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report). The files can be edited in Power BI Desktop after refresh. Power BI Desktop and a live MySQL connection are required for a final visual check; the project generator and data checks can run without them.
