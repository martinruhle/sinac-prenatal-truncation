# Final project proposal (revised version) — Martín Rühle

> Translated from the Spanish original submitted to the course (date: PENDING); content
> unchanged. File names appear under the English names this repository adopted afterwards
> (D-018). What this proposal describes and what the project now does differ in two respects —
> the data source and the accepted scope cuts — which are stated in [`roadmap.md`](roadmap.md)
> and [`decisions.md`](decisions.md), not by editing this document.

## Where the question comes from

In my doctoral project I model preterm birth risk from the vaginal microbiome in a cohort of 43
INPer participants, with samples taken throughout pregnancy. Reviewing that design I found a
problem that is not biological but structural in the data: **delivery interrupts follow-up**. A
woman who gives birth at week 32 had seven weeks less than one who gives birth at week 39 to
attend visits and to have samples taken. When the two groups are compared, part of the observed
difference says nothing about their health: it says only that one pregnancy lasted less than
the other. That phenomenon is called **truncation of the observation window**.

Truncation is structural: in a small cohort it is not corrected by estimating it, it is
corrected by design (a fixed index week). But to know how much it weighs, which definitions
neutralize it and which do not, a large population is needed. The national birth registry has
one. This project uses that registry to measure the phenomenon and compare definitions, and it
builds the infrastructure (data model and cohort definitions) that will later let me apply the
same index-week logic to my own cohort.

## Question

**How much does the association between prenatal care and preterm birth in Mexico change
according to how the exposure and the cohort are defined, and how much of that association can
be produced by truncation of the gestational window alone?**

It is answered in three parts:

**1. Compare the association across four measures of prenatal care.** The problem has two
documented stages. The raw count of visits is truncated by the duration of pregnancy; the APNCU
index (Kotelchuck, 1994) was created to correct for that, but the correction overshoots. Over
591,403 unique births in Ohio, Koroukian and Rimm (2002) showed that 61.2 % of preterm births
fell into "adequate plus care" against 18.9 % of term births, because the reference schedule
concentrates almost a third of the visits in the last 4–5 weeks. The measures are:

| Measure | What it captures | Relation to truncation |
|---|---|---|
| a. Total number of visits | Count declared on the certificate | Truncated by the duration of pregnancy |
| b. APNCU index (approximate) | Observed / expected visits given the starting week and the duration | Overcorrects. SINAC records the *trimester* of the first visit, not the month, so the index is approximated and sensitivity to the assigned month is tested |
| c. Care started in the first trimester | Timeliness of the start | **Not truncated**: it is determined before week 14, before any included birth |
| d. Total visits in *landmark* cohorts | Pregnancies that reached week 28, 32 or 34 | Truncation **bounded**, not eliminated, to the weeks between the landmark and week 37 |

The previous version proposed "visits accumulated up to a fixed index week". **It is not
computable with SINAC**: the certificate records the trimester of the first visit and the total
number of visits in the pregnancy, but not the date or the week of each visit. Measures c and d
replace it: c is the truncation-free version the data do allow, and d applies the index-week
logic to the cohort definition.

For each measure, crude odds ratios and odds ratios adjusted for maternal age and education,
insurance, state and year of birth are reported.

**2. Simulation under the null hypothesis.** Pregnancies are simulated in which prenatal care
has *no effect at all* on preterm birth: visits generated with the NOM-007-SSA2-2016 schedule
(eight visits, from week 6–8 to week 38–41) with variation in adherence, and interrupted at the
delivery week observed in SINAC. Whatever association appears in those data is the one
truncation produces on its own, and it serves as a reference for measures a–d.

**3. Sensitivity of the definition.** Whether the answer depends on definition decisions is
evaluated: preterm cut-off at 37, 34 or 32 weeks; inclusion or exclusion of multiple
pregnancies, of births before week 22 and of the years 2020–2021 (COVID-19 disruption of
services); and the month assigned within the trimester for APNCU. Each definition has its own
attrition table. How the estimate moves across definitions is reported, together with the
gradient by state and by insurance.

## Modality

**A — Characterization study.** The object of study is the cohort definition, so the two extras
this modality requires — attrition table and sensitivity analysis of the definition — are the
central deliverable.

## Data

Birth Information Subsystem (SINAC), DGIS / Secretaría de Salud, in the INSP standardized
version (RIISP catalogue, MEX-INSP-SINAC-2008-2023): 31,486,699 records and 91 variables,
publicly and freely available, with no personal data. The 2019–2023 subset (≈10 million births)
will be used. Main variables: gestational weeks, total prenatal visits, trimester of the first
visit, birth weight, maternal age and education, insurance, state and care unit. The download
date is recorded and the source is credited in the format the licence requires. **The data are
not versioned in the repository**: they are rebuilt from the download.

