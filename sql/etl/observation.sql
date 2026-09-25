-- OBSERVATION: two rows per PERSON, in this order: the declared count of prenatal visits, then
-- the trimester of the first visit (docs/omop_mapping.md §OBSERVATION, D-065). The count is one
-- row, never one visit per declared consultation, and no VISIT_OCCURRENCE is written (D-066).
-- Both are dated on the delivery (D-063); a missing value keeps its row (D-067, D-075).
WITH concepts AS (
    SELECT
        max(concept_id) FILTER (WHERE concept_key = 'registry') AS registry,
        max(concept_id) FILTER (WHERE concept_key = 'prenatal_visits_count') AS visits,
        max(concept_id) FILTER (WHERE concept_key = 'first_prenatal_visit_trimester') AS trimester
    FROM @results_schema.concept_sets
),

events AS (
    SELECT
        r.person_id,
        1 AS position,
        c.visits AS concept_id,
        r.delivery_date,
        r.visits AS value_as_number,
        NULL::integer AS value_as_concept_id,
        'TOTALCONSULTAS' AS source_value,
        r.totalconsultas AS value_source_value
    FROM pg_temp.records AS r
    CROSS JOIN concepts AS c
    WHERE r.loaded
    UNION ALL
    SELECT
        r.person_id,
        2 AS position,
        c.trimester,
        r.delivery_date,
        NULL::numeric,
        r.trimester_concept_id,
        'TRIMESTREPRIMERCONSULTA',
        r.trimestreprimerconsulta
    FROM pg_temp.records AS r
    CROSS JOIN concepts AS c
    WHERE r.loaded
)

INSERT INTO @cdm_schema.observation (
    observation_id,
    person_id,
    observation_concept_id,
    observation_date,
    observation_type_concept_id,
    value_as_number,
    value_as_concept_id,
    observation_source_value,
    observation_source_concept_id,
    value_source_value
)
SELECT
    row_number() OVER (ORDER BY e.person_id, e.position)::integer,
    e.person_id::integer,
    e.concept_id,
    e.delivery_date,
    c.registry,
    e.value_as_number,
    e.value_as_concept_id,
    e.source_value,
    -- The source value is a column name, not a code of any vocabulary: 0 (rule 4, D-074).
    0,
    e.value_source_value
FROM events AS e
CROSS JOIN concepts AS c;
