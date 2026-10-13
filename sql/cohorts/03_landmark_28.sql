-- The landmark cohort of week 28, cohort_definition_id 3, the number of this file (docs/protocol.md
-- §Records analysed, D-087): the analysis cohort, then one step. Measure (d) is measure (a) on its
-- records. It runs after 02_analysis.sql, in the same transaction, and writes:
--   results.cohort         one row per subject of the analysis cohort that passes the step
--   pg_temp.cohort_steps   steps 2 to 9 of the analysis cohort, then step 10
--   pg_temp.cohort_exits   every subject with the first step it fails, NULL when it stays
--
--   step  criterion          in the CDM
--   10    Reached week 28    the gestational age value_as_number is 28 or more
-- The completed weeks at delivery are the only record of how far a pregnancy went, so "reached
-- week 28" is EDADGESTACIONAL >= 28 (D-090). 28 is the WHO bound of extremely preterm birth
-- (docs/protocol.md §The measures). 04_landmark_32.sql and 05_landmark_34.sql are this file with
-- another week.
DELETE FROM @results_schema.cohort WHERE cohort_definition_id = 3;

INSERT INTO @results_schema.cohort (
    cohort_definition_id,
    subject_id,
    cohort_start_date,
    cohort_end_date
)
SELECT
    3,
    c.subject_id,
    c.cohort_start_date,
    c.cohort_end_date
FROM @results_schema.cohort AS c
INNER JOIN pg_temp.base_criteria AS b ON c.subject_id = b.subject_id
WHERE
    c.cohort_definition_id = 2
    AND b.weeks >= 28;

-- The steps of the analysis cohort, then this one. It restricts the cohort through the variable
-- of the outcome, as criterion 6 does: design, not a predictor (rule 3 of CLAUDE.md).
INSERT INTO pg_temp.cohort_steps (cohort_definition_id, step, kind, description)
SELECT
    3,
    s.step,
    s.kind,
    s.description
FROM pg_temp.cohort_steps AS s
WHERE s.cohort_definition_id = 2;

INSERT INTO pg_temp.cohort_steps (cohort_definition_id, step, kind, description)
VALUES (3, 10, 'design', 'Reached week 28');

-- A subject that leaves the analysis cohort leaves this one at the same step; the others leave at
-- step 10 unless they reached the week.
INSERT INTO pg_temp.cohort_exits (cohort_definition_id, source_year, subject_id, exit_step)
SELECT
    3,
    e.source_year,
    e.subject_id,
    CASE
        WHEN e.exit_step IS NOT NULL THEN e.exit_step
        WHEN (b.weeks >= 28) IS NOT TRUE THEN 10
    END
FROM pg_temp.cohort_exits AS e
INNER JOIN pg_temp.base_criteria AS b ON e.subject_id = b.subject_id
WHERE e.cohort_definition_id = 2;
