-- The cast step of the ETL (task 1.4.4): the only place where staged text becomes typed values
-- (D-033). It writes one row per staged record, loaded or not, into pg_temp.records, which the
-- other files of sql/etl/ read. scripts/etl.py builds pg_temp.staged_records, the staging tables
-- of the years of the run joined by UNION ALL, before this file runs.
--
-- Every value is tested before it is cast, so no value can abort the load half way:
--   - a date must read dd/mm/yyyy and name a day of the calendar (pg_input_is_valid, PostgreSQL
--     16), so 31/02/2023 is refused rather than raised;
--   - a number must be digits only. The pattern also refuses the blanks and the sign that a plain
--     cast to integer accepts (' 7', '+7').
--
-- Each value column records the rule it met, and counts.sql counts every rule, zero included
-- (docs/omop_mapping.md rule 3, D-067, D-075):
--   blank             the cell is empty: NULL value and NULL source value
--   code_to_null      a code of the column's vocabulary in source_to_concept_map, for a numeric
--                     field: NULL
--   code_to_concept   a code whose target is a concept: that concept
--   code_to_0         a code whose target is 0 (a flavor of null, or no standard concept): 0
--   value             anything else that casts: the value itself
--   not_integer       a count or a number of weeks that is not digits only: NULL
--   not_in_catalogue  a coded value its catalogue does not publish: NULL for a number, 0 for a
--                     concept
--   not_two_digits    a state that is not a two-digit code: NULL
-- The raw value always stays in the source field, so every rule can be reversed.
DROP TABLE IF EXISTS pg_temp.records;

CREATE TEMP TABLE records ON COMMIT DROP AS
WITH parsed AS (
    SELECT
        s.*,
        -- D-059: (year - 2000) x 10,000,000 + source_row. bigint until unloadable.sql has
        -- checked that it fits the integer columns of the CDM.
        (s.source_year - 2000)::bigint * 10000000 + s.source_row AS person_id,
        CASE
            WHEN s.fechanacimiento ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'
                AND pg_input_is_valid(iso.delivery, 'date')
                THEN iso.delivery::date
        END AS delivery_date,
        CASE
            WHEN mother_code.source_code IS NULL
                AND s.fechanacimientomadre ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'
                AND pg_input_is_valid(iso.mother, 'date')
                THEN iso.mother::date
        END AS mother_birth_date,
        CASE
            WHEN age_code.source_code IS NULL
                AND s.edad ~ '^[0-9]+$'
                AND pg_input_is_valid(s.edad, 'integer')
                THEN s.edad::integer
        END AS mother_age,
        weeks_code.source_code IS NOT NULL AS weeks_is_code,
        plurality_code.source_code IS NOT NULL AS plurality_is_code,
        visits_code.source_code IS NOT NULL AS visits_is_code,
        trimester_code.target_concept_id AS trimester_target,
        country_code.target_concept_id AS country_target,
        state_code.source_code IS NOT NULL AS state_is_code
    FROM pg_temp.staged_records AS s
    CROSS JOIN LATERAL (
        SELECT
            substr(s.fechanacimiento, 7, 4) || '-' || substr(s.fechanacimiento, 4, 2) || '-'
            || substr(s.fechanacimiento, 1, 2) AS delivery,
            substr(s.fechanacimientomadre, 7, 4) || '-' || substr(s.fechanacimientomadre, 4, 2)
            || '-' || substr(s.fechanacimientomadre, 1, 2) AS mother
    ) AS iso
    LEFT JOIN @cdm_schema.source_to_concept_map AS mother_code
        ON mother_code.source_vocabulary_id = 'SINAC20_FECHANACMAD'
        AND mother_code.source_code = s.fechanacimientomadre
        AND mother_code.invalid_reason IS NULL
    LEFT JOIN @cdm_schema.source_to_concept_map AS age_code
        ON age_code.source_vocabulary_id = 'SINAC20_EDAD'
        AND age_code.source_code = s.edad
        AND age_code.invalid_reason IS NULL
    LEFT JOIN @cdm_schema.source_to_concept_map AS weeks_code
        ON weeks_code.source_vocabulary_id = 'SINAC20_EDADGEST'
        AND weeks_code.source_code = s.edadgestacional
        AND weeks_code.invalid_reason IS NULL
    LEFT JOIN @cdm_schema.source_to_concept_map AS plurality_code
        ON plurality_code.source_vocabulary_id = 'SINAC20_PRODEMB'
        AND plurality_code.source_code = s.productoembarazo
        AND plurality_code.invalid_reason IS NULL
    LEFT JOIN @cdm_schema.source_to_concept_map AS visits_code
        ON visits_code.source_vocabulary_id = 'SINAC20_TOTCONS'
        AND visits_code.source_code = s.totalconsultas
        AND visits_code.invalid_reason IS NULL
    LEFT JOIN @cdm_schema.source_to_concept_map AS trimester_code
        ON trimester_code.source_vocabulary_id = 'SINAC20_TRIMCONS'
        AND trimester_code.source_code = s.trimestreprimerconsulta
        AND trimester_code.invalid_reason IS NULL
    LEFT JOIN @cdm_schema.source_to_concept_map AS country_code
        ON country_code.source_vocabulary_id = 'SINAC20_RESEXT'
        AND country_code.source_code = s.resideextranjero
        AND country_code.invalid_reason IS NULL
    LEFT JOIN @cdm_schema.source_to_concept_map AS state_code
        ON state_code.source_vocabulary_id = 'SINAC20_ENTRES'
        AND state_code.source_code = s.entidadresidencia
        AND state_code.invalid_reason IS NULL
),

