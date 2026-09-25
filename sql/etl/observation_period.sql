-- OBSERVATION_PERIOD: one row per PERSON, and one day long: the delivery (D-062). SINAC observes
-- the pregnancy once, at delivery. A window reaching back by the gestational age would write the
-- outcome into the observed time, and a fixed one would rest on an unsourced constant
-- (docs/omop_mapping.md §OBSERVATION_PERIOD).
INSERT INTO @cdm_schema.observation_period (
    observation_period_id,
    person_id,
    observation_period_start_date,
    observation_period_end_date,
    period_type_concept_id
)
SELECT
    r.person_id::integer,
    r.person_id::integer,
    r.delivery_date,
    r.delivery_date,
    (SELECT c.concept_id FROM @results_schema.concept_sets AS c WHERE c.concept_key = 'registry')
FROM pg_temp.records AS r
WHERE r.loaded;
