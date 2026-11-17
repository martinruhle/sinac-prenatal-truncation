# Security review

The security review of milestone `v1.0` (issue #73, D-141). It ran read-only on 16 November 2026,
on `main` at `9dfd584`. The four hardening fixes it led to land with the close of the milestone.

## Scope and method

- **Tool.** The `/security-review` command of Claude Code. The command reviews the diff of a
  pull request. Here its scope was the whole code, because this is the project's first security
  review:
  - the 79 tracked files of `src/`, `scripts/`, `sql/` and `config/`;
  - the Docker and Compose files and the CI workflow;
  - `pyproject.toml` and `uv.lock`;
  - the git history of every ref.

  Tests and documentation fall under the command's exclusions. The history check still read
  every blob of both.
- **Rules.** The command's own rules apply. A finding is a vulnerability with a concrete path from
  an untrusted input, and it is reported only at a confidence of 8 out of 10 or more. The
  exclusions drop the following: denial of service and resource exhaustion, missing hardening,
  outdated libraries, test files and documentation.
- **Trust model.**
  - Trusted: environment variables, command-line flags, `config/` and the repository, all set by
    the author.
  - Untrusted: the content and member names of the DGIS record ZIPs and of the Athena vocabulary
    ZIP, HTTP responses and redirects, and, in CI, the content of pull requests from forks.
- **Organisation.** Six reviewers, one per area:
  1. ingestion: download, staging and the vocabulary;
  2. the ETL and its SQL;
  3. the cohort and analysis SQL;
  4. analysis and publication;
  5. infrastructure and supply chain;
  6. the git history.

  Three independent false-positive filters were to judge each candidate finding: who controls
  the input, a second reading of the code, and the exclusion rules. A candidate was to stand only
  if two of the three rated it 8 or more. The review changed no file, downloaded nothing and did
  not touch the database.

## Result

**No vulnerability was found.** No area proposed a candidate, so the filters had nothing to judge.
The reviewers recorded 95 risks they checked and found handled. They also wrote 30 hardening
notes, which the command's exclusions drop. The notes overlap across areas and are grouped under
§Hardening notes.

What was checked and found handled, by area:

- **Ingestion.**
  - A server never chooses the name or the location of a file.
  - A download is written to a `.part` file and renamed only after its sha256 matches the pin in
    `config/sources.yml`, and a recorded pin is never overwritten.
  - Both archives are hashed before they are opened.
  - The Athena package is read by fixed member names; nothing is extracted from it.
  - The record CSV is written under the last part of its member name (`extracted_name()`).
  - CSV headers must be bare identifiers before they become columns.
  - Values reach Postgres only through `COPY`.
- **SQL.**
  - No value from a record or from the configuration becomes SQL text. Values are bound
    parameters or `COPY` rows, and identifiers go through `psycopg.sql.Identifier`.
  - Schema markers are substituted from code constants, and only after a bare-identifier check.
  - `--years` takes four-digit years only.
  - No SQL file holds dynamic SQL.
  - Temporary tables are read through `pg_temp`.
- **Code.**
  - YAML is loaded only with `yaml.safe_load`.
  - There is no `eval`, `exec`, `pickle` or shell.
  - git is called with argument lists.
- **Credentials.**
  - The database password reaches the connection only. It never reaches a log, `results/`, the
    manifest or `CDM_SOURCE`.
  - Any user name and token are removed from the remote URL before it is written.
  - Secret scanning and push protection are on for the repository.
- **CI.**
  - The workflow runs on `pull_request`, not `pull_request_target`.
  - It has `contents: read` and uses no repository secret.
  - Its database password is generated on each run and masked.
  - No event data reaches a `run` step.
- **Image.**
  - The image runs as a user that cannot change its code.
  - Its build fetches only these:
    - the two base images, by tag;
    - Debian packages from the signed archive;
    - the Python packages of the hash-pinned `uv.lock`.
  - Its build context is an allowlist.

## History of the repository

CLAUDE.md rule 1 keeps records and credentials out of git. This check was made on 16 November 2026
and covered 148 commits:
- the commits of every local ref and of the reflog;
- the unreachable commits;
- every ref that GitHub advertises, pull requests included.

| Check | Result |
|---|---|
| A path under `data/`, or a `.env`, ever committed | None among the 141 paths ever committed |
| An archive or columnar file ever committed (`.zip`, `.7z`, `.gz`, `.rar`, `.parquet`, `.feather`, `.dta`, `.sav`, `.xlsx` and others) | None. No blob holds a NUL byte, so no binary file was ever stored |
| A CSV with record-level data | None. The 10 CSV paths ever committed are the aggregate tables of `results/`, `config/source_to_concept_map.csv` and the bibliographic records of the literature search |
| Credentials in any blob of any commit | None. No private key or token pattern matched, and the 14 password assignments are placeholders, environment lookups or comments |
| Absolute paths of a machine (rule 12) | None |
| Largest blobs | All text. The largest is `docs/literature_search/records.csv` at 756 KB, and the whole pack is 1.13 MiB |

The commits added after 16 November were checked again before the tag (§Recheck at the tag).

## Hardening notes

Each note states a fact that the command's rules exclude from findings. On 17 November 2026 the
author chose to fix the first four in this milestone (D-141).

### Fixed at `v1.0`

| # | Note | Fix |
|---|---|---|
| 1 | The allowlist of `.dockerignore` re-included `src/`, `scripts/`, `sql/`, `config/` and `tests/` whole. A `.env` or a `data/` folder inside them would therefore have reached the build context, which contradicts the file's own header | They are re-excluded at any depth. A throwaway build with four decoys put all four in the context before the fix and none after it |
| 2 | `.gitignore` ignored the exact name `.env` only. It did not ignore an archive or columnar file outside the root `data/`, nor the local worktrees of a coding assistant | It now ignores `.env.*` except `.env.example`, nine archive and columnar extensions and `.claude/worktrees/`. `tests/test_ignore_rules.py` checks them with `git check-ignore` |
| 3 | The only guard against ZIP slip was to keep the base name of the member, and it had no test. On Windows, a network-share name such as `//server/share.csv` has an empty base name, so the member was written beside the extraction folder before the run failed | `extracted_name()` keeps the last part of the name, by the rules of Windows, on every system, and refuses a name without one. Tests cover folders, `..`, roots, drive letters and network shares |
| 4 | The clean-tree checks of `publish` and of the ETL followed the local `status.showUntrackedFiles` setting, so the guarantee of D-080 depended on the machine | Both pass `--untracked-files=all`, with tests |

### Accepted

| Note | Why it is accepted |
|---|---|
| DGIS serves its files over plain HTTP, so each sha256 pin was recorded from an unauthenticated first download on 20 September 2026 | Trust on first use (D-016). Every later download and every file on disk is checked against the pin. No code can check the first download again |
| Three runs are unbounded: a download is not capped by its recorded size and has no overall deadline, a ZIP member is decompressed without a ceiling, and a digit string beyond the integer range stops `cohorts` | This is denial of service, which the command excludes. Each case fails closed: a wrong file fails its sha256, and a failed run keeps the previous one |
| An extracted CSV is reused when its size and CRC-32 match the archive's, which is not a cryptographic hash | Exploiting it needs write access to `data/`, which the trust model treats as the author's |
| The local database runs everything as its superuser, with no `sslmode`. By default it uses the placeholder password of `.env.example` | It is a single-user database published on 127.0.0.1 only (D-039) |
| Raw source values reach the terminal without control characters escaped | Low impact: a message on the author's terminal |
| Schema names are quoted on one code path and unquoted on the other | A latent inconsistency only: the names are lower-case constants |
| A remote that is a local folder would put a machine path into the manifest | The clean clone takes its remote from GitHub |
| The sha256 of the vendored OHDSI DDL is recorded in `sql/ddl/ohdsi/SOURCE.md` but no test checks it | It is trusted repository content, and the hashes matched on 16 November 2026 |
| No hook blocks a commit that carries a credential or a data file | `.gitignore`, the secret scanning and push protection of GitHub, and the history check at each tag cover it |

### Future work

| Note | Recorded in |
|---|---|
| The GitHub Actions are pinned by tag, not by commit SHA, and no Dependabot update keeps them current | D-140 |
| The base images are pinned by tag, not by digest | docs/roadmap.md §4.4 |
| The optional Adminer service of `compose.yml` has no tag, and CI does not pin the version of uv | Here |
| `sqlalchemy` is a dependency that nothing imports | Here |
| Dependabot alerts are off, so the locked versions were not checked against advisories | Here; it is a repository setting |

## Limits of the review

- No advisory database was queried. The review downloaded nothing, and Dependabot alerts are off.
- The image was not scanned for vulnerable operating-system packages.
- Hostile inputs were reviewed by reading the code. The only exception is the handling of member
  names, which was also run on hostile names offline and is now covered by tests.

## Recheck at the tag

PENDING: written at the close, after the last commit before the tag.
