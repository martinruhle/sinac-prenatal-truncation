# Protocol

The question, the data and the methods of the study. The question is stated in
[`proposal_v2.md`](proposal_v2.md); scope changes against it are listed in
[`roadmap.md`](roadmap.md) and argued in [`decisions.md`](decisions.md).

**Draft.** The question, the data source, the study period, the design, the base cohort, the
outcome and the attrition are written. The exposure measures, the analysis, the null simulation,
the covariate set (D-007) and the limitations are PENDING; they are written with the exposure and
analysis tasks of milestone `v0.2-progress`.

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

What this implies for the OMOP mapping (the detail belongs to `omop_mapping.md`):

- One `PERSON` for the mother and one for the newborn per certificate, linked through
  `FACT_RELATIONSHIP`.
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
  exposure definitions, so that the four measures are compared on one population; the rule for it
  is PENDING in §Exposure measures.
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
fails, so the order changes the count of every step, and not the final size. The order is
**coverage, then validity, then design**.

| # | Step | Kind | Rule | Removed | Remaining |
|---|---|---|---|---|---|
| 0 | Records in the files of the study period | — | — | — | 6,531,527 |
| 1 | Born in the study period | coverage | criterion 1 | 0 | 6,531,527 |
| 2 | Mother resident in Mexico | coverage | criterion 2 | 3,700 | 6,527,827 |
| 3 | Gestational age specified | validity | criterion 3 | 4,809 | 6,523,018 |
| 4 | Multiplicity specified | validity | criterion 4 | 10,117 | 6,512,901 |
| 5 | Singleton | design | criterion 5 | 110,358 | 6,402,543 |
| 6 | 22 completed weeks or more | design | criterion 6 | 701 | **6,401,842** |

The two count columns are orientation for the decisions taken here, measured once over the four
record files of 2020–2023 with a throwaway query (the practice of D-047). The table of record is
the one the cohort SQL produces, per year and per definition (rule 5 of
[`../CLAUDE.md`](../CLAUDE.md)).

Why this order (D-056):

- **Coverage** answers whether the record belongs to the population this study takes from the
  registry (steps 1 and 2). **Validity** answers whether the value the study needs is there and
  usable (steps 3 and 4). **Design** answers whether the record belongs in the main question
  (steps 5 and 6).
- The coverage and validity steps are identical in every definition of the cohort, so the
  attrition table of a sensitivity definition differs from this one only in its tail, and the
  reader sees exactly what the axis changed.
- A numeric criterion has to come after the step that removes the sentinel which would pass it:
  99 ≥ 22 is true, so step 6 cannot precede step 3.
- The effect of the order, measured: with step 5 placed first, step 3 removes 4,643 records
  instead of 4,809, because the multiples with no gestational age are counted earlier.

## Sensitivity of the definition

Every axis has two sides, and the base cohort takes exactly one of them: no criterion is both an
exclusion of the base cohort and an axis on that same side (D-054).

| Axis | Base cohort | Alternative definition |
|---|---|---|
| Multiple pregnancies | Excluded (criterion 5) | Included, each certificate one unit |
| Preterm cut-off | Under 37 weeks | Under 34, under 32 |
| Period (COVID-19) | 2020–2023 | 2022–2023 (D-049) |
| Births before 22 weeks | Excluded (criterion 6) | **No axis** (D-055): the step removes 701 records of 6,401,842 |

The full grid runs for measures (a) and (c) only (D-003). How each alternative definition is
estimated and reported, the landmark weeks of measure (d) (D-004) and the gradients by state and
by insurance are PENDING.

## Exposure measures

PENDING. The four measures are listed in [`proposal_v2.md`](proposal_v2.md#question). This section
fixes, for each one, its variables, which sentinel codes count as missing, and whether the four
are computed on one common set of records or each on its own — a decision that belongs here and
not to the base cohort, because a difference between measures must not be a difference of
population.

## Analysis

PENDING. Crude and adjusted odds ratios per measure, with the reduced covariate set of D-007.
Neither gestational age nor birth weight, nor anything derived from them, is ever a predictor
(rule 3 of [`../CLAUDE.md`](../CLAUDE.md)); that is what makes measure (c) the truncation-free
comparison.

## Null simulation

PENDING. Visits generated on the NOM-007-SSA2-2016 schedule with two or three adherence scenarios
(D-010), truncated at the week of delivery observed in SINAC.

## Limitations

PENDING. The limitations that the decisions above already establish are stated where they arise:
one mother `PERSON` per certificate and no link between the pregnancies of one woman (§Design and
unit of analysis), births certified after DGIS closed a year's file and duplicate certificates
that cannot be confirmed (§Base cohort), the selection the two validity steps introduce
(§Outcome), and what the period does not allow (§Data source). The ones the proposal already
anticipated are in [`proposal_v2.md`](proposal_v2.md#anticipated-limitations).

## Changes from proposal v2

| What proposal v2 says | What this protocol does | Where |
|---|---|---|
| SINAC in the INSP standardized version | SSA/DGIS open data | D-001, D-002 |
| Period 2019–2023 | 2020–2023 | D-041, §Data source |
| "Births" as the unit, without stating it | The live-birth certificate, which the restriction to singletons makes a pregnancy, with one mother `PERSON` per certificate | D-051, §Design |
| Preterm cut-offs 37, 34 and 32 with no source | 37 weeks from NOM-007-SSA2-2016 §3.25, over a cohort that starts at 22 weeks (§3.45) | D-053, §Outcome |
| Inclusion or exclusion of births before week 22 as a sensitivity axis | A base exclusion with its count in the attrition table; the axis is dropped | **D-055 `[SCOPE CHANGE]`** |
| Nothing about the mother's residence | Residence in Mexico is an eligibility criterion; residence abroad becomes future work, with the signal that motivates it | D-057, [`roadmap.md`](roadmap.md#46-prenatal-care-of-mothers-resident-abroad) |
