-- The tables of the cohorts (task 1.5.1). They live in results, not in the CDM: the CDM holds only
-- what the source says, and OHDSI tools write cohorts to a schema of their own.
--
-- cohort: the columns of COHORT in the CDM v5.4, one row per subject of each definition. A subject
--   is a mother PERSON, so one row is one certificate and one pregnancy (D-051); start and end are
--   the delivery day, the only day SINAC observes (D-062).
-- attrition: per definition and per year of the record files, one row per step, a step that
--   removes nobody included (docs/protocol.md §Attrition). Step 0 starts from the files and
--   excludes nobody, so its `excluded` is NULL.
-- exposure: one row per mother PERSON of the record files of the run, with the declared prenatal
--   care and measures (a) and (c) (task 1.6.1, docs/protocol.md §The measures). A value the CDM
--   does not know is NULL; which records are analysed is decided by the cohorts, not here.
--
-- scripts/cohorts.py replaces the rows of the definitions it builds, in one transaction.
CREATE TABLE IF NOT EXISTS @results_schema.cohort (
    cohort_definition_id integer NOT NULL,
    subject_id integer NOT NULL,
    cohort_start_date date NOT NULL,
    cohort_end_date date NOT NULL,
    PRIMARY KEY (cohort_definition_id, subject_id)
);

CREATE TABLE IF NOT EXISTS @results_schema.attrition (
    cohort_definition_id integer NOT NULL,
    source_year integer NOT NULL,
    step integer NOT NULL,
    kind text,
    description text NOT NULL,
    remaining bigint NOT NULL,
    excluded bigint,
    PRIMARY KEY (cohort_definition_id, source_year, step)
);

CREATE TABLE IF NOT EXISTS @results_schema.exposure (
    subject_id integer PRIMARY KEY,
    -- TOTALCONSULTAS: measure (a) per count.
    visits integer,
    -- TRIMESTREPRIMERCONSULTA: 0 "NO RECIBIÓ", or the trimester of the first visit.
    first_visit_trimester integer,
    -- Measure (a): '0', '1-4', '5-7' or '8+'.
    visits_level text,
    -- Measure (c): the first visit was in the first trimester.
    first_trimester_start boolean
);

-- The objects of one run, dropped when it commits:
--   cohort_years   the years of --years, written by scripts/cohorts.py
--   cohort_steps   the steps of each definition after the data-model steps 0 and 1
--   cohort_exits   every subject of each definition, with the first step it fails (NULL: it
--                  stays), which attrition.sql counts
DROP TABLE IF EXISTS pg_temp.cohort_years, pg_temp.cohort_steps, pg_temp.cohort_exits;

CREATE TEMP TABLE cohort_years (source_year integer PRIMARY KEY) ON COMMIT DROP;

CREATE TEMP TABLE cohort_steps (
    cohort_definition_id integer NOT NULL,
    step integer NOT NULL,
    kind text NOT NULL,
    description text NOT NULL,
    PRIMARY KEY (cohort_definition_id, step)
) ON COMMIT DROP;

CREATE TEMP TABLE cohort_exits (
    cohort_definition_id integer NOT NULL,
    source_year integer NOT NULL,
    subject_id integer NOT NULL,
    exit_step integer,
    PRIMARY KEY (cohort_definition_id, subject_id)
) ON COMMIT DROP;
