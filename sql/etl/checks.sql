-- The checks that run after the load (task 1.4.4, docs/omop_mapping.md §What the next tasks take
-- from here). Each one counts what breaks one rule, into results.etl_counts as `check` rows, and
-- scripts/etl.py commits the load only when every count is 0 (D-073). Foreign keys are not applied
-- (D-032), so the referential rules are anti-joins here.
--
--   concept_not_in_vocabulary:<table>  distinct concept ids written to the table that CONCEPT
--                                      does not hold
--   orphan_person:<table>              rows whose person_id, or one of the two fact ids of
--                                      FACT_RELATIONSHIP, is not a PERSON
--   orphan_location:person             PERSON rows whose location_id is not a LOCATION
--   person_without_one_observation_period
--                                      PERSON rows without exactly one observation period
--   mother_without_*                   mother PERSONs without the three rows each of
--                                      MEASUREMENT and OBSERVATION
--   newborn_without_one_measurement, newborn_with_an_observation
--                                      newborn PERSONs without exactly one MEASUREMENT row, their
--                                      weight, or with an OBSERVATION row (D-103, D-105)
--   observation_period_not_the_delivery_day
--                                      periods longer than one day, or on another day than the
--                                      delivery of their record (D-062)
--   newborn_birth_not_the_delivery_day newborn PERSONs whose date of birth is not the delivery
--                                      date of their record (D-103)
--   fact_relationship_not_the_record_pair
--                                      rows missing from, or added to, the two rows that link the
--                                      mother and the newborn of each loaded record (D-104)
--   event_outside_observation_period:<table>
--                                      events dated outside their person's observation period
--                                      (D-063)
--   visit_occurrence_rows              the slice writes no visit (D-066)
--   vocabulary_not_registered          source vocabularies of the map missing from VOCABULARY
--   person_not_matched_to_staging      loaded records without their mother or newborn PERSON,
--                                      and PERSON rows that are neither of a loaded record: PERSON
--                                      is twice staging minus the records without a year of birth
--                                      (D-060, D-103)
--   staging_rows_not_load_counts       years whose records differ from the table count staging
--                                      recorded in load_counts (D-069)
--   cdm_source_rows_not_one            CDM_SOURCE holds one row
WITH written (cdm_table, concept_id) AS (
    SELECT DISTINCT
        'person',
        unnest(ARRAY[
            gender_concept_id, race_concept_id, ethnicity_concept_id, gender_source_concept_id,
            race_source_concept_id, ethnicity_source_concept_id
        ])
    FROM @cdm_schema.person
    UNION
    SELECT DISTINCT 'observation_period', period_type_concept_id
    FROM @cdm_schema.observation_period
    UNION
    SELECT DISTINCT
        'measurement',
        unnest(ARRAY[
            measurement_concept_id, measurement_type_concept_id, operator_concept_id,
            value_as_concept_id, unit_concept_id, measurement_source_concept_id,
            unit_source_concept_id, meas_event_field_concept_id
        ])
    FROM @cdm_schema.measurement
    UNION
    SELECT DISTINCT
        'observation',
        unnest(ARRAY[
            observation_concept_id, observation_type_concept_id, value_as_concept_id,
            qualifier_concept_id, unit_concept_id, observation_source_concept_id,
            obs_event_field_concept_id
        ])
    FROM @cdm_schema.observation
    UNION
    SELECT DISTINCT
        'fact_relationship',
        unnest(ARRAY[domain_concept_id_1, domain_concept_id_2, relationship_concept_id])
    FROM @cdm_schema.fact_relationship
    UNION
    SELECT DISTINCT 'location', country_concept_id FROM @cdm_schema.location
    UNION
    SELECT DISTINCT 'cdm_source', cdm_version_concept_id FROM @cdm_schema.cdm_source
    UNION
    SELECT DISTINCT 'source_to_concept_map', unnest(ARRAY[source_concept_id, target_concept_id])
    FROM @cdm_schema.source_to_concept_map
),

missing AS (
    SELECT w.cdm_table, count(*) AS concepts
    FROM written AS w
    WHERE
        w.concept_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM @cdm_schema.concept AS c WHERE c.concept_id = w.concept_id)
    GROUP BY w.cdm_table
),

-- The two PERSONs of each loaded record, with the day both were observed.
roles AS (
    SELECT person_id, 'mother' AS role, delivery_date FROM pg_temp.records WHERE loaded
    UNION ALL
    SELECT newborn_person_id, 'newborn', delivery_date FROM pg_temp.records WHERE loaded
),

