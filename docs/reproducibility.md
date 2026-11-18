# Reproducibility

Every milestone is rebuilt from a clean clone before it is tagged (D-020). The repository is
cloned from GitHub and rebuilt by following README §Reproduce only. A step the README does not
state is fixed in the README before the tag, and each run is logged below.

## Procedure

The procedure is D-083.

1. Clone the branch that closes the milestone from GitHub, into a folder whose name differs from
   the working copy's. Docker Compose names its project after the folder, so a clone in a folder
   of the same name would share the container and the volume of the working database.

   ```bash
   git clone --branch <branch> https://github.com/martinruhle/sinac-prenatal-truncation sinac-clean
   ```

2. Create `.env` from `.env.example`. If the working database already holds port 5432, give the
   clone another `POSTGRES_PORT`, as `.env.example` says.
3. Run README §Reproduce as written, on the years of the milestone:
   - Before `all`, copy the Athena package that `config/sources.yml` declares to the path it
     declares. It is the one file downloaded by hand.
   - The record files are downloaded again from DGIS and checked against their sha256.
4. Check that `pytest` reports no skipped test, so that the database tests ran.
5. Run `pipeline.py publish` on the same years. The run passes when every CSV of `results/`
   keeps the sha256 the committed manifest gives it. `git diff --stat` then lists
   `results/manifest.json` only, which now names the clone's commit and time.
6. Run `docker compose down -v` from the clone's folder, to remove the clone's database, then
   delete the folder.

## Log

| Milestone | Date | Commit cloned | System | Wall time | Result | Steps the README lacked |
|---|---|---|---|---|---|---|
| `v0.1-cohort` | 2026-09-30 | `baa586e` | Windows 11 Pro, Docker Engine 28.4.0, uv 0.12.15 | 9 min 2 s | Passed | None |
| `v0.2-progress`, first run | 2026-10-19 | `7d676ab` | Windows 11 Pro, Docker Engine 28.4.0, uv 0.12.15 | 1 h 19 min | Failed: one test, and `estimates.csv` in its last digits | None |
| `v0.2-progress` | 2026-10-19 | `4f357e5` | Windows 11 Pro, Docker Engine 28.4.0, uv 0.12.15 | 1 h 32 min | Passed | None |
| `v1.0` | 2026-11-17 | `ead987b` | Windows 11 Pro, Docker Engine 28.4.0, uv 0.12.15 | 4 h 34 min, 2 h 50 min of it awake | Passed | None |

### `v0.1-cohort`

- **Years.** The run covered 2023. `all --years 2023` took 7 min 52 s:
  - the record file was downloaded again from DGIS and matched its sha256;
  - `validate-concepts` passed all 15 concept ids;
  - every ETL check and attrition check held.
- **Tests.** `pytest`: 340 passed, none skipped.
- **Publish.** `publish --years 2023` wrote `results/attrition_base.csv` with sha256
  `74c1782ac6846da71174f14ba92c582b3bb692ceda16dbd8a4b4d5e010c203b8`, the one in the committed
  manifest. `git diff` changed two lines of `results/manifest.json`: the time, and the commit
  (`46587aa` became `baa586e`).
- **Setup.** The clone's `POSTGRES_PORT` was 5433, because the working database holds 5432. The
  Athena package of record was copied in. `uv sync` took 2 s because it reused the uv cache of the
  machine; a first install downloads every package.

### `v0.2-progress`

Both runs covered 2020–2023 and followed README §Reproduce with `all --years 2020-2023`, set up as
at `v0.1-cohort`. In each, the four record files were downloaded again from DGIS and matched their
sha256, `validate-concepts` passed all 29 concept ids, and every ETL check and attrition check
held.

- **First run, at `7d676ab`: failed.** It found two problems, both fixed on the branch before the
  second run:
  - **`pytest`: 623 passed, 1 failed.** `test_each_trap_lands_as_the_mapping_says` compared the
    database's `current_date`, which is UTC, with the date of the machine, and at 22:20 at UTC−3
    the two differ. The test now reads the database's date (`52aef5f`).
  - **`publish` reproduced four of the five CSVs.** `estimates.csv` differed in the last digits of
    its adjusted odds ratios (2.4576293672342393 against 2.457629367234245), every count and crude
    odds ratio equal. The model table followed the order in which the database returned the
    aggregated table, and it is sorted now (D-125, `847b5f0`). The results were published again
    at `847b5f0`: four files kept their sha256, and in `estimates.csv` 166 values moved by at
    most 1.3 × 10⁻¹⁴ in relative terms, none at three decimals.
  - `all` took 50 min 6 s, `pytest` 1 min 52 s and `publish` 25 min 33 s.
