-- Rows counted at each stage of staging a year's record file (task 1.2.4, D-069).
--
-- One row per year and stage: `csv` is Python's own count of the extracted CSV, `parquet` the
-- rows of the Parquet copy DuckDB wrote, `table` the rows of the staging table. A load is only
-- committed when the three agree, and it replaces the rows of its year. No timestamp is kept, so
-- staging the same file twice leaves identical rows.
CREATE TABLE IF NOT EXISTS @staging_schema.load_counts (
    source_year integer NOT NULL,
    stage text NOT NULL CHECK (stage IN ('csv', 'parquet', 'table')),
    row_count bigint NOT NULL,
    source_member text NOT NULL,
    source_sha256 text NOT NULL,
    PRIMARY KEY (source_year, stage)
);
