-- The tables of the null simulation (task 1.7.1, docs/protocol.md §Null simulation). They live in
-- results, next to the cohorts they are computed from. scripts/simulate.py rebuilds them in one
-- transaction on every run, so a failed run keeps the previous tables.
--
-- simulation: one row per scenario of config/null_simulation.yml, with the seed and the stream it
--   drew from, and, for the scenario with misses, p and the observed births p was set from
--   (D-096): the protocol writes the parameters next to the output. exact_share_difference is
--   the largest relative difference between a simulated share and the share of the exact
--   expectation (D-115), NULL when no share is reported.
-- simulated_combination: the simulated pregnancies of each scenario, one row per combination of
--   completed weeks at delivery, first-visit trimester and visits. The visits are those of the
--   model, not of SINAC (CLAUDE.md rule 4). Every measure is computed from this table.
-- truncation_share: per definition, measure, variant, level and scenario, the crude comparison of
--   the level with the reference in the observed records and in the simulated pregnancies, and
--   the share of the observed risk difference that truncation alone produces (D-112). A value
--   that does not exist is NULL: an odds ratio with an empty cell, a share that is not reported.
DROP TABLE IF EXISTS
@results_schema.simulation,
@results_schema.simulated_combination,
@results_schema.truncation_share;

CREATE TABLE @results_schema.simulation (
    scenario text PRIMARY KEY,
    name text NOT NULL,
    seed bigint NOT NULL,
    stream integer NOT NULL,
    misses boolean NOT NULL,
    pregnancies bigint NOT NULL,
    visit_probability double precision,
    calibration_from_week integer,
    calibration_births bigint,
    calibration_share double precision,
    exact_share_difference double precision
);

CREATE TABLE @results_schema.simulated_combination (
    scenario text NOT NULL,
    weeks integer NOT NULL,
    first_visit_trimester integer NOT NULL,
    visits integer NOT NULL,
    births bigint NOT NULL,
    PRIMARY KEY (scenario, weeks, first_visit_trimester, visits)
);

CREATE TABLE @results_schema.truncation_share (
    cohort_definition_id integer NOT NULL,
    measure text NOT NULL,
    -- acog_midpoint for (b), empty for the other measures (docs/protocol.md §Output tables).
    variant text NOT NULL,
    level text NOT NULL,
    scenario text NOT NULL,
    reference text NOT NULL,
    observed_odds_ratio double precision,
    observed_lower double precision,
    observed_upper double precision,
    simulated_odds_ratio double precision,
    -- Preterm share of the level minus that of the reference, as a proportion.
    observed_risk_difference double precision,
    simulated_risk_difference double precision,
    share double precision,
    PRIMARY KEY (cohort_definition_id, measure, variant, level, scenario)
);
