# Progress review · 30 October 2026

The written progress review of session 24, shared with the teacher over Slack. It describes the
state tagged as [`v0.2-progress`](https://github.com/martinruhle/sinac-prenatal-truncation/releases/tag/v0.2-progress)
(29 October 2026), so the repository can be reviewed at that tag without a meeting. Every result
below is read from the files of [`results/`](../results/) at the tag, rounded as shown.

**Question.** How much the association between prenatal care and preterm birth in Mexico changes
with the definition of the exposure and of the cohort, and how much of it truncation of the
gestational window produces on its own: a pregnancy that ends early has less time to accumulate
visits ([`protocol.md`](protocol.md#question)).

## 1. Where to look

| Path | What it holds |
|---|---|
| [`docs/protocol.md`](protocol.md) | The question, the cohorts, the four exposure measures, the models and the null simulation, each with a "what the run shows" section |
| [`docs/decisions.md`](decisions.md) | Every non-obvious decision with the rejected alternative; `[SCOPE CHANGE]` marks a change to the proposal |
| [`README.md`](../README.md) | How to reproduce, the course requirements mapped to their evidence, the changes from the proposal and the limitations |
| [`sql/cohorts/`](../sql/cohorts/) | The six cohort definitions in SQL on OMOP CDM v5.4, each with its attrition table |
| [`src/`](../src/) and [`scripts/`](../scripts/) | Pure functions (measures, APNCU, models, simulation) and the I/O around them; `scripts/pipeline.py` is the single entry point |
| [`results/`](../results/) | The five published tables and `manifest.json`, which records the commit, the sha256 of each source file and of each table |
| [`tests/`](../tests/) | 626 tests on synthetic fixtures, run by CI against the compose database |

A suggested order for a first read: the README, then §What the models show and §Null simulation
of the protocol, then `results/estimates.csv`.

## 2. What `v0.2-progress` delivers

- **Data.** The four SINAC files of 2020–2023 from DGIS open data, 6,531,527 records, loaded into
  Postgres with the OMOP CDM v5.4 ([`attrition.csv`](../results/attrition.csv), step 0).
- **Cohorts.** The base cohort holds 6,401,232 singleton births at 22 weeks or more (definition 1)
  and the analysis cohort 6,203,597 (definition 2). Definitions 3 to 5 are the landmark cohorts at
  weeks 28, 32 and 34, and definition 6 keeps multiple births.
- **Exposures.** (a) total visits in four levels and per count, (b) the approximate APNCU index,
  (c) care started in the first trimester, and (d) total visits in the landmark cohorts.
- **Estimates.** Crude and adjusted odds ratios for each measure, adjusted for maternal age,
  education, state and year.
- **Null simulation.** A world in which care has no effect and visits follow the NOM-007-SSA2-2016
  calendar, in two adherence scenarios (E1 perfect, E2 with misses).
- **Sensitivity.** Two axes on measures (a) and (c): the preterm cut-off at 34 and 32 weeks, and the
  definition with multiples.
- **Reproducibility.** The tag was rebuilt from a clean clone, which reproduced the sha256 of the
  five tables ([`reproducibility.md`](reproducibility.md)).

## 3. Results so far

Definition 2, 2020–2023, preterm under 37 weeks
([`estimates.csv`](../results/estimates.csv)). Odds ratios with 95 % intervals.

| Measure | Level, against the reference | Crude OR | Adjusted OR |
|---|---|---|---|
| (a) | 0 visits, against 8 or more | 1.943 (1.911–1.976) | 2.458 (2.415–2.501) |
| (a) | 1–4 visits | 1.704 (1.689–1.719) | 2.030 (2.011–2.049) |
| (a) | 5–7 visits | 1.362 (1.353–1.372) | 1.529 (1.518–1.540) |
| (d) week 34 | 5–7 visits, against 8 or more | 1.232 (1.223–1.242) | 1.357 (1.346–1.368) |
| (b) | Inadequate, against Adequate | 0.635 (0.629–0.640) | 0.575 (0.570–0.581) |
| (c) | trimester 0, 2 or 3, against trimester 1 | 1.000 (0.993–1.008) | 1.065 (1.057–1.073) |

What they show so far:

1. **Fewer visits go with more preterm births, but the measure that counts visits is the one that
   truncation can bias.** In the null world, truncation alone produces a larger difference in
   preterm births than the observed one for every level of (a) and (d): the share of the observed
   risk difference it reproduces runs from 1.5 (0 visits, both scenarios) to 16.1 (5–7 visits at
   the week-34 landmark, E1) ([`truncation_share.csv`](../results/truncation_share.csv)). The
   calendar is stricter than real care, so a share above 1 says that truncation *can* produce the
   association, not how much of it it does (protocol §What truncation alone explains).
2. **The odds ratios of (d) fall as the landmark week rises.** For 5–7 visits, adjusted: 1.529
   with no landmark, then 1.499, 1.435 and 1.357 at weeks 28, 32 and 34.
3. **APNCU (b) is inverted on SINAC.** "Inadequate" and "Intermediate" have fewer preterm births
   than "Adequate". The expected visits of the index depend on the completed weeks at delivery, the
   variable that defines the outcome, so its odds ratio measures an artefact of its construction
   (Koroukian and Rimm, 2002). The null world reproduces the inversion, with shares of 32.6 and
   23.6 in E1.
4. **First-trimester start (c), the measure truncation does not touch, has no crude association**
   (1.000) and a small adjusted one (1.065). In the protocol, younger mothers start later and have
   fewer preterm births, and the two groups cancel out in the crude odds ratio.
5. **Sensitivity.** A lower cut-off moves every odds ratio of (a) away from 1, to 7.978 for 0
   visits under 32 weeks. Including multiples moves the adjusted odds ratios towards 1 (2.181 for 0
   visits).

## 4. Changes from the proposal

Stated in full in [README §Changes from the proposal](../README.md#changes-from-the-proposal):

- the source is the DGIS open data instead of the INSP standardized series;
- the period is 2020–2023 instead of 2019–2023;
- the adjusted models use a reduced covariate set, and insurance becomes a gradient;
- the full sensitivity grid runs for measures (a) and (c) only;
- three sensitivity axes are dropped (the month rule of APNCU, birth weight under 2,500 g as an
  outcome, and births before week 22).

## 5. What is left for `v1.0` (20 November)

From [`roadmap.md` §3](roadmap.md#3-milestones-of-the-semester):

- **Analysis.** The period axis (2020–2023 against 2022–2023), the gradients by state and by
  insurance, and APNCU on the NOM-007 calendar.
- **Engineering.** The analysis image (`Dockerfile`), a complete entry point and a security
  review.
- **Documentation.** The limitations section closed, the release archived on Zenodo with a DOI.
- **In progress.** A documented literature search on gestational-length truncation of
  prenatal-care measures (issue #58), so that the report makes no unsourced claim about prior work.
- **After this review.** The feedback goes into the re-planning of the remaining weeks (issue #48),
  before the presentation of 24 November.

