-- PERSON: the mother, one row per staged record whose mother's year of birth is known (D-060).
-- One PERSON per certificate, not per woman (D-051). docs/omop_mapping.md §PERSON.
INSERT INTO @cdm_schema.person (
    person_id,
    gender_concept_id,
    year_of_birth,
    month_of_birth,
    day_of_birth,
    race_concept_id,
    ethnicity_concept_id,
    location_id,
    person_source_value
)
SELECT
    r.person_id::integer,
    (SELECT c.concept_id FROM @results_schema.concept_sets AS c WHERE c.concept_key = 'female'),
    r.year_of_birth,
    r.month_of_birth,
    r.day_of_birth,
    -- race and ethnicity: 0, "No matching concept", written as OMOP writes it (D-061, D-074).
    0,
    0,
    r.location_id::integer,
    r.source_year || ':' || r.source_row
FROM pg_temp.records AS r
WHERE r.loaded;
