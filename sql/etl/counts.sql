-- What the run counted, into results.etl_counts (tables.sql). Every rule is listed by name, so a
-- rule that met no record still leaves its 0 (D-033, D-075).
--   - Per year of the record files:
--     - `staging rows` counts every staged record: step 0 of the attrition of docs/protocol.md;
--     - `person not_loaded:no_year_of_birth` counts the records without a year of birth for the
--       mother (D-060): step 1;
--     - every other rule counts the loaded records it applied to (records.sql lists the rules);
--     - the `rows` of the four tables keyed by person_id are counted in the tables themselves.
--   - With NULL for the year, the tables built for the whole load: LOCATION, the local
--     vocabularies, SOURCE_TO_CONCEPT_MAP and CDM_SOURCE.
WITH per_year AS (
    SELECT
        source_year,
        count(*) AS staged,
        count(*) FILTER (WHERE NOT loaded) AS not_loaded,
        count(*) FILTER (WHERE year_of_birth_case = 'mother_date') AS yob_mother_date,
        count(*) FILTER (WHERE year_of_birth_case = 'age') AS yob_age,
        count(*) FILTER (WHERE loaded AND weeks_rule = 'value') AS weeks_value,
        count(*) FILTER (WHERE loaded AND weeks_rule = 'code_to_null') AS weeks_code,
        count(*) FILTER (WHERE loaded AND weeks_rule = 'not_integer') AS weeks_not_integer,
        count(*) FILTER (WHERE loaded AND weeks_rule = 'blank') AS weeks_blank,
        count(*) FILTER (WHERE loaded AND plurality_rule = 'value') AS plurality_value,
        count(*) FILTER (WHERE loaded AND plurality_rule = 'code_to_null') AS plurality_code,
        count(*) FILTER (
            WHERE loaded AND plurality_rule = 'not_in_catalogue'
        ) AS plurality_not_in_catalogue,
        count(*) FILTER (WHERE loaded AND plurality_rule = 'blank') AS plurality_blank,
        count(*) FILTER (WHERE loaded AND plurality_at_least) AS plurality_at_least,
        count(*) FILTER (WHERE loaded AND visits_rule = 'value') AS visits_value,
        count(*) FILTER (WHERE loaded AND visits_rule = 'code_to_null') AS visits_code,
        count(*) FILTER (WHERE loaded AND visits_rule = 'not_integer') AS visits_not_integer,
        count(*) FILTER (WHERE loaded AND visits_rule = 'blank') AS visits_blank,
        count(*) FILTER (
            WHERE loaded AND trimester_rule = 'code_to_concept'
        ) AS trimester_concept,
        count(*) FILTER (WHERE loaded AND trimester_rule = 'code_to_0') AS trimester_0,
        count(*) FILTER (
            WHERE loaded AND trimester_rule = 'not_in_catalogue'
        ) AS trimester_not_in_catalogue,
        count(*) FILTER (WHERE loaded AND trimester_rule = 'blank') AS trimester_blank,
        count(*) FILTER (WHERE loaded AND country_rule = 'code_to_concept') AS country_concept,
        count(*) FILTER (WHERE loaded AND country_rule = 'code_to_0') AS country_0,
        count(*) FILTER (
            WHERE loaded AND country_rule = 'not_in_catalogue'
        ) AS country_not_in_catalogue,
        count(*) FILTER (WHERE loaded AND country_rule = 'blank') AS country_blank,
        count(*) FILTER (WHERE loaded AND state_rule = 'value') AS state_value,
        count(*) FILTER (WHERE loaded AND state_rule = 'code_to_null') AS state_code,
        count(*) FILTER (WHERE loaded AND state_rule = 'not_two_digits') AS state_not_two_digits,
        count(*) FILTER (WHERE loaded AND state_rule = 'blank') AS state_blank
    FROM pg_temp.records
    GROUP BY source_year
),

