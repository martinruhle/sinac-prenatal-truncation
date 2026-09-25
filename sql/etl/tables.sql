-- Tables the ETL keeps outside the CDM (task 1.4.4). Both are emptied and refilled on each run,
-- in the same transaction as the CDM tables.
--
-- concept_sets: the concepts of config/concept_sets.yml, by key. The SQL cites a concept by its
-- key and reads its id from here, so no concept_id is ever written in SQL (CLAUDE.md rule 8,
-- D-074).
--
-- etl_counts: what each run counted, per year of the record files (NULL: the whole load). `rows`
-- is the row count of a table; every other rule counts the records it applied to, zero included,
-- so every cast rule leaves its count (D-033, D-075). The `check` rows are the violations of each
-- post-load check, and a run only commits when all of them are 0 (D-073).
CREATE TABLE IF NOT EXISTS @results_schema.concept_sets (
    concept_key text PRIMARY KEY,
    concept_id integer NOT NULL
);

CREATE TABLE IF NOT EXISTS @results_schema.etl_counts (
    source_year integer,
    cdm_table text NOT NULL,
    rule text NOT NULL,
    row_count bigint NOT NULL,
    UNIQUE NULLS NOT DISTINCT (source_year, cdm_table, rule)
);
