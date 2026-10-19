-- The analysis cohort with multiple pregnancies, cohort_definition_id 6, the number of this file
-- (docs/protocol.md §Sensitivity of the definition, D-054, D-087): the base cohort without its
-- step "Singleton", then the two steps of the analysis cohort. It is the other side of the axis
-- "multiple pregnancies", so it differs from definition 2 in that step alone: a multiple
-- pregnancy whose multiplicity is specified stays, and each certificate is one unit (D-099). It
-- runs after 02_analysis.sql, in the same transaction, and writes:
--   results.cohort         one row per subject that meets every criterion but "Singleton"
--   pg_temp.cohort_steps   steps 2 to 9 of the analysis cohort without step 6, so that steps 7 to
--                          9 become 6 to 8 and the steps run without a gap
--   pg_temp.cohort_exits   every subject with the first step it fails, NULL when it stays
--
-- The criteria are those 01_base.sql and 02_analysis.sql computed, read from pg_temp.base_criteria
-- and pg_temp.analysis_criteria, so no criterion is written twice. "Multiplicity specified" stays:
-- a record with PRODUCTOEMBARAZO 0 is neither a known singleton nor a known multiple (D-056).
DELETE FROM @results_schema.cohort WHERE cohort_definition_id = 6;

INSERT INTO @results_schema.cohort (
    cohort_definition_id,
    subject_id,
    cohort_start_date,
    cohort_end_date
)
SELECT
    6,
    b.subject_id,
    b.delivery_date,
    b.delivery_date
FROM pg_temp.base_criteria AS b
INNER JOIN pg_temp.analysis_criteria AS a ON b.subject_id = a.subject_id
WHERE
    b.born_in_period
    AND b.resident_in_mexico
    AND b.weeks_specified
    AND b.multiplicity_specified
    AND b.at_least_22_weeks
    AND a.prenatal_care_known
    AND a.covariates_known;

-- The steps of the analysis cohort, but "Singleton", with the ones after it moved up by one.
INSERT INTO pg_temp.cohort_steps (cohort_definition_id, step, kind, description)
SELECT
    6,
    CASE WHEN s.step > 6 THEN s.step - 1 ELSE s.step END,
    s.kind,
    s.description
FROM pg_temp.cohort_steps AS s
WHERE s.cohort_definition_id = 2 AND s.step <> 6;

-- A subject leaves at the first step it fails, in the order of the steps above.
INSERT INTO pg_temp.cohort_exits (cohort_definition_id, source_year, subject_id, exit_step)
SELECT
    6,
    b.source_year,
    b.subject_id,
    CASE
        WHEN NOT b.born_in_period THEN 2
        WHEN NOT b.resident_in_mexico THEN 3
        WHEN NOT b.weeks_specified THEN 4
        WHEN NOT b.multiplicity_specified THEN 5
        WHEN NOT b.at_least_22_weeks THEN 6
        WHEN NOT a.prenatal_care_known THEN 7
        WHEN NOT a.covariates_known THEN 8
    END
FROM pg_temp.base_criteria AS b
INNER JOIN pg_temp.analysis_criteria AS a ON b.subject_id = a.subject_id;
