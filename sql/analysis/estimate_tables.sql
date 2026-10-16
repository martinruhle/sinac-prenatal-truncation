-- The tables of the odds ratios (task 1.6.4, docs/protocol.md §Model, §Output tables). They live
-- in results, next to the cohorts they are computed from. scripts/estimate.py rebuilds them in one
-- transaction on every run, so a failed run keeps the previous tables.
--
-- aggregated_count: the births of each definition per combination of completed weeks at
--   delivery, first-visit trimester, visits and the four covariates of D-094 (D-093). Every
--   measure is a function of the first three and the outcome a function of the weeks, so each
--   model table of a measure is this table collapsed (D-117). It stays in the database and is
--   never versioned (D-098).
-- estimate: one row per estimate of estimates.csv, with the columns docs/protocol.md
--   §Output tables lists. A value that does not exist is NULL: the odds ratio of a level with an
--   empty cell. births and preterm_births are those of the level.
-- exposure_distribution: the births of each level of each measure, per outcome, with the columns
--   of exposure_distribution.csv.
--
-- An empty value of a text column of the key (variant, stratum) is '', as in truncation_share.
DROP TABLE IF EXISTS
@results_schema.aggregated_count,
@results_schema.estimate,
@results_schema.exposure_distribution;

CREATE TABLE @results_schema.aggregated_count (
    cohort_definition_id integer NOT NULL,
    weeks integer NOT NULL,
    first_visit_trimester integer NOT NULL,
    visits integer NOT NULL,
    age_group text NOT NULL,
    -- The concept of the education level, the value_as_concept_id of D-101.
    education_concept_id integer NOT NULL,
    -- The state of residence, as LOCATION holds it.
    state text NOT NULL,
    -- The year of the delivery.
    year integer NOT NULL,
    births bigint NOT NULL,
    PRIMARY KEY (
        cohort_definition_id,
        weeks,
        first_visit_trimester,
        visits,
        age_group,
        education_concept_id,
        state,
        year
    )
);

CREATE TABLE @results_schema.estimate (
    -- observed, or sim_ and the id of a scenario of config/null_simulation.yml.
    source text NOT NULL,
    cohort_definition_id integer NOT NULL,
    -- The years of the record files, as --years writes them.
    period text NOT NULL,
    -- Completed weeks below which a birth is preterm.
    outcome_cutoff integer NOT NULL,
    measure text NOT NULL,
    variant text NOT NULL,
    level text NOT NULL,
    reference text NOT NULL,
    -- crude or adjusted.
    model text NOT NULL,
    stratum_variable text NOT NULL,
    stratum_value text NOT NULL,
    births bigint NOT NULL,
    preterm_births bigint NOT NULL,
    odds_ratio double precision,
    lower_limit double precision,
    upper_limit double precision,
    PRIMARY KEY (
        source,
        cohort_definition_id,
        period,
        outcome_cutoff,
        measure,
        variant,
        level,
        model,
        stratum_variable,
        stratum_value
    )
);

CREATE TABLE @results_schema.exposure_distribution (
    source text NOT NULL,
    cohort_definition_id integer NOT NULL,
    period text NOT NULL,
    outcome_cutoff integer NOT NULL,
    measure text NOT NULL,
    variant text NOT NULL,
    level text NOT NULL,
    -- preterm or term.
    outcome text NOT NULL,
    births bigint NOT NULL,
    PRIMARY KEY (
        source, cohort_definition_id, period, outcome_cutoff, measure, variant, level, outcome
    )
);