-- The rows FACT_RELATIONSHIP must hold: the mother is the Mother of the newborn, and the newborn
-- the Child of the mother (D-104).
links AS (
    SELECT l.*
    FROM pg_temp.records AS r
    CROSS JOIN (
        SELECT
            max(concept_id) FILTER (WHERE concept_key = 'person_table') AS person,
            max(concept_id) FILTER (WHERE concept_key = 'mother') AS mother,
            max(concept_id) FILTER (WHERE concept_key = 'child') AS child
        FROM @results_schema.concept_sets
    ) AS c
    CROSS JOIN LATERAL (
        VALUES
        (c.person, r.person_id, c.person, r.newborn_person_id, c.mother),
        (c.person, r.newborn_person_id, c.person, r.person_id, c.child)
    ) AS l (domain_1, fact_1, domain_2, fact_2, relationship)
    WHERE r.loaded
),

per_person AS (
    SELECT
        p.person_id,
        r.role,
        coalesce(o.n, 0) AS periods,
        coalesce(m.n, 0) AS measurements,
        coalesce(e.n, 0) AS observations
    FROM @cdm_schema.person AS p
    LEFT JOIN (
        SELECT person_id, count(*) AS n FROM @cdm_schema.observation_period GROUP BY person_id
    ) AS o ON p.person_id = o.person_id
    LEFT JOIN (
        SELECT person_id, count(*) AS n FROM @cdm_schema.measurement GROUP BY person_id
    ) AS m ON p.person_id = m.person_id
    LEFT JOIN (
        SELECT person_id, count(*) AS n FROM @cdm_schema.observation GROUP BY person_id
    ) AS e ON p.person_id = e.person_id
    LEFT JOIN roles AS r ON p.person_id = r.person_id
),

staged AS (
    SELECT source_year, count(*) AS row_count
    FROM pg_temp.records
    GROUP BY source_year
)

