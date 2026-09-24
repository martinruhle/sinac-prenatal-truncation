# Vendored OMOP CDM v5.4 DDL (PostgreSQL)

These three files are copied **unmodified** from the OHDSI reference implementation. They are
never edited here: a change to the data model is a change of the pinned commit, recorded in
`docs/decisions.md`.

| Field | Value |
|---|---|
| Repository | <https://github.com/OHDSI/CommonDataModel> |
| Path | `inst/ddl/5.4/postgresql` |
| Commit | `40ff52f7cb1e634dd45c3d7157307a47b1b78652` (2026-07-31, "More error fixes") |
| Retrieved | 2026-09-19 |
| Licence | Apache License 2.0 (upstream `DESCRIPTION`; the repository has no `LICENSE` file at this commit) |
| CDM version | 5.4 — see D-043 for why v5.5 was not adopted |
| Release | The commit sits 5 commits before the tag `v5.4.3`, and none of them touches the DDL: `OMOPCDM_postgresql_5.4_ddl.sql` at `v5.4.3` has the same sha256 as the file here (checked 2026-09-24). `CDM_SOURCE` therefore records version 5.4.3 (`docs/omop_mapping.md`) |

| File | Bytes | sha256 |
|---|---|---|
| `OMOPCDM_postgresql_5.4_ddl.sql` | 18301 | `c340fc1723cc71c411aa7d5d67844882ec720bed1135eca2b8a9029d0a3ef854` |
| `OMOPCDM_postgresql_5.4_primary_keys.sql` | 2886 | `d8f50617f9a698bd9fbfe8d4106d76dcd543949a6976032786f64a91c1941f81` |
| `OMOPCDM_postgresql_5.4_indices.sql` | 10279 | `ea23abbb327ee94e974728196cce2b2db466c7ad4bb4313f36fa3ce2388e8776` |

## Reproducing the download

```bash
REF=40ff52f7cb1e634dd45c3d7157307a47b1b78652
for f in OMOPCDM_postgresql_5.4_ddl.sql \
         OMOPCDM_postgresql_5.4_primary_keys.sql \
         OMOPCDM_postgresql_5.4_indices.sql; do
  gh api "repos/OHDSI/CommonDataModel/contents/inst/ddl/5.4/postgresql/$f?ref=$REF" \
    --jq '.content' | base64 -d > "sql/ddl/ohdsi/$f"
done
sha256sum sql/ddl/ohdsi/*.sql
```

The files are LF-only upstream, and `.gitattributes` marks this directory `-text` so the bytes
are stored verbatim and the hashes above verify in any clone.

## What is not here

`OMOPCDM_postgresql_5.4_constraints.sql` (the foreign keys) is **not** vendored: D-032 decided
that foreign keys are not applied. They are replaced by explicit anti-join checks in the ETL,
which keep bulk loads fast and make each referential rule visible and countable.

## How it is applied

`scripts/pipeline.py db-init` resolves the `@cdmDatabaseSchema` marker to the `cdm` schema and
applies the files in this order: DDL, primary keys, indices (D-032).
