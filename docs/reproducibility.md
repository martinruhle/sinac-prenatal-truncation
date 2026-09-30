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
5. Run `pipeline.py publish` on the same years. The run passes when `results/attrition_base.csv`
   keeps the sha256 of the committed manifest. `git diff --stat` then lists
   `results/manifest.json` only, which now names the clone's commit and time.
6. Run `docker compose down -v` from the clone's folder, to remove the clone's database, then
   delete the folder.

## Log

| Milestone | Date | Commit cloned | System | Wall time | Result | Steps the README lacked |
|---|---|---|---|---|---|---|
| `v0.1-cohort` | 2026-09-30 | `baa586e` | Windows 11 Pro, Docker Engine 28.4.0, uv 0.12.15 | 9 min 2 s | Passed | None |

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
