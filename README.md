# SINAC prenatal care and truncation of the gestational window

[![CI](https://github.com/martinruhle/sinac-prenatal-truncation/actions/workflows/ci.yml/badge.svg)](https://github.com/martinruhle/sinac-prenatal-truncation/actions/workflows/ci.yml)

How much the association between prenatal care and preterm birth in Mexico changes with the
definition of the exposure and of the cohort, and how much of it truncation of the gestational
window produces on its own.

**No data in this repository.** Everything is rebuilt from the public SINAC download; `/data/`
and `.env` are ignored by git. The question and the method live in
[`docs/protocol.md`](docs/protocol.md) (PENDING), the plan in
[`docs/roadmap.md`](docs/roadmap.md), and every non-obvious decision in
[`docs/decisions.md`](docs/decisions.md).

## Reproduce

```bash
uv sync
uv run pre-commit install
cp .env.example .env
docker compose up -d --wait
uv run --env-file .env python scripts/pipeline.py db-init
uv run --env-file .env python scripts/pipeline.py download --id dgis_sinac_2023
uv run --env-file .env pytest
uv run --env-file .env python scripts/pipeline.py --help
```

`uv sync` installs the locked dependencies, `pre-commit install` is needed once per clone, and
`.env` is created from `.env.example` and never committed. The database needs Docker running and
`db-init` puts the OMOP schema in it. `download` fetches one file declared in
[`config/sources.yml`](config/sources.yml) into `data/raw/dgis/` and checks its sha256 against
the one recorded there, so a download that does not match what this repository was built on
fails instead of being used; a file already on disk is verified, never fetched again. The tests
use synthetic fixtures and download nothing; the ones marked `db` need the compose database.

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
  have to be measured on them. The study period is PENDING (D-041).
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
in Spanish** even though this README is in English (D-035); the year is the year of the dataset
used, so for the 2023 file it reads:

> Fuente: SS/DGIS, SINAC 2023

PENDING: the final year or years depend on the study period, which is still open (D-041).

Each downloaded file is recorded in [`config/sources.yml`](config/sources.yml) with its page, its
URL including the `?V=` version parameter DGIS publishes, the retrieval timestamp, the size and
the sha256. The hash and the size are written once, on the first download, and are never
overwritten afterwards (D-044): if DGIS republishes a file, the hash stops matching and the
pipeline fails on purpose. Only the files the project uses are listed, so while the study period
is open (D-041) that is the 2023 records alone; the descriptors and catalogues are added with the
source inventory.

## Limitations

PENDING: completed together with `docs/protocol.md`. One limitation already applies to this
repository:

- The DGIS files are served over **HTTP without TLS**. The recorded sha256 detects any later
  change to a file, but it does not authenticate the first download.

## AI assistance

PENDING: `docs/ai_use.md` is assembled at milestone `v0.1-cohort` from the "AI assistance"
section of each merged pull request. The development rules given to AI assistants in this
repository are versioned in [`CLAUDE.md`](CLAUDE.md).
