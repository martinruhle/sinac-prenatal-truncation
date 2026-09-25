-- The records the ETL cannot load as they are. Any of them stops the run before a CDM table is
-- written, and scripts/etl.py rolls the transaction back, so the previous load stays in place
-- (D-075). The first ten are listed with their year and source_row, and `total` counts them all.
--   - A delivery date that is not a valid dd/mm/yyyy. The observation period and every event
--     are dated by it (D-062, D-063), and no rule for its absence has been decided. None occurs
--     in 2020-2023 (docs/omop_mapping.md rule 2).
--   - A source_row that person_id cannot hold: at most 10,000,000 - 1 rows per year (D-059).
--   - A raw value longer than the CDM field that keeps it verbatim (D-067): value_source_value
--     and location_source_value are varchar(50), country_source_value varchar(80), in the OMOP CDM
--     v5.4 DDL. The INSERT would fail on it, and a cast would cut it short without a word.
SELECT source_year, source_row, problem, count(*) OVER () AS total
FROM (
    SELECT
        source_year,
        source_row,
        'FECHANACIMIENTO ' || coalesce(quote_literal(fechanacimiento), 'blank')
        || ' is not a valid dd/mm/yyyy date' AS problem
    FROM pg_temp.records
    WHERE delivery_date IS NULL
    UNION ALL
    SELECT source_year, source_row, 'source_row does not fit person_id (D-059)'
    FROM pg_temp.records
    WHERE source_row NOT BETWEEN 1 AND 9999999
    UNION ALL
    SELECT source_year, source_row, 'EDADGESTACIONAL is longer than 50 characters'
    FROM pg_temp.records
    WHERE length(edadgestacional) > 50
    UNION ALL
    SELECT source_year, source_row, 'PRODUCTOEMBARAZO is longer than 50 characters'
    FROM pg_temp.records
    WHERE length(productoembarazo) > 50
    UNION ALL
    SELECT source_year, source_row, 'TOTALCONSULTAS is longer than 50 characters'
    FROM pg_temp.records
    WHERE length(totalconsultas) > 50
    UNION ALL
    SELECT source_year, source_row, 'TRIMESTREPRIMERCONSULTA is longer than 50 characters'
    FROM pg_temp.records
    WHERE length(trimestreprimerconsulta) > 50
    UNION ALL
    SELECT source_year, source_row, 'RESIDEEXTRANJERO is longer than 80 characters'
    FROM pg_temp.records
    WHERE length(resideextranjero) > 80
    UNION ALL
    SELECT
        source_year,
        source_row,
        'RESIDEEXTRANJERO|ENTIDADRESIDENCIA is longer than 50 characters'
    FROM pg_temp.records
    WHERE coalesce(length(resideextranjero), 0) + 1 + coalesce(length(entidadresidencia), 0) > 50
) AS problems
ORDER BY source_year, source_row, problem
LIMIT 10;
