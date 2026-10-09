-- PERSON: two rows per staged record whose mother's year of birth is known (D-060), the mother and
-- the newborn (D-103). docs/omop_mapping.md §PERSON.
--
-- The mother is one PERSON per certificate, not per woman (D-051).
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

-- The newborn: loaded with its mother only, since FACT_RELATIONSHIP links the two. It was born on
-- the delivery date, so its date of birth is complete in every record. The hour is not used
-- (D-063), and the residence the certificate records is the mother's, so neither is written. Its
-- person_source_value is the mother's: both come from the same row of the file.
INSERT INTO @cdm_schema.person (
    person_id,
    gender_concept_id,
    year_of_birth,
    month_of_birth,
    day_of_birth,
    race_concept_id,
    ethnicity_concept_id,
    person_source_value,
    gender_source_value,
    gender_source_concept_id
)
SELECT
    r.newborn_person_id::integer,
    r.newborn_gender_concept_id,
    extract(YEAR FROM r.delivery_date)::integer,
    extract(MONTH FROM r.delivery_date)::integer,
    extract(DAY FROM r.delivery_date)::integer,
    0,
    0,
    r.source_year || ':' || r.source_row,
    r.sexo,
    -- The source value is a local code with no concept of its own: 0 (rule 4, D-074).
    0
FROM pg_temp.records AS r
WHERE r.loaded;
