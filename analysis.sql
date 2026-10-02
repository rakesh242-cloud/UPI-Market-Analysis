-- Rakesh | UPI Market Pulse
-- Units: volume_mn = millions of reported app transactions.
-- Shares use the sum of listed app volume for the same period.

-- 1. Monthly growth compared with the same month one year earlier.
SELECT date, reported_volume_mn,
       ROUND(100.0 * (reported_volume_mn / LAG(reported_volume_mn, 12) OVER (ORDER BY date) - 1), 2) AS yoy_pct
FROM market_month
ORDER BY date;

-- 2. How concentrated is the reported app market?
SELECT year,
       ROUND(AVG(top3_share) * 100, 2) AS average_top3_share_pct,
       ROUND(AVG(listed_apps), 1) AS average_listed_apps
FROM market_month
GROUP BY year
ORDER BY year;

-- 3. Annual competition between the three largest named apps.
SELECT year, app_group,
       ROUND(volume_mn, 2) AS annual_volume_mn,
       ROUND(share * 100, 2) AS reported_app_share_pct
FROM leaders_year
WHERE app_group <> 'All other apps'
ORDER BY year, annual_volume_mn DESC;

-- 4. Latest-month ranking, calculated from the detailed app table.
WITH latest AS (SELECT MAX(date) AS date FROM app_month),
total AS (SELECT SUM(volume_mn) AS volume_mn FROM app_month WHERE date = (SELECT date FROM latest))
SELECT a.date, a.app, ROUND(a.volume_mn, 2) AS volume_mn,
       ROUND(a.volume_mn * 100.0 / t.volume_mn, 2) AS share_pct
FROM app_month a CROSS JOIN total t
WHERE a.date = (SELECT date FROM latest)
ORDER BY a.volume_mn DESC
LIMIT 20;

-- 5. Named apps with the largest absolute growth, 2022 to 2025.
WITH annual AS (
    SELECT year, app, SUM(volume_mn) AS volume_mn
    FROM app_month
    WHERE year IN (2022, 2025) AND LOWER(app) NOT IN ('other', 'others')
    GROUP BY year, app
)
SELECT current.app, ROUND(base.volume_mn, 2) AS volume_2022_mn,
       ROUND(current.volume_mn, 2) AS volume_2025_mn,
       ROUND(current.volume_mn - base.volume_mn, 2) AS increase_mn
FROM annual current JOIN annual base ON current.app = base.app
WHERE current.year = 2025 AND base.year = 2022 AND base.volume_mn >= 10
ORDER BY increase_mn DESC
LIMIT 10;

-- 6. Seasonality after scaling each month by its own year's average.
WITH normalized AS (
    SELECT month, year,
           reported_volume_mn / AVG(reported_volume_mn) OVER (PARTITION BY year) AS index_value
    FROM market_month
)
SELECT month, ROUND(AVG(index_value), 3) AS seasonal_index
FROM normalized
GROUP BY month
ORDER BY month;

-- 7. Missing source transaction-value cells by month.
SELECT date, missing_value_apps
FROM market_month
WHERE missing_value_apps > 0
ORDER BY date;