INSERT INTO @results_schema.etl_counts (source_year, cdm_table, rule, row_count)
SELECT NULL, 'check', c.rule, c.violations
FROM (
    VALUES
    (
        'concept_not_in_vocabulary:person',
        coalesce((SELECT concepts FROM missing WHERE cdm_table = 'person'), 0)
    ),
    (
        'concept_not_in_vocabulary:observation_period',
        coalesce((SELECT concepts FROM missing WHERE cdm_table = 'observation_period'), 0)
    ),
    (
        'concept_not_in_vocabulary:measurement',
        coalesce((SELECT concepts FROM missing WHERE cdm_table = 'measurement'), 0)
    ),
    (
        'concept_not_in_vocabulary:observation',
        coalesce((SELECT concepts FROM missing WHERE cdm_table = 'observation'), 0)
    ),
    (
        'concept_not_in_vocabulary:fact_relationship',
        coalesce((SELECT concepts FROM missing WHERE cdm_table = 'fact_relationship'), 0)
    ),
    (
        'concept_not_in_vocabulary:location',
        coalesce((SELECT concepts FROM missing WHERE cdm_table = 'location'), 0)
    ),
    (
        'concept_not_in_vocabulary:cdm_source',
        coalesce((SELECT concepts FROM missing WHERE cdm_table = 'cdm_source'), 0)
    ),
    (
        'concept_not_in_vocabulary:source_to_concept_map',
        coalesce((SELECT concepts FROM missing WHERE cdm_table = 'source_to_concept_map'), 0)
    ),
    (
        'orphan_person:observation_period',
        (
            SELECT count(*) FROM @cdm_schema.observation_period AS o
            WHERE NOT EXISTS (
                SELECT 1 FROM @cdm_schema.person AS p WHERE p.person_id = o.person_id
            )
        )
    ),
    (
        'orphan_person:measurement',
        (
            SELECT count(*) FROM @cdm_schema.measurement AS m
            WHERE NOT EXISTS (
                SELECT 1 FROM @cdm_schema.person AS p WHERE p.person_id = m.person_id
            )
        )
    ),
    (
        'orphan_person:observation',
        (
            SELECT count(*) FROM @cdm_schema.observation AS o
            WHERE NOT EXISTS (
                SELECT 1 FROM @cdm_schema.person AS p WHERE p.person_id = o.person_id
            )
        )
    ),
    (
        'orphan_person:fact_relationship',
        (
            SELECT count(*) FROM @cdm_schema.fact_relationship AS f
            WHERE
                NOT EXISTS (
                    SELECT 1 FROM @cdm_schema.person AS p WHERE p.person_id = f.fact_id_1
                )
                OR NOT EXISTS (
                    SELECT 1 FROM @cdm_schema.person AS p WHERE p.person_id = f.fact_id_2
                )
        )
    ),
    (
        'orphan_location:person',
        (
            SELECT count(*) FROM @cdm_schema.person AS p
            WHERE
                p.location_id IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM @cdm_schema.location AS l WHERE l.location_id = p.location_id
                )
        )
    ),
    (
        'person_without_one_observation_period',
        (SELECT count(*) FROM per_person WHERE periods <> 1)
    ),
    (
        'mother_without_three_measurements',
        (SELECT count(*) FROM per_person WHERE role = 'mother' AND measurements <> 3)
    ),
    (
        'mother_without_three_observations',
        (SELECT count(*) FROM per_person WHERE role = 'mother' AND observations <> 3)
    ),
    (
        'newborn_without_one_measurement',
        (SELECT count(*) FROM per_person WHERE role = 'newborn' AND measurements <> 1)
    ),
    (
        'newborn_with_an_observation',
        (SELECT count(*) FROM per_person WHERE role = 'newborn' AND observations <> 0)
    ),
    (
        'observation_period_not_the_delivery_day',
        (
            SELECT count(*) FROM @cdm_schema.observation_period AS o
            LEFT JOIN roles AS r ON o.person_id = r.person_id
            WHERE
                o.observation_period_start_date <> o.observation_period_end_date
                OR o.observation_period_start_date IS DISTINCT FROM r.delivery_date
        )
    ),
    (
        'newborn_birth_not_the_delivery_day',
        (
            SELECT count(*) FROM @cdm_schema.person AS p
            INNER JOIN roles AS r ON p.person_id = r.person_id AND r.role = 'newborn'
            WHERE
                make_date(p.year_of_birth, p.month_of_birth, p.day_of_birth)
                IS DISTINCT FROM r.delivery_date
        )
    ),
    (
        'fact_relationship_not_the_record_pair',
        (
            SELECT count(*) FROM (
                (
                    SELECT * FROM links
                    EXCEPT ALL
                    SELECT
                        domain_concept_id_1, fact_id_1, domain_concept_id_2, fact_id_2,
                        relationship_concept_id
                    FROM @cdm_schema.fact_relationship
                )
                UNION ALL
                (
                    SELECT
                        domain_concept_id_1, fact_id_1, domain_concept_id_2, fact_id_2,
                        relationship_concept_id
                    FROM @cdm_schema.fact_relationship
                    EXCEPT ALL
                    SELECT * FROM links
                )
            ) AS differences
        )
    ),
    (
        'event_outside_observation_period:measurement',
        (
            SELECT count(*) FROM @cdm_schema.measurement AS m
            INNER JOIN @cdm_schema.observation_period AS o ON m.person_id = o.person_id
            WHERE
                m.measurement_date NOT BETWEEN o.observation_period_start_date
                AND o.observation_period_end_date
        )
    ),
    (
        'event_outside_observation_period:observation',
        (
            SELECT count(*) FROM @cdm_schema.observation AS e
            INNER JOIN @cdm_schema.observation_period AS o ON e.person_id = o.person_id
            WHERE
                e.observation_date NOT BETWEEN o.observation_period_start_date
                AND o.observation_period_end_date
        )
    ),
    (
        'visit_occurrence_rows',
        (SELECT count(*) FROM @cdm_schema.visit_occurrence)
    ),
    (
        'vocabulary_not_registered',
        (
            SELECT count(DISTINCT m.source_vocabulary_id)
            FROM @cdm_schema.source_to_concept_map AS m
            WHERE NOT EXISTS (
                SELECT 1 FROM @cdm_schema.vocabulary AS v
                WHERE v.vocabulary_id = m.source_vocabulary_id
            )
        )
    ),
    (
        'person_not_matched_to_staging',
        (
            SELECT count(*) FROM roles AS r
            WHERE NOT EXISTS (
                SELECT 1 FROM @cdm_schema.person AS p WHERE p.person_id = r.person_id
            )
        )
        + (SELECT count(*) FROM per_person WHERE role IS NULL)
    ),
    (
        'staging_rows_not_load_counts',
        (
            SELECT count(*) FROM staged AS s
            LEFT JOIN @staging_schema.load_counts AS l
                ON s.source_year = l.source_year AND l.stage = 'table'
            WHERE l.row_count IS DISTINCT FROM s.row_count
        )
    ),
    (
        'cdm_source_rows_not_one',
        (SELECT abs(count(*) - 1) FROM @cdm_schema.cdm_source)
    )
) AS c (rule, violations);
