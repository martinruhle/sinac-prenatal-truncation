# OMOP mapping v0: the vertical slice

How the SINAC records of 2020–2023 land in the OMOP CDM v5.4 for the vertical slice (D-009): the
tables that the base cohort of [`protocol.md`](protocol.md#base-cohort) and the v0.1 milestone
need, and nothing else yet. Source variables are described in
[`data_dictionary.md`](data_dictionary.md); this document says where each one goes (D-017).

Every populated field has one row, with its source, its rule and who decided it:

- **OMOP**: the CDM specification or convention dictates the rule, and it is quoted.
- **Project**: a decision of this study, with its entry in [`decisions.md`](decisions.md).

The concept ids are held in [`../config/concept_sets.yml`](../config/concept_sets.yml) and
[`../config/source_to_concept_map.csv`](../config/source_to_concept_map.csv), never in SQL
(CLAUDE.md rule 8, D-023). They are repeated here to be read, and the configuration is the
reference: `tests/test_concepts.py` checks that every concept there carries its vocabulary, code
and domain, and that each domain is one the CDM allows in the field it is written to.

## Scope

| In v0 | Not in v0 | Why not yet |
|---|---|---|
| `PERSON` (the mother) | `PERSON` (the newborn), `FACT_RELATIONSHIP`, birth weight | No criterion of the base cohort uses the newborn; they arrive with the covariates in v0.2 |
| `OBSERVATION_PERIOD` | `VISIT_OCCURRENCE`, `CARE_SITE` | No criterion uses the delivery visit, and no visit is ever created for prenatal care (D-066) |
| `MEASUREMENT`: gestational age, plurality | `PAYER_PLAN_PERIOD` | Insurance is a covariate of v0.2 |
| `OBSERVATION`: total visits, trimester of the first visit | `ATENCIONPRENATAL` | The rule for missing prenatal care data is PENDING in [`protocol.md`](protocol.md#exposure-measures). Candidate concept, checked in Athena: 44817093, LOINC 75204-8 "Prenatal care indicator [CDC.CS]", Observation |
| `LOCATION`: residence | | |
| `CDM_SOURCE`, and `VOCABULARY` and `SOURCE_TO_CONCEPT_MAP` rows for the local codes | | |

The base cohort needs four source fields: `FECHANACIMIENTO` (criterion 1), `RESIDEEXTRANJERO`
(criterion 2), `EDADGESTACIONAL` (criteria 3 and 6) and `PRODUCTOEMBARAZO` (criteria 4 and 5).
All four land in the CDM, so the cohort SQL never reads `staging` (D-068).

## Rules shared by every table

1. **Type.** Every `*_type_concept_id` is `registry` (32879, "Registry"). OMOP requires a type
   concept that "best represents the provenance of the record"; the source is a registry of
   certificates, not an EHR or a claim. *Project, D-065.*
2. **Dates.** Every event is dated `FECHANACIMIENTO`, the delivery date: gestational age is
   measured at delivery, and the visit count, the trimester and the plurality are recorded on the
   certificate at delivery. `FECHANACIMIENTO` is a full date (`dd/mm/yyyy`) in all 6,531,527
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
     column up to 2099. The newborn, from v0.2, is the mother's id + 1,000,000,000.
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

`SECONSIDERAINDIGENA` and `HABLALENGUAINDIGENA` stay out of `PERSON`. The OMOP race and ethnicity
fields encode US OMB categories, which are not the construct SINAC records (D-061); the question
the two variables open is future work ([`roadmap.md`](roadmap.md#47-indigenous-mothers)).

### OBSERVATION_PERIOD

One row per `PERSON`: **a single day, the delivery** (D-062).

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

Two rows per `PERSON`, in this order: gestational age, then plurality.

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

### OBSERVATION

Two rows per `PERSON`, in this order: total visits, then the trimester of the first visit.

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
`pipeline.py validate-concepts` (task 1.4.3).

| Key | concept_id | Vocabulary | Code | Name | Domain | Written to |
|---|---|---|---|---|---|---|
| `female` | 8532 | Gender | F | FEMALE | Gender | `person.gender_concept_id` |
| `registry` | 32879 | Type Concept | OMOP4976952 | Registry | Type Concept | every `*_type_concept_id` |
| `gestational_age_at_birth` | 4260747 | SNOMED | 412726003 | Length of gestation at birth | Measurement | `measurement.measurement_concept_id` |
| `week` | 8511 | UCUM | wk | week | Unit | `measurement.unit_concept_id` |
| `birth_plurality` | 40760833 | LOINC | 57722-1 | Birth plurality of Pregnancy | Measurement | `measurement.measurement_concept_id` |
| `at_least` | 4171755 | SNOMED | 276138003 | >= | Meas Value Operator | `measurement.operator_concept_id` |
| `prenatal_visits_count` | 40771079 | LOINC | 68493-6 | Prenatal visits for this pregnancy # | Observation | `observation.observation_concept_id` |
| `first_prenatal_visit_trimester` | 44817052 | LOINC | 75163-6 | Mother's Trimester of first prenatal visit [CDC.CS] | Observation | `observation.observation_concept_id` |
| `cdm_version` | 902983 | CDM | CDM v5.4.3 | OMOP CDM Version 5.4.3 | Metadata | `cdm_source.cdm_version_concept_id` |

Targets of `source_to_concept_map`:

| concept_id | Vocabulary | Code | Name | Domain | Source code |
|---|---|---|---|---|---|
| 45880554 | LOINC | LA21196-3 | 1st trimester | Meas Value | `TRIMESTREPRIMERCONSULTA` 1 |
| 45879078 | LOINC | LA21197-1 | 2nd trimester | Meas Value | `TRIMESTREPRIMERCONSULTA` 2 |
| 45885074 | LOINC | LA21198-9 | 3rd trimester | Meas Value | `TRIMESTREPRIMERCONSULTA` 3 |
| 45880561 | LOINC | LA21278-9 | No prenatal care | Meas Value | `TRIMESTREPRIMERCONSULTA` 0 |
| 4075636 | SNOMED | 223687006 | Mexico | Geography | `RESIDEEXTRANJERO` 2 |

Rejected alternatives:

| For | Rejected | Why |
|---|---|---|
| Gestational age | 46234792, LOINC 76516-4 "Gestational age--at birth" (Observation) | Same meaning, but its domain would send the outcome to `OBSERVATION`. The term was created for a physical therapy registry panel ("APTA Registry patient episode of care panel") and nothing maps to it. The SNOMED concept is a descendant of "Fetal gestational age", so a concept set built on that hierarchy finds it. It is also the concept onto which OMOP maps the gestational-age-at-birth codes of CIEL, CDISC, Nebraska Lexicon and Read (D-064) |
| Total visits | 46270506, SNOMED 3401000175105 "Total number of prenatal care visits" (Observation) | Valid as well. LOINC 68493-6 is the item of the "U.S. standard certificate of live birth" panel: the same kind of declared count on the same kind of document (D-065) |
| Trimester | 1470020, LOINC 106723-0 "Month of first prenatal care visit" | A month cannot be derived from a trimester without inventing it (D-005) |
| Trimester, code 0 | Concept 0 | It would merge "NO RECIBIÓ" with the flavors of null (D-065) |
| Plurality | 1469676, LOINC 107310-5 "Birth plurality Pregnancy" | Its answers are only "Singleton pregnancy" and "Multiple pregnancy", which would lose twins against three or more |
| Race | "American Indian or Alaska Native" for `SECONSIDERAINDIGENA` = 1 | A US census category applied to a Mexican self-identification; it would give a race to 8.1 % and 0 to everyone else (D-061) |

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
| `EDAD` | 888 | No Especificado | 0 | not used for `year_of_birth` |
| `EDAD` | 999 | Se Ignora | 670 | not used for `year_of_birth` |
| `FECHANACIMIENTOMADRE` | 09/09/9999 | fecha no especificada | 767 | not used for `year_of_birth` |

`TRIMESTREPRIMERCONSULTA` 0, "NO RECIBIÓ" (167,885 records), and `TOTALCONSULTAS` 0 (195,252
records) are answers, not missing values: they map to "No prenatal care" and to the number 0.

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
- **Data quality checks.** A plausibility check on `year_of_birth`, such as the one of the OHDSI
  Data Quality Dashboard, will flag the one mother born in year 1. That record is known and left
  as it is.
