# Decision log

One entry per non-obvious decision: date, what was decided, the rejected alternative and the
reason, in three lines at most. `[SCOPE CHANGE]` marks a change to proposal v2;
`[SOURCE CHANGE]` marks a change of data source; `FOR APPROVAL` marks a decision waiting for
the author's sign-off.

- **D-001 · 2026-09-17 · [SOURCE CHANGE]** Primary data source: DGIS open-data SINAC files (one ZIP per year).
  Rejected: the INSP standardized series (RIISP, MEX-INSP-SINAC-2008-2023). Why: DGIS is the only download verified as public, direct and scriptable; INSP account registration failed (no verification e-mail).
- **D-002 · 2026-09-17** The INSP series stays as a fallback, only if access is obtained before extending the analysis beyond one year.
  Rejected: waiting for INSP access. Why: it would block the whole schedule.
- **D-003 · 2026-09-17 · [SCOPE CHANGE]** The full sensitivity grid is run only for measures (a) total visits and (c) first-trimester start; (b) APNCU and (d) landmark cohorts appear in the main analysis only.
  Rejected: every axis for every measure. Why: 6 h/week budget.
- **D-004 · 2026-09-17 · [SCOPE CHANGE]** One or two landmark weeks instead of three; the choice is made in docs/protocol.md.
  Rejected: weeks 28, 32 and 34. Why: 6 h/week budget.
- **D-005 · 2026-09-17 · [SCOPE CHANGE]** No sensitivity analysis for the month assigned within the first-visit trimester; a single documented rule is used for APNCU.
  Rejected: keeping that axis. Why: 6 h/week budget.
- **D-006 · 2026-09-17 · [SCOPE CHANGE]** No sensitivity analysis using birth weight <2500 g as an alternative outcome.
  Rejected: keeping it. Why: budget; it addresses gestational-age measurement, not truncation, which is the study question.
- **D-007 · 2026-09-17 · [SCOPE CHANGE]** Adjusted odds ratios use a reduced covariate set, defined in docs/protocol.md.
  Rejected: maternal age, education, insurance, state and year together. Why: 6 h/week budget.
- **D-008 · 2026-09-17** The data quality audit is reduced to per-step row counts, which the attrition table needs anyway.
  Rejected: a separate audit of missingness, ranges and extreme values. Why: it is the first cut allowed by the working plan, and the DGIS quality methodology defines completeness and validity as concepts without publishing numeric ranges.
- **D-009 · 2026-09-17** Development and milestone v0.1 run on 2023 only, with the ETL built as a vertical slice (first the tables the base cohort needs).
  Rejected: full period and all tables before session 18. Why: budget; the full period is loaded for v0.2.
- **D-010 · 2026-09-17** The null simulation uses 2–3 fixed adherence scenarios.
  Rejected: a continuous adherence model. Why: budget; scenarios still express "varying adherence".
- **D-011 · 2026-09-17** The data dictionary covers the variables actually used, built from the DGIS variable descriptors.
  Rejected: documenting every source variable. Why: budget.
- **D-012 · 2026-09-17** Milestone v0.2 (session 24) carries exposures a–d, crude and adjusted ORs, null simulation v1 and one or two sensitivity axes; the remaining axes land in v1.0.
  Rejected: the full sensitivity table by session 24; or sensitivity only at session 30. Why: fastest path that still shows the core result at the progress review.
- **D-013 · 2026-09-17 · FOR APPROVAL** Milestone tags and GitHub milestones are named `v0.1-cohort`, `v0.2-progress`, `v1.0`, `presentation`.
  Rejected: Spanish tag names. Why: everything versioned is in English, and a tag is a git ref.
- **D-014 · 2026-09-17** `results/` holds few central tables, versioned only in milestone commits, together with `results/manifest.json` (commit, source hashes, vocabulary version, period, per-file hashes).
  Rejected: never versioning results; or versioning them on every run. Why: grading reads the repository without running it; the manifest bounds staleness.
- **D-015 · 2026-09-17** An analysis image (Dockerfile) is built after milestone v0.1 with a 2-hour timebox; whatever does not fit is future work.
  Rejected: no image. Why: learning goal and same Python on PC, Docker and CI.
- **D-016 · 2026-09-17** Source file hashes are verified at run time inside `scripts/`; the pure digest functions live in `src/` and are unit-tested with synthetic bytes.
  Rejected: a pytest test over the real files. Why: CI has no data.
- **D-017 · 2026-09-17** OMOP mapping lives in docs/omop_mapping.md and source variables in docs/data_dictionary.md, cross-linked.
  Rejected: mapping inside the dictionary, as the roadmap said. Why: different audiences and different rates of change.
