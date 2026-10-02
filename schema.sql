CREATE TABLE IF NOT EXISTS app_month (
    date DATE NOT NULL,
    year SMALLINT NOT NULL,
    month TINYINT NOT NULL,
    app VARCHAR(255) NOT NULL,
    volume_mn DECIMAL(18,2) NOT NULL,
    value_cr DECIMAL(20,2) NULL,
    value_complete TINYINT NOT NULL,
    PRIMARY KEY (date, app),
    INDEX ix_app_month_app (app)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS market_month (
    date DATE NOT NULL PRIMARY KEY,
    year SMALLINT NOT NULL,
    month TINYINT NOT NULL,
    reported_volume_mn DECIMAL(18,2) NOT NULL,
    listed_apps SMALLINT NOT NULL,
    top3_share DECIMAL(12,6) NOT NULL,
    phonepe_share DECIMAL(12,6) NOT NULL,
    googlepay_share DECIMAL(12,6) NOT NULL,
    paytm_share DECIMAL(12,6) NOT NULL,
    missing_value_apps SMALLINT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS leaders_month (
    date DATE NOT NULL,
    year SMALLINT NOT NULL,
    app_group VARCHAR(40) NOT NULL,
    volume_mn DECIMAL(18,2) NOT NULL,
    share DECIMAL(12,6) NOT NULL,
    PRIMARY KEY (date, app_group)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS leaders_year (
    year SMALLINT NOT NULL,
    app_group VARCHAR(40) NOT NULL,
    volume_mn DECIMAL(18,2) NOT NULL,
    share DECIMAL(12,6) NOT NULL,
    PRIMARY KEY (year, app_group)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS seasonality (
    month TINYINT NOT NULL PRIMARY KEY,
    month_name VARCHAR(3) NOT NULL,
    mean_reported_volume_mn DECIMAL(18,2) NOT NULL,
    years_observed TINYINT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
