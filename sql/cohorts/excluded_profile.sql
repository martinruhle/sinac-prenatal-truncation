-- The records each validity step removes, against those it keeps (docs/protocol.md §Output
-- tables, D-121): RECORD and STROBE ask for this comparison next to the attrition. Per definition
-- this run built and per step of kind validity, it writes two rows to results.excluded_profile,
-- pooled over the years of --years:
--   excluded   the subjects whose first failed step is this one: the step's `excluded`
--   retained   the subjects that fail neither this step nor one before it: its `remaining`
-- scripts/cohorts.py checks both counts against results.attrition before the run commits.
--
-- It runs last, in the transaction of the cohorts, because it reads what that transaction drops
-- when it commits:
--   pg_temp.cohort_exits    the first step each subject fails, per definition
--   pg_temp.base_criteria   the completed weeks at delivery of every subject (01_base.sql)
-- and the trimester of the first visit of every subject in results.exposure (exposure.sql).
--
-- Each share is a percentage with two decimals over the births of the group whose value is known,
-- and NULL when none is:
--   preterm_percent                22 to 36 completed weeks, of the births at 22 weeks or more:
--                                  the outcome of docs/protocol.md §Outcome (NOM-007-SSA2-2016
--                                  §3.25 and §3.45), which a birth below 22 weeks does not have
--   first_trimester_start_percent  a first visit in trimester 1, of the births with a trimester
--                                  of 0 to 3: measure (c)
--   no_prenatal_care_percent       trimester 0 "NO RECIBIÓ", of the same births (D-065)
DELETE FROM @results_schema.excluded_profile
WHERE cohort_definition_id IN (SELECT s.cohort_definition_id FROM pg_temp.cohort_steps AS s);

WITH exits AS (
    SELECT
        e.cohort_definition_id,
        e.exit_step,
        count(*) AS births,
        count(*) FILTER (WHERE b.weeks >= 22) AS with_outcome,
        count(*) FILTER (WHERE b.weeks >= 22 AND b.weeks < 37) AS preterm,
        count(x.first_visit_trimester) AS with_trimester,
        count(*) FILTER (WHERE x.first_visit_trimester = 1) AS first_trimester,
        count(*) FILTER (WHERE x.first_visit_trimester = 0) AS no_care
    FROM pg_temp.cohort_exits AS e
    INNER JOIN pg_temp.base_criteria AS b ON e.subject_id = b.subject_id
    LEFT JOIN @results_schema.exposure AS x ON e.subject_id = x.subject_id
    GROUP BY e.cohort_definition_id, e.exit_step
),

groups AS (
    SELECT
        s.cohort_definition_id,
        s.step,
        g.subject_group,
        coalesce(sum(x.births), 0) AS births,
        coalesce(sum(x.with_outcome), 0) AS with_outcome,
        coalesce(sum(x.preterm), 0) AS preterm,
        coalesce(sum(x.with_trimester), 0) AS with_trimester,
        coalesce(sum(x.first_trimester), 0) AS first_trimester,
        coalesce(sum(x.no_care), 0) AS no_care
    FROM pg_temp.cohort_steps AS s
    CROSS JOIN (VALUES ('excluded'), ('retained')) AS g (subject_group)
    LEFT JOIN exits AS x
        ON
            s.cohort_definition_id = x.cohort_definition_id
            AND CASE
                WHEN g.subject_group = 'excluded' THEN x.exit_step = s.step
                ELSE x.exit_step IS NULL OR x.exit_step > s.step
            END
    WHERE s.kind = 'validity'
    GROUP BY s.cohort_definition_id, s.step, g.subject_group
)

INSERT INTO @results_schema.excluded_profile (
    cohort_definition_id,
    step,
    subject_group,
    births,
    preterm_percent,
    first_trimester_start_percent,
    no_prenatal_care_percent
)
SELECT
    g.cohort_definition_id,
    g.step,
    g.subject_group,
    g.births,
    round(100.0 * g.preterm / nullif(g.with_outcome, 0), 2),
    round(100.0 * g.first_trimester / nullif(g.with_trimester, 0), 2),
    round(100.0 * g.no_care / nullif(g.with_trimester, 0), 2)
FROM groups AS g;
