# AI assistance

This project was developed with an AI coding assistant: Claude Code (Anthropic), running Claude
Opus 5 and, from pull request #25, Claude Opus 5.5. This file states how the assistant was used
and, pull request by pull request, what it did and what the author decided or checked. The record
is assembled from the "AI assistance" section that every pull request carries since #18, as the
[pull request template](../.github/pull_request_template.md) asks.

## How the assistant is used

- **Rules.** The development rules given to the assistant are versioned in
  [`CLAUDE.md`](../CLAUDE.md): no data or credentials in git, no invented values, gestational age
  and birth weight never as predictors, cohort definitions only in `sql/cohorts/`, and the rest.
  The author's personal notes and planning guide stay local and are not versioned (D-026).
- **Workflow.** For each issue the assistant reads the planning item, explores the repository and
  proposes a plan, which the author approves before any file is edited. The assistant then writes
  the code, tests, SQL and documentation, runs the checks and opens the pull request; the author
  reviews the diff and merges.
- **Judgment tasks.** For the study period, the protocol and the OMOP mapping (#23, #24, #25) the
  author drafted the answers, the assistant reviewed them against the measured sources and priced
  each option on the record files, and the author took every decision.
- **Data.** The assistant read the public DGIS record files and the Athena vocabulary package on
  the author's machine and reported aggregate counts, measured with the pipeline or with throwaway
  scripts kept outside the repository (D-047). No record is in the repository (rule 1 of
  `CLAUDE.md`).
- **Attribution.** The commit that merged each pull request, except #18, carries a
  `Co-Authored-By: Claude …` trailer naming the model active when the commit was written, and each
  pull request description since #1 ends with a "Generated with Claude Code" line.

## Record by pull request

### Milestone `v0.1-cohort`

The three lines under each pull request are copied from its "AI assistance" section, in the
author's voice.

#### Before the template

- [#1](https://github.com/martinruhle/sinac-prenatal-truncation/pull/1) · Project skeleton. It has
  no "AI assistance" section, because the template arrived with #18, and its description is in
  Spanish, from before D-018. The merge commit carries a Claude Opus 5 trailer.
- The first commit, `007826f` (the Spanish roadmap), was pushed to `main` before #1 and carries a
  Claude Opus 5 trailer.

#### [#18](https://github.com/martinruhle/sinac-prenatal-truncation/pull/18) · Adopt English naming and repository conventions (1.1.2)

- Tool / model: Claude Code (Opus 5)
- What the assistant did: proposed the plan, performed the renames and translations, wrote `CLAUDE.md`, `CLAUDE.local.md`, the PR template and `docs/decisions.md` (the last two copied verbatim from the local planning guide), and ran the verification commands.
- What I decided or checked myself: approved the plan and the scope, confirmed that the PR template belonged in this task, and reviewed the diff.

#### [#19](https://github.com/martinruhle/sinac-prenatal-truncation/pull/19) · Roadmap in English, proposal translation and README skeleton (1.1.3)

- Tool / model: Claude Code (Opus 5), plan mode first, then edits
- What the assistant did: translated and restructured `docs/roadmap.md`, translated proposal v2, drafted the README skeleton, ran the checks and the naming / PENDING / absolute-path greps
- What I decided or checked myself: to record the extras as D-042 rather than leave the change in the roadmap only, and to include the evidence-map skeleton now instead of an empty heading; reviewed the section-by-section summary of the roadmap before the PR was opened

#### [#20](https://github.com/martinruhle/sinac-prenatal-truncation/pull/20) · OMOP CDM v5.4 DDL, SQL runner and database job in CI (1.4.1)

- Tool / model: Claude Code (Opus 5)
- What the assistant did: looked up the upstream commit, file hashes and the v5.5 release notes
  with `gh api`; wrote the renderer, runner, entry point, tests, CI steps and documentation; ran
  the verification locally.
- What I decided or checked myself: confirmed decision A1 (v5.4); chose to create
  `config/sources.yml` now rather than leaving it to 1.2.1; chose the `db-init` behaviour on a
  non-empty schema (refuse by default, `--recreate` opt-in).

#### [#21](https://github.com/martinruhle/sinac-prenatal-truncation/pull/21) · Reproducible DGIS download with a source manifest (1.2.1)

- Tool / model: Claude Code (Opus 5)
- What the assistant did: read the DGIS page to copy the download URL, the page URL and the terms
  URL, and found that the page's "Términos y Condiciones" link is broken; designed and wrote the
  two pure modules, the download script, the subcommand and the tests; ran the lint, type, test
  and end-to-end verification above; checked the ZIP's single member to confirm the file's
  identity when its size did not match the published one.
- What I decided or checked myself: that the manifest lists only `sinac_2023.zip` for now rather
  than all fifteen published files; that `--record` patches the YAML as text instead of adding
  `ruamel.yaml` or re-emitting the file; approved the plan before any code was written.

#### [#22](https://github.com/martinruhle/sinac-prenatal-truncation/pull/22) · Source inventory of DGIS descriptors and catalogues (1.2.2)

- Tool / model: Claude Code (Opus 5), plan mode with author approval before edits[^model]
- What the assistant did: read guide §1.2.2 and §8, downloaded and hashed the nine sources,
  wrote a throwaway script (not versioned, D-047) to measure ZIP structure, encoding, delimiters,
  row/column counts (DuckDB) and to pair and diff the two catalogue periods from published
  metadata only, then wrote `docs/source_inventory.md` and the two decision entries
- What I decided or checked myself: chose the 2019–2023 scope and the throwaway-script approach
  (AskUserQuestion) before any edit; reviewed the diff and spot-checked catalogue-difference cells
  against the named source files before merging

#### [#23](https://github.com/martinruhle/sinac-prenatal-truncation/pull/23) · Decide the study period (1.2.3)

- Tool / model: Claude Code (Opus 5)[^model]
- What the assistant did:
  - Reviewed the author's draft answers to the five questions of planning item 1.2.3 against the
    source inventory.
  - Counted which coded variables change between catalogue periods and by role.
  - Laid out the covariate / sensitivity trade-off for year of birth.
  - Searched earlier session transcripts for the literature search behind a novelty claim, and
    found none.
  - Wrote the documents and the `--years` option with its tests.
- What I decided or checked myself: chose the period (2020–2023, with 2019 conditional), both
  roles for year of birth, and the one-week timebox; dropped the novelty claim.

#### [#24](https://github.com/martinruhle/sinac-prenatal-truncation/pull/24) · Protocol v0: population, outcome, base cohort and attrition (1.3.1)

- Tool / model: Claude Code, Claude Opus 5
- What the assistant did: reviewed my seven draft answers against the descriptor, the catalogues
  and the record files; measured the counts quoted above and the comparisons of excluded against
  retained records; checked the NOM-007-SSA2-2016 definitions on the DOF; wrote the protocol
  sections, the decision entries and the roadmap and README changes.
- What I decided or checked myself: every one of the seven questions. In particular I asked for
  the unit-of-analysis alternatives to be laid out as the tables each one produces before
  confirming the certificate as the unit, and I asked for the measured signal on residence abroad
  to be kept as the justification of the future-work item rather than dropped with the exclusion.

#### [#25](https://github.com/martinruhle/sinac-prenatal-truncation/pull/25) · OMOP mapping v0 for the vertical slice (1.4.2)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did:
  - reviewed my draft answers to the eight questions of 1.4.2 and priced each option on the
    record files: dates, maternal age, duplicates, sentinel codes, the attrition with the new
    step;
  - looked up every candidate concept in Athena and quoted the OMOP conventions;
  - wrote the mapping, the configuration and its checks, the decision entries and the protocol,
    roadmap and README changes.
- What I decided or checked myself:
  - every decision. I asked for plain explanations with an honest severity for `person_id`, for
    the observation period (what is lost if it carries no information) and for why gestational
    age is a Measurement and not an Observation, before accepting each one;
  - that the OMOP limitation on race and ethnicity be documented, and that indigenous mothers
    become future work.

#### [#26](https://github.com/martinruhle/sinac-prenatal-truncation/pull/26) · Stage 2023 records and data dictionary v0 (1.2.4)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did:
  - measured the ZIP, the DuckDB options and the descriptor before planning;
  - proposed the plan, then wrote the code, the tests, the dictionary and the decision entries;
  - ran the two real loads and the throwaway measurement for the dictionary.
- What I decided or checked myself:
  - approved the plan, including the one-table-per-year layout, lower-case names and blank as
    NULL;
  - approved the dictionary scope (22 columns);
  - reviewed the counts and timings of both runs before the push.

#### [#27](https://github.com/martinruhle/sinac-prenatal-truncation/pull/27) · Load vocabularies and validate concept sets (1.4.3)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did:
  - inspected the package read-only (delimiter, quotes, dates, empty NOT NULL fields, over-long values, the headers, the version, and a preview of every configured concept id);
  - measured decompressing against extracting;
  - wrote the loader, the validator, the tests and the docs;
  - ran the real load twice and the validation.
- What I decided or checked myself: approved the plan before any edit; told the assistant to keep the package compressed unless extracting it proved more efficient.

#### [#28](https://github.com/martinruhle/sinac-prenatal-truncation/pull/28) · ETL vertical slice from staging to the CDM (1.4.4)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: measured the value forms of the 2023 staging table, proposed the plan, wrote the SQL, the orchestrator, the pure helpers, the tests and the docs, and ran both loads.
- What I decided or checked myself: the plan; that an invalid delivery date stops the load while other uncastable values keep their row (D-075); concept 0 as a literal (D-074); that OBSERVATION_PERIOD stays the delivery day (D-062).

#### [#29](https://github.com/martinruhle/sinac-prenatal-truncation/pull/29) · Base cohort SQL with attrition and tests (1.5.1)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: read the protocol, the mapping and the ETL, proposed the plan, wrote the tests first and showed them red, then wrote the SQL, the runner, the pure helpers and the docs; ran the mutation checks and both real runs.
- What I decided or checked myself: the plan; merging #28 first; reading Mexico from the map instead of adding it to `concept_sets.yml` (D-076); keeping the new traps in the cohort tests only.

#### [#30](https://github.com/martinruhle/sinac-prenatal-truncation/pull/30) · Run the base cohort on 2023 and publish results (1.5.2)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: priced A3 on the real 2023 attrition and checked the OHDSI rule in the CohortDiagnostics source; designed and wrote `publish` test-first; ran the mutation checks, the real run and the independent cross-checks; wrote the docs.
- What I decided or checked myself: A3, no small-cell suppression, because the data are public.

#### [#31](https://github.com/martinruhle/sinac-prenatal-truncation/pull/31) · Close milestone v0.1 (1.9.1)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: checked the repository against the minimum requirements of the course
  and found that a third party could not rebuild with a newer Athena package without an
  undocumented step, and that a clone in a folder of the same name would share the working
  database; wrote `pipeline.py all` test-first; assembled this file from the pull requests; filled
  the evidence map and the changes from the proposal; ran the clean-clone reproduction.
- What I decided or checked myself: adding `all` now instead of at v1.0; approving D-013 and
  D-057 before the tag; closing #2; that #22 and #23 were done mostly with Opus 5.

#### [#33](https://github.com/martinruhle/sinac-prenatal-truncation/pull/33) · Align the D-055 count between decisions.md and protocol.md (no planning ID)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: traced the three counts through git history, recomputed the attrition chain, checked which years the CDM holds, edited the two lines, opened #32 and this PR.
- What I decided or checked myself: not filled in before the merge. The correction was started
  from a task the assistant suggested while closing the milestone.

#### [#35](https://github.com/martinruhle/sinac-prenatal-truncation/pull/35) · Align the D-056 count between decisions.md and protocol.md (no planning ID)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: traced 10,117 to the v0 table of #24 through git history, checked which years the CDM holds, compared the raw and sequential multiplicity counts on 2023, edited the one number, opened #34 and this PR.
- What I decided or checked myself: not filled in before the merge.

[^model]: The merge commits of #22 and #23 carry a `Co-Authored-By: Claude Sonnet 5` trailer,
    which names the model active when the commit was written. According to the author, most of
    the work of both pull requests was done with Claude Opus 5, as their sections state.
