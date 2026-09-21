# Roadmap

This document separates three things: what the course delivers, what was left out of this
semester, and what continues after it as part of the doctoral project. The question, the
population and the method live in [`protocol.md`](protocol.md) (so far the data source and the
study period; the rest is PENDING). Every scope change stated here is recorded in [`decisions.md`](decisions.md), and
the proposal it is stated against is translated in [`proposal_v2.md`](proposal_v2.md).

## 1. Core: the course deliverable

This is the commitment for the final submission. Everything is rebuilt from the public SINAC
download; **the repository contains no data**, only the code that loads and transforms it.

| Component | Content |
|---|---|
| Data model | Postgres with a subset of the OMOP CDM v5.4 and a reproducible ETL from the DGIS open-data download (see [Data source](#2-data-source)). Study period: 2020–2023 (D-041); development runs on 2023 (D-009) |
| Cohorts | Documented cohort definitions in SQL, with an attrition table per definition |
| Exposures | (a) total number of visits; (b) approximate APNCU index; (c) care started in the first trimester; (d) total visits in landmark cohorts, with one or two landmark weeks instead of three (D-004) |
| Association estimates | Crude and adjusted odds ratios for each measure, with a reduced covariate set (D-007) |
| Simulation | The association that truncation produces on its own, under the null hypothesis (NOM-007-SSA2-2016 schedule), with 2–3 fixed adherence scenarios (D-010) |
| Sensitivity | Preterm cut-off (37/34/32), multiple pregnancies, births before week 22, the years 2020–2021 (2020–2023 against 2022–2023, D-049); gradient by state and by insurance. The full grid runs for measures (a) and (c) only (D-003) |
| Engineering | `compose.yml`, pytest, CI on GitHub Actions, a single entry point (`scripts/pipeline.py`), and a data dictionary covering the variables actually used (D-011) |
| Documentation | Reproducible README, limitations, AI-assistance statement, decision log |

### Planned OMOP mapping decisions

The detail lives in `docs/omop_mapping.md` and `docs/data_dictionary.md` (D-017); these are the
ones that shape the schema.

| SINAC item | OMOP destination | Note |
|---|---|---|
| Mother and newborn | `PERSON` (two records) | Linked through `FACT_RELATIONSHIP` |
| Birth | `VISIT_OCCURRENCE` | Care unit in `CARE_SITE`, state in `LOCATION` |
| Gestational weeks, birth weight | `MEASUREMENT` | Gestation on the mother, weight on the newborn |
| Total visits, trimester of the first visit | `OBSERVATION` | This is a **declared count**, not one row per visit; it is not modelled as visits |
| Insurance | `PAYER_PLAN_PERIOD` | |
| Variables with no standard concept | `concept_id = 0` + `*_source_value` | OMOP convention; they are listed in the dictionary |

## 2. Data source

The source changed after the proposal was submitted (D-001, D-002). What this implies:

| Proposal v2 | Now | Consequence |
|---|---|---|
| SINAC in the **INSP standardized version** (RIISP catalogue, `MEX-INSP-SINAC-2008-2023`), 31,486,699 records and 91 variables | **SSA/DGIS open data**, one ZIP per year | The record and variable counts of the proposal **do not apply**: they have to be measured on the DGIS files and reported |
| A standardized series, already harmonized by the INSP | Annual series, not harmonized across catalogue periods | Harmonization across years is our own work, and it is part of the study-period decision |
| Citation under the INSP licence | Citation under the SSA/DGIS terms of free use | The credit line is kept verbatim in Spanish in the README (D-035) |
| The download date is recorded | Also the URL with its `?V=` parameter, size and sha256, in `config/sources.yml` | `?V=` is the version DGIS publishes; if it changes, the hash stops matching and the pipeline fails on purpose |
| — | The files are served over **HTTP without TLS** | The sha256 detects later changes, it does **not** authenticate the first download. This is a limitation, stated in the README and in `protocol.md` |

The proposal committed to 2019–2023. The period is now **2020–2023**, a scope change (D-041).
The [source inventory](source_inventory.md) measured the cost of each option:

- The four years 2020–2023 share one descriptor, one catalogue set and identical headers.
- 2019 needs a harmonization of its own and has no descriptor published by DGIS.

2019 stays as a conditional extension ([§4.5](#45-the-year-2019), D-050). Development runs on
2023 (D-009). The argument is in [`protocol.md`](protocol.md#data-source).

## 3. Milestones of the semester

| Milestone | Date | Committed content | Release |
|---|---|---|---|
| `v0.1-cohort` | Fri 9 Oct 2026 (session 18) | OMOP ETL of the vertical slice on 2023, base cohort in SQL with its attrition table, SQL tests in CI, README with the evidence map v1 and the source and scope changes written down | tag + release + clean-clone test |
| `v0.2-progress` | Thu 29 Oct 2026 (tag), Fri 30 Oct (progress review, session 24) | Full period (2020–2023) loaded, remaining mapping and covariate ETL, exposures a–d, crude and adjusted odds ratios, null simulation v1, one or two sensitivity axes (D-012) | tag + release + clean-clone test |
| `v1.0` | Fri 20 Nov 2026 (session 30, submission) | Remaining sensitivity axes and gradients, analysis image, complete entry point, documentation closed, security review, DOI (D-025) | tag + release + clean-clone test + Zenodo |
| presentation | Tue 24 Nov 2026 (session 31) | 12 minutes plus 5 for questions | — |

The `v0.2-progress` tag is cut on the Thursday, the day before the progress review: the review
sees a stable state, and the feedback goes into the re-planning rather than into work in
progress. Every milestone tag is reproduced from a clean clone before it is released (D-020).

## 4. Out of scope for this semester (future work)

The weekly time budget does not cover everything the proposal described as possible. What
follows is out of the semester, not out of the project.

### 4.1 Artifact demonstration with ML + SHAP

Not started this semester (D-042); proposal v2 already described it as conditional.

- **What:** two gradient boosting models (LightGBM) that predict preterm birth. The *naive*
  model uses the raw total number of visits; the *truncation-free* model uses first-trimester
  start and sociodemographic variables.
- **Variables excluded from both:** gestational weeks, birth weight and anything derived from
  them (including APNCU), because they contain the outcome.
- **Explanation:** SHAP on a stratified subsample, because TreeSHAP over 10 million records is
  neither necessary nor practical.
- **What it is meant to show:** whether the naive model uses truncation as its main signal. It
  is contrasted with the null simulation.
- **What it is not:** an estimator of the association. With a truncated count, a predictive
  model learns exactly the bias the study wants to measure; that is why it is used to
  demonstrate it.

### 4.2 Interactive dashboard

Not started this semester (D-042); proposal v2 already described it as conditional.

- **What:** an interface to change the cohort definition (preterm cut-off, landmark week,
  exclusions) and see how the estimate of each prenatal care measure moves, APNCU included.
- **How:** on top of the sensitivity table and pre-aggregated counts, so the estimates are
  recomputed in real time without querying the 10 million records again.

### 4.3 Definition axes left out of the sensitivity analysis

Each one is a scope change against proposal v2, recorded in `decisions.md`; the reason in every
case is the weekly time budget.

| Left out | Decision |
|---|---|
| The full sensitivity grid for measures (b) APNCU and (d) landmark cohorts; they appear in the main analysis only | D-003 |
| The third landmark week: one or two are used instead of three | D-004 |
| Sensitivity to the month assigned within the first-visit trimester for APNCU; a single documented rule is used instead | D-005 |
| Sensitivity using birth weight <2500 g as an alternative outcome | D-006 |
| The full covariate set in the adjusted odds ratios | D-007 |

### 4.4 Engineering left for later

The analysis image (`Dockerfile`) is built after milestone `v0.1-cohort` within a two-hour
timebox; whatever does not fit in that timebox is future work as well (D-015).

### 4.5 The year 2019

2019 is the only pre-pandemic year among the candidates, and the last year of the 2015–2019
catalogue period. It is added this semester only if two conditions hold (D-050):

- `v0.2-progress` has been tagged with all of its committed content.
- The work fits in a one-week timebox (6 hours) before `v1.0` starts.

Otherwise it is future work. What it costs is listed in [`protocol.md`](protocol.md#data-source).

## 5. After the semester: continuity with the doctoral project

### 5.1 What does not transfer: a model trained on SINAC

A model trained on SINAC cannot be applied to the INPer cohort. The variables of the two
sources overlap very little:

| Variable | SINAC | INPer cohort (analysis variables) |
|---|---|---|
| Maternal age | Yes | Yes |
| Education | Yes | Yes, with 4 levels (needs recoding) |
| Marital status | Yes | Yes |
| Total prenatal visits | Yes | No |
| Trimester of the first visit | Yes | No |
| Insurance | Yes | No (and it would be almost constant) |
| State of residence | Yes | No |
| Multiple pregnancy | Yes | No |
| Gestational weeks at delivery | Yes | Yes (defines the outcome; not a predictor) |
| Birth weight, newborn sex | Yes | Yes (posterior to the outcome; not predictors) |
| Gestational week of each sample | No | Yes |
| Vaginal microbiome | No | Yes |

Among the variables that precede delivery, only age, education and marital status coincide. The
cohort also comes from a referral hospital for high-risk pregnancies, which is not
representative of the national registry. The table reflects the analysis variables of the
cohort; whether the full clinical metadata contains any of the missing ones is still to be
reviewed.

One limited possibility, to be evaluated but not committed to, is a sociodemographic risk score
derived from SINAC and used as a single covariate in the cohort. It requires recoding the
variables the same way in both sources and does not guarantee calibration across populations.

### 5.2 What does transfer

1. **The data model.** The INPer cohort enters as a second source on the same schema:
   - `PERSON`, one per participant;
   - `OBSERVATION_PERIOD`, from the first visit to delivery;
   - `SPECIMEN`, the vaginal samples with the gestational week of collection;
   - `MEASUREMENT`, the clinical variables per visit.

   The de-identified clinical metadata is read from its source repository; it is not copied
   into this one.
2. **The index-week and landmark cohort logic.** The same SQL definitions apply to the samples:
   use only samples taken before week X, on participants who reached week X.
3. **The null simulation**, adapted to the sampling schedule of the cohort. It serves to assess
   how much information about pregnancy duration is carried by the gestational week at sampling
   and by the number of samples per participant.
4. **The dashboard**, as a tool for exploring the sampling window. The main window is
   pre-specified before looking at results; with 43 participants and 14 events, choosing it
   afterwards would invalidate the estimate.

### 5.3 Out of scope, also after the semester

- Integrating microbiome abundances into OMOP beyond recording the sample in `SPECIMEN`.
- Linking SINAC records to INPer participants; it is neither possible nor intended.

## Related repositories

- Doctoral project analysis: <https://github.com/martinruhle/Mexican-PretermBirth-analysis>
- 16S sequence processing: <https://github.com/martinruhle/Mexican-PretermBirth-16S-processing>