- **D-018 · 2026-09-17** Everything versioned is in English. Renamed: `resultados/`→`results/`, `sql/cohortes/`→`sql/cohorts/`, `docs/decisiones.md`→`docs/decisions.md`.
  Rejected: Spanish docs with English code. Why: portfolio value; the reader of the final repository works in English.
- **D-019 · 2026-09-17** "Peer verification" is green CI plus a clean-clone reproduction plus the author's own diff review; the course teacher reviews at session 24.
  Rejected: weekly peer sign-off as in the lab seminar. Why: individual project.
- **D-020 · 2026-09-17** A clean-clone reproduction runs at every milestone tag.
  Rejected: only before v1.0. Why: undocumented manual steps are cheap to fix early and expensive at the end.
- **D-021 · 2026-09-17** Eligibility and quality thresholds must cite a published source (DGIS descriptors, catalogues, birth-certificate filling manual) or be tagged FOR APPROVAL.
  Rejected: the unsourced ranges in the working plan. Why: rule 2 in CLAUDE.md; the DGIS quality methodology publishes no numeric ranges.
- **D-022 · 2026-09-17** One idempotent SQL runner in `scripts/` applies DDL, ETL and cohort SQL; CI starts the database with `docker compose up -d --wait`.
  Rejected: `initdb/` scripts; an Actions service container. Why: `initdb/` only runs on an empty volume and cannot cover ETL; a service container starts before checkout and would not test this compose file.
- **D-023 · 2026-09-17** `concept_id` values live in `config/concept_sets.yml` and `config/source_to_concept_map.csv`, never in SQL; tests use synthetic ids above 2,000,000,000 (the OMOP range for local concepts); local source vocabularies are registered in VOCABULARY with `vocabulary_concept_id = 0`.
  Rejected: hard-coded ids. Why: CI must not depend on the Athena bundle.
- **D-024 · 2026-09-17** Code license: Apache-2.0.
  Rejected: MIT. Why: matches the license declared by the OHDSI CommonDataModel package whose DDL is vendored here, and adds an explicit patent grant.
- **D-025 · 2026-09-17** A DOI is minted only for v1.0, through the Zenodo–GitHub integration.
  Rejected: a DOI per milestone. Why: intermediate tags are progress snapshots and archives are permanent.
- **D-026 · 2026-09-17** CLAUDE.md is versioned (English, development rules only); personal notes and the pointer to the local planning guide live in an ignored CLAUDE.local.md.
  Rejected: keeping CLAUDE.md out of git. Why: it is direct evidence for the AI-assistance requirement and reproduces the workflow in a clean clone, while the repository keeps no references to non-versioned files.
- **D-027 · 2026-09-17** Python stays pinned to 3.12 (`requires-python >=3.12,<3.13` plus `.python-version`).
  Rejected: an open upper bound. Why: this is an application, not a library, and the same Python must run on the laptop, in Docker and in CI.
- **D-028 · 2026-09-17** pre-commit hooks run through `uv run`, so hooks, CI and terminal share the versions in uv.lock.
  Rejected: remote hook repositories. Why: a single source of tool versions.
- **D-029 · 2026-09-17** pandas 3.x is kept.
  Rejected: pinning pandas 2.x. Why: new code base and the doctoral repository is R, so there is nothing to stay compatible with; copy-on-write and the default string dtype are reviewed in each diff.
- **D-030 · 2026-09-17** CI also runs `ruff format --check`, `mypy` (covering `scripts/`) and the `db`-marked tests, with an 80 % coverage floor; pandas typing uses pandas-stubs plus local documented ignores.
  Rejected: leaving format and types to pre-commit. Why: hooks can be skipped and do not exist in a fresh clone; the branch ruleset only enforces the CI check.
- **D-031 · 2026-09-17** GitHub Actions are pinned by commit SHA and updated by Dependabot (monthly, `github-actions` only); the Postgres image is pinned to the minor version in use.
  Rejected: floating tags. Why: tags are mutable.
- **D-032 · 2026-09-17** The vendored OHDSI DDL is applied in full into schema `cdm` (clinical and vocabulary tables), with `staging` and `results` as separate schemas; primary keys and indices are applied, foreign keys are not.
  Rejected: a separate vocabulary schema; enforcing foreign keys. Why: the specification expects all tables to exist; FK enforcement slows bulk loads and anti-join checks give the same guarantee explicitly.
- **D-033 · 2026-09-17** `staging` keeps every source column as text; casting happens in the ETL with an explicit count of discarded rows per rule.
  Rejected: typing at load time. Why: leading zeros in geographic keys and "not specified" codes are destroyed by early casting.
- **D-034 · 2026-09-17** The single entry point is `scripts/pipeline.py` with argparse subcommands; `.env` is read with `uv run --env-file`; downloads use httpx.
  Rejected: typer, python-dotenv, Makefile, `[project.scripts]`. Why: no extra tooling, works the same in PowerShell and CI, and keeps I/O out of `src/`.
