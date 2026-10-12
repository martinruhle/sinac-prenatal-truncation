-- Measures (a) and (c) of docs/protocol.md §The measures (task 1.6.1), for every subject of
-- 01_base.sql: the mother PERSONs of the record files of --years. It reads the two OBSERVATION
-- rows of the declared prenatal care (D-065) and writes results.exposure, one row per subject.
-- No date of a visit is read: SINAC records none (rule 4 of CLAUDE.md, D-066).
--
-- A value the CDM does not know stays NULL here, and so does every measure built on it:
--   visits                 the count, value_as_number; NULL for code 99, a blank or a value
--                          that does not cast (D-067, D-075)
--   first_visit_trimester  0 to 3, the code of the catalogue TRIMESTRE_PRIMER_CONSULTA whose
--                          concept value_as_concept_id holds; NULL for codes 8 and 9, a blank or
--                          an uncatalogued code, which the ETL wrote as concept 0 or NULL
-- Whether the two agree is a criterion of the analysis cohort (02_analysis.sql), not a rule of
-- the measures: a record whose data are incoherent keeps its measures here and leaves there.
DELETE FROM @results_schema.exposure;

WITH concepts AS (
    SELECT
        max(c.concept_id) FILTER (WHERE c.concept_key = 'prenatal_visits_count') AS visits,
        max(c.concept_id) FILTER (
            WHERE c.concept_key = 'first_prenatal_visit_trimester'
        ) AS trimester
    FROM @results_schema.concept_sets AS c
),

-- The concept of each trimester is the target of its code in the map the ETL loaded, so no
-- concept_id is written here (rule 8, D-076). Codes 0 "NO RECIBIÓ", 1, 2 and 3 are the answers
-- of the catalogue; scripts/cohorts.py checks that each maps to exactly one concept other than 0
-- before this runs.
trimesters AS (
    SELECT
        m.source_code::integer AS trimester,
        m.target_concept_id
    FROM @cdm_schema.source_to_concept_map AS m
    WHERE
        m.source_vocabulary_id = 'SINAC20_TRIMCONS'
        AND m.source_code IN ('0', '1', '2', '3')
        AND m.invalid_reason IS NULL
),

declared AS (
    SELECT
        b.subject_id,
        visits.value_as_number::integer AS visits,
        t.trimester
    FROM pg_temp.base_criteria AS b
    CROSS JOIN concepts AS c
    LEFT JOIN @cdm_schema.observation AS visits
        ON b.subject_id = visits.person_id AND c.visits = visits.observation_concept_id
    LEFT JOIN @cdm_schema.observation AS first_visit
        ON b.subject_id = first_visit.person_id AND c.trimester = first_visit.observation_concept_id
    LEFT JOIN trimesters AS t ON first_visit.value_as_concept_id = t.target_concept_id
)

INSERT INTO @results_schema.exposure (
    subject_id,
    visits,
    first_visit_trimester,
    visits_level,
    first_trimester_start
)
SELECT
    d.subject_id,
    d.visits,
    d.trimester,
    -- Measure (a), D-088: no care; below the minimum of five visits; below the calendar of
    -- eight; the full calendar. Five and eight are NOM-007-SSA2-2016 §5.2.1.15, copied in
    -- config/nom007_schedule.yml as minimum_visits and its eight visits.
    CASE
        WHEN d.visits = 0 THEN '0'
        WHEN d.visits < 5 THEN '1-4'
        WHEN d.visits < 8 THEN '5-7'
        WHEN d.visits >= 8 THEN '8+'
    END,
    -- Measure (c), D-089: the first trimester against 0 "NO RECIBIÓ", 2 and 3.
    d.trimester = 1
FROM declared AS d;
