-- The aggregated table of the models (task 1.6.4, docs/protocol.md §Model, D-093, D-117): the
-- births of each definition per combination of completed weeks at delivery, first-visit
-- trimester, visits and the covariates of §Covariates. It reads the cohorts that
-- scripts/cohorts.py built, after estimate_tables.sql, and its one parameter is the list of
-- definitions.
--
--   weeks                  completed weeks at delivery, as combinations.sql reads them
--   first_visit_trimester  0 to 3, from results.exposure
--   visits                 the count of visits, from results.exposure
--   age_group              the declared age (D-100) in the groups of §Covariates
--   education_concept_id   the concept of the education level (D-101)
--   state                  the state of residence, from LOCATION
--   year                   the year of the delivery, the cohort start (D-062)
--
-- Every subject of the analysis cohort has all of them (steps 8 and 9 of 02_analysis.sql), and
-- scripts/estimate.py checks that the births of each definition add up to its cohort.
WITH concepts AS (
    SELECT
        max(c.concept_id) FILTER (WHERE c.concept_key = 'gestational_age_at_birth') AS weeks,
        max(c.concept_id) FILTER (WHERE c.concept_key = 'mother_age_at_delivery') AS age,
        max(c.concept_id) FILTER (WHERE c.concept_key = 'mother_education') AS education
    FROM @results_schema.concept_sets AS c
),

subjects AS (
    SELECT
        c.cohort_definition_id,
        w.value_as_number::integer AS weeks,
        x.first_visit_trimester,
        x.visits,
        -- The age groups of docs/protocol.md §Covariates (D-094, FOR APPROVAL), in completed
        -- years.
        CASE
            WHEN a.value_as_number < 15 THEN 'under 15'
            WHEN a.value_as_number < 20 THEN '15-19'
            WHEN a.value_as_number < 25 THEN '20-24'
            WHEN a.value_as_number < 30 THEN '25-29'
            WHEN a.value_as_number < 35 THEN '30-34'
            WHEN a.value_as_number < 40 THEN '35-39'
            WHEN a.value_as_number >= 40 THEN '40 and over'
        END AS age_group,
        e.value_as_concept_id AS education_concept_id,
        l.state,
        extract(YEAR FROM c.cohort_start_date)::integer AS year
    FROM @results_schema.cohort AS c
    CROSS JOIN concepts AS k
    INNER JOIN @results_schema.exposure AS x ON c.subject_id = x.subject_id
    INNER JOIN @cdm_schema.measurement AS w
        ON c.subject_id = w.person_id AND k.weeks = w.measurement_concept_id
    INNER JOIN @cdm_schema.measurement AS a
        ON c.subject_id = a.person_id AND k.age = a.measurement_concept_id
    INNER JOIN @cdm_schema.observation AS e
        ON c.subject_id = e.person_id AND k.education = e.observation_concept_id
    INNER JOIN @cdm_schema.person AS p ON c.subject_id = p.person_id
    INNER JOIN @cdm_schema.location AS l ON p.location_id = l.location_id
    WHERE c.cohort_definition_id = ANY(%(definitions)s)
)

INSERT INTO @results_schema.aggregated_count (
    cohort_definition_id,
    weeks,
    first_visit_trimester,
    visits,
    age_group,
    education_concept_id,
    state,
    year,
    births
)
SELECT
    s.cohort_definition_id,
    s.weeks,
    s.first_visit_trimester,
    s.visits,
    s.age_group,
    s.education_concept_id,
    s.state,
    s.year,
    count(*) AS births
FROM subjects AS s
GROUP BY
    s.cohort_definition_id,
    s.weeks,
    s.first_visit_trimester,
    s.visits,
    s.age_group,
    s.education_concept_id,
    s.state,
    s.year;