- **D-035 · 2026-09-17** The DGIS credit line is kept verbatim in Spanish in the README, even though the README is in English.
  Rejected: translating it. Why: the terms of free use prescribe the wording.
- **D-036 · 2026-09-17** An English translation of proposal v2 is versioned as docs/proposal_v2.md.
  Rejected: not versioning it. Why: scope changes are stated against it and the reader must be able to check them.
- **D-037 · 2026-09-17** Work tracking lives in GitHub: issues are minimum objectives, milestones are milestones, weekly labels record the Monday commitment, and the four seminar states map to closed-by-PR plus three labels.
  Rejected: a GitHub Project with custom fields. Why: least overhead for one person.
- **D-038 · 2026-09-17** `.gitignore` anchors `/data/` to the repository root.
  Rejected: the unanchored `data/` pattern. Why: it would silently ignore test fixtures under `tests/**/data`.
- **D-039 · 2026-09-17** `.env.example` keeps a placeholder password for the localhost-only development database; CI generates a random password per run.
  Rejected: an empty value. Why: a clean clone must start with one command, and no secret is stored in the repository.
- **D-040 · 2026-09-17 · FOR APPROVAL** Counts below 5 are suppressed in published tables under `results/`, with a footnote citing OHDSI practice (`minCellCount = 5` in CohortDiagnostics).
  Rejected: no suppression. Why: the source microdata are public and carry no personal data, so this is precaution rather than de-identification.
- **D-041 · 2026-09-17 · PENDING** Study period: decided in task 1.2.3 (issue #8), after the source inventory.
  Rejected: deciding before measuring the harmonisation cost. Why: the cost of including 2019 is unknown until the descriptors and catalogues are compared.
- **D-042 · 2026-09-19** The two conditional extras of proposal v2 (ML + SHAP demonstration, interactive dashboard) are not started this semester; they move to the future-work section of docs/roadmap.md.
  Rejected: keeping them as conditional work inside the semester. Why: 6 h/week budget; proposal v2 already framed them as conditional, so this is not a scope change.
- **D-043 · 2026-09-19** The data model is OMOP CDM **v5.4** (open decision A1); the DDL is vendored unmodified from OHDSI/CommonDataModel, pinned to commit 40ff52f (`sql/ddl/ohdsi/SOURCE.md`).
  Rejected: v5.5, released 2026-08-25. Why: the OHDSI analytic tools this project leans on (ATLAS, Achilles, DQD, CohortDiagnostics) still target 5.4, and proposal v2 and the roadmap are written against it, so migrating mid-project would be a scope change with no benefit for the question asked.
- **D-044 · 2026-09-20** `sha256`, `size_bytes` and `retrieved_at` start empty in `config/sources.yml` and are written once by `pipeline.py download --record`, which refuses to overwrite a recorded value; a file already on disk is verified, never downloaded again or overwritten.
  Rejected: hashes written by hand; a `--record` that always rewrites. Why: a hash that any run can rewrite is not a tripwire for a republished file, which is the only thing that protects a download served over plain HTTP.
- **D-045 · 2026-09-20** `--record` patches only the three value lines of the entry, with a pure function in `src/sinac_truncation/manifest.py`, instead of re-emitting the file with a YAML dumper.
  Rejected: `ruamel.yaml` round-trip; `yaml.safe_dump` plus a fixed header. Why: the manifest is hand-written with comments and per-entry `notes` and is read as a diff; a text patch keeps that diff at three lines and adds no dependency.
- **D-046 · 2026-09-20** The `terms` field points at the DGIS Datos Abiertos page, which publishes the Términos de Libre Uso in full, because the "Términos y Condiciones" link of the Nacimientos page (`http://www.dgis.salud.gob.mx/terminos`) returns 404 (checked 2026-09-20).
  Rejected: recording the 404 URL; leaving `terms` empty. Why: the field has to lead a reader to the terms actually in force, and an empty field would look like an oversight.
- **D-047 · 2026-09-20** The source inventory is measured with a throwaway script and only `docs/source_inventory.md` is versioned.
  Rejected: a `pipeline.py inventory` subcommand with pure helpers and tests. Why: the time budget of the task, and every cell of the document names the file it was measured from, so any of them can be re-measured.
- **D-048 · 2026-09-20** The source inventory covers 2019-2023 only; the 2024 and 2025 files are neither downloaded nor measured.
  Rejected: extending it to 2024-2025. Why: it prices the period proposal v2 committed to, while the 2020-2025 option would add two more catalogue comparisons and 2025 is PENDING as a definitive or a preliminary closure.
