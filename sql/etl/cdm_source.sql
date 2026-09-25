-- CDM_SOURCE: one row describing the load (docs/omop_mapping.md §CDM_SOURCE). What varies with
-- the run (the files loaded, their retrieval date, the commit) comes from pg_temp.etl_run, which
-- scripts/etl.py writes from config/sources.yml and git.
INSERT INTO @cdm_schema.cdm_source (
    cdm_source_name,
    cdm_source_abbreviation,
    cdm_holder,
    source_description,
    source_documentation_reference,
    cdm_etl_reference,
    source_release_date,
    cdm_release_date,
    cdm_version,
    cdm_version_concept_id,
    vocabulary_version
)
SELECT
    'SINAC live-birth certificates, SSA/DGIS open data',
    'SINAC-DGIS',
    'sinac-prenatal-truncation',
    run.source_description,
    run.source_documentation_reference,
    run.cdm_etl_reference,
    run.source_release_date,
    current_date,
    'v5.4.3',
    (
        SELECT c.concept_id FROM @results_schema.concept_sets AS c
        WHERE c.concept_key = 'cdm_version'
    ),
    (SELECT v.vocabulary_version FROM @cdm_schema.vocabulary AS v WHERE v.vocabulary_id = 'None')
FROM pg_temp.etl_run AS run;
