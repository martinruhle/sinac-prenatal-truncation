-- The attrition of every definition this run built (docs/protocol.md §Attrition, CLAUDE.md rule
-- 5): per definition and per year of the record files of --years, one row per step, a step that
-- removes nobody included. A record that fails several criteria is counted at the first of them.
--   step 0    the records staged from the file: `staging rows` of results.etl_counts
--   step 1    the data model: the records the ETL could not load as a PERSON for lack of the
--             mother's year of birth leave (`person not_loaded:no_year_of_birth`, D-060), and the
--             PERSONs of the file remain. Steps 0 and 1 are the same in every definition.
--   step 2+   the steps of the definition (pg_temp.cohort_steps): each excludes the subjects whose
--             first failed step it is, and the subjects that fail none of it or the steps before
--             remain (pg_temp.cohort_exits).
-- Remaining and excluded are counted apart, so scripts/cohorts.py can check that they agree. At
-- step 1 that crosses the counts of the ETL with the PERSONs of the CDM.
DELETE FROM @results_schema.attrition
WHERE cohort_definition_id IN (SELECT s.cohort_definition_id FROM pg_temp.cohort_steps AS s);

WITH definitions AS (
    SELECT DISTINCT s.cohort_definition_id FROM pg_temp.cohort_steps AS s
),

files AS (
    SELECT
        y.source_year,
        max(c.row_count) FILTER (WHERE c.cdm_table = 'staging' AND c.rule = 'rows') AS staged,
        max(c.row_count) FILTER (
            WHERE c.cdm_table = 'person' AND c.rule = 'not_loaded:no_year_of_birth'
        ) AS not_loaded
    FROM pg_temp.cohort_years AS y
    LEFT JOIN @results_schema.etl_counts AS c ON y.source_year = c.source_year
    GROUP BY y.source_year
),

exits AS (
    SELECT
        e.cohort_definition_id,
        e.source_year,
        e.exit_step,
        count(*) AS subjects
    FROM pg_temp.cohort_exits AS e
    GROUP BY e.cohort_definition_id, e.source_year, e.exit_step
),

loaded AS (
    SELECT
        d.cohort_definition_id,
        f.source_year,
        f.not_loaded,
        coalesce(sum(x.subjects), 0) AS subjects
    FROM definitions AS d
    CROSS JOIN files AS f
    LEFT JOIN exits AS x
        ON d.cohort_definition_id = x.cohort_definition_id AND f.source_year = x.source_year
    GROUP BY d.cohort_definition_id, f.source_year, f.not_loaded
)

INSERT INTO @results_schema.attrition (
    cohort_definition_id,
    source_year,
    step,
    kind,
    description,
    remaining,
    excluded
)
SELECT
    d.cohort_definition_id,
    f.source_year,
    0,
    NULL,
    'Records in the files of the study period',
    f.staged,
    NULL
FROM definitions AS d
CROSS JOIN files AS f
UNION ALL
SELECT
    l.cohort_definition_id,
    l.source_year,
    1,
    'data model',
    'Mother''s year of birth known',
    l.subjects,
    l.not_loaded
FROM loaded AS l
UNION ALL
SELECT
    s.cohort_definition_id,
    y.source_year,
    s.step,
    s.kind,
    s.description,
    coalesce(sum(x.subjects) FILTER (WHERE x.exit_step IS NULL OR x.exit_step > s.step), 0),
    coalesce(sum(x.subjects) FILTER (WHERE x.exit_step = s.step), 0)
FROM pg_temp.cohort_steps AS s
CROSS JOIN pg_temp.cohort_years AS y
LEFT JOIN exits AS x
    ON s.cohort_definition_id = x.cohort_definition_id AND y.source_year = x.source_year
GROUP BY s.cohort_definition_id, y.source_year, s.step, s.kind, s.description;
