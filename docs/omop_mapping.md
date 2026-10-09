# OMOP mapping v1: the vertical slice, the covariates and the newborn

How the SINAC records of 2020–2023 land in the OMOP CDM v5.4. Version 0 mapped the vertical slice
(D-009): the tables that the base cohort of [`protocol.md`](protocol.md#base-cohort) and the v0.1
milestone need. Version 1 adds the covariates of the adjusted odds ratios
([`protocol.md`](protocol.md#covariates), D-094): the mother's age and education. It also adds
the newborn as a `PERSON` of its own, linked to the mother, with its birth weight (D-103 to
D-106). Source variables are described in [`data_dictionary.md`](data_dictionary.md); this
document says where each one goes (D-017).

Every populated field has one row, with its source, its rule and who decided it:

- **OMOP**: the CDM specification or convention dictates the rule, and it is quoted.
- **Project**: a decision of this study, with its entry in [`decisions.md`](decisions.md).

The concept ids are held in [`../config/concept_sets.yml`](../config/concept_sets.yml) and
[`../config/source_to_concept_map.csv`](../config/source_to_concept_map.csv), never in SQL
(CLAUDE.md rule 8, D-023). They are repeated here to be read, and the configuration is the
reference: `tests/test_concepts.py` checks that every concept there carries its vocabulary, code
and domain, and that each domain is one the CDM allows in the field it is written to.

## Scope

| Mapped | Not mapped yet | Why not yet |
|---|---|---|
| `PERSON`: the mother, and the newborn (v1) | | |
| `FACT_RELATIONSHIP`: mother and newborn (v1) | | |
| `OBSERVATION_PERIOD` | `VISIT_OCCURRENCE`, `CARE_SITE` | No criterion uses the delivery visit, and no visit is ever created for prenatal care (D-066) |
| `MEASUREMENT`: gestational age, plurality, mother's age (v1), birth weight (v1) | `AFILIACION` (insurance) | Only the gradient by insurance uses it (D-094, D-099), so it is mapped in v1.0 with the gradient (D-102) |
| `OBSERVATION`: total visits, trimester of the first visit, mother's education (v1) | `ATENCIONPRENATAL` | No rule of the protocol uses it: the common set of records rests on the trimester and the visit count (D-086). Candidate concept if it is ever mapped, checked in Athena: 44817093, LOINC 75204-8 "Prenatal care indicator [CDC.CS]", Observation |
| `LOCATION`: residence | | |
| `CDM_SOURCE`, and `VOCABULARY` and `SOURCE_TO_CONCEPT_MAP` rows for the local codes | | |

The base cohort needs four source fields: `FECHANACIMIENTO` (criterion 1), `RESIDEEXTRANJERO`
(criterion 2), `EDADGESTACIONAL` (criteria 3 and 6) and `PRODUCTOEMBARAZO` (criteria 4 and 5).
The adjusted models add four covariates (D-094): the mother's age (`EDAD`) and education
(`ESCOLARIDAD`), the state of residence (`ENTIDADRESIDENCIA`, already in `LOCATION`) and the year
of the delivery date. All of them land in the CDM, so the cohort SQL never reads `staging` (D-068).
The newborn adds `SEXO` and `PESO`, which no criterion, covariate or model reads (CLAUDE.md rule
3): they complete the data model the proposal commits to, with mother and newborn as two persons.

## Rules shared by every table

1. **Type.** Every `*_type_concept_id` is `registry` (32879, "Registry"). OMOP requires a type
   concept that "best represents the provenance of the record"; the source is a registry of
   certificates, not an EHR or a claim. *Project, D-065.*
2. **Dates.** Every event is dated `FECHANACIMIENTO`, the delivery date: gestational age and birth
   weight are measured at delivery, and the visit count, the trimester, the plurality and the
   mother's age and education are recorded on the certificate at delivery. `FECHANACIMIENTO` is a full date (`dd/mm/yyyy`) in all 6,531,527
   records of 2020–2023, so no date is imputed: a record without a valid one would fail
   criterion 1. `*_datetime` fields stay NULL: they are optional, the hour is not used, and 68
   records carry `99:99`. *Project, D-063.*
3. **Codes and flavors of null.** Each source column that carries codes has a local source
   vocabulary of its own, per catalogue period (prefix `SINAC20_` for 2020–2023), with its codes
   in `source_to_concept_map`. A value listed in its column's vocabulary is a code: it takes the
   row's target concept, and the target is 0 when the code is a flavor of null or has no standard
   concept. Any other value is the value itself (a number, a date, a state code). A blank cell is
   NULL in both the value and the source value. *OMOP and project, D-067:*
   - OMOP makes "no distinction … why a piece of information is not available": every flavor of
     null maps to concept 0 (Book of OHDSI §5.6.10).
   - The row is written even when the value is missing: the MEASUREMENT conventions say
     `value_as_number` and `value_as_concept_id` "are not mandatory as often the result is not
     given in the source data". The unanswered question stays countable (D-056), and the raw value
     stays in `value_source_value`, so every rule can be reversed.
   - The rule is per column, never global, because a code changes meaning between catalogues of
     the same period. In `SI_NO`, 0 is "NO ESPECIFICADO" and 8 is "NO APLICA". In
     `TRIMESTRE_PRIMER_CONSULTA`, 0 is "NO RECIBIÓ", an answer given in 167,885 records, and 8 is
     "NO ESPECIFICADO".
   - A value that is neither a code nor castable also keeps its row, as NULL (a number) or 0 (a
     concept), with the raw value in the source field. Examples are weeks that are not digits, or
     a plurality or trimester its catalogue does not publish. A delivery date that is not a valid
     date stops the load instead, because every date hangs on it. The ETL counts each rule per
     year in `results.etl_counts`, zero included; in 2023 only the codes above occur (D-075).
   - No custom concepts (ids above 2,000,000,000): OMOP makes them "always non-standard", usable
     only "in the `_source_concept_id` fields", so they would not change `value_as_concept_id`.
     They would only add CONCEPT rows that OHDSI tools cannot see.
4. **Source fields.** `*_source_value` of a concept field holds the source column name (for
   example `measurement_source_value = 'EDADGESTACIONAL'`), and `*_source_concept_id` is 0: a
   column name is not a code of any vocabulary. *OMOP: "If the source code is not found in a
   vocabulary, the SOURCE_CONCEPT_ID field is set to 0."*
5. **The domain decides the table.** "Write the data record into the table(s) corresponding to
   the domain of the Standard CONCEPT_ID(s)" (CDM data model conventions). Every concept below is
   standard, and its domain matches its table. *OMOP.*
6. **Local vocabularies** are registered in `VOCABULARY` with `vocabulary_concept_id = 0`, as the
   DDL requires a value and none exists for them. *Project, D-023.*
7. **Ids.** The ETL truncates and reloads every table on each run (task 1.4.4), and nothing
   outside the CDM stores an id: results are aggregates (D-014). *Project, D-059.*
   - `source_row` is the 1-based ordinal of the data row in the year's CSV member, with the header
     excluded. It is assigned once, when `staging` loads the file (task 1.2.4), and every CDM table
     reads it from there. It is never recomputed with an `ORDER BY`, which is what keeps the
     tables of one person on one record.
   - `person_id` of the mother = (year − 2000) × 10,000,000 + `source_row`. Row 1,234,567 of 2023
     is person 231,234,567, so any id leads back to its CSV row. Loading 2020–2022 after 2023 does
     not renumber 2023. The largest file has 1,747,847 rows, and the formula fits the `integer`
     column up to 2099.
   - `person_id` of the newborn = the mother's + 1,000,000,000 (D-103). Every mother id is below
     1,000,000,000, and the newborn of row 9,999,999 of 2099 is 1,999,999,999, which still fits.
     Row 1,234,567 of 2023 gives mother 231,234,567 and newborn 1,231,234,567.
   - `observation_period_id` = `person_id` (one period per person).
   - `measurement_id` and `observation_id` are `row_number()` over (`person_id`, the order of the
     rows listed below), recomputed on each load.
   - `location_id` is `row_number()` over the distinct pairs (`RESIDEEXTRANJERO`,
     `ENTIDADRESIDENCIA`) in code order.
   - The file version is pinned by its sha256 (D-044), so ids hold within that version. A
     republished file changes the hash and stops the pipeline. Once the new version is recorded,
     the CDM is rebuilt from zero and the ids of that year may change. CDM_SOURCE names the
     versions loaded.

## Tables

### PERSON (the mother)

One row per staged record whose mother's year of birth is known (D-060). The mother is one
`PERSON` per certificate, not per woman (D-051).

| Field | DDL | Source | Rule | Decided by |
|---|---|---|---|---|
| `person_id` | required | year, `source_row` | (year − 2000) × 10,000,000 + `source_row` | Project, D-059 |
| `gender_concept_id` | required | — | `female` (8532). The certificate records the mother | Project |
| `year_of_birth` | required | `FECHANACIMIENTOMADRE`, `EDAD`, `FECHANACIMIENTO` | (1) The year of `FECHANACIMIENTOMADRE` when it parses as `dd/mm/yyyy`, is not a code of `SINAC20_FECHANACMAD` and precedes `FECHANACIMIENTO`. (2) Otherwise the year of `FECHANACIMIENTO` minus `EDAD`, when `EDAD` is not a code of `SINAC20_EDAD`. (3) Otherwise the record is not loaded | OMOP for (1): "For data sources with date of birth, the year should be extracted". Project for (2) and (3), D-060 |
| `month_of_birth`, `day_of_birth` | optional | `FECHANACIMIENTOMADRE` | From the date in case (1); NULL in case (2) | OMOP: "For data sources that provide the precise date of birth, the month should be extracted" |
| `race_concept_id` | required | — | 0 | OMOP: "Only use this field if you have information about race or ethnic background". Project, D-061 |
| `ethnicity_concept_id` | required | — | 0 | OMOP: the field "distinguishes only between 'Hispanic' and 'Not Hispanic'" (US OMB). Project, D-061 |
| `location_id` | optional | `RESIDEEXTRANJERO`, `ENTIDADRESIDENCIA` | The `LOCATION` of residence | Project, D-068 |
| `person_source_value` | optional | year, `source_row` | `'<year>:<source_row>'`, e.g. `'2023:1234567'` | Project, D-059 |
| every other field | optional | — | NULL | — |

What the year-of-birth rule meets in 2020–2023 (orientation, measured once over the four record
files with a throwaway query, as in D-047):

| Case | Records | Note |
|---|---|---|
| (1) Mother's date of birth | 6,530,667 (99.987 %) | The age computed from it equals `EDAD` in 99.41 % of them. One record carries a date in year 1; it passes the rule and is left as it is: no criterion uses maternal age |
| (2) Age only | 190 | The date is unusable in 860 records, which cases (2) and (3) share: 767 carry the sentinel `09/09/9999`, 91 carry `99/99/9999`, which the descriptor does not declare and which does not parse, and 2 carry a date on or after the delivery. Where both fields exist, year of delivery − `EDAD` equals the year of the date in 50.5 % of records and is one year late in 49.4 %, so the error is at most one year |
| (3) Neither (`EDAD` = 999, "Se Ignora") | 670 (0.010 %) | 579 in 2020, 68 in 2021, 23 in 2022, none in 2023. 610 of them would otherwise reach the base cohort. They leave at attrition step 1 of [`protocol.md`](protocol.md#attrition) |

The mother's age covariate is not computed from these fields. It is the age the certificate
declares, held as a `MEASUREMENT` row ([below](#measurement), D-100).

`SECONSIDERAINDIGENA` and `HABLALENGUAINDIGENA` stay out of `PERSON`. The OMOP race and ethnicity
fields encode US OMB categories, which are not the construct SINAC records (D-061); the question
the two variables open is future work ([`roadmap.md`](roadmap.md#47-indigenous-mothers)).

### PERSON (the newborn)

One row per loaded record, that is, per mother `PERSON` (D-103). The live-born child of the
certificate is a person of its own, linked to the mother through
[`FACT_RELATIONSHIP`](#fact_relationship). A record whose mother is not loaded (D-060) gives no
newborn either: the link needs both persons, and the record leaves at attrition step 1.

| Field | DDL | Source | Rule | Decided by |
|---|---|---|---|---|
| `person_id` | required | year, `source_row` | The mother's id + 1,000,000,000 | Project, D-059, D-103 |
| `gender_concept_id` | required | `SEXO` | The target of the code in `SINAC20_SEXO`: 1 "HOMBRE" → `MALE` (8507), 2 "MUJER" → `FEMALE` (8532); 0 "NO ESPECIFICADO", 9 "SE IGNORA", a blank or a code the catalogue does not publish → 0 | OMOP: "Use the gender or sex value present in the data under the assumption that it is the biological sex at birth". Project, D-067, D-103 |
| `year_of_birth`, `month_of_birth`, `day_of_birth` | required, optional, optional | `FECHANACIMIENTO` | The delivery date, a full date in every record (rule 2) | OMOP: "For data sources that provide the precise date of birth, the month should be extracted" |
| `birth_datetime` | optional | — | NULL. The hour is not used (D-063), and 68 records of 2020 carry `HORANACIMIENTO` `99:99` | Project, D-103 |
| `race_concept_id`, `ethnicity_concept_id` | required | — | 0, as for the mother | Project, D-061 |
| `location_id` | optional | — | NULL. The residence the certificate records is the mother's | Project, D-103 |
| `person_source_value` | optional | year, `source_row` | The mother's: `'<year>:<source_row>'`. Both come from the same row of the file, and the id tells them apart | Project, D-059 |
| `gender_source_value` | optional | `SEXO` | Verbatim | OMOP: "Put the assigned sex at birth of the person as it appears in the source data" |
| `gender_source_concept_id` | optional | — | 0: a code of a local vocabulary has no concept (rule 4) | OMOP (rule 4) |
| every other field | optional | — | NULL | — |

- **Why 0 for the unknown sexes, not `UNKNOWN`.** The Gender vocabulary has 8551 "UNKNOWN", but it
  is deprecated and non-standard in the loaded bundle; only `MALE` and `FEMALE` are standard. The
  flavors of null map to 0 (rule 3), and the raw code stays in `gender_source_value`.
- **The newborn never enters a cohort.** The subjects are the mothers, found through
  `FACT_RELATIONSHIP` ([below](#fact_relationship), D-106).

### OBSERVATION_PERIOD

One row per `PERSON`: **a single day, the delivery** (D-062). The newborn is observed on the same
day, its birth, and on no other: OMOP asks for at least one period per `PERSON`, and SINAC sees
the newborn once (D-103).

| Field | DDL | Source | Rule | Decided by |
|---|---|---|---|---|
| `observation_period_id` | required | — | = `person_id` | Project, D-059 |
| `person_id` | required | — | — | — |
| `observation_period_start_date` | required | `FECHANACIMIENTO` | The delivery date | OMOP: "can be inferred as the earliest Event date available for the Person" |
| `observation_period_end_date` | required | `FECHANACIMIENTO` | The delivery date | OMOP: "can be inferred as the last Event date available for the Person" |
| `period_type_concept_id` | required | — | `registry` (32879) | Project, D-065 |

An observation period is a span "with a high capture rate of Clinical Events". SINAC observes the
pregnancy once, at delivery, and records what happened before as a declaration. Everything else
follows from that:

- **The window is the delivery day.** Every event of the certificate is dated then, and the CDM
  infers start and end from the earliest and last event dates.
- **No prenatal window.** A window that started at delivery minus the gestational age would make
  the observed time equal to the outcome. A birth at 30 weeks would get 210 observed days and one
  at term 280, so the truncation this study measures would be written into the data model. Any
  tool that used observed time would then use the outcome without saying so.
- **No fixed window either.** One of 280 or 294 days would rest on an unsourced constant and claim
  observation SINAC does not have.
- **Nothing the question needs is lost.** Gestational age stays in `MEASUREMENT`. The outcome,
  the landmark cohorts of measure (d) and the null simulation read it there, where the use of the
  gestational window is explicit. No table of the analysis reads `OBSERVATION_PERIOD`.
- **For OHDSI tools**, every period lasts one day. That describes the source correctly, and the
  CDM itself warns that "absence of an Event outside these time spans cannot be construed as
  evidence of absence". A cohort definition that asks for days of observation before the index
  date finds none, which is also true of the source.

### MEASUREMENT

Three rows per mother `PERSON`, in this order: gestational age, plurality, then the mother's age.
One row per newborn `PERSON`: its birth weight. The newborns have the highest ids, so their rows
come last.

**Gestational age at delivery**, on the mother (roadmap):

| Field | DDL | Source | Rule | Decided by |
|---|---|---|---|---|
| `measurement_id` | required | — | Row number (rule 7) | Project, D-059 |
| `measurement_concept_id` | required | `EDADGESTACIONAL` | `gestational_age_at_birth` (4260747) | Project, D-064 |
| `measurement_date` | required | `FECHANACIMIENTO` | Delivery date | Project, D-063 |
| `measurement_type_concept_id` | required | — | `registry` (32879) | Project, D-065 |
| `value_as_number` | optional | `EDADGESTACIONAL` | Completed weeks as an integer; NULL for the code 99 of `SINAC20_EDADGEST` | Project, D-067 |
| `unit_concept_id` | optional | — | `week` (8511) | Descriptor: "Semanas de gestación del nacido vivo (semanas)" |
| `measurement_source_value` | optional | — | `'EDADGESTACIONAL'` | OMOP (rule 4) |
| `measurement_source_concept_id` | optional | — | 0 | OMOP (rule 4) |
| `value_source_value` | optional | `EDADGESTACIONAL` | Verbatim | Project, D-067 |
| every other field | optional | — | NULL. No `range_low`/`range_high`: DGIS publishes no range for 2020–2023 (D-053) | — |

Why `MEASUREMENT`:

- The CDM defines measurements as "structured values … obtained through systematic and
  standardized examination or testing"; observations "do not require a standardized test or some
  other activity". No instrument is implied: the Apgar score, assigned by looking at the newborn,
  is a Measurement (4016464, SNOMED 169909004 "Apgar at 5 minutes").
- Gestational age at delivery is a clinical estimate with a unit, from the last menstrual period,
  ultrasound or examination of the newborn; SINAC does not record which.
- The table is decided by the domain of the concept (rule 5), so the real choice is the concept.
  See [Concepts](#concepts) for the rejected LOINC term.

**Plurality** (`PRODUCTOEMBARAZO`), which criteria 4 and 5 read:

| Field | DDL | Source | Rule | Decided by |
|---|---|---|---|---|
| `measurement_concept_id` | required | `PRODUCTOEMBARAZO` | `birth_plurality` (40760833) | Project, D-068 |
| `measurement_date`, `measurement_type_concept_id`, `measurement_source_*` | | | As for gestational age | — |
| `value_as_number` | optional | `PRODUCTOEMBARAZO` | 1 "ÚNICO" → 1, 2 "GEMELAR" → 2, 3 "TRES O MÁS" → 3; NULL for the code 0 of `SINAC20_PRODEMB` | Project, D-068 |
| `operator_concept_id` | optional | `PRODUCTOEMBARAZO` | `at_least` (4171755, ">=") for 3, which means three or more; NULL otherwise | Project, D-068 |
| `value_source_value` | optional | `PRODUCTOEMBARAZO` | Verbatim | Project, D-067 |

Criterion 4, "multiplicity specified", is `value_as_number IS NOT NULL`, and criterion 5,
"singleton", is `value_as_number = 1`. LOINC 57722-1 is a count ("Number (count)", ordinal
scale). It is an item of the US standard certificate of live birth, and CDISC "Birth Plurality"
maps to it.

**Mother's age at delivery** (`EDAD`), the maternal age covariate of the adjusted models (D-094):

| Field | DDL | Source | Rule | Decided by |
|---|---|---|---|---|
| `measurement_concept_id` | required | `EDAD` | `mother_age_at_delivery` (36203531) | Project, D-100 |
| `measurement_date`, `measurement_type_concept_id`, `measurement_source_*` | | | As for gestational age | — |
| `value_as_number` | optional | `EDAD` | Completed years as an integer; NULL for the codes 888 and 999 of `SINAC20_EDAD` | Project, D-067 |
| `unit_concept_id` | optional | — | `year` (9448) | Descriptor: "Edad de la madre en años cumplidos" |
| `value_source_value` | optional | `EDAD` | Verbatim | Project, D-067 |

Why the declared age, and not one computed from `PERSON`:

- **The protocol adjusts for the age declared on the certificate** (D-094), and LOINC 85724-3
  "Age of Mother --at delivery" names that item. Its domain is Measurement, so it goes here
  (rule 5).
- **The year of birth alone moves records between groups.** Over the base cohort of 2020–2023
  (orientation, D-047), the year of delivery minus `year_of_birth` puts 632,810 records (9.9 %) in
  another five-year group than `EDAD`.
- **The full date of birth nearly agrees.** The exact age from `FECHANACIMIENTOMADRE` equals
  `EDAD` in 99.41 % of the base cohort and changes the group of 9,948 records (0.16 %). Some of the
  differences are of five years or more, typing errors in one of the two fields that the data
  cannot settle. OMOP tools that compute age from `PERSON` keep doing so; the study reads `EDAD`.

**Birth weight** (`PESO`), on the newborn (D-105). No criterion, covariate or model reads it
(CLAUDE.md rule 3):

| Field | DDL | Source | Rule | Decided by |
|---|---|---|---|---|
| `person_id` | required | — | The newborn | Project, D-064, D-105 |
| `measurement_concept_id` | required | `PESO` | `birth_weight` (3011043) | Project, D-105 |
| `measurement_date`, `measurement_type_concept_id`, `measurement_source_*` | | | As for gestational age | — |
| `value_as_number` | optional | `PESO` | Grams as an integer, as recorded; NULL for the code 9999 of `SINAC20_PESO`, a blank or a value that is not digits only | Project, D-067, D-105 |
| `unit_concept_id` | optional | — | `gram` (8504) | Descriptor: "Peso del nacido vivo (gramos)" |
| `value_source_value` | optional | `PESO` | Verbatim | Project, D-067 |
| every other field | optional | — | NULL. No `range_low`/`range_high`: DGIS publishes no range for 2020–2023 | Project, D-053, D-105 |

- **The concept is the item of the birth certificate.** LOINC 8339-4 "Birth weight Measured"
  belongs to the panel "U.S. standard certificate of live birth - recommended 2003 revision set"
  (LOINC 86347-2), the panel of the visit count and of plurality (D-065).
- **Every weight is loaded as recorded.** Over 2020–2023, 328 weights are below 500 g (the lowest
  270 g) and one is 7,650 g (2022). The 2015–2019 list of DGIS gives an acceptable range of 20 to
  6,000 g; the 2020–2023 descriptor gives none, so no range is applied, as for gestational age
  (D-053).
- **Code 9999 is frequent and not at random.** It occurs in 354,847 records of 2020–2023 (5.4 %).
  Among singletons it occurs in 11.1 % of the preterm births and in 4.8 % of the births at term.
  Any descriptive table of birth weight has to state this
  ([`data_dictionary.md`](data_dictionary.md#what-the-files-show)).

### OBSERVATION

Three rows per `PERSON`, in this order: total visits, the trimester of the first visit, then the
mother's education.

**Total prenatal visits** (`TOTALCONSULTAS`), a **declared count**:

| Field | DDL | Source | Rule | Decided by |
|---|---|---|---|---|
| `observation_id` | required | — | Row number (rule 7) | Project, D-059 |
| `observation_concept_id` | required | `TOTALCONSULTAS` | `prenatal_visits_count` (40771079) | Project, D-065 |
| `observation_date` | required | `FECHANACIMIENTO` | Delivery date | Project, D-063 |
| `observation_type_concept_id` | required | — | `registry` (32879) | Project, D-065 |
| `value_as_number` | optional | `TOTALCONSULTAS` | The count, 0 to 30; NULL for the code 99 of `SINAC20_TOTCONS` or a blank cell | Project, D-067 |
| `observation_source_value` | optional | — | `'TOTALCONSULTAS'` | OMOP (rule 4) |
| `observation_source_concept_id` | optional | — | 0 | OMOP (rule 4) |
| `value_source_value` | optional | `TOTALCONSULTAS` | Verbatim | Project, D-067 |
| every other field | optional | — | NULL | — |

**The count is one row, never one visit per declared consultation** (D-066). It is a number
written on the certificate at delivery, and its value depends on how long the pregnancy lasted:
that dependence is the truncation this study measures. Expanding it into `VISIT_OCCURRENCE` rows
would need visit dates SINAC does not record (CLAUDE.md rule 4). Any date would be invented, and
every query and tool would then read the invented calendar as observed care. The only place where
visits get dates is the null simulation, on purpose and outside the CDM (D-010). Three things
keep the count from being read as visits:

- the concept is a count item of a birth certificate, "#" included;
- the vertical slice creates no `VISIT_OCCURRENCE` at all;
- the ETL checks of task 1.4.4 assert that no `VISIT_OCCURRENCE` row exists.

**Trimester of the first prenatal visit** (`TRIMESTREPRIMERCONSULTA`):

| Field | DDL | Source | Rule | Decided by |
|---|---|---|---|---|
| `observation_concept_id` | required | `TRIMESTREPRIMERCONSULTA` | `first_prenatal_visit_trimester` (44817052) | Project, D-065 |
| `observation_date`, `observation_type_concept_id`, `observation_source_*` | | | As for total visits | — |
| `value_as_concept_id` | optional | `TRIMESTREPRIMERCONSULTA` | The target of the code in `SINAC20_TRIMCONS`: 1, 2 and 3 → the LOINC answers "1st", "2nd" and "3rd trimester"; 0 "NO RECIBIÓ" → "No prenatal care"; 8 and 9 → 0 | Project, D-065, D-067 |
| `value_source_value` | optional | `TRIMESTREPRIMERCONSULTA` | Verbatim | Project, D-067 |

"No prenatal care" (LOINC LA21278-9) is an answer of the sibling question of the same CDC form,
"Prenatal care indicator" (LOINC 75204-8), not of the trimester question. It is used anyway,
because concept 0 would merge the 167,885 mothers who received no care with the codes that mean
"not specified" (D-065).

**Mother's education** (`ESCOLARIDAD`), the education covariate of the adjusted models (D-094):

| Field | DDL | Source | Rule | Decided by |
|---|---|---|---|---|
| `observation_concept_id` | required | `ESCOLARIDAD` | `mother_education` (40760823) | Project, D-101 |
| `observation_date`, `observation_type_concept_id`, `observation_source_*` | | | As for total visits | — |
| `value_as_concept_id` | optional | `ESCOLARIDAD` | The target of the code in `SINAC20_ESCOL`: the level the code belongs to (below); 0, 88 and 99 → 0 | Project, D-067, D-101 |
| `value_source_value` | optional | `ESCOLARIDAD` | Verbatim | Project, D-067 |

Each code of the `ESCOLARIDAD` catalogue maps to the level of D-094, by the general level
attended, complete or not; a technical program counts at the general level it requires:

| Level (D-094) | Codes | Target |
|---|---|---|
| None | 1 NINGUNA | 4074913, SNOMED 224294005 "No formal education" |
| Primary | 31, 32 | 44800023, SNOMED 342271000000107 "Educated to primary school level" |
| Secondary | 51, 52, 111, 112 | 43020414, SNOMED 603435002 "Educated to junior high school level" |
| Upper secondary | 71, 72, 131, 132 | 43020395, SNOMED 603434003 "Educated to senior high school level" |
| Higher | 81, 82, 101, 102 | 4076230, SNOMED 224299000 "Received higher education" |

- **The levels are the concepts.** The cohort SQL groups by `value_as_concept_id` with no further
  configuration, and a change to the grouping, which D-094 leaves `FOR APPROVAL`, is a change of
  rows in [`../config/source_to_concept_map.csv`](../config/source_to_concept_map.csv), not of
  SQL.
- **What the concepts drop stays in the source value.** Complete or incomplete, a technical
  program, and postgraduate against undergraduate studies are all in `value_source_value`.
- **Junior and senior high name the Mexican cycles.** *Secundaria* is the lower secondary cycle
  that follows primary school, and *bachillerato* or *preparatoria* the upper secondary cycle.
  "Educated to secondary school level" (4074914) would merge both.
- LOINC 57712-2 is the item of the US standard certificate of live birth, the same panel as the
  visit count (D-065).

### FACT_RELATIONSHIP

Two rows per loaded record, which link its mother and its newborn (D-104). The CDM asks for every
relationship in both directions: "All relationships are directional, and each relationship is
represented twice symmetrically within the FACT_RELATIONSHIP table". A row reads "fact 1 is
*relationship* of fact 2".

| Row | `domain_concept_id_1` | `fact_id_1` | `domain_concept_id_2` | `fact_id_2` | `relationship_concept_id` |
|---|---|---|---|---|---|
| The mother is the Mother of the newborn | `person_table` (1147314) | mother | `person_table` | newborn | `mother` (4248584) |
| The newborn is the Child of the mother | `person_table` | newborn | `person_table` | mother | `child` (4285883) |

- **The relationship concepts.** SNOMED 72705000 "Mother" and 67822003 "Child" are standard
  concepts of the Relationship domain, and "Mother" says more than "Parent". The pair proposed on
  the OHDSI forum, "Parent of" (4050951) and "Child of" (4051272), sits in the Observation domain,
  which that same thread took for an error to be fixed. It still does in the loaded bundle.
- **The domain concept** (FOR APPROVAL). The CDM examples name a fact's table through a concept of
  the Domain vocabulary, here 56 "Person". That concept is deprecated in the loaded bundle (valid
  until 27 September 2022) with no replacement. The CDM vocabulary names the table itself,
  1147314 "person" (class Table), which is standard and valid. The OHDSI forum points to the
  Table concepts for this field (2021 and 2022); the CDM specification has not settled it, and its
  `domain_concept_id_*` fields require no domain.
- **What reads it.** The cohort SQL finds the mothers as the first fact of a `mother` row
  (D-106), so the newborns, which share the mother's `person_source_value`, never become
  subjects. ATLAS and Achilles do not read this table.

### LOCATION (residence)

One row per distinct pair (`RESIDEEXTRANJERO`, `ENTIDADRESIDENCIA`), referenced by
`PERSON.location_id`. Residence, not place of delivery, defines the cohort (D-057).

| Field | DDL | Source | Rule | Decided by |
|---|---|---|---|---|
| `location_id` | required | — | Row number (rule 7) | Project, D-059 |
| `country_concept_id` | optional | `RESIDEEXTRANJERO` | The target of the code in `SINAC20_RESEXT`: 2 "NO" (does not reside abroad) → `Mexico` (4075636); 1 "SI" → 0, because the certificate does not say which country; 88, a code the `SI_NO` catalogue does not publish (D-057), and the null flavors of `SI_NO` → 0 | Project, D-068 |
| `country_source_value` | optional | `RESIDEEXTRANJERO` | Verbatim | Project, D-067 |
| `state` | optional | `ENTIDADRESIDENCIA` | The two-digit code of the `ENTIDADES` catalogue; NULL for its codes 00, 88 and 99 (`SINAC20_ENTRES`) | Project, D-068 |
| `location_source_value` | optional | both | `'<RESIDEEXTRANJERO>\|<ENTIDADRESIDENCIA>'`, verbatim | Project |
| every other field | optional | — | NULL | — |

Criterion 2 is `country_concept_id` = `Mexico`. `state` is there for the state gradient of v0.2.

### CDM_SOURCE

One row describing the load. Every field below is required by the DDL unless marked optional.

| Field | Rule | Decided by |
|---|---|---|
| `cdm_source_name` | `'SINAC live-birth certificates, SSA/DGIS open data'` | Project |
| `cdm_source_abbreviation` | `'SINAC-DGIS'` | Project |
| `cdm_holder` | `'sinac-prenatal-truncation'`, this repository | Project |
| `source_description` (optional) | Each loaded file with its `?V=` version and its sha256, from `config/sources.yml` | Project, D-059 |
| `source_documentation_reference` (optional) | The `page` URL of the DGIS entries in `config/sources.yml` | Project |
| `cdm_etl_reference` (optional) | The repository URL and the commit the ETL ran from | Project |
| `source_release_date` | The latest `retrieved_at` of the loaded record files. DGIS publishes a dated version for 2022 and 2023 only (`?V=1.1` for 2020 and 2021), so the retrieval date is the one date every file has | Project |
| `cdm_release_date` | The date of the ETL run | Project |
| `cdm_version` (optional) | `'v5.4.3'` | Project |
| `cdm_version_concept_id` | `cdm_version` (902983, "OMOP CDM Version 5.4.3"). The vendored DDL is byte-identical to the one of the upstream tag `v5.4.3` ([`../sql/ddl/ohdsi/SOURCE.md`](../sql/ddl/ohdsi/SOURCE.md)) | Project |
| `vocabulary_version` | The `vocabulary_version` of the `VOCABULARY` row whose `vocabulary_id` is `'None'`, from the Athena bundle (task 1.4.3) | OMOP |

## Concepts

Looked up in Athena on 2026-09-24 (LOINC 2.82): every one was Standard and Valid, with the
domain shown. They are checked again against the bundle actually loaded, by
`pipeline.py validate-concepts` (task 1.4.3). Against the bundle `v5.0 29-AUG-26`
([`../config/sources.yml`](../config/sources.yml)) all 15 concept ids pass, the map targets below
and concept 0 included: each exists and is valid, each but concept 0 is standard with the
vocabulary and domain recorded here, and the concepts of this table also keep their code.

The concepts added for the covariates (v1: `mother_age_at_delivery`, `year`, `mother_education`
and the five targets of `ESCOLARIDAD`) were copied on 2026-10-08 from `CONCEPT` of that same
bundle (LOINC 2.82, SNOMED CT International 2026-02-01, UCUM 1.8.2). With them,
`validate-concepts` passes all 23 concept ids.

The concepts added for the newborn (v1: `birth_weight`, `gram`, `mother`, `child`, `person_table`
and the two targets of `SEXO`) were copied on 2026-10-09 from the same bundle. With them,
`validate-concepts` passes all 29 concept ids.

| Key | concept_id | Vocabulary | Code | Name | Domain | Written to |
|---|---|---|---|---|---|---|
| `female` | 8532 | Gender | F | FEMALE | Gender | `person.gender_concept_id` |
| `registry` | 32879 | Type Concept | OMOP4976952 | Registry | Type Concept | every `*_type_concept_id` |
| `gestational_age_at_birth` | 4260747 | SNOMED | 412726003 | Length of gestation at birth | Measurement | `measurement.measurement_concept_id` |
| `week` | 8511 | UCUM | wk | week | Unit | `measurement.unit_concept_id` |
| `birth_plurality` | 40760833 | LOINC | 57722-1 | Birth plurality of Pregnancy | Measurement | `measurement.measurement_concept_id` |
| `at_least` | 4171755 | SNOMED | 276138003 | >= | Meas Value Operator | `measurement.operator_concept_id` |
| `mother_age_at_delivery` | 36203531 | LOINC | 85724-3 | Age of Mother --at delivery | Measurement | `measurement.measurement_concept_id` |
| `year` | 9448 | UCUM | a | year | Unit | `measurement.unit_concept_id` |
| `prenatal_visits_count` | 40771079 | LOINC | 68493-6 | Prenatal visits for this pregnancy # | Observation | `observation.observation_concept_id` |
| `first_prenatal_visit_trimester` | 44817052 | LOINC | 75163-6 | Mother's Trimester of first prenatal visit [CDC.CS] | Observation | `observation.observation_concept_id` |
| `mother_education` | 40760823 | LOINC | 57712-2 | Highest level of education Mother | Observation | `observation.observation_concept_id` |
| `birth_weight` | 3011043 | LOINC | 8339-4 | Birth weight Measured | Measurement | `measurement.measurement_concept_id` |
| `gram` | 8504 | UCUM | g | gram | Unit | `measurement.unit_concept_id` |
| `mother` | 4248584 | SNOMED | 72705000 | Mother | Relationship | `fact_relationship.relationship_concept_id` |
| `child` | 4285883 | SNOMED | 67822003 | Child | Relationship | `fact_relationship.relationship_concept_id` |
| `person_table` | 1147314 | CDM | CDM370 | person | Metadata | `fact_relationship.domain_concept_id_1`, `_2` |
| `cdm_version` | 902983 | CDM | CDM v5.4.3 | OMOP CDM Version 5.4.3 | Metadata | `cdm_source.cdm_version_concept_id` |

Targets of `source_to_concept_map`:

| concept_id | Vocabulary | Code | Name | Domain | Source code |
|---|---|---|---|---|---|
| 45880554 | LOINC | LA21196-3 | 1st trimester | Meas Value | `TRIMESTREPRIMERCONSULTA` 1 |
| 45879078 | LOINC | LA21197-1 | 2nd trimester | Meas Value | `TRIMESTREPRIMERCONSULTA` 2 |
| 45885074 | LOINC | LA21198-9 | 3rd trimester | Meas Value | `TRIMESTREPRIMERCONSULTA` 3 |
| 45880561 | LOINC | LA21278-9 | No prenatal care | Meas Value | `TRIMESTREPRIMERCONSULTA` 0 |
| 4075636 | SNOMED | 223687006 | Mexico | Geography | `RESIDEEXTRANJERO` 2 |
| 4074913 | SNOMED | 224294005 | No formal education | Observation | `ESCOLARIDAD` 1 |
| 44800023 | SNOMED | 342271000000107 | Educated to primary school level | Observation | `ESCOLARIDAD` 31, 32 |
| 43020414 | SNOMED | 603435002 | Educated to junior high school level | Observation | `ESCOLARIDAD` 51, 52, 111, 112 |
| 43020395 | SNOMED | 603434003 | Educated to senior high school level | Observation | `ESCOLARIDAD` 71, 72, 131, 132 |
| 4076230 | SNOMED | 224299000 | Received higher education | Observation | `ESCOLARIDAD` 81, 82, 101, 102 |
| 8507 | Gender | M | MALE | Gender | `SEXO` 1 |
| 8532 | Gender | F | FEMALE | Gender | `SEXO` 2 |

Rejected alternatives:

| For | Rejected | Why |
|---|---|---|
| Gestational age | 46234792, LOINC 76516-4 "Gestational age--at birth" (Observation) | Same meaning, but its domain would send the outcome to `OBSERVATION`. The term was created for a physical therapy registry panel ("APTA Registry patient episode of care panel") and nothing maps to it. The SNOMED concept is a descendant of "Fetal gestational age", so a concept set built on that hierarchy finds it. It is also the concept onto which OMOP maps the gestational-age-at-birth codes of CIEL, CDISC, Nebraska Lexicon and Read (D-064) |
| Total visits | 46270506, SNOMED 3401000175105 "Total number of prenatal care visits" (Observation) | Valid as well. LOINC 68493-6 is the item of the "U.S. standard certificate of live birth" panel: the same kind of declared count on the same kind of document (D-065) |
| Trimester | 1470020, LOINC 106723-0 "Month of first prenatal care visit" | A month cannot be derived from a trimester without inventing it (D-005) |
| Trimester, code 0 | Concept 0 | It would merge "NO RECIBIÓ" with the flavors of null (D-065) |
| Plurality | 1469676, LOINC 107310-5 "Birth plurality Pregnancy" | Its answers are only "Singleton pregnancy" and "Multiple pregnancy", which would lose twins against three or more |
| Race | "American Indian or Alaska Native" for `SECONSIDERAINDIGENA` = 1 | A US census category applied to a Mexican self-identification; it would give a race to 8.1 % and 0 to everyone else (D-061) |
| Mother's age | The age computed from `PERSON` at the delivery date | The protocol adjusts for the declared age (D-094). From the year of birth alone the five-year group changes in 9.9 % of the base cohort, from the full date of birth in 0.16 % (D-100) |
| Mother's age | 3007191, LOINC 21612-7 "Age - Reported"; 4028487, SNOMED 13506008 "Maternal age" (both Observation) | Valid, but neither says at which moment the age is taken. LOINC 85724-3 names the mother's age at delivery, which is what the certificate records |
| Education, answers | The LOINC answers of the US certificate, such as LA12455-4 "8th grade or less" and LA12456-2 "9th - 12th grade, no diploma" | They follow US grades, and *secundaria* falls across two of them (D-101) |
| Education, answers | Concept 0 for every code, with the levels in SQL | A valid answer would look like a missing one, the distinction D-065 kept for the trimester, and the grouping would need configuration of its own (D-101) |
| Insurance | `PAYER_PLAN_PERIOD` in v0.2 | No analysis of v0.2 uses insurance; it is mapped with the gradient of v1.0 (D-102) |
| Newborn sex, codes 0 and 9 | 8551 "UNKNOWN" (Gender) | Deprecated and non-standard in the loaded bundle; a flavor of null is 0 (D-067, D-103) |
| Newborn location | The mother's `LOCATION` | The certificate records the mother's residence, not the newborn's (D-103) |
| Mother–newborn link | 4050951 "Parent of" and 4051272 "Child of" (SNOMED, Observation) | Observation concepts, and less precise than Mother and Child (D-104) |
| Mother–newborn link | 581436 "Parent to Child Measurement" (Relationship) | It links measurements, not persons (D-104) |
| Domain of the linked facts | 56 "Person" (Domain) | Deprecated in the loaded bundle since 2022-09-27, with no replacement (D-104) |
| Birth weight | 4264825, SNOMED 364589006 "Birth weight" (Measurement) | Valid, but 8339-4 is the item of the birth certificate panel, as for the visit count (D-105) |
| Birth weight | 40759177, LOINC 56056-5 "Birth weight - Reported" (Observation) | Its domain would send the weight to `OBSERVATION` (D-105) |

## Codes without a standard concept

Every one is a row of `source_to_concept_map` with `target_concept_id = 0`, and keeps its raw
value in the source field. Record counts are orientation, over 2020–2023.

| Column | Code | DGIS label | Records | Lands as |
|---|---|---|---|---|
| `EDADGESTACIONAL` | 99 | No Especificado | 4,813 | `value_as_number` NULL |
| `TOTALCONSULTAS` | 99 | No Especificado | 47,158 | `value_as_number` NULL |
| `TOTALCONSULTAS` | blank | — (descriptor note: nulls are values not specified or not applicable) | 12,985 | `value_as_number` and `value_source_value` NULL |
| `TRIMESTREPRIMERCONSULTA` | 8 | NO ESPECIFICADO | 65,545 | `value_as_concept_id` 0 |
| `TRIMESTREPRIMERCONSULTA` | 9 | SE IGNORA | 57,115 | `value_as_concept_id` 0 |
| `PRODUCTOEMBARAZO` | 0 | NO ESPECIFICADO | 10,257 | `value_as_number` NULL |
| `RESIDEEXTRANJERO` | 1 | SI | 3,069 | `country_concept_id` 0: resident abroad, country not recorded |
| `RESIDEEXTRANJERO` | 88 | not in `SI_NO` | 631 | `country_concept_id` 0 (D-057) |
| `RESIDEEXTRANJERO` | 0, 8, 9 | NO ESPECIFICADO, NO APLICA, SE IGNORA | 0 | `country_concept_id` 0 |
| `ENTIDADRESIDENCIA` | 00 | NO ESPECIFICADO | 4,349 | `state` NULL |
| `ENTIDADRESIDENCIA` | 88 | NO APLICA | 3,069 | `state` NULL |
| `ENTIDADRESIDENCIA` | 99 | SE IGNORA | 2,783 | `state` NULL |
| `EDAD` | 888 | No Especificado | 0 | `value_as_number` NULL; not used for `year_of_birth` |
| `EDAD` | 999 | Se Ignora | 670 | not used for `year_of_birth`. None of the 670 has a usable date of birth either, so none is loaded (D-060) and no age row is written |
| `ESCOLARIDAD` | 0 | NO ESPECIFICADO | 29,338 | `value_as_concept_id` 0 |
| `ESCOLARIDAD` | 88 | NO APLICA | 64 | `value_as_concept_id` 0 |
| `ESCOLARIDAD` | 99 | SE IGNORA | 17,734 | `value_as_concept_id` 0 |
| `FECHANACIMIENTOMADRE` | 09/09/9999 | fecha no especificada | 767 | not used for `year_of_birth` |
| `SEXO` | 0 | NO ESPECIFICADO | 3,957 | `gender_concept_id` 0 of the newborn |
| `SEXO` | 9 | SE IGNORA | 654 | `gender_concept_id` 0 of the newborn |
| `PESO` | 9999 | No Especificado (descriptor) | 354,847 | `value_as_number` NULL |

`TRIMESTREPRIMERCONSULTA` 0, "NO RECIBIÓ" (167,885 records), and `TOTALCONSULTAS` 0 (195,252
records) are answers, not missing values: they map to "No prenatal care" and to the number 0.

`ESCOLARIDAD` 88, "NO APLICA", is a flavor of null like the other two (D-067): the descriptor
says the system sets it when the question does not apply, and education applies to every mother.
`ESCOLARIDAD` has no blank cell in 2020–2023, and `EDAD` neither.

## What the next tasks take from here

- **1.2.4, staging.** `staging` carries `source_row` as defined in rule 7. A test loads the same
  synthetic CSV twice and gets the same ordinals, in file order.
- **1.4.3, vocabularies.** `validate-concepts` reads both configuration files: `concept_sets.yml`
  gives the expected vocabulary, code and domain of each concept, and `target_domain_id` gives the
  domain of each map target.
- **1.4.4, ETL.** It registers the `SINAC20_*` vocabularies, loads the map and writes
  `CDM_SOURCE`. Its checks assert, besides the anti-joins of that task:
  - no `VISIT_OCCURRENCE` row exists (D-066);
  - every event date equals the person's observation period;
  - the records not loaded for lack of a year of birth are counted, so attrition step 1 can be
    reported (D-060).

  Implemented in [`../sql/etl/`](../sql/etl/) (`pipeline.py cdm`). The counts and the checks are
  rows of `results.etl_counts`, and a run commits only when every check is 0 (D-073).
- **1.4.5, covariates (v1).** The ETL writes the age and education rows and counts each of their
  rules per year (`mother_age_at_delivery:*`, `mother_education:*`). Its checks now require three
  rows each of `MEASUREMENT` and `OBSERVATION` per `PERSON`.
- **1.4.6, the newborn.** The ETL writes the newborn `PERSON`, its observation period, its birth
  weight and the two `FACT_RELATIONSHIP` rows, and counts the sex and weight rules per year
  (`gender:*`, `birth_weight:*`) with `person rows:mother` and `rows:newborn`. The per-person
  checks count the mothers apart from the newborns (`mother_without_*`,
  `newborn_without_one_measurement`, `newborn_with_an_observation`), and new checks assert the
  newborn's date of birth and the two links of every record. The cohort SQL takes the mothers
  through `FACT_RELATIONSHIP` (D-106).
- **1.6.4, odds ratios.** The step "covariates known" (D-095) reads the CDM: `value_as_number` of
  `mother_age_at_delivery` is not NULL, `value_as_concept_id` of `mother_education` is not 0, and
  `LOCATION.state` is not NULL. The seven age groups are cut from `value_as_number`, with bounds
  that go to configuration, not SQL (D-094, `FOR APPROVAL`). The education levels are the
  concepts.
- **v1.0, insurance.** `AFILIACION` is mapped with the gradient by insurance (D-102). Its
  destination is still open. `PAYER_PLAN_PERIOD` needs start and end dates, which could only be the
  delivery day under D-062 and D-063, and the payer vocabulary of the CDM (SOPT) is a US typology.
- **Data quality checks.** A plausibility check on `year_of_birth`, such as the one of the OHDSI
  Data Quality Dashboard, will flag the one mother born in year 1. That record is known and left
  as it is.
