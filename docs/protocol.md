# Protocol

The question, the data and the methods of the study. The question is stated in
[`proposal_v2.md`](proposal_v2.md); scope changes against it are listed in
[`roadmap.md`](roadmap.md) and argued in [`decisions.md`](decisions.md).

**Draft.** Everything but the limitations is written: the question, the data, the design, the
cohorts and their attrition, the outcome, the exposure measures, the analysis, the null simulation
and the output tables. The limitations are PENDING; they are completed for milestone `v1.0`.

## Question

How much does the association between prenatal care and preterm birth in Mexico change according
to how the exposure and the cohort are defined, and how much of that association can be produced
by truncation of the gestational window alone? It is answered in three parts, stated in full in
[`proposal_v2.md`](proposal_v2.md#question): four measures of prenatal care compared on one
population, a simulation under the null hypothesis, and the sensitivity of the answer to the
definition of the cohort and of the exposure.

## Data source

SINAC birth records published by SSA/DGIS as open data, one ZIP per year (D-001). Every file the
project uses is declared in [`../config/sources.yml`](../config/sources.yml) with its URL, its
published version and its sha256, and what each file contains, and how the two catalogue periods
differ, is measured in [`source_inventory.md`](source_inventory.md). The files are served over
HTTP without TLS: the sha256 detects a later change to a file, it does not authenticate the first
download.

### Study period: 2020–2023

| Year | Records | Descriptor | Catalogues |
|---|---|---|---|
| 2020 | 1,747,847 | 2020–2025 | 2020–2023 |
| 2021 | 1,639,479 | 2020–2025 | 2020–2023 |
| 2022 | 1,622,921 | 2020–2025 | 2020–2023 |
| 2023 | 1,521,280 | 2020–2025 | 2020–2023 |
| **Total** | **6,531,527** | | |

Records are the rows of each year's CSV, as measured in the source inventory (table 1). The four
years are one catalogue period: one descriptor, one catalogue set, and CSV headers identical in
names and order. Development and milestone `v0.1-cohort` run on 2023 alone (D-009). Every
pipeline step that reads records takes `--years`, whose default is this period.

**This is a scope change against proposal v2, which committed to 2019–2023 (D-041).** Nothing in
the question needs a pre-pandemic year. Truncation of the gestational window operates within
each pregnancy, in any calendar year. Neither the comparison of the four measures nor the null
simulation depends on the calendar.

Adding 2019 would add 1,868,214 records, at a cost the source inventory measures:

- 74 of its 76 variables are renamed, and the file has another format (LF line endings, no
  quoting) and carries free-text fields.
- DGIS publishes no descriptor for 2015–2019, so the meaning of every 2019 variable rests on
  sources that describe the layout but not that year.
- Maternal education needs a crosswalk with information loss, because the two code systems share
  only `88` and `99`.
- Insurance needs a rule to collapse `DERHAB` and `DERHAB2` into `AFILIACION`.
- Three missing-value codes change role between the periods (`00`, `88`, `99`).

None of these code changes falls on an exposure or the outcome. The project uses eight coded
variables:

- Five change their valid categories: education, insurance, pregnancy multiplicity, newborn sex
  and CLUES.
- Two change only missing-value or peripheral codes: prenatal care received and state.
- The trimester of the first visit keeps all six codes.

Total visits and gestational age have no catalogue in either period. One risk of 2019 does touch
the outcome, and it was not measured. For 2015–2019 DGIS publishes an acceptable range of 13 to
42 weeks for `GESTACH`; for 2020–2023 it publishes only sentinel values. Whether that range was
enforced at capture is unknown.

Restricting the period to 2023 alone was also rejected. 2020–2022 share the format, descriptor
and catalogues of 2023, so they cost no harmonisation. Without them, the year covariate and the
COVID-19 sensitivity axis of the proposal disappear.

### Year of birth

Year of birth enters the analysis in two ways, which answer different questions (D-049):

- **As a categorical covariate** in the adjusted odds ratios. It absorbs differences in level
  between years, in prenatal care and in preterm birth alike. It is categorical rather than
  linear because the pandemic is a shock, not a trend.
- **As the COVID-19 sensitivity axis.** The estimates on 2020–2023 are set against the same
  estimates on 2022–2023 (`--years 2022,2023`), for measures (a) and (c) (D-003). Because the
  period starts in 2020, this sets years of acute disruption against years of recovery, not
  against a pre-pandemic baseline.

### What the period does not allow

- **No pre-pandemic reference.** The secular trend and the effect of the pandemic cannot be told
  apart.
- **2022–2023 is not a baseline.** The health system changed inside the period, as the 2020–2023
  insurance catalogue itself records ("SEGURO POPULAR / INSABI", "IMSS BIENESTAR").
- **Year of birth is a coarse proxy for exposure to the pandemic.** What matters is the window of
  each pregnancy, not the year of the birth. A birth in January 2020 had its prenatal care before
  the pandemic, and a birth in January 2022 had it in 2021.
- **Comparability with the literature is limited by the data, not by the length of the period.**
  The study that showed the APNCU bias used a single state registry (591,403 births in Ohio;
  Koroukian and Rimm, 2002), and 2023 alone holds 1,521,280 records. What limits comparability is
  already stated in the proposal:
  - SINAC records the trimester of the first visit, not the month, so APNCU is approximated.
  - The visit count is declared on the certificate.
  - The health system is a different one.

### Reversal criterion

The decision is reversed only by adding 2019, and only under D-050:

- `v0.2-progress` has been tagged with all of its committed content.
- 2019 then gets a timebox of one week of the budget (6 hours) before work on `v1.0` starts.
- If it does not close within the timebox, 2019 moves to future work.

To keep that cost to the harmonisation itself, the ETL reads each catalogue period through its
own adapter, which maps source column names to canonical names. It also registers each period's
codes as a source vocabulary of its own in `source_to_concept_map`. Adding 2019 then means an
adapter, mapping rows and the 2019 part of the data dictionary, and no change to cohort or
analysis code.

## Design and unit of analysis

A characterization study on records collected in routine practice (modality A). The design is
cross-sectional at the level of the birth certificate: prenatal care and the outcome are recorded
on the same document, at delivery, and no record is followed over time. No criterion and no
measure uses the date of a prenatal visit, because SINAC does not record them (rule 4 of
[`../CLAUDE.md`](../CLAUDE.md)).

**The unit of analysis is the live-birth certificate**, and the base cohort keeps singletons only,
so one certificate is one pregnancy that ended in a live birth. The pregnancy is the unit the
question is about, because the exposure (prenatal care) and the outcome (gestational age) are
properties of the pregnancy and not of the newborn. Restricting the cohort to singletons makes the
observed unit coincide with it, without linking any record to any other.

Where the two do not coincide, the pregnancy cannot be reconstructed. SINAC publishes no mother
and no pregnancy identifier, so the certificates of one multiple pregnancy cannot be grouped:
`ORDENPRODUCTO` is absent in 35,868 of the 110,475 certificates from multiple pregnancies, and a
pregnancy whose first product was stillborn has no certificate with order 1 at all, because SINAC
certifies live births. Keeping one certificate per multiple pregnancy would therefore discard
about a third of them, and not at random (D-051). In the sensitivity analysis that includes
multiples, each certificate is one unit, so a multiple pregnancy weighs as many units as it has
live-born children.

What this implies for the OMOP mapping (the detail is in [`omop_mapping.md`](omop_mapping.md)):

- One `PERSON` for the mother and one for the newborn per certificate, linked through
  `FACT_RELATIONSHIP` (D-103, D-104). Only the mothers are subjects of the cohorts (D-106).
- **The mother `PERSON` is one per certificate, not one per woman.** A woman with two births in
  2020–2023 becomes two `PERSON` records. This is a documented deviation from the OMOP convention
  that a `PERSON` is a unique individual, and it is unavoidable here: no published variable
  identifies the mother, and probabilistic linkage on her date of birth, residence and delivery
  unit was rejected because nothing in these files could validate it (D-051).
- A `COHORT` row is (definition, subject, start, end) with a person as the subject, so one row of
  the base cohort is one certificate and one pregnancy.
- Certificates of the same woman are independent rows in every analysis, and how many women have
  more than one birth in the period cannot be measured. That is a limitation, not a choice.

## Base cohort

Every criterion is executable from the published files alone. Source values are quoted as DGIS
publishes them, and the source of each rule is the 2020–2025 variable descriptor
(`Descriptores_SINAC_2020.xlsx`) or the named catalogue of the 2020–2023 catalogue set, both
inventoried in [`source_inventory.md`](source_inventory.md).

| # | Criterion | Kind | Rule | Source of the rule |
|---|---|---|---|---|
| 1 | Live birth of the study period | coverage | year of `FECHANACIMIENTO` in `--years` (default 2020–2023) | descriptor: `FECHANACIMIENTO`; D-041, D-052 |
| 2 | Mother resident in Mexico | coverage | `RESIDEEXTRANJERO` = 2 ("NO") | catalogue `SI_NO` |
| 3 | Gestational age specified | validity | `EDADGESTACIONAL` ≠ 99 | descriptor: 99 = "No Especificado" |
| 4 | Multiplicity specified | validity | `PRODUCTOEMBARAZO` ≠ 0 | catalogue `PRODUCTO_EMBARAZO`: 0 = "NO ESPECIFICADO" |
| 5 | Singleton | design | `PRODUCTOEMBARAZO` = 1 ("ÚNICO") | catalogue; sensitivity axis (D-054) |
| 6 | 22 completed weeks or more | design | `EDADGESTACIONAL` ≥ 22 | NOM-007-SSA2-2016 §3.45 and §3.1 (D-053) |

Each of the following notes is a decision, not a detail:

- **No criterion uses an exposure variable.** Missing prenatal care data is handled with the
  exposure definitions, so that the four measures are compared on one population. The rule is in
  [§Exposure measures](#one-set-of-records-for-the-four-measures), and it is a step of the analysis
  cohort, not of the base cohort (D-086, D-087).
- **Criterion 1 needs no exception for late certification.** In each of the four files, every
  record is a birth of that file's year; the certificates dated in the following year (6,496 to
  12,533 per file) stay in the file of the year of birth, and the median lag between birth and
  certification is 0 days. `FECHACERTIFICADO` is used by no criterion (D-052). What stays
  invisible is a birth certified after DGIS closed that year's file.
- **Criterion 4 is separate from criterion 5 on purpose.** `PRODUCTOEMBARAZO` = 0 is a question
  the certifier did not answer: such a record is neither a known singleton nor a known multiple,
  so it can enter neither the base cohort nor the definition that includes multiples. Merging the
  two criteria would hide those records inside the count of a design exclusion (D-056).
- **631 records carry `RESIDEEXTRANJERO` = 88**, a code the `SI_NO` catalogue does not publish (it
  publishes 8 for "NO APLICA"); all of them have `ENTIDADRESIDENCIA` = 00. They are treated as
  residence unknown and leave with criterion 2. `FOR APPROVAL` (D-057).
- **Residence, not place of delivery, defines the cohort and the state gradient.** Prenatal care
  is received where the mother lives, and 4.9 % of births happen outside the state of residence,
  up to 11.9 % for residents of the state of México. `ENTIDADFEDERATIVAPARTO` describes referral
  and is no eligibility criterion (D-057).
- Mothers resident in Mexico whose state is not specified (`ENTIDADRESIDENCIA` 00 or 99, 6,501
  records) stay in the cohort and leave only the state gradient.
- **Exact duplicates are not removed.** 213 singleton records repeat another record in all 64
  published columns (0.003 %). SINAC publishes no identifier that could confirm a duplicate
  certificate, so they are counted and reported, not dropped (D-058).

## Outcome

**Preterm birth: gestational age under 37 completed weeks**, in a cohort that starts at 22
completed weeks. Both bounds are published in NOM-007-SSA2-2016 (DOF, 7 April 2016). §3.25 defines
a preterm birth as one that "ocurre antes de las 37 semanas completas (menos de 259 días) de
gestación", and §3.45 defines a preterm newborn as one whose gestation "haya sido de 22 a menos de
37 semanas"; §3.1 places the 500 g of the definition of abortion at approximately 22 completed
weeks. The outcome is binary: 22 to 36 weeks against 37 weeks and over.

`EDADGESTACIONAL` is the only source of the outcome: completed weeks as an integer, with 99 = "No
Especificado" as the only value the descriptor declares to be a sentinel.

- **"Not specified" leaves the cohort at its own attrition step** (criterion 3), neither before
  the attrition nor as a category of the outcome: an odds ratio needs a known outcome.
- **No plausibility range is applied.** DGIS publishes no acceptable range for `EDADGESTACIONAL`
  in 2020–2023; the 13-to-42-week range of `CatVariables.csv` belongs to the 2015–2019 catalogue
  period ([`source_inventory.md`](source_inventory.md)). Every value other than 99 recorded in the
  four files lies between 13 and 45 weeks, and any upper cut would remove records classified as not
  preterm without changing one classification, at the price of an unsourced threshold (D-021,
  D-053).
- **The alternative cut-offs (34 and 32 weeks) are a sensitivity axis on the outcome, not a
  criterion of the cohort**: only the threshold moves, the cohort and its attrition do not.
- The records that leave for an unspecified gestational age are not like the rest: 8.5 % of them
  record no prenatal care against 2.6 %, 59.1 % a first-trimester start against 75.8 %, and 21.8 %
  a birth at home, in the street or elsewhere against 2.5 %. They are 0.074 % of the files, and
  that fraction is what bounds the bias they can introduce; the size of the registry is not an
  argument for excluding anything. **The comparison of the excluded records against the retained
  ones is published next to the attrition table** for the two validity steps, as RECORD and STROBE
  ask.

## Attrition

Attrition is sequential: a record that fails two criteria is counted only in the first step it
fails, so the order changes the count of every step, and not the final size. The order is **data
model, then coverage, then validity, then design**.

| # | Step | Kind | Rule | Removed | Remaining |
|---|---|---|---|---|---|
| 0 | Records in the files of the study period | — | — | — | 6,531,527 |
| 1 | Mother's year of birth known | data model | loaded as a mother `PERSON` ([`omop_mapping.md`](omop_mapping.md#person-the-mother)) | 670 | 6,530,857 |
| 2 | Born in the study period | coverage | criterion 1 | 0 | 6,530,857 |
| 3 | Mother resident in Mexico | coverage | criterion 2 | 3,698 | 6,527,159 |
| 4 | Gestational age specified | validity | criterion 3 | 4,806 | 6,522,353 |
| 5 | Multiplicity specified | validity | criterion 4 | 10,115 | 6,512,238 |
| 6 | Singleton | design | criterion 5 | 110,305 | 6,401,933 |
| 7 | 22 completed weeks or more | design | criterion 6 | 701 | **6,401,232** |

The two count columns are orientation for the decisions taken here, measured once over the four
record files of 2020–2023 with a throwaway query (the practice of D-047). On 2023 alone, step 1
removes nothing. The table of record is the one the cohort SQL produces, per year and per
definition (rule 5 of [`../CLAUDE.md`](../CLAUDE.md)): [`../sql/cohorts/`](../sql/cohorts/) writes
it into `results.attrition` with `pipeline.py cohorts` (D-078), and `pipeline.py publish` writes the
base cohort's to [`../results/attrition_base.csv`](../results/attrition_base.csv), with a manifest
that names the commit and the source files (D-080). Step 0 counts the staged records
and step 1 the ones the ETL could not load, so the table starts from the files and not from the
CDM. Both are rows of `results.etl_counts`, per year: `staging` `rows` and `person`
`not_loaded:no_year_of_birth` (D-073).

Why this order (D-056, D-060):

- **The data model** comes first because a record that OMOP cannot hold never reaches the cohort
  SQL. `year_of_birth` is required, and 670 records carry neither the mother's date of birth nor
  her age: 579 in 2020, 68 in 2021, 23 in 2022, none in 2023. It is not a criterion of the study,
  it is the same in every definition, and no value for those records could be written without
  inventing it.
- **Coverage** answers whether the record belongs to the population this study takes from the
  registry (steps 2 and 3). **Validity** answers whether the value the study needs is there and
  usable (steps 4 and 5). **Design** answers whether the record belongs in the main question
  (steps 6 and 7).
- The data-model, coverage and validity steps are identical in every definition of the cohort,
  so the attrition table of a sensitivity definition differs from this one only in its tail, and
  the reader sees exactly what the axis changed.
- A numeric criterion has to come after the step that removes the sentinel which would pass it:
  99 ≥ 22 is true, so step 7 cannot precede step 4.
- The effect of the order, measured: with the singleton step placed first, step 4 removes 4,641
  records instead of 4,806, because the multiples with no gestational age are counted earlier.

## Sensitivity of the definition

Every axis has two sides, and the base cohort takes exactly one of them: no criterion is both an
exclusion of the base cohort and an axis on that same side (D-054).

| Axis | Base cohort | Alternative definition |
|---|---|---|
| Multiple pregnancies | Excluded (criterion 5) | Included, each certificate one unit |
| Preterm cut-off | Under 37 weeks | Under 34, under 32 |
| Period (COVID-19) | 2020–2023 | 2022–2023 (D-049) |
| Births before 22 weeks | Excluded (criterion 6) | **No axis** (D-055): the step removes 701 of the 6,401,933 records that reach the step |

The full grid runs for measures (a) and (c) only (D-003). How each alternative definition is
estimated and reported, and the gradients by state and by insurance, are in
[§Analysis](#sensitivity-analyses-and-gradients). The landmark weeks of measure (d) are in
[§Exposure measures](#the-measures).

## Exposure measures

The certificate records prenatal care in three items, all declared at delivery:

- `ATENCIONPRENATAL`: whether the mother received prenatal care (catalogue `SI_NO`).
- `TRIMESTREPRIMERCONSULTA`: the trimester of the first visit, where 0 is "NO RECIBIÓ" (catalogue
  `TRIMESTRE_PRIMER_CONSULTA`).
- `TOTALCONSULTAS`: the number of visits during the pregnancy, a count with 99 "No Especificado".

No item records the date of a visit, and no measure uses one (rule 4 of
[`../CLAUDE.md`](../CLAUDE.md)). The DGIS filling guide asks for the trimester and the count only
when care was received. It has 0 visits written when no care was received, and "Se ignora" chosen
when the answer is unknown. It counts every visit to a health professional, including visits for
problems of the pregnancy.[^guide]

[^guide]: DGIS, *Guía para el correcto llenado del Certificado de Nacimiento, Modelo 2025*,
    question P13. It is the only edition at hand and it is later than the study period, so the
    wording of the certificates of 2020–2023 has not been checked against it.

### One set of records for the four measures

The four measures are computed on the same records, so that a difference between two measures is
never a difference of population (D-086). A record has known prenatal care data when all of these
hold:

1. `TRIMESTREPRIMERCONSULTA` is 0, 1, 2 or 3. Codes 8 "NO ESPECIFICADO" and 9 "SE IGNORA" and a
   blank are missing.
2. `TOTALCONSULTAS` is a count: neither 99 nor blank.
3. The two agree: the trimester is 0 "NO RECIBIÓ" if and only if the count is 0.
4. The trimester is possible given the delivery: a first visit in the third trimester needs 28
   completed weeks or more at delivery ([§Trimester boundaries](#trimester-boundaries)).

Why these rules:

- **Rule 3 is the rule of the APNCU program** (Kotelchuck, version 3, 1994). The program recodes
  both items to missing when one says there was no care and the other says there was. 110 records
  break it: 93 with trimester 0 and visits, 17 with a trimester and no visits.
- **The program's default for an unknown start does not fit SINAC.** By default it reads 0 visits
  with an unknown start as no care, and it tells the user to change that default when it does not
  fit the data. In SINAC, 33,860 records carry 0 visits with trimester 8 or 9. Among all the
  records with 0 visits, 30,932 also answer "SE IGNORA" or "NO ESPECIFICADO" to whether care was
  received. There the zero reads as unknown, not as no care.
- **`ATENCIONPRENATAL` is used by no rule.** Trimester 0 already records that no care was
  received, and the item is only described.
- Rule 4 removes 295 records.

The four rules form the step "prenatal care data known and coherent" of the analysis cohort
([§Records analysed](#records-analysed)). Measured once as orientation, the step removes 153,707
records of the base cohort (2.4 %). 7.90 % of them are preterm, against 7.05 % of the retained
records, and the two groups are compared in `excluded_profile.csv`.

### The measures

| Measure | Built from | Levels | Reference | Truncation |
|---|---|---|---|---|
| (a) Total visits | `TOTALCONSULTAS` | 0; 1–4; 5–7; 8 or more | 8 or more | Truncated by the length of the pregnancy |
| (a) per count | `TOTALCONSULTAS` | each count observed, 0 to 30 in 2020–2023 | 8 | As (a). Its high counts also carry the visits of complicated pregnancies |
| (b) APNCU | trimester, count, completed weeks at delivery | Inadequate; Intermediate; Adequate; Adequate Plus | Adequate | Over-corrected: it divides by the visits expected up to delivery |
| (c) First-trimester start | `TRIMESTREPRIMERCONSULTA` | trimester 1; trimester 0, 2 or 3 | trimester 1 | None: every pregnancy of the cohort passed the first trimester |
| (d) Total visits in landmark cohorts | as (a), on the landmark cohorts | as (a) | 8 or more | Bounded to the weeks after the landmark |

Each reference is care that meets the norm, so in every measure an odds ratio above 1 reads as
less care being associated with more preterm birth.

- **(a)** The cut points come from NOM-007-SSA2-2016 §5.2.1.15, copied in
  [`../config/nom007_schedule.yml`](../config/nom007_schedule.yml) (D-088):
  - 0 is no care;
  - five visits is the minimum the norm asks for;
  - eight is its full calendar.
- **(a) per count** (D-088). Each count is a level of its own, with 8 as reference, so the curve
  of odds ratios can bend. An odds ratio per additional visit would force a straight line onto a
  curve that falls and then rises. The high counts include the visits of complicated pregnancies,
  which the guide counts and which the null calendar cannot produce
  ([§Null simulation](#what-it-computes)).
  - It is reported in the main analysis only.
  - Counts heap at 10, 12, 15, 20 and 25, and at 30, the largest count recorded. Counts above 20
    are few, so their intervals are wide. No count is grouped, because a grouping threshold would
    have no source.
- **(c)** A binary measure (D-089). More levels would bring truncation back: a first visit in the
  third trimester needs a pregnancy that reached the third trimester. "NO RECIBIÓ" belongs to the
  group that did not start in the first trimester.
- **(d)** "Reached week X" means `EDADGESTACIONAL` ≥ X, because the completed weeks at delivery are
  the only record of how far a pregnancy went (D-090). The landmarks are weeks 28, 32 and 34, as
  proposal v2 set them:
  - 28 and 32 are the WHO bounds of extremely and very preterm birth. 34 is the start of late
    preterm birth, 34 0/7 to 36 6/7 weeks (Raju et al., 2006).
  - With the base cohort, which starts at 22 weeks, they give four points. An odds ratio that
    falls as the landmark rises is the signature of truncation.
  - A landmark restricts the cohort through the variable of the outcome. That is design, as
    criterion 6 is, and not a predictor (rule 3).
  - A landmark also changes what preterm means. In the landmark cohort of week 34, a preterm birth
    is one at 34 to 36 weeks.
  - The landmark must stay below the preterm cut-off, so landmark cohorts use the cut-off of 37
    weeks only. D-003 already keeps (d) out of the sensitivity grid.

### APNCU (measure b)

Measure (b) is the Adequacy of Prenatal Care Utilization index (Kotelchuck, 1994). It is computed
with the algorithm of its SAS computational program, version 3 (September 1994), which publishes
the full table that the article summarises in one example (D-091). The algorithm has four steps:

1. **Expected visits for the length of the pregnancy.** They come from the ACOG schedule for
   uncomplicated pregnancies: a visit a month to week 28, one every two weeks to week 36, and one
   a week after that.

   | Completed weeks at delivery | 22–25 | 26–29 | 30–31 | 32–33 | 34 | 35 and over |
   |---|---|---|---|---|---|---|
   | Expected visits | 5 | 6 | 7 | 8 | 9 | weeks − 26 (14 at 40) |

   The program also lists 0 to 21 weeks, which the cohort does not contain.
2. **Minus the visits missed before the month care began.** The adjustment is 0 for month 1, then
   1, 2, 3, 5, 6, 7, 9 and 13 for months 2 to 9. The expected count is never below 1.
3. **Received services: observed visits over expected visits.** The ratio gives four levels:
   Inadequate up to 49.99 %, Intermediate up to 79.99 %, Adequate up to 109.99 %, and Adequate
   Plus above.
4. **Summary index.** It is Inadequate when care began after month 4, when there was no care, or
   when received services are Inadequate. Otherwise it takes the level of received services.

What SINAC changes in the algorithm:

- **Month from trimester** (D-092, `FOR APPROVAL`). SINAC records the trimester of the first
  visit, so each trimester takes its middle month: 2, 5 and 8.
  - With this rule every start in the second trimester falls after month 4, so it is Inadequate
    whatever its visits. With the first month of each trimester they would all pass the month-4
    bound, and with the last none would.
  - The article groups initiation by pairs of months because a trimester is too broad, and SINAC
    records exactly that coarser category.
  - The sensitivity to the rule was cut (D-005, [`roadmap.md`](roadmap.md#43-definition-axes-left-out-of-the-sensitivity-analysis)).
    The function takes the rule as a parameter.
- **The program's consistency check is applied to the trimester.** Part 3a of the program sets a
  start month above weeks ÷ 4 to missing. Applied to an imputed month 8, it would remove 967 births
  that started care in the third trimester and were delivered at 28 to 31 weeks, all of them
  preterm. Rule 4 of the common set checks the trimester instead (D-092). Those births stay, and
  they are Inadequate anyway, because care began after month 4.
- **The other parts change nothing.**
  - The range edits of part 3a remove no record of the cohort.
  - Part 4, which imputes a missing gestational age from birth weight, is not used. Records
    without a gestational age leave at criterion 3, and birth weight is never used (rule 3).

**The index contains the outcome.** Its expected visits depend on the completed weeks at delivery,
so APNCU is derived from gestational age. Its odds ratio measures the artefact of its construction,
which Koroukian and Rimm (2002) showed. It is never read as an effect and never used as a predictor
of a model (rule 3), and that is why measure (c) is the comparison free of truncation.

**Reference schedule.** The main analysis uses the ACOG schedule, as the program does, so the index
is Kotelchuck's and can be compared with the literature. The ACOG schedule asks for more visits than
NOM-007, so more mothers fall in the lower levels than the Mexican norm would place there.

A variant on the NOM-007 calendar is planned for `v1.0`. It is the same algorithm, with the expected
visits taken from [`../config/nom007_schedule.yml`](../config/nom007_schedule.yml). Its own rules,
how a range of weeks is read and which visits a later start misses, are written with it and are
`FOR APPROVAL`.

### Trimester boundaries

The first trimester runs to 13 completed weeks, the second from 14 to 27, and the third from 28
(D-092, `FOR APPROVAL`).

- **No source defines them.** The descriptor, the catalogue and the 2025 filling guide do not:
  question 13.2 asks only for the trimester. NOM-007-SSA2-2016 §5.2.1.16 places the first-trimester
  scan at weeks 11 to 13.6 and the third at 29 to 30 or later, which agrees with these bounds but
  does not set them.
- **They are used twice:** by rule 4 of the common set, and for the first visit of a simulated
  pregnancy. The month rule of APNCU does not use them.

## Analysis

### Records analysed

| Definition | Built as | Removed, orientation |
|---|---|---|
| 1 · Base cohort | [§Base cohort](#base-cohort) | — |
| 2 · Analysis cohort | Definition 1, then the step "prenatal care data known and coherent", then the step "covariates known" | 153,707, then 44,063 |
| 3 · Landmark 28 | Definition 2, then the step "reached week 28" | 14,117 (423,074 preterm births stay) |
| 4 · Landmark 32 | Definition 2, then the step "reached week 32" | 50,891 (386,300 preterm births stay) |
| 5 · Landmark 34 | Definition 2, then the step "reached week 34" | 100,264 (336,927 preterm births stay) |

- **Every definition has its own attrition table** (rule 5 of [`../CLAUDE.md`](../CLAUDE.md)).
  Each sensitivity definition repeats the same tail after its own prefix (D-087).
- **Definition 2 is [`../sql/cohorts/02_analysis.sql`](../sql/cohorts/02_analysis.sql)**, with
  steps 8 and 9 of its attrition (D-107). It reads measures (a) and (c), which
  [`../sql/cohorts/exposure.sql`](../sql/cohorts/exposure.sql) writes for every mother into
  `results.exposure` (D-108).
- **The counts are orientation**, measured once with a throwaway query over an approximation of the
  base cohort that differs from it by 526 records. The table of record is the one the cohort SQL
  writes.
- **The records removed at "covariates known" differ a little from the rest.** 7.76 % are preterm
  and 70.7 % started care in the first trimester, against 7.05 % and 77.2 % of the retained ones.

### Model

The odds ratios come from one model, specified once (D-093):

- **The model.** A binomial generalized linear model with a logit link, fitted on an aggregated
  table with one row per combination of levels of the exposure and the covariates. Each row holds
  its births and its preterm births. With every term categorical, its estimates are those of a
  logistic regression on the individual records. The aggregated table is built in SQL.
- **Crude and adjusted.** The crude model has the exposure alone. The adjusted model adds the
  covariates below. Both use the same records of a definition, so the difference between them is
  confounding, not population.
- **One model per measure.** The measures are never adjusted for one another. For (a) per count,
  the table has one row per count.
- **What is reported.** 95 % Wald confidence intervals. The coefficients of the covariates are not
  reported: the model is built to estimate the exposure, and those coefficients have no causal
  reading in it.

### Covariates

D-094 is a `[SCOPE CHANGE]` against proposal v2, and it specifies D-007.

| Covariate | Source | Levels | Reference | Missing |
|---|---|---|---|---|
| Maternal age | `EDAD`, completed years | under 15; 15–19; 20–24; 25–29; 30–34; 35–39; 40 and over (`FOR APPROVAL`) | 20–24 | `888`, `999`; neither occurs in the base cohort |
| Education | `ESCOLARIDAD` | none (1); primary (31, 32); secondary (51, 52, 111, 112); upper secondary (71, 72, 131, 132); higher (81, 82, 101, 102) (`FOR APPROVAL`) | secondary | `0`, `88`, `99`, blank |
| State of residence | `ENTIDADRESIDENCIA` | the 32 states | `15` (México) | `00`, `88`, `99`, blank |
| Year of birth | `FECHANACIMIENTO` | 2020 to 2023, categorical (D-049) | 2023 | none |

- **Age in five-year groups.** Preterm birth rises from 6.2 % at 20–24 to 11.4 % at 40 and over,
  and it is 8.9 % under 15. Three groups would blur that curve.
- **Education by the general level attended**, complete or not. A technical program counts at the
  general level it requires.
- **The reference is the largest level**, except for the year. Its reference, 2023, belongs to
  every definition, including 2022–2023. The reference of a covariate does not change the odds
  ratio of the exposure.
- **Insurance is not adjusted for**, for two reasons:
  - 10.2 % of the base cohort has no usable value (`99` "SE IGNORA", `00` "NO ESPECIFICADO",
    `88` "NO APLICA"), against 0.7 % at most for the covariates kept.
  - Its categories changed meaning inside the period. In the analysis cohort, the records declaring
    Seguro Popular/INSABI fell from 258,936 in 2020 to 117,078 in 2021, while those declaring no
    affiliation rose from 630,384 to 743,555.

  It enters as the gradient by insurance instead, where an unknown value is a level of its own.
- **Maternal age is the age declared on the certificate.** It reaches the CDM as it was declared,
  not computed from the mother's year of birth, which would move 9.9 % of the base cohort to
  another age group ([`omop_mapping.md`](omop_mapping.md#measurement), D-100).

### Missing covariates

A record without age, education or state of residence leaves the analysis cohort at the step
"covariates known", with its count in the attrition table (D-095). This is a complete-case
analysis.

- The step removes 0.7 % of the records.
- An "unknown" level would keep confounding inside that level.
- Multiple imputation would need the individual records that the aggregated table avoids, to
  recover less than 1 %.

### Sensitivity analyses and gradients

D-099 sets how the alternatives are estimated and reported.

- **Each alternative definition** of [§Sensitivity of the definition](#sensitivity-of-the-definition)
  runs the crude and adjusted models of measures (a) and (c) (D-003).
  - The cut-offs of 34 and 32 weeks change only the outcome.
  - The definition with multiples and the period 2022–2023 change the cohort, and each carries its
    attrition.
  - `v0.2-progress` carries one or two of them, the cut-off first (D-012), and the others land in
    `v1.0`.
- **In the definition with multiples, each certificate is one unit.** Its confidence intervals
  ignore that the twins of one pregnancy are not independent, because no published variable groups
  them (D-051).
- **Gradients (`v1.0`).** The adjusted odds ratios of (a) and (c) are fitted separately within
  each state of residence and within each insurance group, with the other covariates. The
  insurance groups are `FOR APPROVAL`:

  | Group | `AFILIACION` codes |
  |---|---|
  | IMSS | 02 |
  | ISSSTE | 03 |
  | Other social security | 04 PEMEX, 05 SEDENA, 06 SEMAR, 11 ISSFAM |
  | No social security | 01 NINGUNA, 07 SEGURO POPULAR / INSABI, 10 IMSS BIENESTAR |
  | Other | 08 OTRA |
  | Unknown | 00, 88, 99 |

  Codes 01, 07 and 10 form one group because records moved between them inside the period, as
  shown above. A gradient by code would read that move as a change of coverage.

### Output tables

The output tables are defined here, before anything runs (D-098).

- **What they cover.** All of them cover 2020–2023 pooled, with the year as a covariate. The
  attrition is per year.
- **Where they go.** `pipeline.py publish` writes them to `results/` at a milestone (D-014, D-080).
- **What is not versioned.** The aggregated table of counts stays in the `results` schema of the
  database.

| File | One row per | Columns |
|---|---|---|
| `attrition.csv` | definition, year of the record files, step | those of `attrition_base.csv`, which it replaces at the `v0.2-progress` publish |
| `exposure_distribution.csv` | source, definition, period, outcome cut-off, measure, variant, level, outcome | births |
| `estimates.csv` | estimate | source, definition, period, outcome cut-off, measure, variant, level, reference, model, stratum variable, stratum value, births, preterm births, odds ratio, lower and upper limits of the 95 % interval |
| `truncation_share.csv` | definition, measure, variant, level, scenario | observed crude odds ratio, simulated odds ratio, share |
| `excluded_profile.csv` | definition, step, group (retained, excluded) | births, % preterm, % first-trimester start, % no prenatal care, % born outside a health facility |

The columns take these values:

| Column | Values |
|---|---|
| source | `observed`, `sim_e1`, `sim_e2` |
| measure | `a`, `a_count`, `b`, `c`, `d` |
| variant | `acog_midpoint` for (b), and `nom007_midpoint` in `v1.0`; empty for the other measures |
| model | `crude`, `adjusted` |
| stratum variable | empty, `state` or `insurance` |
| % preterm | empty for the records that leave for an unknown gestational age |

## Null simulation

The simulation builds a world in which prenatal care has no effect on preterm birth. Visits follow
the NOM-007 calendar, and the only link between visits and preterm birth is that delivery stops the
calendar. Whatever association appears in that world is the one truncation produces on its own
(D-096, D-097).

### Pregnancies

- **One simulated pregnancy per record of the analysis cohort**, with that record's completed weeks
  at delivery. The delivery weeks are then the empirical distribution of definition 2, read from
  the aggregated table, and the size equals that of definition 2.
- **The trimester of the first visit is drawn independently of the delivery week**, from its
  distribution in definition 2.
- **The first visit is the first one of the calendar in that trimester.** That is visit 1 (week 6)
  for the first trimester, visit 3 (week 16) for the second and visit 5 (week 28) for the third
  ([§Trimester boundaries](#trimester-boundaries)).
- **A visit happens when the completed weeks at delivery reach its first week** (`FOR APPROVAL`).
  A range counts from its first week, so a pregnancy delivered at 37 weeks has seven visits at
  most and one delivered at 38 weeks has eight.
- **A pregnancy that ends before its first visit has no visit.** It is recorded as no care,
  trimester 0.

### Scenarios

Two fixed scenarios (D-010, D-096):

| Scenario | Visits after the first one |
|---|---|
| E1 · Perfect calendar | Every visit of the calendar until delivery |
| E2 · Calendar with misses | Each visit, independently, with probability p |

- **How p is set** (`FOR APPROVAL`). Take the simulated pregnancies that start in the first
  trimester and are delivered at 38 weeks or more, the only ones the calendar lets reach eight
  visits. p makes their share with eight visits equal to the observed share with 8 or more visits
  among the same births of definition 2. It is computed from definition 2 when the simulation runs
  and written next to its output.
- **Why the world is null.** In both scenarios, adherence ignores how long the pregnancy lasts.
- **What each one shows.** E1 gives the largest association the calendar can produce, and E2 a
  realistic one.

### What it computes

- **The same measures as the observed analysis, with the same code**: (a), (a) per count, (b) on
  the ACOG schedule with the midpoint rule, (c), and (d) on the same landmark weeks. Only crude
  odds ratios are computed, because the simulated world has no confounders.
- **A built-in check.** The odds ratio of (c) must be 1 within its confidence interval, because the
  first trimester is drawn independently of the delivery week.
- **The calendar caps the count at eight.** The observed mean is 8.25 visits among term births that
  started care in the first trimester.
  - The simulation reproduces the levels of (a), whose top level is 8 or more, and the per-count
    curve up to 8.
  - It produces nothing above eight, so no association above eight observed visits can come from
    truncation.
- **Seed and parameters live in configuration.** One integer seed gives each scenario a stream of
  its own, so adding a scenario does not change the others. Two runs with the same seed give the
  same output.
- **One run per scenario, at the size of definition 2** (D-097).
  - The simulated confidence intervals then have the width of the observed ones.
  - At that size, Monte Carlo replicates are not needed.
  - The tests run the same code on a small size.

### What truncation alone explains

For each measure, level and scenario, the share is log(simulated odds ratio) ÷ log(observed crude
odds ratio) (D-097, `FOR APPROVAL`).

- **How to read it.** 1 means that truncation alone reproduces the observed association, and 0
  that it produces none of it.
- **When it is reported.** Only where the observed confidence interval excludes 1.
- **Why the crude odds ratio.** The simulation has no covariates, so the observed crude odds ratio
  is the comparison. The adjusted one is reported beside it in `estimates.csv`.

## Limitations

PENDING. The limitations that the decisions above already establish are stated where they arise:
one mother `PERSON` per certificate and no link between the pregnancies of one woman (§Design and
unit of analysis), births certified after DGIS closed a year's file and duplicate certificates
that cannot be confirmed (§Base cohort), the selection the two validity steps introduce
(§Outcome), the 670 records the data model cannot hold (§Attrition), and what the period does not
allow (§Data source). Two more come from the data model
([`omop_mapping.md`](omop_mapping.md)):

- **OMOP cannot carry the ethnicity SINAC records.** The race and ethnicity fields of `PERSON`
  encode US OMB categories. SINAC records whether the mother considers herself indigenous and
  whether she speaks an indigenous language, so both fields are 0 and the two variables stay out
  of `PERSON` (D-061). The question they open is future work
  ([`roadmap.md`](roadmap.md#47-indigenous-mothers)).
- **The observation period is the delivery day.** SINAC observes nothing of the pregnancy but its
  end and a declaration made then, so OMOP tools see no prenatal window. That is the premise of
  the study, written into the data model rather than hidden by it (D-062).

The exposure measures, the analysis and the simulation add five more, stated where they arise:

- APNCU is approximated from the trimester, with a month rule whose sensitivity was cut
  (§APNCU).
- The ACOG schedule of the index is not the Mexican norm (§APNCU).
- The bounds of the trimesters have no published source (§Trimester boundaries).
- The intervals of the definition with multiples ignore the twins of one pregnancy (§Sensitivity
  analyses and gradients).
- The simulated calendar cannot produce more than eight visits (§Null simulation).

The ones the proposal already anticipated are in
[`proposal_v2.md`](proposal_v2.md#anticipated-limitations).

## Changes from proposal v2

| What proposal v2 says | What this protocol does | Where |
|---|---|---|
| SINAC in the INSP standardized version | SSA/DGIS open data | D-001, D-002 |
| Period 2019–2023 | 2020–2023 | D-041, §Data source |
| "Births" as the unit, without stating it | The live-birth certificate, which the restriction to singletons makes a pregnancy, with one mother `PERSON` per certificate | D-051, §Design |
| Preterm cut-offs 37, 34 and 32 with no source | 37 weeks from NOM-007-SSA2-2016 §3.25, over a cohort that starts at 22 weeks (§3.45) | D-053, §Outcome |
| Inclusion or exclusion of births before week 22 as a sensitivity axis | A base exclusion with its count in the attrition table; the axis is dropped | **D-055 `[SCOPE CHANGE]`** |
| Nothing about the mother's residence | Residence in Mexico is an eligibility criterion; residence abroad becomes future work, with the signal that motivates it | D-057, [`roadmap.md`](roadmap.md#46-prenatal-care-of-mothers-resident-abroad) |
| Nothing about missing prenatal care data | The four measures on one set of records with known and coherent prenatal care data | D-086, §Exposure measures |
| Landmark cohorts at weeks 28, 32 or 34 | The three weeks. D-004 had cut them to one or two, and D-090 restores them | D-090, §Exposure measures |
| APNCU, with the sensitivity to the month assigned within the trimester | Kotelchuck's program, with one rule: the middle month of the trimester | **D-005 `[SCOPE CHANGE]`**, D-091, D-092 |
| Odds ratios adjusted for maternal age and education, insurance, state and year | Adjusted for age, education, state and year; insurance becomes a gradient | **D-007, D-094 `[SCOPE CHANGE]`**, §Analysis |
| The full sensitivity of the definition for every measure | The full grid for measures (a) and (c) | **D-003 `[SCOPE CHANGE]`**, §Analysis |
| Visits generated with variation in adherence | Two fixed scenarios, the perfect calendar and a calendar with misses | D-010, D-096, §Null simulation |
| Birth weight under 2,500 g as an alternative outcome | Not run | **D-006 `[SCOPE CHANGE]`** |

## References

- DGIS. *Guía para el correcto llenado del Certificado de Nacimiento, Modelo 2025*. Secretaría de
  Salud.
- Koroukian SM, Rimm AA. The "Adequacy of Prenatal Care Utilization" (APNCU) index to study low
  birth weight: is the index biased? *J Clin Epidemiol.* 2002;55(3):296–305.
- Kotelchuck M. An evaluation of the Kessner Adequacy of Prenatal Care Index and a proposed
  Adequacy of Prenatal Care Utilization Index. *Am J Public Health.* 1994;84(9):1414–1420.
- Kotelchuck M. Adequacy of Prenatal Care Utilization Index: SAS computational program, version 3.
  September 1994. <https://www.mchlibrary.org/databases/HSNRCPDFs/APNCU994_20SAS.pdf>
- NOM-007-SSA2-2016, Para la atención de la mujer durante el embarazo, parto y puerperio, y de la
  persona recién nacida. *Diario Oficial de la Federación*, 7 April 2016.
  <https://dof.gob.mx/nota_detalle.php?codigo=5432289&fecha=07/04/2016>
- Raju TNK, et al. Optimizing care and outcome for late-preterm (near-term) infants: a summary of
  the workshop sponsored by the National Institute of Child Health and Human Development.
  *Pediatrics.* 2006;118(3):1207–1214.
- World Health Organization. Preterm birth, fact sheet, 10 May 2023.
  <https://www.who.int/en/news-room/fact-sheets/detail/preterm-birth>
