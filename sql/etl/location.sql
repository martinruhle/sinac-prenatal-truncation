-- LOCATION: the residence of the mother, one row per distinct pair (RESIDEEXTRANJERO,
-- ENTIDADRESIDENCIA) of the loaded records, with the id records.sql numbered it with
-- (docs/omop_mapping.md §LOCATION, D-068). Residence, not place of delivery, defines the cohort
-- (D-057).
--   country_concept_id  the target of RESIDEEXTRANJERO in SINAC20_RESEXT: Mexico for 2 "NO"
--                       (does not reside abroad), 0 for every other code and for any value the
--                       catalogue does not publish
--   state               the two-digit code of ENTIDADRESIDENCIA; NULL for its codes 00, 88, 99
--   *_source_value      verbatim; the pair as '<RESIDEEXTRANJERO>|<ENTIDADRESIDENCIA>'
INSERT INTO @cdm_schema.location (
    location_id,
    state,
    location_source_value,
    country_concept_id,
    country_source_value
)
SELECT DISTINCT
    r.location_id::integer,
    r.state,
    CASE
        WHEN r.resideextranjero IS NOT NULL OR r.entidadresidencia IS NOT NULL
            THEN coalesce(r.resideextranjero, '') || '|' || coalesce(r.entidadresidencia, '')
    END,
    r.country_concept_id,
    r.resideextranjero
FROM pg_temp.records AS r
WHERE r.loaded;
