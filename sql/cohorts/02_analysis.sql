-- The analysis cohort, cohort_definition_id 2, the number of this file (docs/protocol.md §Records
-- analysed, D-087): the base cohort, then two steps. The four exposure measures and the models
-- are computed on its records, so a difference between two measures is never a difference of
-- population (D-086). It runs after 01_base.sql and exposure.sql, in the same transaction, and
-- writes:
--   results.cohort         one row per subject of the base cohort that passes both steps
--   pg_temp.cohort_steps   steps 2 to 7 of the base cohort, then steps 8 and 9
--   pg_temp.cohort_exits   every subject with the first step it fails, NULL when it stays
--
--   step  criterion                                in the CDM
--   8     Prenatal care data known and coherent    the four rules of §One set of records for the
--                                                  four measures, on results.exposure (D-086):
--                                                  1 the trimester of the first visit is 0 to 3
--                                                  2 the count of visits is known
--                                                  3 the trimester is 0 if and only if the count
--                                                    is 0
--                                                  4 a first visit in the third trimester needs
--                                                    28 completed weeks or more at delivery
--   9     Covariates known                         the declared age has a value (D-100), the
--                                                  education a concept other than 0 (D-101), and
--                                                  LOCATION a state (D-095); the year of the
--                                                  delivery is always known
-- ATENCIONPRENATAL is read by no rule (D-086). As in 01_base.sql, a criterion is met only when it
-- is true, so a NULL never meets one.
DROP TABLE IF EXISTS pg_temp.analysis_criteria;

CREATE TEMP TABLE analysis_criteria ON COMMIT DROP AS
WITH concepts AS (
    SELECT
        max(c.concept_id) FILTER (WHERE c.concept_key = 'mother_age_at_delivery') AS age,
        max(c.concept_id) FILTER (WHERE c.concept_key = 'mother_education') AS education
    FROM @results_schema.concept_sets AS c
)

SELECT
    b.subject_id,
    (
        x.first_visit_trimester IS NOT NULL
        AND x.visits IS NOT NULL
        AND (x.first_visit_trimester = 0) = (x.visits = 0)
        -- 28 completed weeks: the start of the third trimester in docs/protocol.md §Trimester
        -- boundaries (D-092, FOR APPROVAL).
        AND NOT (x.first_visit_trimester = 3 AND b.weeks < 28)
    ) IS TRUE AS prenatal_care_known,
    (
        age.value_as_number IS NOT NULL
        AND education.value_as_concept_id <> 0
        AND l.state IS NOT NULL
    ) IS TRUE AS covariates_known
FROM pg_temp.base_criteria AS b
CROSS JOIN concepts AS c
INNER JOIN @results_schema.exposure AS x ON b.subject_id = x.subject_id
INNER JOIN @cdm_schema.person AS p ON b.subject_id = p.person_id
LEFT JOIN @cdm_schema.measurement AS age
    ON b.subject_id = age.person_id AND c.age = age.measurement_concept_id
LEFT JOIN @cdm_schema.observation AS education
    ON b.subject_id = education.person_id AND c.education = education.observation_concept_id
LEFT JOIN @cdm_schema.location AS l ON p.location_id = l.location_id;

DELETE FROM @results_schema.cohort WHERE cohort_definition_id = 2;

INSERT INTO @results_schema.cohort (
    cohort_definition_id,
    subject_id,
    cohort_start_date,
    cohort_end_date
)
SELECT
    2,
    c.subject_id,
    c.cohort_start_date,
    c.cohort_end_date
FROM @results_schema.cohort AS c
INNER JOIN pg_temp.analysis_criteria AS a ON c.subject_id = a.subject_id
WHERE
    c.cohort_definition_id = 1
    AND a.prenatal_care_known
    AND a.covariates_known;

-- The steps of the base cohort, then the two of this definition (docs/protocol.md §Records
-- analysed). Both ask whether a value the study needs is there and usable: validity.
INSERT INTO pg_temp.cohort_steps (cohort_definition_id, step, kind, description)
SELECT
    2,
    s.step,
    s.kind,
    s.description
FROM pg_temp.cohort_steps AS s
WHERE s.cohort_definition_id = 1;

INSERT INTO pg_temp.cohort_steps (cohort_definition_id, step, kind, description)
VALUES
(2, 8, 'validity', 'Prenatal care data known and coherent'),
(2, 9, 'validity', 'Covariates known');

-- A subject that leaves the base cohort leaves this one at the same step; the others leave at the
-- first of steps 8 and 9 they fail.
INSERT INTO pg_temp.cohort_exits (cohort_definition_id, source_year, subject_id, exit_step)
SELECT
    2,
    e.source_year,
    e.subject_id,
    CASE
        WHEN e.exit_step IS NOT NULL THEN e.exit_step
        WHEN NOT a.prenatal_care_known THEN 8
        WHEN NOT a.covariates_known THEN 9
    END
FROM pg_temp.cohort_exits AS e
INNER JOIN pg_temp.analysis_criteria AS a ON e.subject_id = a.subject_id
WHERE e.cohort_definition_id = 1;