ruled AS (
    SELECT
        p.*,
        -- The year of birth of the mother, D-060: (1) her date of birth, when it precedes the
        -- delivery; (2) otherwise the year of delivery minus her age; (3) otherwise none, and
        -- the record is not loaded as a PERSON.
        CASE
            WHEN p.mother_birth_date < p.delivery_date THEN 'mother_date'
            WHEN p.mother_age IS NOT NULL AND p.delivery_date IS NOT NULL THEN 'age'
        END AS year_of_birth_case,
        CASE
            WHEN p.edadgestacional IS NULL THEN 'blank'
            WHEN p.weeks_is_code THEN 'code_to_null'
            WHEN p.edadgestacional ~ '^[0-9]+$' THEN 'value'
            ELSE 'not_integer'
        END AS weeks_rule,
        CASE
            WHEN p.productoembarazo IS NULL THEN 'blank'
            WHEN p.plurality_is_code THEN 'code_to_null'
            -- 1 "ÚNICO", 2 "GEMELAR", 3 "TRES O MÁS": the answers of the catalogue
            -- PRODUCTO_EMBARAZO (docs/omop_mapping.md §MEASUREMENT, D-068).
            WHEN p.productoembarazo IN ('1', '2', '3') THEN 'value'
            ELSE 'not_in_catalogue'
        END AS plurality_rule,
        CASE
            WHEN p.totalconsultas IS NULL THEN 'blank'
            WHEN p.visits_is_code THEN 'code_to_null'
            WHEN p.totalconsultas ~ '^[0-9]+$' THEN 'value'
            ELSE 'not_integer'
        END AS visits_rule,
        CASE
            WHEN p.trimestreprimerconsulta IS NULL THEN 'blank'
            WHEN p.trimester_target = 0 THEN 'code_to_0'
            WHEN p.trimester_target IS NOT NULL THEN 'code_to_concept'
            ELSE 'not_in_catalogue'
        END AS trimester_rule,
        CASE
            WHEN p.resideextranjero IS NULL THEN 'blank'
            WHEN p.country_target = 0 THEN 'code_to_0'
            WHEN p.country_target IS NOT NULL THEN 'code_to_concept'
            ELSE 'not_in_catalogue'
        END AS country_rule,
        CASE
            WHEN p.entidadresidencia IS NULL THEN 'blank'
            WHEN p.state_is_code THEN 'code_to_null'
            WHEN p.entidadresidencia ~ '^[0-9]{2}$' THEN 'value'
            ELSE 'not_two_digits'
        END AS state_rule
    FROM parsed AS p
)

SELECT
    r.source_year,
    r.source_row,
    r.person_id,
    r.fechanacimiento,
    r.delivery_date,
    r.year_of_birth_case IS NOT NULL AS loaded,
    r.year_of_birth_case,
    CASE r.year_of_birth_case
        WHEN 'mother_date' THEN extract(YEAR FROM r.mother_birth_date)::integer
        WHEN 'age' THEN extract(YEAR FROM r.delivery_date)::integer - r.mother_age
    END AS year_of_birth,
    CASE
        WHEN r.year_of_birth_case = 'mother_date'
            THEN extract(MONTH FROM r.mother_birth_date)::integer
    END AS month_of_birth,
    CASE
        WHEN r.year_of_birth_case = 'mother_date'
            THEN extract(DAY FROM r.mother_birth_date)::integer
    END AS day_of_birth,
    -- One LOCATION per distinct residence pair of the loaded records, numbered in code order
    -- (docs/omop_mapping.md rule 7). The "C" collation keeps the order, and so the ids, the
    -- same whatever the locale of the database.
    CASE
        WHEN r.year_of_birth_case IS NOT NULL THEN dense_rank() OVER (
            PARTITION BY r.year_of_birth_case IS NOT NULL
            ORDER BY
                r.resideextranjero COLLATE "C" NULLS LAST,
                r.entidadresidencia COLLATE "C" NULLS LAST
        )
    END AS location_id,
    r.resideextranjero,
    r.country_rule,
    CASE r.country_rule
        WHEN 'code_to_concept' THEN r.country_target
        WHEN 'code_to_0' THEN 0
        WHEN 'not_in_catalogue' THEN 0
    END AS country_concept_id,
    r.entidadresidencia,
    r.state_rule,
    CASE WHEN r.state_rule = 'value' THEN r.entidadresidencia END AS state,
    r.edadgestacional,
    r.weeks_rule,
    CASE WHEN r.weeks_rule = 'value' THEN r.edadgestacional::numeric END AS weeks,
    r.productoembarazo,
    r.plurality_rule,
    CASE WHEN r.plurality_rule = 'value' THEN r.productoembarazo::numeric END AS plurality,
    -- 3 means "three or more", so its value carries the operator ">=" (D-068).
    r.plurality_rule = 'value' AND r.productoembarazo = '3' AS plurality_at_least,
    r.totalconsultas,
    r.visits_rule,
    CASE WHEN r.visits_rule = 'value' THEN r.totalconsultas::numeric END AS visits,
    r.trimestreprimerconsulta,
    r.trimester_rule,
    CASE r.trimester_rule
        WHEN 'code_to_concept' THEN r.trimester_target
        WHEN 'code_to_0' THEN 0
        WHEN 'not_in_catalogue' THEN 0
    END AS trimester_concept_id
FROM ruled AS r;
