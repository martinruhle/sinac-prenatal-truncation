# sinac-prenatal-truncation — instructions for AI coding assistants

Development rules for Claude Code sessions in this repository. They describe how code is
written here; they are not results.

## What this is
Final project (Modality A) of the UNAM course "Applied Data Science in Biomedicine" (2027-1).
Question and methods: docs/protocol.md · Scope, milestones and changes: docs/roadmap.md

## Commands
- Install:      `uv sync` · hooks (once per clone): `uv run pre-commit install`
- Environment:  `cp .env.example .env` (never commit `.env`)
- Lint / types: `uv run ruff check .` · `uv run ruff format .` · `uv run mypy`
- Tests:        `uv run --env-file .env pytest` (database tests are marked `db`)
- Database:     `docker compose up -d --wait` (Docker Desktop must be running)
- Pipeline:     `uv run --env-file .env python scripts/pipeline.py --help`

## Rules that are not negotiable
1. No SINAC/DGIS records and no credentials in git or in a Docker build context.
   `/data/` and `.env` are ignored.
2. Do not invent values (thresholds, calendars, codes, concept_ids, variable names).
   Every number needs a source. If a threshold is the author's own criterion, mark it
   `FOR APPROVAL`. If something is missing, ask or write `PENDING`.
3. Gestational age, birth weight and anything derived from them (including APNCU) are
   never used as model predictors.
4. SINAC does not record prenatal visit dates: never write code that assumes them.
5. Cohort definitions live only in `sql/cohorts/`, and every definition produces its
   attrition table.
6. `src/` holds pure functions (no file or database I/O); all I/O lives in `scripts/`.
7. Tests use small synthetic fixtures, never real data. CI never downloads data; it does
   start the compose database for the tests marked `db`.
8. `concept_id` values are never hard-coded in SQL: they come from
   `config/concept_sets.yml` or from `source_to_concept_map`.
9. Everything versioned is in English (code, names, docs, comments, commit messages).
   Source values published by SINAC/DGIS stay as they are.
10. One branch and one PR per issue, Conventional Commits, never push to `main`.
11. Non-obvious decisions go to `docs/decisions.md`: date, rejected alternative, reason,
    three lines at most, tagged `[SCOPE CHANGE]` when they change the proposal.
12. No absolute paths from any machine; paths are relative to the repository root.
