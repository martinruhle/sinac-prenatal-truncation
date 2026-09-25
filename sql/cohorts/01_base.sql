-- The base cohort, cohort_definition_id 1, the number of this file (docs/protocol.md §Base cohort),
-- with its criteria as steps 2 to 7 of the attrition, in the order of §Attrition (D-056). It reads
-- only the CDM (D-068) and writes:
--   results.cohort         one row per subject that meets every criterion, on its delivery day
--   pg_temp.cohort_steps   its steps, after the data-model steps 0 and 1 of attrition.sql
--   pg_temp.cohort_exits   every subject with the first step it fails, NULL when it stays
--
-- The subjects are the mother PERSONs of the record files of --years (pg_temp.cohort_years). The
-- year of the file is the one person_source_value carries, '<year>:<source_row>' (D-059).
--
-- Each criterion is read as the CDM holds it (docs/omop_mapping.md), and is met only when it is
-- true: a value the CDM does not know, NULL, never meets one, so no record passes a criterion
-- because its value is missing, and every flag below is true or false.
--   step  criterion                        in the CDM
--   2     1 Born in the study period       the year of the delivery is in --years (D-073)
--   3     2 Mother resident in Mexico      LOCATION.country_concept_id is Mexico (D-057)
--   4     3 Gestational age specified      its value_as_number is not NULL: code 99, a blank or
--                                          a value that does not cast (D-067, D-075)
--   5     4 Multiplicity specified         the plurality value_as_number is not NULL
--   6     5 Singleton                      the plurality value_as_number is 1
--   7     6 22 completed weeks or more     the gestational age value_as_number is 22 or more
DROP TABLE IF EXISTS pg_temp.base_criteria;

CREATE TEMP TABLE base_criteria ON COMMIT DROP AS
WITH concepts AS (
    SELECT
        max(c.concept_id) FILTER (WHERE c.concept_key = 'gestational_age_at_birth') AS weeks,
        max(c.concept_id) FILTER (WHERE c.concept_key = 'birth_plurality') AS plurality,
        -- Mexico is the target of RESIDEEXTRANJERO 2, "NO" (does not reside abroad), in the map
        -- the ETL loaded (docs/omop_mapping.md §LOCATION). scripts/cohorts.py checks that there
        -- is exactly one, and that both keys above are in concept_sets, before this runs.
        (
            SELECT m.target_concept_id
            FROM @cdm_schema.source_to_concept_map AS m
            WHERE
                m.source_vocabulary_id = 'SINAC20_RESEXT'
                AND m.source_code = '2'
                AND m.invalid_reason IS NULL
        ) AS mexico
    FROM @results_schema.concept_sets AS c
),

subjects AS (
    SELECT
        p.person_id,
        p.location_id,
        y.source_year
    FROM @cdm_schema.person AS p
    INNER JOIN pg_temp.cohort_years AS y
        ON split_part(p.person_source_value, ':', 1) = y.source_year::text
)

SELECT
    s.person_id AS subject_id,
    s.source_year,
    -- The delivery: every event of a certificate is dated FECHANACIMIENTO (D-063).
    weeks.measurement_date AS delivery_date,
    EXISTS (
        SELECT 1
        FROM pg_temp.cohort_years AS y
        WHERE y.source_year = extract(YEAR FROM weeks.measurement_date)
    ) AS born_in_period,
    (l.country_concept_id = c.mexico) IS TRUE AS resident_in_mexico,
    weeks.value_as_number IS NOT NULL AS weeks_specified,
    plurality.value_as_number IS NOT NULL AS multiplicity_specified,
    -- 1 is "ÚNICO" in the catalogue PRODUCTO_EMBARAZO (D-068).
    (plurality.value_as_number = 1) IS TRUE AS singleton,
    -- 22 completed weeks: NOM-007-SSA2-2016 §3.45 and §3.1 (D-053).
    (weeks.value_as_number >= 22) IS TRUE AS at_least_22_weeks
FROM subjects AS s
CROSS JOIN concepts AS c
LEFT JOIN @cdm_schema.measurement AS weeks
    ON s.person_id = weeks.person_id AND c.weeks = weeks.measurement_concept_id
LEFT JOIN @cdm_schema.measurement AS plurality
    ON s.person_id = plurality.person_id AND c.plurality = plurality.measurement_concept_id
LEFT JOIN @cdm_schema.location AS l ON s.location_id = l.location_id;

DELETE FROM @results_schema.cohort WHERE cohort_definition_id = 1;

-- One row per subject that meets every criterion, from the start to the end of its observation:
-- the delivery day (D-062).
INSERT INTO @results_schema.cohort (
    cohort_definition_id,
    subject_id,
    cohort_start_date,
    cohort_end_date
)
SELECT
    1,
    b.subject_id,
    b.delivery_date,
    b.delivery_date
FROM pg_temp.base_criteria AS b
WHERE
    b.born_in_period
    AND b.resident_in_mexico
    AND b.weeks_specified
    AND b.multiplicity_specified
    AND b.singleton
    AND b.at_least_22_weeks;

-- The kinds and descriptions of docs/protocol.md §Attrition.
INSERT INTO pg_temp.cohort_steps (cohort_definition_id, step, kind, description)
VALUES
(1, 2, 'coverage', 'Born in the study period'),
(1, 3, 'coverage', 'Mother resident in Mexico'),
(1, 4, 'validity', 'Gestational age specified'),
(1, 5, 'validity', 'Multiplicity specified'),
(1, 6, 'design', 'Singleton'),
(1, 7, 'design', '22 completed weeks or more');

-- A subject that fails several criteria leaves at the first of them, in the order of the steps.
INSERT INTO pg_temp.cohort_exits (cohort_definition_id, source_year, subject_id, exit_step)
SELECT
    1,
    b.source_year,
    b.subject_id,
    CASE
        WHEN NOT b.born_in_period THEN 2
        WHEN NOT b.resident_in_mexico THEN 3
        WHEN NOT b.weeks_specified THEN 4
        WHEN NOT b.multiplicity_specified THEN 5
        WHEN NOT b.singleton THEN 6
        WHEN NOT b.at_least_22_weeks THEN 7
    END
FROM pg_temp.base_criteria AS b;
