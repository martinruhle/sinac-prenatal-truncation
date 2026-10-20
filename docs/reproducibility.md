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