- **Second run, at `4f357e5`: passed.**
  - **`all`** took 62 min 24 s: `download` 1 min 38 s, `stage` 5 min 25 s, `vocab` 3 min 49 s,
    `validate-concepts` 3 s, `cdm` 31 min 19 s, `cohorts` 13 min 52 s, `simulate` 1 min 5 s and
    `estimate` 5 min 10 s.
  - **`pytest`**: 626 passed, none skipped.
  - **`publish --years 2020-2023`** took 27 min 12 s and wrote the five files with the sha256 of
    the committed manifest:

    | File | sha256 |
    |---|---|
    | `attrition.csv` | `c9da90f71b1535cf6ba3d485fe2a2011e4f422441e72e54f20821b696531fc25` |
    | `exposure_distribution.csv` | `d83c8dfa3198e54caf6d42734014c75227e04a3d4b03c1901b07861ecefd341d` |
    | `estimates.csv` | `1fc083bb3b2b9262a791a81786ae17d5db8629ee74bce3bd10d6ecdda465a17b` |
    | `truncation_share.csv` | `fdb7a53842714f2df18fc8b006eb56198a33b7149ca07a79d8d1cc9217c9946c` |
    | `excluded_profile.csv` | `7cf8961669c0ee2bfb7cb314a71bd444ee782d59c56f1bee3b5f0d78e8a1b012` |

    `git diff` changed two lines of `results/manifest.json`: the time, and the commit (`847b5f0`
    became `4f357e5`).
  - **In all**, 1 h 31 min 59 s from `git clone` to the end of `publish`.
- **Disk.** `data/` held 2.35 GB. The Postgres data directory peaked at 27.1 GB while `publish`
  rebuilt the cohorts, and held 22.5 GB at the end, in samples taken every 30 s.
- **Where the results come from.** `publish` ran on the working database, loaded many times
  since 2 October, and each clone on a fresh one. Since D-125 the order in which a database
  returns the aggregated table no longer reaches the estimates.

### `v1.0`

The run covered 2020–2023 at `ead987b`, the head of the closing branch on GitHub when it was
cloned on 17 November 2026. The later commits of the branch change only documentation and two
docstrings of `src/sinac_truncation/apncu.py`. The run followed README §Reproduce with
`all --years 2020-2023`, set up as at `v0.1-cohort`. The four record files were downloaded again
from DGIS and matched their sha256, `validate-concepts` passed all 30 concept ids, and every ETL
check and attrition check held.

- **The laptop slept for 1 h 43 min 53 s**, according to the Windows System log (Kernel-Power
  event 507, `SleepDurationInUs`). The pipeline's timers place all of it in `checks.sql`, the last
  file of `cdm`. The timers kept counting through it, so the times below also give the time awake
  wherever the sleep falls.
- **`all`** took 3 h 44 min 42 s, 2 h 0 min 49 s of it awake: `download` 2 min 2 s, `stage`
  5 min 49 s, `vocab` and `validate-concepts` 9 min 49 s together, `cdm` 2 h 42 min 5 s (58 min
  12 s awake), `cohorts` 31 min 5 s, `simulate` 2 min 10 s and `estimate` 11 min 44 s. Unlike the
  runs of `v0.2-progress`, this one did not stamp each line of its output:
  - `download` runs from the start of `all` to the time of the last ZIP it wrote;
  - `stage` runs from there to the end of its last table load, which its own timer gives;
  - the times from `cdm` to `estimate` are the pipeline's own;
  - the rest of the total is the time of `vocab` and `validate-concepts`.
- **`checks.sql`** took 2 h 16 min 27 s, 32 min 34 s of it awake. The same checks took 29 min 21 s
  on the working database earlier that day, at `e9708d7`, whose code is that of `ead987b`.
- **`vocab`** loads the same package with the same code as at `v0.2-progress`. Its three largest
  tables took 9 min 36 s by its own timers, against 3 min 49 s for the whole step then, with no
  sleep in them. The record does not show why, so the times awake are those of this run.
- **`pytest`**: 738 passed, none skipped.
- **`publish --years 2020-2023`** took 46 min 43 s and wrote the five files with the sha256 of
  the committed manifest:

  | File | sha256 |
  |---|---|
  | `attrition.csv` | `c9da90f71b1535cf6ba3d485fe2a2011e4f422441e72e54f20821b696531fc25` |
  | `exposure_distribution.csv` | `52d84a6c845b662315853e84b1746650e0706dfa2020676d8950d3f9fd23fea4` |
  | `estimates.csv` | `f025632df70e03e61d867b9122331bddf9e6e352856cd9e024b44c0e94f9c160` |
  | `truncation_share.csv` | `057a5e760987c0c2dade0ba44bcd777875bb900845e9e6906b2c1c6cca1546a8` |
  | `excluded_profile.csv` | `7cf8961669c0ee2bfb7cb314a71bd444ee782d59c56f1bee3b5f0d78e8a1b012` |

  `git diff` changed two lines of `results/manifest.json`: the time, and the commit (`e9708d7`
  became `ead987b`).
- **In all**, 4 h 33 min 41 s from `git clone` to the end of `publish`, 2 h 49 min 48 s of it
  awake.
- **Disk.** `data/` held 2.35 GB. The Postgres data directory peaked at 28.5 GB while `publish`
  rebuilt the cohorts, and held 24.8 GB at the end, in readings taken every 30 s while the laptop
  was awake.
- **Where the results come from.** The committed results were published on the working database
  at `e9708d7`, and the clone rebuilt them on a fresh database, from the download on.
- **A first attempt** the same day stopped right after `git clone`, before the first step of
  README §Reproduce. The script that drove the run, under Git Bash, cloned into one folder and
  then looked for the clone in another. The error was the script's, not the repository's.
