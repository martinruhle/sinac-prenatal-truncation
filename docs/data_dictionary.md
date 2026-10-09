# Data dictionary v0

The source variables this project reads, as DGIS publishes them for 2020–2023, and how they are
held in the `staging` schema. Where each one lands in the OMOP CDM is in
[`omop_mapping.md`](omop_mapping.md) (D-017).

**Scope.** Only the variables the project uses get a row (D-011). That is 22 of the 64 published
columns:
- the items of table 2 of [`source_inventory.md`](source_inventory.md);
- `RESIDEEXTRANJERO` and `FECHANACIMIENTOMADRE`, which the OMOP mapping reads;
- `LUGARNACIMIENTO`, which [`protocol.md`](protocol.md#outcome) uses to compare the excluded
  records with the retained ones.

The other 42 columns are staged too and are listed by name at the end. Nothing here covers 2019,
whose variables are `PENDING` unless 2019 is added (D-050).

## Sources

- **Descriptor.** `Descriptores_SINAC_2020.xlsx`, inside `sinac_descriptores_2020_2025.zip`
  (`dgis_sinac_descriptores_2020_2025` in [`../config/sources.yml`](../config/sources.yml)). It
  has one row per variable with four fields: `ID`, `VARIABLE`, `DESCRIPCIÓN` and `Catálogo`. It
  has **no type or unit field**. Units are taken from the description text, and only when the
  text states one.
- **Catalogues.** The code lists of `sinac_catalogos_2020_2023.zip`, named by the `Catálogo` field
  of the descriptor.
- **Form in 2023.** Measured once over `staging.sinac_2023` with a throwaway query (the practice of
  D-047): the pattern the values follow and how many cells are blank. It describes the 2023 file,
  not a rule.

The notes of the descriptor define the three flavors of null its codes use, in substance:

- **"No Especificado"**: the certifier recorded no answer.
- **"Se Ignora"**: the certifier did not find or did not know the answer.
- **"No Aplica"**: the system sets it by validation when the question does not apply.

The notes also say that a null (blank) value is either a variable that is not on the 2020
certificate model or a value that is not specified or does not apply.

## How staging holds them

`pipeline.py stage --years <years>` loads each year's file into `staging.sinac_<year>` (D-069):

- **Every source column is `text`** (D-033). Leading zeros carry meaning: in 2023, 332,476 values
  of `ENTIDADRESIDENCIA` and 1,399,617 of `AFILIACION` start with `0`, and the catalogue keys are
  written that way (`09`, `00`). Casting happens in the ETL, with explicit handling of invalid
  values.
- **Column names are the published names in lower case.** Postgres folds unquoted identifiers to
  lower case, so `SELECT EDADGESTACIONAL FROM staging.sinac_2023` works as published.
- **A blank cell is NULL**, whether it was written empty or as `""`. No other value is changed:
  `99`, `09/09/9999` and `  ` stay as they are.
- **`source_row`** (integer, primary key) is the 1-based ordinal of the record in the year's CSV,
  header excluded (D-059). It is taken from the position of the row in the Parquet copy, which
  DuckDB writes in file order (D-070).
- **`staging.load_counts`** records, per year, the rows counted in the CSV, the Parquet copy and
  the table, with the member name and the sha256 of the ZIP. A load commits only when the three
  counts agree. The 2023 load holds 1,521,280 records in each of the three.

## Columns in scope

In the table, `#` is the `ID` of the descriptor and the columns are listed in that order. Flavors
of null are quoted as published, from the descriptor text or from the catalogue named in the row.

| # | Source name | Description | Form in 2023 | Unit | Catalogue | Flavors of null, as published | Used by |
|---|---|---|---|---|---|---|---|
| 2 | `ENTIDADNACIMIENTO` | Mother's state of birth | 2-digit code, zero-padded | — | `ENTIDADES` | `00` "NO ESPECIFICADO", `88` "NO APLICA", `99` "SE IGNORA" | State items of the inventory; descriptive |
| 4 | `EDAD` | Mother's age | 2-digit integer, 10 to 59 | completed years | — | `888` "No Especificado", `999` "Se Ignora" (neither occurs in 2023) | `PERSON.year_of_birth`, case (2) (D-060); maternal age covariate in seven groups (D-094), as a `MEASUREMENT` row with the declared value (D-100) |
| 7 | `FECHANACIMIENTOMADRE` | Mother's date of birth | `dd/mm/yyyy` | — | — | `09/09/9999` "fecha no especificada" (1 record in 2023) | `PERSON.year_of_birth`, case (1) (D-060) |
| 9 | `RESIDEEXTRANJERO` | Whether the mother resides abroad | 1-digit code; only `1` and `2` occur in 2023 | — | `SI_NO` | `0` "NO ESPECIFICADO", `8` "NO APLICA", `9` "SE IGNORA" | Base cohort criterion 2; `LOCATION.country_concept_id` (D-057, D-068) |
| 10 | `ENTIDADRESIDENCIA` | Mother's state of residence | 2-digit code, zero-padded | — | `ENTIDADES` | `00` "NO ESPECIFICADO", `88` "NO APLICA", `99` "SE IGNORA" | `LOCATION.state`; state covariate and state gradient (D-057, D-068, D-094) |
| 20 | `ATENCIONPRENATAL` | Whether the mother received prenatal care | 1-digit code | — | `SI_NO` | `0` "NO ESPECIFICADO", `8` "NO APLICA", `9` "SE IGNORA" | Described only; no rule uses it ([`protocol.md`](protocol.md#one-set-of-records-for-the-four-measures), D-086) |
| 21 | `TRIMESTREPRIMERCONSULTA` | Trimester of the mother's first prenatal visit | 1-digit code | — | `TRIMESTRE_PRIMER_CONSULTA` | `8` "NO ESPECIFICADO", `9` "SE IGNORA". `0` "NO RECIBIÓ" is an answer, not a null (D-065) | Exposures (b) and (c), and the common set of records (D-086, D-089, D-092); `OBSERVATION` (D-065) |
| 22 | `TOTALCONSULTAS` | Total prenatal visits during the pregnancy | integer, 0 to 30; blank in 2,554 records | visits (a count) | — | `99` "No Especificado"; blank | Exposures (a), (b) and (d), and the common set of records (D-086, D-088); `OBSERVATION` (D-065, D-066) |
| 24 | `AFILIACION` | Health-service affiliation (*derechohabiencia*) | 2-digit code, zero-padded | — | `AFILIACION_CERTIFICADOS` | `00` "NO ESPECIFICADO", `88` "NO APLICA", `99` "SE IGNORA" | Insurance gradient (v1.0); not an adjustment covariate (D-094, D-099); not in the CDM until v1.0 (D-102) |
| 25 | `ESCOLARIDAD` | Mother's education | code of 1 to 3 digits, not padded | — | `ESCOLARIDAD` | `0` "NO ESPECIFICADO", `88` "NO APLICA", `99` "SE IGNORA" | Education covariate in five levels (D-094), as an `OBSERVATION` row whose concept is the level (D-101) |
| 30 | `FECHANACIMIENTO` | Date of birth of the live-born child | `dd/mm/yyyy` | — | — | none declared | Base cohort criterion 1; the date of every CDM event (D-052, D-063) |
| 32 | `SEXO` | Sex of the live-born child | 1-digit code; `1` "HOMBRE", `2` "MUJER" | — | `SEXO` | `0` "NO ESPECIFICADO", `9` "SE IGNORA" | `gender_concept_id` of the newborn `PERSON`, with `0` and `9` as concept 0 (D-103); no criterion or model |
| 33 | `EDADGESTACIONAL` | Weeks of gestation of the live-born child | 2-digit integer, 14 to 45 | weeks | — | `99` "No Especificado" | The outcome; base cohort criteria 3 and 6; landmark cohorts and APNCU expected visits (D-090, D-091); `MEASUREMENT` (D-053, D-064). Never a predictor (CLAUDE.md rule 3) |
| 35 | `PESO` | Weight of the live-born child | integer of 3 or 4 digits, 350 to 5,450 | grams | — | `9999` "No Especificado" | Birth weight, a `MEASUREMENT` of the newborn (D-105); never a criterion or a predictor (CLAUDE.md rule 3) |
| 43 | `PRODUCTOEMBARAZO` | Type of pregnancy by the products delivered: single, twins, three or more | 1-digit code | — | `PRODUCTO_EMBARAZO` | `0` "NO ESPECIFICADO" | Base cohort criteria 4 and 5; `MEASUREMENT` (D-068) |
| 44 | `ORDENPRODUCTO` | Order of the product in the delivery | 1-digit integer; blank in 1,494,848 records | — | — | none declared; blank | Multiplicity (D-051) |
| 45 | `TOTALPRODUCTOS` | Total products delivered in the event | 1-digit integer; blank in 1,493,576 records | — | — | none declared; blank | Multiplicity (D-051) |
| 48 | `LUGARNACIMIENTO` | Place where the birth occurred | 2-digit code, zero-padded | — | `LUGAR_NACIMIENTO` | `00` "NO ESPECIFICADO", `99` "SE IGNORA" | Comparison of excluded and retained records ([`protocol.md`](protocol.md#outcome)) |
| 49 | `CLUES` | Establishment key (CLUES) of the site where the delivery was attended, as the provider recorded it | 11 characters, 5 letters and 6 digits, or `9998`; blank in 22 records | — | `ESTABLECIMIENTOS_SALUD` [^clues] | `9998` "No tiene CLUES" | Care unit (inventory); `CARE_SITE` is not in v0 |
| 56 | `ENTIDADFEDERATIVAPARTO` | State where the delivery was attended | 2-digit code, zero-padded | — | `ENTIDADES` | `00` "NO ESPECIFICADO", `88` "NO APLICA", `99` "SE IGNORA" | Place of delivery, descriptive (D-057) |
| 60 | `CLUESCERTIFICA` | Establishment key (CLUES) of the certifying establishment | as `CLUES`; blank in 591,931 records | — | `ESTABLECIMIENTOS_SALUD` [^clues] | none declared; `9998` occurs [^cluescert] | Care unit (inventory) |
| 61 | `ENTIDADFEDERATIVACERTIFICA` | State of the certifying establishment | 2-digit code, zero-padded | — | `ENTIDADES` | `00` "NO ESPECIFICADO", `88` "NO APLICA", `99` "SE IGNORA" | State items of the inventory; descriptive |

[^clues]: The descriptor names the catalogue `ESTABLECIMIENTOS_SALUD`. The ZIP publishes it as
    `ESTABLECIMIENTO_SALUD_202204.xlsx`, and that file has no `9998` key
    ([`source_inventory.md`](source_inventory.md#gaps-in-the-catalogues-themselves)).

[^cluescert]: The descriptor declares `9998` "No tiene CLUES" for `CLUES` only. It occurs in
    21,098 records of `CLUESCERTIFICA` in 2023 anyway. It is read with the meaning declared for
    `CLUES` only once the ETL needs this column.

## What the files show

These are measurements, not rules. They are inputs for the tasks that decide what to do with them.
The first three cover the 2023 file; the last two cover the four files of 2020–2023, measured once
with a throwaway query (D-047) when the newborn was mapped.

- **`PESO` = 9999 in 80,048 of 1,521,280 records (5.3 %).** That is far more than the sentinels
  of the variables the cohort uses: `EDADGESTACIONAL` = 99 occurs in 492 and
  `TOTALCONSULTAS` = 99 in 5,426. Birth weight is not a predictor (CLAUDE.md rule 3), but any
  descriptive table that reports it has to state this.
- **Multiplicity is written in two ways.** `PRODUCTOEMBARAZO` is filled in every record.
  `ORDENPRODUCTO` is filled in 26,421 of the 27,782 records with `PRODUCTOEMBARAZO` 2 or 3, and
  in 11 singletons. `TOTALPRODUCTOS` is filled in 27,704 of those records and in no singleton.
  This matches D-051: `ORDENPRODUCTO` cannot stand in for the pregnancy.
- **Codes that do not occur in 2023.** `RESIDEEXTRANJERO` has no `0`, `8`, `9` or the
  uncatalogued `88` of D-057. `EDAD` has no `888` or `999`. `LUGARNACIMIENTO` has no `13`
  "INSABI" or `99`. Rules for these codes are still needed, because other years carry them
  ([`omop_mapping.md`](omop_mapping.md#codes-without-a-standard-concept)).
- **Birth weight, 2020–2023.** `PESO` = 9999 in 354,847 of 6,531,527 records (5.4 %), and it is
  not missing at random. Among singletons it occurs in 11.1 % of the births at 22 to 36 weeks
  (50,477 of 453,015) and in 4.8 % of those at 37 weeks or more (288,066 of 5,952,435), and in
  617 of the 702 births below 22 weeks. No value is blank or other than digits. 328 weights are
  below 500 g, the lowest 270 g, and one is above 6,000 g: 7,650 g in 2022. All are loaded as
  recorded (D-105).
- **Newborn sex, 2020–2023.** `SEXO` is `1` in 3,324,680 records and `2` in 3,202,236; `0` in
  3,957 and `9` in 654 (0.07 % together). `9` almost disappears after 2020: 630 records in 2020,
  15 in 2021, 9 in 2022 and none in 2023.

## Staged but not in scope

Staged as text with their `source_row`, with no dictionary row (D-011):

`NACIOEXTRANJERO`, `MUNICIPIONACIMIENTO`, `SECONSIDERAINDIGENA`, `HABLALENGUAINDIGENA`,
`ESTADOCONYUGAL`, `MUNICIPIORESIDENCIA`, `LOCALIDADRESIDENCIA`, `NUMEROEMBARAZOS`,
`HIJOSNACIDOSMUERTOS`, `HIJOSNACIDOSVIVOS`, `HIJOSSOBREVIVIENTES`, `CONDICIONHIJOANTERIOR`,
`VIVEHIJOANTERIOR`, `ORDENNACIMIENTO`, `SOBREVIVIOPARTO`, `INTERRUMPIOESTUDIOS`,
`CLAVEOCUPACIONHABITUAL`, `TRABAJAACTUALMENTE`, `EDADPADRE`, `HORANACIMIENTO`, `TALLA`, `APGAR`,
`SILVERMAN`, `TAMIZAUDITIVO`, `VACUNA_BCG`, `VACUNAHEPATITIS_B`, `VITAMINA_A`, `VITAMINA_K`,
`CODIGOCIEANOMALIA1`, `CODIGOCIEANOMALIA2`, `TIEMPOTRASLADO`, `RESOLUCIONEMBARAZO`,
`UTILIZOFORCEPS`, `TIPOCESAREA`, `PERSONALATENDIO`, `TIPOMEDICOATENDIO`, `MUNICIPIOPARTO`,
`LOCALIDADPARTO`, `CERTIFICADOPOR`, `MUNICIPIOCERTIFICA`, `LOCALIDADCERTIFICA`,
`FECHACERTIFICADO`.

`FECHACERTIFICADO` is used by no criterion (D-052). `SECONSIDERAINDIGENA` and
`HABLALENGUAINDIGENA` are future work (D-061). `CODIGOCIEANOMALIA1` and `CODIGOCIEANOMALIA2`
refer to a `DIAGNOSTICOS` catalogue that is not published, which is `PENDING` in the inventory.
