# Source inventory: DGIS open data, 2019–2023

What each downloaded file actually is, which of the variables this project needs exists in each
candidate year and under which published name, and how the code catalogues differ between the
2015–2019 and the 2020–2023 catalogue periods.

This document exists to price the study-period decision, which was taken on these numbers in
D-041: 2020–2023, argued in [`protocol.md`](protocol.md#data-source). It measures; it does not
choose. Every cell below comes from a file listed in
[`../config/sources.yml`](../config/sources.yml), named in the cell or in the footnote under its
table. Nothing here is inferred from a neighbouring year, and nothing that DGIS does not publish
is filled in: what is missing is marked `PENDING`.

**Scope.** The 2019–2023 files only. The 2024 and 2025 records and catalogues were not downloaded
and are not measured (D-048), so the "2020–2025" period option cannot be decided from this
document. Development runs on 2023 regardless of the period chosen (D-009).

**Source and credit.** Secretaría de Salud / Dirección General de Información en Salud, SINAC,
open data, page "Nacimientos – Datos Abiertos" (`Última modificación: Jueves 09 de julio de
2026`), under the Términos de Libre Uso. Source values published by DGIS are quoted as they are
published, in Spanish. The files are served over plain HTTP, without TLS.

## Method

Nine ZIP files were downloaded with `pipeline.py download --record`, which streams each file,
computes its sha256 and records hash, size and retrieval date in the manifest. Everything below
was then measured with a throwaway script, outside the repository (D-047):

- ZIP members, their uncompressed size and their internal date come from the archive directory.
- Encoding is a single strict UTF-8 decode over the whole member; a file that fails is reported as
  it is, never re-encoded.
- Delimiter, quoting and line ending are read from the bytes and confirmed with DuckDB's
  `sniff_csv`.
- Row and column counts come from DuckDB `read_csv(..., all_varchar=true, header=true)` over the
  member extracted to a scratch directory, which is deleted afterwards. Nothing was loaded into
  the database and no record was copied into the repository.
- Catalogue comparisons pair the two periods using only published metadata: the `CATALOGO` column
  of `CatVariables.csv` for 2015–2019 and the `Catálogo` column of the 2020–2025 descriptor for
  2020–2023.

## Table 1 · Files

| Scope | File | Announced | `size_bytes` | sha256 (12) | Member(s) | Uncompressed | Internal date | Encoding | Delimiter · line ending | Rows | Columns |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Records 2019 | `sinac_2019.zip` | 62.6 Mb | 65,668,263 | `6f4889d77823` | `sinac2019DatosAbiertos.csv` | 630,367,248 | 2020-06-25 | UTF-8, non-ASCII from byte 5,317 | `,` · LF | 1,868,214 | 76 |
| Records 2020 | `sinac_2020.zip` | 64.5 Mb | 67,723,114 | `e13f0b82ad6a` | `sinac_2020.csv` | 439,281,639 | 2021-06-04 | UTF-8, ASCII only | `,` · CRLF | 1,747,847 | 64 |
| Records 2021 | `sinac_2021.zip` | 63.8 Mb | 66,957,000 | `03f30739ba4e` | `Nacimientos_2021.csv` | 418,386,009 | 2022-05-06 | UTF-8, non-ASCII from byte 154,364,462 | `,` · CRLF | 1,639,479 | 64 |
| Records 2022 | `sinac_2022.zip` | 66.5 Mb | 69,760,730 | `3ab100466dc4` | `Nacimientos_2022.csv` | 416,548,370 | 2023-05-18 | UTF-8, ASCII only | `,` · CRLF | 1,622,921 | 64 |
| Records 2023 | `sinac_2023.zip` | 54.8 Mb [^size] | 65,441,383 | `6440cc1bc2b4` | `Nacimientos_2023.csv` | 399,341,384 | 2024-05-08 | UTF-8, ASCII only | `,` · CRLF | 1,521,280 | 64 |
| Descriptor 2014 | `sinac_descriptores_2014.zip` | 1.71 Kb | 1,758 | `04377adcfb83` | `sinac_descriptores_2014.csv` | 4,563 | 2015-05-26 | **not UTF-8** [^enc] | `,` · CRLF | 76 | 2 |
| Descriptor 2020–2025 | `sinac_descriptores_2020_2025.zip` | 13.0 Kb | 13,347 | `61be6ed40d78` | `Descriptores/sinac_descriptores_2020_2025.zip` → `Descriptores_SINAC_2020.xlsx` [^nested] | 13,030 → 15,480 | 2026-07-09 | n/a, XLSX | n/a | 64 variables | 4 |
| Catalogues 2015–2019 | `sinac_catalogos_2015-2019.zip` | 3.23 Mb | 3,395,980 | `e327fca7a92b` | 24 CSV files | 16,220,127 | 2020-11-23 | UTF-8 | `,` · CRLF | 341,045 over the 24 | 2 to 15 |
| Catalogues 2020–2023 | `sinac_catalogos_2020_2023.zip` | 23.2 Mb | 24,408,182 | `9c7dcd52dd8f` | 20 XLSX files | 24,957,799 | 2021-05-14 to 2022-05-17 | n/a, XLSX | n/a | 397,136 over the 20 [^rows] | 2 to 82 |

[^size]: The page announces 54.8 Mb for 2023 and 62.4 Mb for 2024, while the server serves
    65,441,383 bytes (62.4 MiB) for 2023 and 57,555,277 bytes (54.9 MiB) for 2024 (`HEAD`,
    2026-09-20). The two announced sizes appear to be swapped. Recorded as an observation: the
    manifest verifies files by sha256, never by the announced size.

[^enc]: All of its non-ASCII bytes are in the range 0xA0–0xFF, so it decodes identically as
    cp1252, latin-1 or ISO-8859-15, and the three cannot be told apart from the file itself. It is
    the only downloaded file that is not valid UTF-8. Documented, not converted.

[^nested]: The published ZIP contains a second ZIP, which contains one workbook. The workbook is
    named `Descriptores_SINAC_2020.xlsx` although the published file covers 2020–2025.

[^rows]: Counting every non-empty row, including each sheet's title and header rows. Two members
    carry most of it: `LOCALIDADES_202203 (2).xlsx` (352,584) and
    `ESTABLECIMIENTO_SALUD_202204.xlsx` (41,802).

Four observations an ETL has to survive:

1. **The member name follows no pattern**: `sinac2019DatosAbiertos.csv`, `sinac_2020.csv`,
   `Nacimientos_2021.csv`, `Nacimientos_2022.csv`, `Nacimientos_2023.csv`.
2. **2019 has a different file format**: LF line endings and no quoting, against CRLF and quoted
   fields in 2020–2023. Quoting matters here because the geographic keys carry leading zeros
   (`"09"`).
3. **2019 carries free text** (`UNIMED`, `OCUPHAB`, `ESPECIFIQUE`, `ACELRN`) where 2020–2023 carry
   codes only.
4. The **headers of 2020, 2021, 2022 and 2023 are identical**, same names in the same order
   (checked column by column).

Total for 2019–2023: **8,399,741 records**. The 31,486,699 records and 91 variables quoted in
proposal v2 describe the INSP standardized series, not these files, and do not apply (D-001).

## Table 2 · Presence of the variables this project needs

Names are copied from the source. `D` = the name appears in a published DGIS descriptor;
`H` = the name appears in the file's own CSV header. The 2019 column carries no `D`: DGIS
publishes descriptors for 2008–2013, 2014 and 2020–2025 only, so **no descriptor is published for
the 2015–2019 period**, and the meaning of every 2019 variable is `PENDING` against the
alternative sources listed below the table.

| Item | 2019 | 2020 · 2021 · 2022 · 2023 [^same] |
|---|---|---|
| Gestational age (weeks) | `GESTACH` (H, PENDING) | `EDADGESTACIONAL` (D, H) |
| Total prenatal visits | `TOT_CONS` (H, PENDING) | `TOTALCONSULTAS` (D, H) |
| Trimester of the first prenatal visit | `TRIM_CONS` (H, PENDING) | `TRIMESTREPRIMERCONSULTA` (D, H) |
| Prenatal care received [^extra] | `ATEN_PREN` (H, PENDING) | `ATENCIONPRENATAL` (D, H) |
| Birth weight | `PESOH` (H, PENDING) | `PESO` (D, H) |
| Maternal age | `EDADM` (H, PENDING) | `EDAD` (D, H) |
| Maternal education | `NIV_ESCOL` (H, PENDING) | `ESCOLARIDAD` (D, H) |
| Insurance (derechohabiencia) | `DERHAB`, `DERHAB2` (H, PENDING) | `AFILIACION` (D, H) |
| State | `ENT_NACM`, `ENT_RES`, `ENT_NAC`, `ENT_CERT` (H, PENDING) | `ENTIDADNACIMIENTO`, `ENTIDADRESIDENCIA`, `ENTIDADFEDERATIVAPARTO`, `ENTIDADFEDERATIVACERTIFICA` (D, H) |
| Care unit | `CLUES`, `UNIMED`, `CLUES_33_2`, `UNIMED_33_1` (H, PENDING) | `CLUES`, `CLUESCERTIFICA` (D, H) |
| Pregnancy type / multiplicity | `PRODUCTO` (H, PENDING) | `PRODUCTOEMBARAZO`, `ORDENPRODUCTO`, `TOTALPRODUCTOS` (D, H) |
| Date of birth | `FECH_NACH` (H, PENDING) | `FECHANACIMIENTO` (D, H) |
| Newborn sex | `SEXOH` (H, PENDING) | `SEXO` (D, H) |

[^same]: One column, because the four headers are identical in names and order. Sources: the 64
    rows of `Descriptores_SINAC_2020.xlsx` for `D`, and each year's own CSV header for `H`
    (64 columns in each of the four years).

[^extra]: Not one of the twelve items the task lists, but the exposure measures depend on it, so
    it is inventoried here.

Every item the project needs exists in every candidate year, so the matrix has no empty cell. The
cost is not presence, it is naming and coding:

- **Only 2 of the 76 names of 2019 also appear in 2020–2023**: `CLUES` and `SILVERMAN`. Every
  other variable was renamed between the two periods.
- **Two insurance fields become one.** 2019 carries `DERHAB` and `DERHAB2`; 2020–2023 carries a
  single `AFILIACION`. How to collapse the pair is a modelling decision, not a rename, and it is
  `PENDING` for task 1.3.1.
- **Multiplicity is recorded differently.** 2019 has `PRODUCTO` alone; 2020–2023 adds
  `ORDENPRODUCTO` and `TOTALPRODUCTOS`.

### What was consulted for 2019, and what it does and does not establish

1. **`sinac_descriptores_2014.zip`.** Its 76 field names are identical, and in the same order, to
   the 76 columns of `sinac2019DatosAbiertos.csv` (checked name by name). That is strong evidence
   about the layout, but the file describes 2014: it is not a descriptor for 2019, and
   `TIPO_FORMATO` in that same list distinguishes certificate formats "2010" and "2015", so a
   change between 2014 and 2019 cannot be excluded from this file. Meanings stay `PENDING`.
2. **`CatVariables.csv`, inside `sinac_catalogos_2015-2019.zip`.** DGIS does publish a variable
   list for this period, inside the catalogue ZIP rather than as a descriptor: 109 variables with
   `TIPO`, `LONGITUD`, `DESCRIP` and `CATALOGO`. It covers the certificate, not the open-data
   extract: 109 variables against the 76 published columns, and it includes identifiers
   (`NOMBRE`, `CURP_M`) that the open data does not carry. It also publishes **acceptable ranges**
   for several variables of interest, quoted verbatim: `GESTACH` "Rango aceptable 13 a 42 semanas,
   99 No Especificado", `PESOH` "Rango aceptable 20 a 6000 gramos, 9999 No Especificado", `EDADM`
   "Rango aceptable de 9-59 años", `TOT_CONS` "0 - 30, 99 NO ESPECIFICADO". These are published
   ranges for 2015–2019 and are an input for task 1.3.1; no equivalent was found for 2020–2023,
   where the descriptor states sentinel values only.
3. **INEGI, Red Nacional de Metadatos, record `MEX-SALUD-SINAC-2019`**
   (`https://www.inegi.org.mx/rnm/index.php/catalog/807`, consulted 2026-09-20). It documents a
   dataset `SINAC2019` with a label and the certificate question for each variable, in the same
   naming convention as the 2019 file (`gestach`, `tot_cons`, `trim_cons`, `niv_escol`,
   `derhab`). Three caveats, recorded as read: it declares **62 variables**, not 76; it declares
   **0 cases**; and it describes itself as "la información recabada en los Certificados de
   Nacimientos durante 2018" under the year "Mexico, 2018", while its title says 2019.

None of the three is a descriptor published by DGIS for 2019. The `PENDING` marks stand.

## Table 3 · Catalogue differences, 2015–2019 against 2020–2023

Pairs come from published metadata only: the `CATALOGO` column of `CatVariables.csv` on the left
and the `Catálogo` column of the 2020–2025 descriptor on the right. "Same code, other label"
counts codes present in both catalogues whose published label differs.

| Item | 2015–2019 | 2020–2023 | Codes | Identical | Only 2015–2019 | Only 2020–2023 | Same code, other label |
|---|---|---|---|---|---|---|---|
| Trimester of the first visit | `TRIM_CONS` · `CatTrimestres.csv` | `TRIMESTREPRIMERCONSULTA` · `TRIMESTRE_PRIMER_CONSULTA.xlsx` | 6 → 6 | 0 | 0 | 0 | 6 |
| Prenatal care received | `ATEN_PREN` · `CatSiNo.csv` | `ATENCIONPRENATAL` · `SI_NO.xlsx` | 5 → 5 | 2 | 0 | 0 | 3 |
| Insurance | `DERHAB` · `CATDEREC.csv` | `AFILIACION` · `AFILIACION_CERTIFICADOS.xlsx` | 12 → 13 | 7 | 0 | 1 | 5 |
| Maternal education | `NIV_ESCOL` · `CatEscolaridad.csv` | `ESCOLARIDAD` · `ESCOLARIDAD.xlsx` | 13 → 18 | 0 | 11 | 16 | 2 |
| State | `ENT_RES` · `CatEstados.csv` | `ENTIDADRESIDENCIA` · `ENTIDADES.xlsx` | 37 → 35 | 25 | 4 | 2 | 8 |
| Newborn sex | `SEXOH` · `CatSexo.csv` | `SEXO` · `SEXO.xlsx` | 3 → 4 | 2 | 0 | 1 | 1 |
| Pregnancy multiplicity | `PRODUCTO` · `CATPRODUCTO.csv` | `PRODUCTOEMBARAZO` · `PRODUCTO_EMBARAZO.xlsx` | 4 → 4 | 3 | 1 | 1 | 0 |
| Place of birth | `INST_NAC` · `CatLugarNac.csv` | `LUGARNACIMIENTO` · `LUGAR_NACIMIENTO.xlsx` | 13 → 15 | 7 | 0 | 2 | 6 |
| Care unit (CLUES) | `CLUES` · `CATCLUES.csv` | `CLUES` · `ESTABLECIMIENTO_SALUD_202204.xlsx` [^clues] | 39,178 → 41,801 | 36,235 | 46 | 2,669 | 2,897 |

[^clues]: The descriptor names this catalogue `ESTABLECIMIENTOS_SALUD`; the ZIP carries
    `ESTABLECIMIENTO_SALUD_202204.xlsx`, the only establishment catalogue in it. The two files
    have different shapes (15 columns against 82), so the comparison uses the `CLUES` key of each
    and the unit name of each (`NOM_UNI`, `NOMBRE DE LA UNIDAD`).

### The differences that change meaning silently

These are the ones a rename does not fix. Labels are quoted as published.

**Place of birth: four codes shift meaning.** A 2019 value read with the 2020–2023 catalogue lands
on the wrong category.

| Code | 2015–2019 | 2020–2023 |
|---|---|---|
| `02` | IMSS OPORTUNIDADES | IMSS PROSPERA |
| `09` | *(absent)* | UNIDAD MÉDICA PRIVADA |
| `10` | UNIDAD MÉDICA PRIVADA | VÍA PÚBLICA |
| `11` | VÍA PÚBLICA | HOGAR |
| `12` | HOGAR | OTRO LUGAR |
| `13` | OTRO LUGAR | INSABI |

**Missing-value sentinels are reused.** Across `CatSiNo` / `SI_NO`, `CATDEREC` /
`AFILIACION_CERTIFICADOS` and `CatEscolaridad` / `ESCOLARIDAD`, the same codes change role:
`00`/`0` "N/A" → "NO ESPECIFICADO", `88` "N.E." → "NO APLICA", `99` "S.I." → "SE IGNORA". Pooling
the two periods as one scheme mixes "not applicable" with "not specified".

**Maternal education is a different code system**, not an extension: 2015–2019 uses zero-padded
`01`–`12`; 2020–2023 uses `0`, `1`, `31`, `32`, `51`, `52`, `71`, `72`, `81`, `82`, `101`, `102`,
`111`, `112`, `131`, `132`, plus `88` and `99`. No code except `88` and `99` is shared, and
2020–2023 adds four "TÉCNICO TERMINAL" categories with no 2015–2019 counterpart. This is the one
covariate in table 3 that needs a hand-written crosswalk, and the crosswalk loses the distinction
between the technical categories and the rest.

**Insurance** keeps its codes and changes two of them by policy: `07` "SEGURO POPULAR" → "SEGURO
POPULAR / INSABI", `10` "IMSS OPORTUNIDADES" → "IMSS BIENESTAR"; `11` "ISSFAM" is new. The label
change follows a change in the programmes themselves, so pooling 2019 with 2020–2023 pools two
different insurance landscapes whatever the coding does.

**State** is stable where it matters: 25 of 37 codes identical, 8 relabelled by accent or official
renaming (`09` "DISTRITO FEDERAL" → "CIUDAD DE MÉXICO", `22` "QUERETARO  DE ARTEAGA" →
"QUERÉTARO", and six accent-only changes). The four codes dropped in 2020–2023 are foreign-birth
categories (`33` ESTADOS UNIDOS DE NORTEAMERICA, `34` OTROS PAISES DE LATINOAMERICA, `35` OTROS
PAISES, `36` ESTADOS UNIDOS MEXICANOS); 2020–2023 records the same information in the separate
`NACIOEXTRANJERO` and `RESIDEEXTRANJERO` variables and adds `00` "NO ESPECIFICADO" and `88` "NO
APLICA".

**The trimester of the first visit, the key exposure, keeps every code.** All six
(`0`, `1`, `2`, `3`, `8`, `9`) are present in both periods with the same ordering and the same
meaning; only the wording changes ("PRIMERO" → "PRIMER TRIMESTRE", "N.E." → "NO ESPECIFICADO",
"S.I." → "SE IGNORA"). **Total visits and gestational age are not coded at all**: both are
integers with sentinel values in both periods.

**CLUES** is a moving register rather than a code list: 36,235 keys identical in key and unit
name, 2,897 keys whose unit name changed, 2,669 keys only in 2020–2023 and 46 only in 2015–2019.
Three of those 46 are the sentinels `9997` "NO APLICA", `9998` "NO TIENE CLUES" and `9999` "NO
ESPECIFICADO", which the 2020–2023 establishment catalogue does not contain although the
descriptor still refers to `9998`.

### Gaps in the catalogues themselves

- The 2020–2025 descriptor names 21 catalogues. `DIAGNOSTICOS` (for `CODIGOCIEANOMALIA1` and
  `CODIGOCIEANOMALIA2`) **has no file** in `sinac_catalogos_2020_2023.zip`. `PENDING`: the ICD-10
  list is not published with these files.
- Three catalogues are published under a name other than the one the descriptor uses:
  `ESTABLECIMIENTOS_SALUD` → `ESTABLECIMIENTO_SALUD_202204.xlsx`, `MUNICIPIOS` →
  `MUNICIPIOS_202201 (2).xlsx`, `LOCALIDADES` → `LOCALIDADES_202203 (2).xlsx`. The name carries
  the version date of the register, and two carry a " (2)" suffix.
- The 2020–2023 catalogues are dated between 2021-05-14 and 2022-05-17: no file in that ZIP is
  later than 2022, although the period runs to 2023.

## What this measures for the period decision (1.2.3)

Stated as measurements. The decision is task 1.2.3 and belongs to the author.

- **2020–2023 costs nothing to harmonise.** One descriptor, one catalogue set, four identical
  headers, 6,531,527 records.
- **Adding 2019 costs** a rename of 74 of 76 variables, one crosswalk with real information loss
  (education), one structural decision (`DERHAB` + `DERHAB2` → `AFILIACION`), and care with four
  place-of-birth codes and three sentinel conventions that change meaning silently. It adds
  1,868,214 records and the only pre-pandemic year in the candidate set.
- **The exposures survive the change.** The trimester of the first visit keeps all six codes;
  total visits and gestational age are uncoded integers in both periods. The harmonisation risk
  sits in the covariates, above all education, and in the place-of-birth recoding.
- **2019 stays undocumented by DGIS.** The three sources consulted describe the layout well enough
  to work with, and none of them is a descriptor published for that year.

## PENDING

| What | Why | Where it is resolved |
|---|---|---|
| Meaning of every 2019 variable | DGIS publishes no descriptor for 2015–2019 | Only if 2019 is added (D-050): data dictionary, from the three sources above with their caveats stated |
| `DERHAB` + `DERHAB2` → `AFILIACION` | Two fields against one, and no published rule | Only if 2019 is added (D-050): protocol |
| Education crosswalk 2015–2019 ↔ 2020–2023 | Disjoint code systems; four categories have no counterpart | Only if 2019 is added (D-050): protocol |
| ICD-10 catalogue for 2020–2023 | `DIAGNOSTICOS` is named by the descriptor and not published in the ZIP | Only if congenital anomalies enter the analysis |
| Whether 2024 and 2025 are definitive or preliminary | Outside the scope of this inventory (D-048) | Only if the period is extended |
