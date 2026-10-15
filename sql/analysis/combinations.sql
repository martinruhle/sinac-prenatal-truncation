-- The births of each definition per combination of completed weeks at delivery, first-visit
-- trimester and visits (task 1.7.1, D-113): the table the null simulation draws its pregnancies
-- from, and the one the observed measures and their crude odds ratios are computed from, with the
-- same code as the simulated ones. It reads the cohorts that scripts/cohorts.py built, and its one
-- parameter is the list of definitions.
--
--   weeks                  completed weeks at delivery: the gestational age of MEASUREMENT that
--                          01_base.sql reads, so the outcome is that of the cohorts
--   first_visit_trimester  0 to 3, from results.exposure
--   visits                 the count of visits, from results.exposure
--
-- Every subject of the analysis cohort has all three (step 8 of 02_analysis.sql), and
-- scripts/simulate.py checks that the births of each definition add up to its cohort.
WITH concepts AS (
    SELECT max(c.concept_id) FILTER (WHERE c.concept_key = 'gestational_age_at_birth') AS weeks
    FROM @results_schema.concept_sets AS c
)

SELECT
    c.cohort_definition_id,
    w.value_as_number::integer AS weeks,
    x.first_visit_trimester,
    x.visits,
    count(*) AS births
FROM @results_schema.cohort AS c
CROSS JOIN concepts AS k
INNER JOIN @results_schema.exposure AS x ON c.subject_id = x.subject_id
INNER JOIN @cdm_schema.measurement AS w
    ON c.subject_id = w.person_id AND k.weeks = w.measurement_concept_id
WHERE c.cohort_definition_id = ANY(%(definitions)s)
GROUP BY c.cohort_definition_id, w.value_as_number::integer, x.first_visit_trimester, x.visits
ORDER BY c.cohort_definition_id, weeks, x.first_visit_trimester, x.visits;
