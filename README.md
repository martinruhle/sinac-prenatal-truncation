# SINAC prenatal care and truncation of the gestational window

[![CI](https://github.com/martinruhle/sinac-prenatal-truncation/actions/workflows/ci.yml/badge.svg)](https://github.com/martinruhle/sinac-prenatal-truncation/actions/workflows/ci.yml)

How much the association between prenatal care and preterm birth in Mexico changes with the
definition of the exposure and of the cohort, and how much of it truncation of the gestational
window produces on its own.

**No data in this repository.** Everything is rebuilt from the public SINAC download; `/data/`
and `.env` are ignored by git. The question and the method live in
[`docs/protocol.md`](docs/protocol.md) (the limitations are still PENDING there), the plan in
[`docs/roadmap.md`](docs/roadmap.md), and every non-obvious decision in
[`docs/decisions.md`](docs/decisions.md).

## Reproduce

```bash
uv sync
uv run pre-commit install
cp .env.example .env
docker compose up -d --wait
uv run --env-file .env python scripts/pipeline.py db-init
uv run --env-file .env python scripts/pipeline.py all --years 2023
uv run --env-file .env pytest
uv run --env-file .env python scripts/pipeline.py --help
```

`uv sync` installs the locked dependencies, `pre-commit install` is needed once per clone, and
`.env` is created from `.env.example` and never committed. The database needs Docker running and
`db-init` puts the OMOP schema in it.

One file is downloaded by hand before `all`: the Athena vocabulary package (see `vocab` below).
`all` then runs `download`, `stage`, `vocab`, `validate-concepts`, `cdm` and `cohorts` in that
order on the years given, and stops at the first step that fails (D-082). Each step is also a
subcommand of its own, described below. `publish` is not a step of `all`: it runs at a milestone
only. Every milestone is rebuilt this way from a clean clone before it is tagged
([`docs/reproducibility.md`](docs/reproducibility.md)).

The commands above rebuild 2023, the year development runs on (D-009). The whole study period is
`all --years 2020-2023`, which is also what `all` runs without `--years` (D-041). It was measured
on 2 October 2026 on a laptop with an Intel Core i5-1240P, 16 GB of RAM and an NVMe SSD, under
Windows 11 Pro with Docker Engine 28.4.0 limited to 6 CPUs and 12.5 GB, keeping the Postgres
defaults of [`compose.yml`](compose.yml):

- **Wall time: 24 min 15 s.** `all` took 21 min 2 s with the four record files already on disk:
  `stage` 2 min 31 s, `vocab` 4 min 56 s, `cdm` 12 min 43 s and `cohorts` 47 s. Downloading the
  four files took another 3 min 13 s on that connection.
- **Disk: 17.0 GB at the peak.** `data/` holds 2.35 GB: the four ZIPs (0.27 GB), their extracted
  CSVs (1.67 GB), the Parquet copies (0.21 GB) and the Athena package (0.20 GB). The Postgres
  volume holds 11.2 GB once the run ends, 10.1 GB of database and 1.1 GB of write-ahead log. It
  peaked at 14.6 GB during `cdm`, in samples taken every 30 s.

`download` fetches the record files of the years given in `--years` from
[`config/sources.yml`](config/sources.yml) into `data/raw/dgis/`. It checks each sha256 against
the one recorded there, so a download that does not match what this repository was built on
fails instead of being used, and a file already on disk is verified, never fetched again.
Development runs on 2023 (D-009). Without `--years`, `download` takes the whole study period,
2020–2023 (D-041), and `--id` fetches any other entry, such as a catalogue.

`stage` loads those files into the `staging` schema, one table per year, keeping every value as
text (D-033). It extracts the CSV into `data/raw/dgis/extracted/` and writes a Parquet copy into
`data/interim/`. It then counts the rows of the CSV, the Parquet copy and the table, and commits
only when the three agree. The counts are kept in `staging.load_counts`, and running it again
gives the same result (D-069). The staged columns are described in
[`docs/data_dictionary.md`](docs/data_dictionary.md).

`vocab` loads the OMOP standardized vocabularies into `cdm`. The pipeline does not download them:
[Athena](https://athena.ohdsi.org) builds the package for a logged-in account, so it is
downloaded by hand into `data/raw/athena/<package date>/` and never committed. The `vocabulary:`
block of [`config/sources.yml`](config/sources.yml) declares that package, with its sha256, its
vocabulary version and the rows of each table, and `vocab` refuses a package that differs. It
reads the ZIP directly, without extracting it, and loads seven tables in one transaction (D-071,
D-072). `validate-concepts` then checks every concept id of the configuration against the loaded
vocabulary: it must exist, be valid and be standard where it has to be, and its domain must fit
the field it is written to. CI runs neither step; their tests load a synthetic package.

Athena builds each package on request, so a package downloaded later is a different file. To
rebuild with one, the package has to hold the vocabularies that
[`config/concept_sets.yml`](config/concept_sets.yml) takes concepts from: SNOMED, LOINC and UCUM,
plus OMOP's own Gender, Type Concept and CDM. Put the ZIP under `data/raw/athena/<package date>/`
and write its date, path, size, sha256, vocabulary version and rows per table into the `vocabulary:`
block. When one of them differs, `vocab` refuses the package and states the value the package
has: the sha256 and size, the version and, table by table, the rows.

`cdm` populates the OMOP tables of the vertical slice from `staging`, as
[`docs/omop_mapping.md`](docs/omop_mapping.md) maps them: PERSON (the mother and the newborn),
a one-day OBSERVATION_PERIOD, MEASUREMENT, OBSERVATION, FACT_RELATIONSHIP, LOCATION, CDM_SOURCE
and the map of local codes.
The SQL is in [`sql/etl/`](sql/etl/) and reads every concept id from the configuration, loaded
into `results.concept_sets`. Every value is cast there, and each rule's count goes to
`results.etl_counts`, together with the post-load checks. The run is one transaction that commits
only when every check counts 0, and running it again gives the same tables (D-073). It registers
the local vocabularies in VOCABULARY, which `vocab` empties, so run `cdm` again after `vocab`.

`cohorts` builds the base cohort of [`docs/protocol.md`](docs/protocol.md#base-cohort) and the
analysis cohort of [§Records analysed](docs/protocol.md#records-analysed) from the CDM, with the
SQL of [`sql/cohorts/`](sql/cohorts/), on the record files of the years given in `--years`, which
`cdm` must have loaded. It writes one row per mother and pregnancy into `results.cohort`, the
attrition table into `results.attrition` (one row per step, per definition and per year, a step
that removes nobody included), and exposure measures (a) and (c) of every mother into
`results.exposure`. The run is one transaction that
commits only when the attrition is consistent: the counts never grow, each step excludes what it
removes, and the last step equals the cohort. Running it again gives the same tables.

`publish` writes the results a milestone versions under [`results/`](results/) (D-014): the
attrition of the base cohort, `results/attrition_base.csv`, and `results/manifest.json`, which
names the commit, the period, the sha256 of each record file and of the vocabulary package, and
the sha256 of the CSV. It publishes what one commit produces end to end, so it refuses a working
tree with changes outside `results/` and a CDM that `cdm` did not load from that commit, then
rebuilds the cohorts and reads the CSV back against the run (D-080). The counts are exact, with no
small-cell suppression, because the source records are public (D-040).

The tests use synthetic fixtures and download nothing; the ones marked `db` need the compose
database.

## Requirements → evidence

Where the evidence for each minimum requirement of the course lives, and its status at milestone
`v0.1-cohort`. **Met** means the evidence is in place for this milestone; **Partial** says what is
still missing and when it lands.

| Requirement | Evidence | Status |
|---|---|---|
| Real commit history | [Pull requests merged into `main`](https://github.com/martinruhle/sinac-prenatal-truncation/pulls?q=is%3Apr+is%3Amerged), each with its checks and its AI assistance section | **Met**: #1, then #18–#31, #33 and #35, one per issue |
| README lets a third party reproduce the work | README §Reproduce, [`docs/reproducibility.md`](docs/reproducibility.md) | **Met**: rebuilt from a clean clone on 2023, with the same attrition sha256; the Athena package is the one file downloaded by hand |
| Containerized environment | [`compose.yml`](compose.yml) (+ `Dockerfile` from v1.0) | **Met** with `compose.yml`: Postgres 16.15 with a healthcheck, the same file CI starts. The analysis image comes with v1.0 (D-015) |
| At least one documented cohort definition in SQL on OMOP | [`sql/cohorts/01_base.sql`](sql/cohorts/01_base.sql), [`docs/protocol.md`](docs/protocol.md#base-cohort) §Base cohort, [`results/attrition_base.csv`](results/attrition_base.csv) | **Met**: the base cohort on 2023, 1,490,896 singleton births, with its attrition table |
| Automated tests with pytest and CI | [`tests/`](tests/), [`.github/workflows/ci.yml`](.github/workflows/ci.yml), CI badge | **Met**: 340 tests on synthetic fixtures, the `db` ones against the compose database. CI runs ruff, the format check, mypy and pytest with an 80 % coverage floor (D-030) |
| Data dictionary | [`docs/data_dictionary.md`](docs/data_dictionary.md) | **Met** for v0.1: the 22 of 64 published columns the project uses (D-011). It grows with the variables of v0.2 |
| Honest limitations section | README §Limitations, [`docs/protocol.md`](docs/protocol.md#limitations) §Limitations | **Partial**: the limitations of the source, the design and the data model are written. Those of the exposure measures and the analysis come with them, in v0.2 and v1.0 |
| AI assistance statement | [`docs/ai_use.md`](docs/ai_use.md), [`CLAUDE.md`](CLAUDE.md) | **Met**: one entry per pull request, taken from its AI assistance section |
| No credentials, no identifiable data | [`.gitignore`](.gitignore), [`.dockerignore`](.dockerignore), `results/` policy (D-014, D-040), security review notes (v1.0) | **Met** for v0.1: `/data/` and `.env` are ignored, CI generates its database password per run (D-039), `results/` holds aggregate counts only, and the history was checked at the tag ([release notes](https://github.com/martinruhle/sinac-prenatal-truncation/releases/tag/v0.1-cohort)). The security review is part of v1.0 |

## Changes from the proposal

The changes are stated against proposal v2, which is translated in
[`docs/proposal_v2.md`](docs/proposal_v2.md). They are written up in
[`docs/roadmap.md`](docs/roadmap.md), and their reasons are in
[`docs/decisions.md`](docs/decisions.md), where they are tagged `[SOURCE CHANGE]` or
`[SCOPE CHANGE]`.

- **Data source.** The SSA/DGIS open-data files replace the INSP standardized series (D-001,
  D-002). The 31,486,699 records and 91 variables in the proposal describe that series. The four
  files of the study period hold 6,531,527 records, with 64 columns each
  ([`docs/source_inventory.md`](docs/source_inventory.md)).
- **Study period.** 2020–2023 replaces 2019–2023 (D-041). The source inventory measured the cost:
  2019 needs a harmonization of its own and has no DGIS descriptor, while the four later years
  are one catalogue period. 2019 is added only under the criterion of D-050.
- **Scope.** The adjusted odds ratios use a reduced covariate set, and the sensitivity analysis
  is smaller (D-003 to D-007):
  - the full sensitivity grid runs for two of the four exposure measures;
  - one or two landmark weeks are used instead of three;
  - two sensitivity axes are dropped.

  A third axis, births before week 22, is dropped too. The exclusion stays in the base cohort,
  with its count in the attrition table: 701 records in 2020–2023 (D-055). The two conditional
  extras of the proposal are not started this semester and stay as future work (D-042).
- **What the proposal left unstated.** The protocol fixes three things the proposal did not
  state:
  - the unit of analysis: the live-birth certificate, with singletons only (D-051);
  - the source of the preterm cut-off: NOM-007-SSA2-2016 (D-053);
  - residence in Mexico as an eligibility criterion (D-057).

  The table in [`docs/protocol.md`](docs/protocol.md#changes-from-proposal-v2) sets each one
  against the proposal.

## Data model

Postgres with the OMOP Common Data Model **v5.4**. The DDL is not written here: the official
PostgreSQL files are vendored unmodified from
[OHDSI/CommonDataModel](https://github.com/OHDSI/CommonDataModel), pinned to a commit and
recorded with their sha256 in [`sql/ddl/ohdsi/SOURCE.md`](sql/ddl/ohdsi/SOURCE.md). One command
applies them:

```bash
uv run --env-file .env python scripts/pipeline.py db-init
```

That creates the `cdm`, `staging` and `results` schemas and applies the tables, primary keys and
indices to `cdm`. Foreign keys are **not** applied: referential rules are explicit anti-join
checks in the ETL, which keeps bulk loads fast and makes each rule countable (D-032). Re-running
the command refuses to touch a schema that already has tables unless `--recreate` is passed.

Where each SINAC variable lands in the model, and with which concept, is in
[`docs/omop_mapping.md`](docs/omop_mapping.md). The concept ids live only in
[`config/concept_sets.yml`](config/concept_sets.yml) and
[`config/source_to_concept_map.csv`](config/source_to_concept_map.csv), never in SQL.

**CDM v5.5 exists and is not used here.** It was released on 25 August 2026 and is additive:
fields added to existing tables, three tables for vocabulary metadata, nothing removed or
renamed. The OHDSI analytic tools this project leans on still target v5.4, and proposal v2 and
the roadmap are written against it, so migrating mid-project would be a scope change with no
benefit for the question being asked (D-043).

## Data source and citation

Subsistema de Información sobre Nacimientos (SINAC), published as open data by the Dirección
General de Información en Salud (DGIS), Secretaría de Salud, Mexico: one ZIP file per year,
plus variable descriptors and catalogues. The files are public and free, and carry no personal
data.

The Términos de Libre Uso of SSA/DGIS allow copying, distributing, adapting and extracting the
information, provided the Secretaría de Salud / DGIS is credited as the author and, where
technically possible, the source is named with their formula. That line is used **verbatim and
in Spanish** even though this README is in English (D-035). The year in the line is the year of
the dataset used, and the study period is 2020–2023 (D-041), so the line is given once for each
of the four files:

> Fuente: SS/DGIS, SINAC 2020
>
> Fuente: SS/DGIS, SINAC 2021
>
> Fuente: SS/DGIS, SINAC 2022
>
> Fuente: SS/DGIS, SINAC 2023

Each downloaded file is recorded in [`config/sources.yml`](config/sources.yml) with its page, its
URL including the `?V=` version parameter DGIS publishes, the retrieval timestamp, the size and
the sha256. The hash and the size are written once, on the first download, and are never
overwritten afterwards (D-044): if DGIS republishes a file, the hash stops matching and the
pipeline fails on purpose. The manifest lists the files the
[source inventory](docs/source_inventory.md) measured:

- the 2020–2023 records of the study period;
- the 2019 records, kept because 2019 is a conditional extension (D-050);
- the descriptors and catalogues of both catalogue periods.

## Limitations

PENDING: completed together with `docs/protocol.md`. Four limitations already apply:

- The DGIS files are served over **HTTP without TLS**. The recorded sha256 detects any later
  change to a file, but it does not authenticate the first download.
- **The study period, 2020–2023, has no pre-pandemic year** (D-041). The secular trend and the
  effect of the COVID-19 pandemic cannot be told apart. The COVID-19 sensitivity axis therefore
  sets the years of acute disruption against the years of recovery, not against a pre-pandemic
  baseline ([`docs/protocol.md`](docs/protocol.md#what-the-period-does-not-allow)).
- **SINAC publishes no mother identifier**, so the pregnancies of one woman cannot be linked and
  the mother is one `PERSON` per certificate. The certificates of one multiple pregnancy cannot be
  grouped either, which is why the base cohort keeps singletons only (D-051,
  [`docs/protocol.md`](docs/protocol.md#design-and-unit-of-analysis)).
- **The vocabulary package cannot be downloaded again as it is.** Athena builds each package on
  request, so a rebuild months later uses another package, and its sha256 in
  `results/manifest.json` differs. `validate-concepts` checks that every configured concept is
  still valid and standard in it, but the published counts were verified with the package of
  record only (see `vocab` in §Reproduce).

## AI assistance

The project was developed with Claude Code. [`docs/ai_use.md`](docs/ai_use.md) states how the
assistant was used and, pull request by pull request, what it did and what the author decided or
checked. The development rules given to the assistant are versioned in [`CLAUDE.md`](CLAUDE.md).
