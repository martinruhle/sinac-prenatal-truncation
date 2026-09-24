# SINAC prenatal care and truncation of the gestational window

[![CI](https://github.com/martinruhle/sinac-prenatal-truncation/actions/workflows/ci.yml/badge.svg)](https://github.com/martinruhle/sinac-prenatal-truncation/actions/workflows/ci.yml)

How much the association between prenatal care and preterm birth in Mexico changes with the
definition of the exposure and of the cohort, and how much of it truncation of the gestational
window produces on its own.

**No data in this repository.** Everything is rebuilt from the public SINAC download; `/data/`
and `.env` are ignored by git. The question and the method live in
[`docs/protocol.md`](docs/protocol.md) (the exposure measures, the analysis and the limitations
are still PENDING there), the plan in [`docs/roadmap.md`](docs/roadmap.md), and every non-obvious
decision in [`docs/decisions.md`](docs/decisions.md).

## Reproduce

```bash
uv sync
uv run pre-commit install
cp .env.example .env
docker compose up -d --wait
uv run --env-file .env python scripts/pipeline.py db-init
uv run --env-file .env python scripts/pipeline.py download --years 2023
uv run --env-file .env pytest
uv run --env-file .env python scripts/pipeline.py --help
```

`uv sync` installs the locked dependencies, `pre-commit install` is needed once per clone, and
`.env` is created from `.env.example` and never committed. The database needs Docker running and
`db-init` puts the OMOP schema in it.

`download` fetches the record files of the years given in `--years` from
[`config/sources.yml`](config/sources.yml) into `data/raw/dgis/`. It checks each sha256 against
the one recorded there, so a download that does not match what this repository was built on
fails instead of being used, and a file already on disk is verified, never fetched again.
Development runs on 2023 (D-009). Without `--years`, `download` takes the whole study period,
2020–2023 (D-041), and `--id` fetches any other entry, such as a catalogue.

The tests use synthetic fixtures and download nothing; the ones marked `db` need the compose
database.

## Requirements → evidence

PENDING: the `Status` column is filled at milestone `v0.1-cohort`, when a third party must be
able to locate the evidence for each requirement without running anything.

| Requirement | Evidence | Status |
|---|---|---|
| Real commit history | PRs merged into `main` | |
| README lets a third party reproduce the work | README §Reproduce | |
| Containerized environment | `compose.yml` (+ `Dockerfile` from v1.0) | |
| At least one documented cohort definition in SQL on OMOP | `sql/cohorts/01_base.sql`, `docs/protocol.md` §Base cohort | |
| Automated tests with pytest and CI | `tests/`, `.github/workflows/ci.yml`, CI badge | |
| Data dictionary | `docs/data_dictionary.md` | |
| Honest limitations section | README §Limitations, `docs/protocol.md` §Limitations | |
| AI assistance statement | `docs/ai_use.md`, `CLAUDE.md` | |
| No credentials, no identifiable data | `.gitignore`, `.dockerignore`, `results/` policy, security review notes | |

## Changes from the proposal

PENDING: completed at milestone `v0.1-cohort`. Two changes are already settled and written up
in [`docs/roadmap.md`](docs/roadmap.md), with their reasons in
[`docs/decisions.md`](docs/decisions.md):

- **Data source.** The SSA/DGIS open-data files replace the INSP standardized series (D-001,
  D-002). The record and variable counts stated in the proposal do not describe these files and
  have to be measured on them.
- **Study period.** 2020–2023 replaces 2019–2023 (D-041). The source inventory measured the cost:
  2019 needs a harmonization of its own and has no DGIS descriptor, while the four later years
  are one catalogue period. 2019 is added only under the criterion of D-050.
- **Scope.** The full sensitivity grid runs for two of the four exposure measures, one or two
  landmark weeks are used instead of three, two sensitivity axes are dropped and the adjusted
  odds ratios use a reduced covariate set (D-003 to D-007). The two conditional extras of the
  proposal are not started this semester and stay as future work (D-042).

The proposal these changes are stated against is translated in
[`docs/proposal_v2.md`](docs/proposal_v2.md).

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

PENDING: completed together with `docs/protocol.md`. Three limitations already apply:

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

## AI assistance

PENDING: `docs/ai_use.md` is assembled at milestone `v0.1-cohort` from the "AI assistance"
section of each merged pull request. The development rules given to AI assistants in this
repository are versioned in [`CLAUDE.md`](CLAUDE.md).
