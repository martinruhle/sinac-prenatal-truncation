-- MEASUREMENT: two rows per PERSON, in this order: gestational age at delivery, then plurality
-- (docs/omop_mapping.md §MEASUREMENT, D-064, D-068). Both are dated on the delivery (D-063), and
-- a missing value keeps its row, with the raw value in value_source_value (D-067, D-075).
WITH concepts AS (
    SELECT
        max(concept_id) FILTER (WHERE concept_key = 'registry') AS registry,
        max(concept_id) FILTER (WHERE concept_key = 'gestational_age_at_birth') AS weeks,
        max(concept_id) FILTER (WHERE concept_key = 'week') AS week,
        max(concept_id) FILTER (WHERE concept_key = 'birth_plurality') AS plurality,
        max(concept_id) FILTER (WHERE concept_key = 'at_least') AS at_least
    FROM @results_schema.concept_sets
),

events AS (
    SELECT
        r.person_id,
        1 AS position,
        c.weeks AS concept_id,
        r.delivery_date,
        NULL::integer AS operator_concept_id,
        r.weeks AS value_as_number,
        c.week AS unit_concept_id,
        'EDADGESTACIONAL' AS source_value,
        r.edadgestacional AS value_source_value
    FROM pg_temp.records AS r
    CROSS JOIN concepts AS c
    WHERE r.loaded
    UNION ALL
    SELECT
        r.person_id,
        2 AS position,
        c.plurality,
        r.delivery_date,
        CASE WHEN r.plurality_at_least THEN c.at_least END,
        r.plurality,
        NULL::integer,
        'PRODUCTOEMBARAZO',
        r.productoembarazo
    FROM pg_temp.records AS r
    CROSS JOIN concepts AS c
    WHERE r.loaded
)

INSERT INTO @cdm_schema.measurement (
    measurement_id,
    person_id,
    measurement_concept_id,
    measurement_date,
    measurement_type_concept_id,
    operator_concept_id,
    value_as_number,
    unit_concept_id,
    measurement_source_value,
    measurement_source_concept_id,
    value_source_value
)
SELECT
    row_number() OVER (ORDER BY e.person_id, e.position)::integer,
    e.person_id::integer,
    e.concept_id,
    e.delivery_date,
    c.registry,
    e.operator_concept_id,
    e.value_as_number,
    e.unit_concept_id,
    e.source_value,
    -- The source value is a column name, not a code of any vocabulary: 0 (rule 4, D-074).
    0,
    e.value_source_value
FROM events AS e
CROSS JOIN concepts AS c;
