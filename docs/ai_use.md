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
  reviews the diff and merges. The assistant also drafts the entries of `docs/decisions.md`, which
  the author approves, or leaves `FOR APPROVAL`, before the merge. In #63 the author asked the
  assistant to merge.
- **Judgment tasks.** For the study period, the protocol and the OMOP mapping (#23, #24, #25) the
  author drafted the answers, the assistant reviewed them against the measured sources and priced
  each option on the record files, and the author took every decision. From `v0.2-progress`,
  where a task left questions open, the assistant laid them out with options and a
  recommendation, measured on the 2020–2023 records where the records bore on them and priced in
  hours of the weekly budget where scope was at stake; the author chose (#49, #51 to #55, #57,
  #60, #62). In #56 and #63 it first checked that the protocol and the decisions already settled
  every choice. For the reference tables of #55 and #57 the author computed some rows blind and
  approved the others from the assistant's step-by-step trace.
- **Data.** The assistant read the public DGIS record files and the Athena vocabulary package on
  the author's machine and reported aggregate counts, measured with the pipeline or with throwaway
  scripts kept outside the repository (D-047). No record is in the repository (rule 1 of
  `CLAUDE.md`). It also read the NOM-007-SSA2-2016 text published in the DOF, Kotelchuck's SAS
  program and the OHDSI conventions, and the author supplied the Kotelchuck (1994) article and the
  2025 DGIS filling guide (#51, #53). For the re-plan of #49 it measured the active time of the
  Claude Code sessions of this repository, as a proxy for the hours worked.
- **Parallel work.** From `v0.2-progress` some issues were worked on in parallel, each on its own
  branch: #54 and #55 were merged four minutes apart, and #55 merged `main` to number its
  decision after those of #54 (D-110). From #63 each ran in a git worktree of its own.
- **Subagents and workflows.** Up to #63 the assistant worked as a single agent: the session
  transcripts of the project show no subagent in any earlier pull request. The close of
  `v0.2-progress` (#64) is the first pull request in which it ran workflows, scripts that spread a
  task over several subagents running in parallel; its section below says for what.
- **The author's line.** "What I decided or checked myself" is the author's statement. In #62 and
  #63 the author asked the assistant to write it from what the author had done and decided in the
  session.
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

### Milestone `v0.2-progress`

The three lines under each pull request are copied from its "AI assistance" section, in the
author's voice. #49 closed the last issue of `v0.1-cohort` (1.12.1), but it was merged after that
tag, so it is recorded here.

#### [#49](https://github.com/martinruhle/sinac-prenatal-truncation/pull/49) · Re-plan at milestone 18 (1.12.1)

- Tool / model: Claude Code (Claude Opus 5.5)
- What the assistant did:
  - Measured the hour proxy from the session transcripts with a throwaway script, and read the issues, PRs, milestones and decisions.
  - Found the mismatch between the mapping docs and the plan on the newborn.
  - Proposed the week-by-week plan and the checkpoint, wrote D-084 and D-085, and created the issues and labels.
- What I decided or checked myself:
  - Accepted the proxy and kept the 6 h a week budget.
  - Chose to start v0.2 in week 41 with the week gained as buffer, and to load the newborn in v0.2.
  - Chose to run 1.2.5 this weekend, and confirmed 2.0 h for 1.4.5 and the checkpoint of 16 October.

#### [#50](https://github.com/martinruhle/sinac-prenatal-truncation/pull/50) · Load the study period 2020-2023 (1.2.5)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: ran `all --years 2020-2023` in the working database with a timestamped log and a disk sampler on the Postgres data directory; timed a separate download of the four files; wrote and ran the independent check against the inventory and the protocol; ran the gates; wrote the README paragraph and this PR.
- What I decided or checked myself: kept the Postgres defaults of `compose.yml`, since the measured run needed no change; kept `all --years 2023` as the command of §Reproduce until the milestone publishes the full period, so that it still matches `results/`; read the README paragraph in the diff.

#### [#51](https://github.com/martinruhle/sinac-prenatal-truncation/pull/51) · Protocol v1: exposures, analysis, null simulation and sensitivity plan (1.3.2)

- Tool / model: Claude Code (Claude Opus 5.5)
- What the assistant did:
  - Measured each option on the 2020–2023 records with throwaway queries: the visit and trimester distributions, landmark sizes, missing covariates, APNCU under three month rules and on the NOM-007 calendar, and insurance by year.
  - Found Kotelchuck's SAS program v3. Verified the NOM-007 calendar against the raw DOF HTML, and the WHO and NICHD bounds.
  - Checked the 2025 DGIS filling guide, which does not define trimester weeks.
  - Proposed every option with its cost, and wrote the protocol, the decisions, the roadmap, the config and its test.
- What I decided or checked myself:
  - Accepted the common set of records and its rules, the measures and their references, and the three landmark weeks.
  - Chose APNCU with the ACOG schedule and the middle-month rule, the NOM-007 variant for v1.0, and the aggregated model.
  - Chose the covariate set and complete case, the two simulation scenarios, and the output tables.
  - Supplied the Kotelchuck 1994 article and the 2025 filling guide.

#### [#52](https://github.com/martinruhle/sinac-prenatal-truncation/pull/52) · OMOP mapping v1 and covariate ETL (1.4.5)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did:
  - laid out the questions of 1.4.5 with options priced on the 2020–2023 records (age groups that change under each age source, missing education codes);
  - searched the Athena bundle for the concepts;
  - wrote the SQL, configuration, tests and docs;
  - ran the full load.
- What I decided or checked myself: deferring insurance to v1.0, the declared age as a `MEASUREMENT`, and SNOMED levels for education.

#### [#53](https://github.com/martinruhle/sinac-prenatal-truncation/pull/53) · Newborn PERSON, FACT_RELATIONSHIP and birth weight (1.4.6)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did:
  - laid out the four questions of 1.4.6, and a fifth it found (newborns entering the cohort), with options measured on the 2020–2023 records (`SEXO` 0/9, `PESO` 9999 by gestational age, weight extremes);
  - checked every candidate concept in the loaded Athena bundle and the OHDSI conventions;
  - wrote the SQL, configuration, tests and docs;
  - ran the full load and the cohorts.
- What I decided or checked myself: approved the recommendations of the review (Mother/Child in both directions, concept 0 for unknown sex, 9999 as a NULL row, no range, a one-day period for the newborn, mothers found through the link). I also approved the switch from concept 56 to 1147314, which came up during the work.

#### [#54](https://github.com/martinruhle/sinac-prenatal-truncation/pull/54) · Measures (a) and (c) in SQL, with tests (1.6.1)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: laid out the open questions of 1.6.1 with options and a recommendation; wrote the SQL, the runner check, the tests and the docs; ran the cohorts on 2020–2023 and recounted step 8 from the raw values.
- What I decided or checked myself: chose the four recommended options (build definition 2 here; a table per mother; the trimester through `source_to_concept_map`; literal thresholds with their source).

#### [#55](https://github.com/martinruhle/sinac-prenatal-truncation/pull/55) · compute_apncu() as a pure function, with reference tests (1.6.2)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: proposed the reference table and the design, wrote the function, the tests and the docs, and cross-checked the function against a transcription of the SAS program and on the real records.
- What I decided or checked myself: accepted the eleven records and the design (one record per call, invalid records refused, every step returned); worked out rows 3 and 5 by hand from the program and approved the other nine from their trace.

#### [#56](https://github.com/martinruhle/sinac-prenatal-truncation/pull/56) · Landmark cohorts (measure d) with their attrition (1.6.3)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: checked that protocol v1 and D-087, D-090 and D-107 settle every choice of 1.6.3; wrote the three SQL files, the tests and the docs; ran the cohorts on 2020–2023 and recounted step 10 from the CDM.
- What I decided or checked myself: accepted D-111 (one file per landmark, kept equal by a test) over a single file built from a list of weeks. Read `03_landmark_28.sql`, checked that `04` and `05` differ only in the definition and the week, and compared the step-10 counts with the orientation figures of protocol §Records analysed.

#### [#57](https://github.com/martinruhle/sinac-prenatal-truncation/pull/57) · Null simulation v1 (1.7.1)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did:
  - prototyped the simulation on the real definition-2 counts and found that the reference levels hold one outcome only;
  - priced three ways out, A, B and C (C prototyped with three rates of extra visits), and explained them;
  - wrote the modules, script, SQL, tests and docs;
  - ran `compute()` on the 2020–2023 counts and checked the tests by mutation.
- What I decided or checked myself: chose option B, the share on the risk-difference scale (D-112), over keeping the log odds-ratio share and over adding visits off the calendar. Computed two rows of `E1_VISITS` blind: one matched, the other missed the visit of the delivery week. I then approved the inclusive reading of D-096 and the other 18 rows from their trace. Asked for the exact cross-check. Read and accepted D-113, including computing the observed crude odds ratios here before 1.6.4, D-114 and D-115. Ran `pipeline.py simulate` on 2020–2023 and checked p, the built-in check, the cross-check and one share by hand (5–7 against 8+ in E2: 10.38 ÷ 1.93 = 5.4).

#### [#60](https://github.com/martinruhle/sinac-prenatal-truncation/pull/60) · Crude and adjusted odds ratios on an aggregated table (1.6.4)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: measured the options on the real records, proposed the two choices the author approved (statsmodels; CSV files in a separate issue), wrote the SQL, module, script, tests and docs, ran them on 2020–2023, and opened #59.
- What I decided or checked myself: Chose statsmodels and moving the CSV files to #59 (option A) in review; read and approved D-117 to D-119, including the reading of rule 3 for measure (b). Computed by hand the crude OR of 0 visits against 8 or more from the counts (1.943) and ran the new tests locally.

#### [#62](https://github.com/martinruhle/sinac-prenatal-truncation/pull/62) · Publish the five output tables of D-098 (no planning ID, split from 1.6.4)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: priced mapping `LUGARNACIMIENTO` against dropping the column on the 2020–2023 records and the weekly budget, found the candidate OMOP concepts in the Athena bundle, then wrote the SQL, modules, script, tests and docs once option (b) was approved.
- What I decided or checked myself:[^author] Chose dropping the place-of-birth column (option (b)) after the assistant priced both options on the 2020–2023 records and explained them in plain language, and left an urban/rural covariate out of scope. Reviewed this PR and approved D-121 to D-123, including D-123 without the `[SCOPE CHANGE]` tag.

#### [#63](https://github.com/martinruhle/sinac-prenatal-truncation/pull/63) · Sensitivity v1: preterm cut-off and multiples, measures (a) and (c) (1.8.1)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did: checked the guide, the protocol and the decisions for anything left for the author to decide, worked in a separate worktree, wrote the SQL of definition 6, the changes to the models and the script, the tests and the docs, ran the pipeline on 2020–2023 for the counts and the orientation estimates, checked by mutation that the new tests fail, and logged D-124.
- What I decided or checked myself: Asked before the work started whether the task needed a decision of mine. Approved D-124 as written: the two axes, definition 6 with its steps moved up by one, and no cut-off on definition 6. Asked the assistant to fill this section and to merge once everything was ready.

#### [#64](https://github.com/martinruhle/sinac-prenatal-truncation/pull/64) · Close milestone v0.2-progress (1.9.2)

- Tool / model: Claude Code, Claude Opus 5.5
- What the assistant did:
  - audited the milestone with a workflow of four read-only subagents: the `FOR APPROVAL`
    markers behind the published numbers, with a fourth subagent trying to refute that list; the
    promises the documentation made for v0.2; and the AI assistance section of each pull request;
  - removed the markers the author approved, ran `cdm` and `publish` on 2020–2023, and committed
    `results/`;
  - assembled this section from the pull requests and the session transcripts, and updated the
    README, the protocol and the decision log;
  - compared every number of the documentation with the published tables in a second workflow,
    with a skeptic re-deriving each disagreement, and reviewed the diff in a third;
  - ran the clean-clone reproduction, found and fixed two bugs test-first (D-125 and a test that
    depended on the time zone), republished, ran the clean clone again, ran the history scan, and
    drafted the release notes.
- What I decided or checked myself: PENDING: copied from the pull request once the author fills
  it in, before the merge.

[^model]: The merge commits of #22 and #23 carry a `Co-Authored-By: Claude Sonnet 5` trailer,
    which names the model active when the commit was written. According to the author, most of
    the work of both pull requests was done with Claude Opus 5, as their sections state.
[^author]: The author asked the assistant to write this line from what the author had done and
    decided in the session, as in #63. The author confirmed it when this milestone closed.