table_rows AS (
    SELECT r.source_year, t.cdm_table, count(*) AS row_count
    FROM (
        SELECT 'person' AS cdm_table, person_id FROM @cdm_schema.person
        UNION ALL
        SELECT 'observation_period', person_id FROM @cdm_schema.observation_period
        UNION ALL
        SELECT 'measurement', person_id FROM @cdm_schema.measurement
        UNION ALL
        SELECT 'observation', person_id FROM @cdm_schema.observation
    ) AS t
    INNER JOIN pg_temp.records AS r ON t.person_id = r.person_id
    GROUP BY r.source_year, t.cdm_table
)

INSERT INTO @results_schema.etl_counts (source_year, cdm_table, rule, row_count)
SELECT p.source_year, v.cdm_table, v.rule, v.row_count
FROM per_year AS p
CROSS JOIN LATERAL (
    VALUES
    ('staging', 'rows', p.staged),
    ('person', 'not_loaded:no_year_of_birth', p.not_loaded),
    ('person', 'year_of_birth:mother_date', p.yob_mother_date),
    ('person', 'year_of_birth:age', p.yob_age),
    ('measurement', 'gestational_age_at_birth:value', p.weeks_value),
    ('measurement', 'gestational_age_at_birth:code_to_null', p.weeks_code),
    ('measurement', 'gestational_age_at_birth:not_integer', p.weeks_not_integer),
    ('measurement', 'gestational_age_at_birth:blank', p.weeks_blank),
    ('measurement', 'birth_plurality:value', p.plurality_value),
    ('measurement', 'birth_plurality:code_to_null', p.plurality_code),
    ('measurement', 'birth_plurality:not_in_catalogue', p.plurality_not_in_catalogue),
    ('measurement', 'birth_plurality:blank', p.plurality_blank),
    ('measurement', 'birth_plurality:at_least', p.plurality_at_least),
    ('observation', 'prenatal_visits_count:value', p.visits_value),
    ('observation', 'prenatal_visits_count:code_to_null', p.visits_code),
    ('observation', 'prenatal_visits_count:not_integer', p.visits_not_integer),
    ('observation', 'prenatal_visits_count:blank', p.visits_blank),
    ('observation', 'first_prenatal_visit_trimester:code_to_concept', p.trimester_concept),
    ('observation', 'first_prenatal_visit_trimester:code_to_0', p.trimester_0),
    (
        'observation',
        'first_prenatal_visit_trimester:not_in_catalogue',
        p.trimester_not_in_catalogue
    ),
    ('observation', 'first_prenatal_visit_trimester:blank', p.trimester_blank),
    ('location', 'country_concept_id:code_to_concept', p.country_concept),
    ('location', 'country_concept_id:code_to_0', p.country_0),
    ('location', 'country_concept_id:not_in_catalogue', p.country_not_in_catalogue),
    ('location', 'country_concept_id:blank', p.country_blank),
    ('location', 'state:value', p.state_value),
    ('location', 'state:code_to_null', p.state_code),
    ('location', 'state:not_two_digits', p.state_not_two_digits),
    ('location', 'state:blank', p.state_blank)
) AS v (cdm_table, rule, row_count)
UNION ALL
SELECT p.source_year, t.cdm_table, 'rows', coalesce(tr.row_count, 0)
FROM per_year AS p
CROSS JOIN (
    VALUES ('person'), ('observation_period'), ('measurement'), ('observation')
) AS t (cdm_table)
LEFT JOIN table_rows AS tr
    ON p.source_year = tr.source_year AND t.cdm_table = tr.cdm_table
UNION ALL
SELECT NULL, 'location', 'rows', count(*) FROM @cdm_schema.location
UNION ALL
SELECT NULL, 'vocabulary', 'rows', count(*)
FROM @cdm_schema.vocabulary
WHERE vocabulary_id IN (SELECT source_vocabulary_id FROM @cdm_schema.source_to_concept_map)
UNION ALL
SELECT NULL, 'source_to_concept_map', 'rows', count(*) FROM @cdm_schema.source_to_concept_map
UNION ALL
SELECT NULL, 'cdm_source', 'rows', count(*) FROM @cdm_schema.cdm_source;