## Deliverable

**Core (the commitment for the semester's submission):**

- A Postgres database on a **subset of the OMOP CDM v5.4**, with a reproducible ETL from the
  download. The mapping decisions are documented: mother and newborn as distinct persons, the
  visit count as an observation, insurance as a coverage period, and standard concepts where
  they exist (with `concept_id = 0` and `source_value` where they do not).
- Documented cohort definitions in SQL, with an attrition table per definition.
- Exposure measures a–d, simulation under the null and a sensitivity table for the definition.
- `docs/protocol.md`, a data dictionary and `docs/roadmap.md`.
- A containerized environment (`compose.yml`), pytest and CI on GitHub Actions.
- A README that allows everything to be reproduced from the download, a limitations section and
  a statement on the use of AI assistants. Python and SQL.

**Extras (conditional).** They will be attempted within the semester *after* the core is
closed. **They carry a real risk of not being finished** because of their complexity and the
extra work they imply. If they are not completed, they stay documented in `docs/roadmap.md` and
**will be continued once the semester ends**, without affecting the core:

- **Artifact demonstration with ML + SHAP.** Two gradient boosting models (LightGBM) that
  predict preterm birth: one with the raw total number of visits and another with
  truncation-free variables only (first-trimester start and sociodemographic variables).
  Gestational weeks, birth weight and any variable derived from them are excluded, because they
  contain the outcome. The SHAP analysis, on a stratified subsample, shows whether the naive
  model uses truncation as its main signal. ML is used to *demonstrate* the artifact, not as an
  estimator of the association: with a truncated count, a predictive model learns exactly the
  bias that is to be measured.
- **Interactive dashboard** to change the cohort definition (preterm cut-off, landmark week,
  exclusions) and see in real time how the estimate of each measure moves, APNCU included. It
  is built on the pre-aggregated sensitivity table, so it does not require recomputing over the
  10 million records.

## Continuity with the doctoral project

Outside the scope being graded, documented in `docs/roadmap.md`. The schema and the cohort
definitions are designed to later host the INPer cohort as a second source on the same data
model. That way, the same index-week and fixed-window logic can be applied to the 43
participants.

**What transfers are the definitions, not a trained model.** The variables of the two sources
overlap very little. The central exposures of this study (total number of visits and trimester
of the first visit) are not part of the analysis variables of the INPer cohort. Among the
variables that precede delivery, only age, education and marital status coincide. The cohort
also comes from a high-risk referral hospital, not representative of the national registry.

## Anticipated limitations

- **Measurement of gestational weeks.** They agree only moderately with the clinical record,
  the lowest agreement among the certificate variables. A sensitivity analysis with birth
  weight <2500 g as an alternative outcome will be carried out. That sensitivity addresses the
  *measurement* of the weeks, **not truncation**: low birth weight depends largely on the
  duration of the pregnancy and inherits the same mechanism.
- **Visits and APNCU.** The total number of visits is a count declared on the certificate, not
  a record of verified encounters. Without visit dates, APNCU can only be approximated.
- **Reverse causation.** Pregnancies with complications receive more visits. Part of the
  association is not an effect of care, and the study is one of association, not causation.
- **Coverage of the registry.** It covers live births only and does not link pregnancies of the
  same mother, so previous obstetric history is available only as self-report.
- **Period 2019–2023.** It includes the COVID-19 disruption of services, which is treated as a
  sensitivity of the definition.

## Changes from the previous version

1. The measure "visits accumulated up to a fixed index week" was replaced by *first-trimester
   start* and *landmark cohorts*, because SINAC does not record the date of each visit.
2. A simulation under the null hypothesis was added, to quantify the association that
   truncation produces on its own.
3. Two extras suggested in the review were incorporated, the ML + SHAP demonstration and the
   dashboard, marked as conditional.
4. What transfers to the INPer cohort was made precise: definitions, not a trained model.
5. The scope of the birth-weight sensitivity analysis was made precise, and reverse causation
   and COVID-19 were added as limitations.

### References

- Koroukian SM, Rimm AA. The "Adequacy of Prenatal Care Utilization" (APNCU) index to study low
  birth weight: is the index biased? *J Clin Epidemiol.* 2002;55(3):296–305.
- Kotelchuck M. An evaluation of the Kessner Adequacy of Prenatal Care Index and a proposed
  Adequacy of Prenatal Care Utilization Index. *Am J Public Health.* 1994;84(9):1414–1420.
- NOM-007-SSA2-2016, Para la atención de la mujer durante el embarazo, parto y puerperio, y de
  la persona recién nacida.
- DGIS. Guía para el correcto llenado del Certificado de Nacimiento (prenatal care section:
  trimester of the first visit and total number of visits).
