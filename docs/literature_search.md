# Literature search

**Status:** protocol v1, written on 2026-10-15 and waiting for the author's approval (issue #58).
Only the pilot searches in [`literature_search/pilots.csv`](literature_search/pilots.csv) have
been run. The search, the screening and the report (the sections marked PENDING) come after the
approval.

## Purpose

The search finds out what is already known about the dependence of prenatal-care measures on the
length of gestation, so that the project states its contribution accurately. It is not meant to
show that the project is new: it looks as hard for work that makes the project redundant as for
work that supports it. The report writes no novelty claim. An absence is reported as "no study
meeting criterion X was found in sources Y searched on date Z".

Screening uses the design of the project only, as listed below. It does not use
[`protocol.md` §What the run shows](protocol.md#what-the-run-shows) or any result of the project.

| Design element | Content |
|---|---|
| Data | Mexico's live-birth certificates (SINAC, DGIS open data), 2020–2023 |
| Exposures | Total prenatal visits; the APNCU index; care started in the first trimester; visits in landmark cohorts |
| Outcome | Preterm birth (< 37 weeks) |
| Concern | Pregnancies that end earlier have less time for visits, so visit counts are truncated by the length of gestation |
| Method | A null simulation of visits on the NOM-007-SSA2-2016 schedule, whose crude odds ratios and risk differences are compared with the observed ones |

## Review questions

- **Q1.** Has the bias that the length of gestation induces in prenatal-care counts or indices
  been described or quantified in studies of preterm birth or gestational age, and with which
  methods (index adjustments, landmark or time-dependent designs, simulation, analytic
  expectation)?
- **Q2.** Has it been examined with data from Mexico (SINAC, birth certificates, national surveys,
  institutional records) or from elsewhere in Latin America?
- **Q3.** Has a null simulation, or an exact expectation, of visits under a recommended schedule
  been used to quantify the association that truncation alone produces?
- **Q4.** How have studies using Mexican birth-certificate data measured prenatal care and related
  it to preterm birth or low birth weight, and did they address truncation?

## Eligibility criteria

### Common to every question

- **Reports.** Any record that reports data, a method, a simulation, a review or an argument:
  journal articles, preprints, theses, reports, letters, editorials and conference abstracts.
  Errata, retraction notices and records without a title are not reports.
- **Population.** Human pregnancies or births; the country is set by each question.
- **Prenatal-care measure.** The number of prenatal visits; an index built from visits and their
  timing (APNCU/Kotelchuck, Kessner, GINDEX, R-GINDEX or another); the timing or trimester of the
  first visit; visits counted up to a fixed gestational week. A programme, an intervention or the
  content of care (supplements, screening tests) is not a measure of use.
- **Gestational outcome or axis.** Preterm birth, gestational age or the duration of pregnancy,
  birth weight or low birth weight. Birth weight is included because the closest study known
  before the search, Koroukian & Rimm 2002 (a seed), analyses low birth weight (pilot P02f).
- **Languages.** English, Spanish and Portuguese, judged on the full text. A record in another
  language with an English abstract is excluded (E1).
- **Dates.** No start date; the end date is the date on which each source is searched.

### Q1 · The bias described or quantified

A record is included when it (a) studies a prenatal-care measure as an exposure, or as the object
of a methods paper, (b) against a gestational outcome or axis, and (c) describes, quantifies or
addresses the dependence of the measure on the length of gestation. Any name counts (truncation,
gestational age bias, reverse causation, immortal time, length of exposure), and so does any means:
an index adjusted for gestational age, a ratio to expected visits, visits per week, a landmark or
time-dependent exposure, survival methods, simulation, an analytic expectation, or a statement in
the text, a stated limitation included.

Using an index that adjusts for gestational age is not (c) by itself: the record must state,
assess or justify that adjustment as an answer to the dependence.

Each included record is graded **mentioned** (stated only), **addressed** (handled by design or
adjustment) or **quantified** (the size of the bias is estimated).

### Q2 · With data from Mexico or Latin America

Q1, with data collected in Mexico or another country of Latin America and the Caribbean, from any
source (vital records, surveys, institutional records). The region is the set of MeSH headings
Latin America, Central America, South America, Caribbean Region and Mexico. Data on women of
Mexican or Latin American origin collected elsewhere, such as United States vital statistics, do
not count.

### Q3 · A null simulation or an exact expectation

A record is included when it computes the association, or the distribution of a prenatal-care
measure, that would arise if care had no effect on the length of gestation, either by simulating
visits under a schedule (recommended or observed) or by an analytic expectation, and reports it as
the size of the bias or sets it against an observed association. Any country, data source or
gestational outcome qualifies, and so does a methods paper without data. Computing expected visits
only to build an index, as APNCU does, is Q1 and not Q3.

### Q4 · Mexican birth-certificate data

A record is included when it (a) uses data from the Mexican certificate of live birth
(*certificado de nacimiento*, captured by SINAC and published by DGIS; any year; microdata or
published aggregates), (b) has a prenatal-care measure and (c) preterm birth, gestational age, low
birth weight or birth weight, and (d) reports a relation between (b) and (c): any estimate, crude
or adjusted and on any scale, or a table of (c) by (b), also when (b) is a covariate whose estimate
is shown. The handling of truncation is graded as in Q1, with **not mentioned** added. A record
whose data source is unclear goes to full text.

### Exclusion reasons

A record is excluded only when it meets no question. The reason recorded is the first that
applies, in this order:

| Code | Reason |
|---|---|
| E1 | Language other than English, Spanish or Portuguese |
| E2 | Not a report (erratum, retraction notice, record without a title) |
| E3 | Not about human pregnancy or birth |
| E4 | No prenatal-care measure as defined above |
| E5 | No gestational outcome or axis |
| E6 | The dependence on the length of gestation is not described, quantified or addressed (fails Q1–Q3), and the data are not from Mexican birth certificates (fails Q4) |
| E7 | Duplicate found during screening |

## Information sources

| Source | Platform | Searches | Notes |
|---|---|---|---|
| PubMed | NCBI E-utilities (`esearch`, `efetch`) | S1, S2, S3 | MeSH and title/abstract fields |
| Europe PMC | REST API (`search`) | S1, S2, S3 | All its sources (MEDLINE, PubMed Central, preprints, Agricola and the rest), with no source limit; the `KW` field carries MeSH headings (P01) |
| OpenAlex | REST API (`/works`, filter `title_and_abstract.search`) | S1, S2, S3 in English, and again in Spanish and Portuguese | A record without an abstract is matched on its title only |
| LILACS | BVS regional portal (`pesquisa.bvsalud.org`), filter `db:("LILACS")`, opened in the session's built-in browser | S1, S2, S3, in three languages | LILACS is the only database selected in the portal, whose MEDLINE records PubMed covers |
| SciELO | SciELO Search (`search.scielo.org`), in the same browser | S1, S2, S3, in three languages | Returned no results on the pilot date (P11); see the retry rule under [Running the search](#running-the-search) |
| Citation chasing | OpenAlex (`referenced_works`, filter `cites:`) and Europe PMC (references, `CITES:`) | — | From the seeds and the included studies |

Not searched: Scopus, Web of Science and Embase, which are subscription databases, and Google
Scholar, which has no export or API for a reproducible search (see
[Planned limitations](#planned-limitations)). No study registry is searched: the questions concern
observational and methodological work. No author or expert is contacted.

### Seeds

The seeds are the journal articles among the references of
[`protocol.md` §References](protocol.md#references). Their identifiers come from pilot P00.

| Seed | PMID | DOI |
|---|---|---|
| Koroukian SM, Rimm AA. The "Adequacy of Prenatal Care Utilization" (APNCU) index to study low birth weight: is the index biased? *J Clin Epidemiol.* 2002;55(3):296–305 | 11864801 | 10.1016/s0895-4356(01)00471-1 |
| Kotelchuck M. An evaluation of the Kessner Adequacy of Prenatal Care Index and a proposed Adequacy of Prenatal Care Utilization Index. *Am J Public Health.* 1994;84(9):1414–1420 | 8092364 | 10.2105/ajph.84.9.1414 |
| Raju TNK, et al. Optimizing care and outcome for late-preterm (near-term) infants: a summary of the workshop sponsored by the National Institute of Child Health and Human Development. *Pediatrics.* 2006;118(3):1207–1214 | 16951017 | 10.1542/peds.2006-0018 |

The other four references (the DGIS filling guide, the APNCU SAS program, NOM-007-SSA2-2016 and
the WHO fact sheet) have no DOI or PMID and are not chased. The seeds enter the records under
"other methods" and are screened like any other record.

## Search strategy

### Concept blocks

- **A · Prenatal-care measures.** Prenatal or antenatal care, visits, consultations, attendance
  and check-ups; number of visits; APNCU, Kotelchuck, Kessner, GINDEX, R-GINDEX; MeSH Prenatal
  Care.
- **B · Gestational outcome.** Preterm, prematurity; gestational age, length or duration; length
  or duration of pregnancy; birth weight; MeSH Premature Birth, Infant, Premature, Obstetric Labor,
  Premature, Gestational Age, Infant, Low Birth Weight and Birth Weight.
- **C · Bias and methods.** The six terms of the task (truncation, gestational age bias,
  time-dependent, immortal time, length of gestation, simulation), plus the terms the pilots showed
  to be needed: time-varying, landmark, expected visits, observed-to-expected, rate of visits,
  visit rate, visits per week, survival analysis, reverse causation, spurious, artifact or
  artefact, gestational age adjustment, bias and biased; MeSH Bias, Computer Simulation and
  Proportional Hazards Models. The six task terms alone give 184 PubMed records and miss
  Koroukian & Rimm 2002 (P02d), which is found only by expected visits, observed-to-expected or
  bias (P03).
- **MX · Mexico.** Mexico, Mexican, SINAC, *Subsistema de Información sobre Nacimientos*; MeSH
  Mexico.
- **CERT · Birth certificates.** Birth certificate(s), SINAC, *certificado(s) de nacimiento*,
  *Subsistema de Información sobre Nacimientos*, birth registry, birth records, *Dirección General
  de Información en Salud*, DGIS; MeSH Birth Certificates.

LILACS, SciELO and the second OpenAlex search add the Spanish and Portuguese terms of each block
(for example *control prenatal*, *atenção pré-natal*, *edad gestacional*, *peso ao nascer*,
*sesgo*, *viés*, *truncamiento*).

### Searches

| Search | Blocks | Serves | Why |
|---|---|---|---|
| S1 | A AND B AND C | Q1, Q3, and Q2 outside Mexico | The bias search, with no geographic limit |
| S2 | A AND B AND MX | Q2 in Mexico, Q4 | Every Mexican study of prenatal care and a gestational outcome, with or without bias terms, because Q4 asks how all of them measured care |
| S3 | B AND MX AND CERT | Q4 | Certificate-based studies whose abstract does not name prenatal care: 41 PubMed records that S2 misses (P09b) |

Latin America outside Mexico has no search of its own. With block C its records are a subset of
S1 (33 PubMed records, P02m); without it, the search would add 1,185 PubMed records on prenatal
care and gestational outcomes in general (P02k), which Q2 does not ask about.

Pilot counts of the final strings (P10, P12), as orientation for the size of the run:

| Source | S1 | S2 | S3 |
|---|---|---|---|
| PubMed | 751 | 193 | 65 |
| Europe PMC | 725 | 186 | 66 |
| OpenAlex, English | 962 | 221 | 81 |
| OpenAlex, Spanish and Portuguese | 75 | 32 | 2 |
| LILACS | 56 | 57 | 42 |
| SciELO | not available | not available | not available |

The sum is 3,514 records before de-duplication and citation chasing. PubMed and Europe PMC
overlap heavily: 707 of the 725 Europe PMC records of S1 are MEDLINE records (P05c).

### Full query strings

Each string is copied from the file that ran the final pilots (P10, P12) and is run exactly as
written:

- PubMed: the `term` of `esearch.fcgi?db=pubmed`.
- Europe PMC: the `query` of `/europepmc/webservices/rest/search`.
- OpenAlex: the value of `filter=title_and_abstract.search:` on `/works`. OpenAlex stems words
  and accepts no wildcard (P01), so stems are written out as words.
- LILACS: the `q` of `https://pesquisa.bvsalud.org/portal/?lang=en`.
- SciELO: the `q` of `https://search.scielo.org/?lang=en`. These strings could not be tested
  (P11).

PubMed reports three phrases of S2 and S3 as absent from its index (the Spanish names of SINAC and
DGIS, and *certificados de nacimiento*): they match nothing in PubMed and are kept so that the
blocks read the same in every source.

<details>
<summary>PubMed</summary>

S1 · A AND B AND C

```text
("Prenatal Care"[Mesh] OR "prenatal care"[tiab] OR "antenatal care"[tiab] OR "pre-natal care"[tiab] OR "ante-natal care"[tiab] OR "prenatal visit*"[tiab] OR "antenatal visit*"[tiab] OR "prenatal consultation*"[tiab] OR "antenatal consultation*"[tiab] OR "prenatal attendance"[tiab] OR "antenatal attendance"[tiab] OR "prenatal check-up*"[tiab] OR "antenatal check-up*"[tiab] OR "number of visits"[tiab] OR APNCU[tiab] OR Kotelchuck[tiab] OR Kessner[tiab] OR GINDEX[tiab] OR "R-GINDEX"[tiab]) AND ("Premature Birth"[Mesh] OR "Infant, Premature"[Mesh] OR "Obstetric Labor, Premature"[Mesh] OR "Gestational Age"[Mesh] OR "Infant, Low Birth Weight"[Mesh] OR "Birth Weight"[Mesh] OR preterm[tiab] OR "pre-term"[tiab] OR prematur*[tiab] OR "gestational age*"[tiab] OR "gestational length"[tiab] OR "gestational duration"[tiab] OR "length of gestation"[tiab] OR "duration of gestation"[tiab] OR "pregnancy duration"[tiab] OR "duration of pregnancy"[tiab] OR "length of pregnancy"[tiab] OR "birth weight"[tiab] OR birthweight[tiab]) AND ("Bias"[Mesh] OR "Computer Simulation"[Mesh] OR "Proportional Hazards Models"[Mesh] OR truncat*[tiab] OR "gestational age bias"[tiab] OR "gestational age adjust*"[tiab] OR "time-dependent"[tiab] OR "time dependent"[tiab] OR "time-varying"[tiab] OR "time varying"[tiab] OR "immortal time"[tiab] OR "length of gestation"[tiab] OR "duration of gestation"[tiab] OR "length of pregnancy"[tiab] OR simulat*[tiab] OR landmark*[tiab] OR "expected visits"[tiab:~3] OR "observed to expected"[tiab] OR "observed-to-expected"[tiab] OR "rate of visits"[tiab:~2] OR "visit rate*"[tiab] OR "visits per week"[tiab:~3] OR "survival analysis"[tiab] OR "reverse caus*"[tiab] OR spurious[tiab] OR artifact*[tiab] OR artefact*[tiab] OR bias[tiab] OR biased[tiab])
```

S2 · A AND B AND MX

```text
("Prenatal Care"[Mesh] OR "prenatal care"[tiab] OR "antenatal care"[tiab] OR "pre-natal care"[tiab] OR "ante-natal care"[tiab] OR "prenatal visit*"[tiab] OR "antenatal visit*"[tiab] OR "prenatal consultation*"[tiab] OR "antenatal consultation*"[tiab] OR "prenatal attendance"[tiab] OR "antenatal attendance"[tiab] OR "prenatal check-up*"[tiab] OR "antenatal check-up*"[tiab] OR "number of visits"[tiab] OR APNCU[tiab] OR Kotelchuck[tiab] OR Kessner[tiab] OR GINDEX[tiab] OR "R-GINDEX"[tiab]) AND ("Premature Birth"[Mesh] OR "Infant, Premature"[Mesh] OR "Obstetric Labor, Premature"[Mesh] OR "Gestational Age"[Mesh] OR "Infant, Low Birth Weight"[Mesh] OR "Birth Weight"[Mesh] OR preterm[tiab] OR "pre-term"[tiab] OR prematur*[tiab] OR "gestational age*"[tiab] OR "gestational length"[tiab] OR "gestational duration"[tiab] OR "length of gestation"[tiab] OR "duration of gestation"[tiab] OR "pregnancy duration"[tiab] OR "duration of pregnancy"[tiab] OR "length of pregnancy"[tiab] OR "birth weight"[tiab] OR birthweight[tiab]) AND ("Mexico"[Mesh] OR mexic*[tiab] OR SINAC[tiab] OR "Subsistema de Informacion sobre Nacimientos"[tiab])
```

S3 · B AND MX AND CERT

```text
("Premature Birth"[Mesh] OR "Infant, Premature"[Mesh] OR "Obstetric Labor, Premature"[Mesh] OR "Gestational Age"[Mesh] OR "Infant, Low Birth Weight"[Mesh] OR "Birth Weight"[Mesh] OR preterm[tiab] OR "pre-term"[tiab] OR prematur*[tiab] OR "gestational age*"[tiab] OR "gestational length"[tiab] OR "gestational duration"[tiab] OR "length of gestation"[tiab] OR "duration of gestation"[tiab] OR "pregnancy duration"[tiab] OR "duration of pregnancy"[tiab] OR "length of pregnancy"[tiab] OR "birth weight"[tiab] OR birthweight[tiab]) AND ("Mexico"[Mesh] OR mexic*[tiab] OR SINAC[tiab] OR "Subsistema de Informacion sobre Nacimientos"[tiab]) AND ("Birth Certificates"[Mesh] OR "birth certificate*"[tiab] OR SINAC[tiab] OR "certificado de nacimiento"[tiab] OR "certificados de nacimiento"[tiab] OR "Subsistema de Informacion sobre Nacimientos"[tiab] OR "birth registry"[tiab] OR "birth records"[tiab] OR "Direccion General de Informacion en Salud"[tiab] OR DGIS[tiab])
```

</details>

<details>
<summary>Europe PMC</summary>

S1 · A AND B AND C

```text
(TITLE_ABS:("prenatal care" OR "antenatal care" OR "pre-natal care" OR "ante-natal care" OR "prenatal visit" OR "prenatal visits" OR "antenatal visit" OR "antenatal visits" OR "prenatal consultation" OR "prenatal consultations" OR "antenatal consultation" OR "antenatal consultations" OR "prenatal attendance" OR "antenatal attendance" OR "prenatal check-up" OR "prenatal check-ups" OR "antenatal check-up" OR "antenatal check-ups" OR "number of visits" OR APNCU OR Kotelchuck OR Kessner OR GINDEX OR "R-GINDEX") OR KW:("Prenatal Care")) AND (TITLE_ABS:(preterm OR "pre-term" OR prematur* OR "gestational age" OR "gestational ages" OR "gestational length" OR "gestational duration" OR "length of gestation" OR "duration of gestation" OR "pregnancy duration" OR "duration of pregnancy" OR "length of pregnancy" OR "birth weight" OR birthweight) OR KW:("Premature Birth" OR "Infant, Premature" OR "Obstetric Labor, Premature" OR "Gestational Age" OR "Infant, Low Birth Weight" OR "Birth Weight")) AND (TITLE_ABS:(truncat* OR "gestational age bias" OR "gestational age adjusted" OR "gestational age-adjusted" OR "gestational age adjustment" OR "time-dependent" OR "time dependent" OR "time-varying" OR "time varying" OR "immortal time" OR "length of gestation" OR "duration of gestation" OR "length of pregnancy" OR simulat* OR landmark* OR "expected visits"~3 OR "observed to expected" OR "observed-to-expected" OR "rate of visits"~2 OR "visit rate" OR "visit rates" OR "visits per week"~3 OR "survival analysis" OR "reverse causation" OR "reverse causality" OR spurious OR artifact* OR artefact* OR bias OR biased) OR KW:("Bias" OR "Computer Simulation" OR "Proportional Hazards Models"))
```

S2 · A AND B AND MX

```text
(TITLE_ABS:("prenatal care" OR "antenatal care" OR "pre-natal care" OR "ante-natal care" OR "prenatal visit" OR "prenatal visits" OR "antenatal visit" OR "antenatal visits" OR "prenatal consultation" OR "prenatal consultations" OR "antenatal consultation" OR "antenatal consultations" OR "prenatal attendance" OR "antenatal attendance" OR "prenatal check-up" OR "prenatal check-ups" OR "antenatal check-up" OR "antenatal check-ups" OR "number of visits" OR APNCU OR Kotelchuck OR Kessner OR GINDEX OR "R-GINDEX") OR KW:("Prenatal Care")) AND (TITLE_ABS:(preterm OR "pre-term" OR prematur* OR "gestational age" OR "gestational ages" OR "gestational length" OR "gestational duration" OR "length of gestation" OR "duration of gestation" OR "pregnancy duration" OR "duration of pregnancy" OR "length of pregnancy" OR "birth weight" OR birthweight) OR KW:("Premature Birth" OR "Infant, Premature" OR "Obstetric Labor, Premature" OR "Gestational Age" OR "Infant, Low Birth Weight" OR "Birth Weight")) AND (TITLE_ABS:(Mexico OR Mexican OR Mexicans OR SINAC OR "Subsistema de Informacion sobre Nacimientos") OR KW:("Mexico"))
```

S3 · B AND MX AND CERT

```text
(TITLE_ABS:(preterm OR "pre-term" OR prematur* OR "gestational age" OR "gestational ages" OR "gestational length" OR "gestational duration" OR "length of gestation" OR "duration of gestation" OR "pregnancy duration" OR "duration of pregnancy" OR "length of pregnancy" OR "birth weight" OR birthweight) OR KW:("Premature Birth" OR "Infant, Premature" OR "Obstetric Labor, Premature" OR "Gestational Age" OR "Infant, Low Birth Weight" OR "Birth Weight")) AND (TITLE_ABS:(Mexico OR Mexican OR Mexicans OR SINAC OR "Subsistema de Informacion sobre Nacimientos") OR KW:("Mexico")) AND (TITLE_ABS:("birth certificate" OR "birth certificates" OR SINAC OR "certificado de nacimiento" OR "certificados de nacimiento" OR "Subsistema de Informacion sobre Nacimientos" OR "birth registry" OR "birth records" OR "Direccion General de Informacion en Salud" OR DGIS) OR KW:("Birth Certificates"))
```

</details>

<details>
<summary>OpenAlex (English)</summary>

S1 · A AND B AND C

```text
("prenatal care" OR "antenatal care" OR "pre-natal care" OR "ante-natal care" OR "prenatal visit" OR "antenatal visit" OR "prenatal consultation" OR "antenatal consultation" OR "prenatal attendance" OR "antenatal attendance" OR "prenatal check-up" OR "antenatal check-up" OR "number of visits" OR APNCU OR Kotelchuck OR Kessner OR GINDEX OR "R-GINDEX") AND (preterm OR "pre-term" OR premature OR prematurity OR "gestational age" OR "gestational length" OR "gestational duration" OR "length of gestation" OR "duration of gestation" OR "pregnancy duration" OR "duration of pregnancy" OR "length of pregnancy" OR "birth weight" OR birthweight) AND (truncation OR truncated OR "gestational age bias" OR "gestational age adjusted" OR "gestational age adjustment" OR "time-dependent" OR "time-varying" OR "immortal time" OR "length of gestation" OR "duration of gestation" OR "length of pregnancy" OR simulation OR simulated OR landmark OR "expected visits" OR "expected number of visits" OR "observed to expected" OR "rate of visits" OR "visit rate" OR "visits per week" OR "survival analysis" OR "reverse causation" OR "reverse causality" OR spurious OR artifact OR artifactual OR artefact OR artefactual OR bias OR biased)
```

S2 · A AND B AND MX

```text
("prenatal care" OR "antenatal care" OR "pre-natal care" OR "ante-natal care" OR "prenatal visit" OR "antenatal visit" OR "prenatal consultation" OR "antenatal consultation" OR "prenatal attendance" OR "antenatal attendance" OR "prenatal check-up" OR "antenatal check-up" OR "number of visits" OR APNCU OR Kotelchuck OR Kessner OR GINDEX OR "R-GINDEX") AND (preterm OR "pre-term" OR premature OR prematurity OR "gestational age" OR "gestational length" OR "gestational duration" OR "length of gestation" OR "duration of gestation" OR "pregnancy duration" OR "duration of pregnancy" OR "length of pregnancy" OR "birth weight" OR birthweight) AND (Mexico OR Mexican OR SINAC OR "Subsistema de Información sobre Nacimientos")
```

S3 · B AND MX AND CERT

```text
(preterm OR "pre-term" OR premature OR prematurity OR "gestational age" OR "gestational length" OR "gestational duration" OR "length of gestation" OR "duration of gestation" OR "pregnancy duration" OR "duration of pregnancy" OR "length of pregnancy" OR "birth weight" OR birthweight) AND (Mexico OR Mexican OR SINAC OR "Subsistema de Información sobre Nacimientos") AND ("birth certificate" OR SINAC OR "certificado de nacimiento" OR "Subsistema de Información sobre Nacimientos" OR "birth registry" OR "birth records" OR "Dirección General de Información en Salud" OR DGIS)
```

</details>

<details>
<summary>OpenAlex (Spanish/Portuguese)</summary>

S1 · A AND B AND C

```text
("control prenatal" OR "controles prenatales" OR "atención prenatal" OR "cuidado prenatal" OR "consulta prenatal" OR "consultas prenatales" OR "visitas prenatales" OR "cuidado pré-natal" OR "assistência pré-natal" OR "atenção pré-natal" OR "consulta pré-natal" OR "consultas pré-natais" OR "consultas de pré-natal" OR "número de consultas") AND (prematuro OR prematuros OR prematura OR prematuridad OR prematuridade OR pretérmino OR "pré-termo" OR "edad gestacional" OR "idade gestacional" OR "peso al nacer" OR "peso ao nascer" OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez") AND (sesgo OR sesgos OR sesgado OR viés OR truncamiento OR truncamento OR truncado OR simulación OR simulação OR "dependiente del tiempo" OR "dependente do tempo" OR "tiempo inmortal" OR "tempo imortal" OR espurio OR espuria OR espúrio OR espúria OR artefacto OR artefato OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez" OR "visitas esperadas" OR "consultas esperadas" OR "análisis de supervivencia" OR "análise de sobrevivência" OR "causalidad inversa" OR "causalidade reversa")
```

S2 · A AND B AND MX

```text
("control prenatal" OR "controles prenatales" OR "atención prenatal" OR "cuidado prenatal" OR "consulta prenatal" OR "consultas prenatales" OR "visitas prenatales" OR "cuidado pré-natal" OR "assistência pré-natal" OR "atenção pré-natal" OR "consulta pré-natal" OR "consultas pré-natais" OR "consultas de pré-natal" OR "número de consultas") AND (prematuro OR prematuros OR prematura OR prematuridad OR prematuridade OR pretérmino OR "pré-termo" OR "edad gestacional" OR "idade gestacional" OR "peso al nacer" OR "peso ao nascer" OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez") AND (México OR mexicana OR mexicanas OR mexicano OR mexicanos OR SINAC)
```

S3 · B AND MX AND CERT

```text
(prematuro OR prematuros OR prematura OR prematuridad OR prematuridade OR pretérmino OR "pré-termo" OR "edad gestacional" OR "idade gestacional" OR "peso al nacer" OR "peso ao nascer" OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez") AND (México OR mexicana OR mexicanas OR mexicano OR mexicanos OR SINAC) AND ("certificado de nacimiento" OR "certificados de nacimiento" OR SINAC OR "Subsistema de Información sobre Nacimientos" OR "Dirección General de Información en Salud" OR DGIS)
```

</details>

<details>
<summary>LILACS (BVS portal)</summary>

S1 · A AND B AND C

```text
(mh:("Prenatal Care") OR tw:("prenatal care" OR "antenatal care" OR "prenatal visit" OR "prenatal visits" OR "antenatal visit" OR "antenatal visits" OR "control prenatal" OR "controles prenatales" OR "atención prenatal" OR "cuidado prenatal" OR "consulta prenatal" OR "consultas prenatales" OR "visitas prenatales" OR "cuidado pré-natal" OR "assistência pré-natal" OR "atenção pré-natal" OR "consulta pré-natal" OR "consultas pré-natais" OR "consultas de pré-natal" OR "número de consultas" OR "number of visits" OR APNCU OR Kotelchuck OR Kessner OR GINDEX)) AND (mh:("Premature Birth" OR "Infant, Premature" OR "Obstetric Labor, Premature" OR "Gestational Age" OR "Infant, Low Birth Weight" OR "Birth Weight") OR tw:(preterm OR "pre-term" OR prematur$ OR "gestational age" OR "edad gestacional" OR "idade gestacional" OR pretérmino OR "pré-termo" OR "birth weight" OR birthweight OR "peso al nacer" OR "peso al nacimiento" OR "peso ao nascer" OR "length of gestation" OR "duration of pregnancy" OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez")) AND (mh:("Bias" OR "Computer Simulation" OR "Proportional Hazards Models") OR tw:(truncat$ OR truncamiento OR truncamento OR "gestational age bias" OR bias OR biased OR sesgo OR sesgos OR sesgado OR viés OR vies OR enviesado OR "time-dependent" OR "time-varying" OR "dependiente del tiempo" OR "dependientes del tiempo" OR "dependente do tempo" OR "immortal time" OR "tiempo inmortal" OR "tempo imortal" OR simulat$ OR simulación OR simulação OR landmark OR "length of gestation" OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez" OR "expected visits" OR "visitas esperadas" OR "consultas esperadas" OR "observed to expected" OR spurious OR espurio OR espuria OR espúrio OR espúria OR artifact OR artefact OR artefacto OR artefato OR "survival analysis" OR "análisis de supervivencia" OR "análise de sobrevivência" OR "reverse causation" OR "causalidad inversa" OR "causalidade reversa")) AND db:("LILACS")
```

S2 · A AND B AND MX

```text
(mh:("Prenatal Care") OR tw:("prenatal care" OR "antenatal care" OR "prenatal visit" OR "prenatal visits" OR "antenatal visit" OR "antenatal visits" OR "control prenatal" OR "controles prenatales" OR "atención prenatal" OR "cuidado prenatal" OR "consulta prenatal" OR "consultas prenatales" OR "visitas prenatales" OR "cuidado pré-natal" OR "assistência pré-natal" OR "atenção pré-natal" OR "consulta pré-natal" OR "consultas pré-natais" OR "consultas de pré-natal" OR "número de consultas" OR "number of visits" OR APNCU OR Kotelchuck OR Kessner OR GINDEX)) AND (mh:("Premature Birth" OR "Infant, Premature" OR "Obstetric Labor, Premature" OR "Gestational Age" OR "Infant, Low Birth Weight" OR "Birth Weight") OR tw:(preterm OR "pre-term" OR prematur$ OR "gestational age" OR "edad gestacional" OR "idade gestacional" OR pretérmino OR "pré-termo" OR "birth weight" OR birthweight OR "peso al nacer" OR "peso al nacimiento" OR "peso ao nascer" OR "length of gestation" OR "duration of pregnancy" OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez")) AND (mh:("Mexico") OR tw:(mexic$ OR méxico OR SINAC OR "Subsistema de Información sobre Nacimientos" OR "certificado de nacimiento" OR "certificados de nacimiento")) AND db:("LILACS")
```

S3 · B AND MX AND CERT

```text
(mh:("Premature Birth" OR "Infant, Premature" OR "Obstetric Labor, Premature" OR "Gestational Age" OR "Infant, Low Birth Weight" OR "Birth Weight") OR tw:(preterm OR "pre-term" OR prematur$ OR "gestational age" OR "edad gestacional" OR "idade gestacional" OR pretérmino OR "pré-termo" OR "birth weight" OR birthweight OR "peso al nacer" OR "peso al nacimiento" OR "peso ao nascer" OR "length of gestation" OR "duration of pregnancy" OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez")) AND (mh:("Mexico") OR tw:(mexic$ OR méxico OR SINAC OR "Subsistema de Información sobre Nacimientos" OR "certificado de nacimiento" OR "certificados de nacimiento")) AND (mh:("Birth Certificates") OR tw:("birth certificate" OR "birth certificates" OR SINAC OR "certificado de nacimiento" OR "certificados de nacimiento" OR "Subsistema de Información sobre Nacimientos" OR "birth registry" OR "birth records" OR "Dirección General de Información en Salud" OR DGIS)) AND db:("LILACS")
```

</details>

<details>
<summary>SciELO Search</summary>

S1 · A AND B AND C

```text
("prenatal care" OR "antenatal care" OR "prenatal visit" OR "prenatal visits" OR "antenatal visit" OR "antenatal visits" OR "control prenatal" OR "controles prenatales" OR "atención prenatal" OR "cuidado prenatal" OR "consulta prenatal" OR "consultas prenatales" OR "visitas prenatales" OR "cuidado pré-natal" OR "assistência pré-natal" OR "atenção pré-natal" OR "consulta pré-natal" OR "consultas pré-natais" OR "consultas de pré-natal" OR "número de consultas" OR "number of visits" OR APNCU OR Kotelchuck OR Kessner OR GINDEX) AND (preterm OR "pre-term" OR prematur$ OR "gestational age" OR "edad gestacional" OR "idade gestacional" OR pretérmino OR "pré-termo" OR "birth weight" OR birthweight OR "peso al nacer" OR "peso al nacimiento" OR "peso ao nascer" OR "length of gestation" OR "duration of pregnancy" OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez") AND (truncat$ OR truncamiento OR truncamento OR "gestational age bias" OR bias OR biased OR sesgo OR sesgos OR sesgado OR viés OR vies OR enviesado OR "time-dependent" OR "time-varying" OR "dependiente del tiempo" OR "dependientes del tiempo" OR "dependente do tempo" OR "immortal time" OR "tiempo inmortal" OR "tempo imortal" OR simulat$ OR simulación OR simulação OR landmark OR "length of gestation" OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez" OR "expected visits" OR "visitas esperadas" OR "consultas esperadas" OR "observed to expected" OR spurious OR espurio OR espuria OR espúrio OR espúria OR artifact OR artefact OR artefacto OR artefato OR "survival analysis" OR "análisis de supervivencia" OR "análise de sobrevivência" OR "reverse causation" OR "causalidad inversa" OR "causalidade reversa")
```

S2 · A AND B AND MX

```text
("prenatal care" OR "antenatal care" OR "prenatal visit" OR "prenatal visits" OR "antenatal visit" OR "antenatal visits" OR "control prenatal" OR "controles prenatales" OR "atención prenatal" OR "cuidado prenatal" OR "consulta prenatal" OR "consultas prenatales" OR "visitas prenatales" OR "cuidado pré-natal" OR "assistência pré-natal" OR "atenção pré-natal" OR "consulta pré-natal" OR "consultas pré-natais" OR "consultas de pré-natal" OR "número de consultas" OR "number of visits" OR APNCU OR Kotelchuck OR Kessner OR GINDEX) AND (preterm OR "pre-term" OR prematur$ OR "gestational age" OR "edad gestacional" OR "idade gestacional" OR pretérmino OR "pré-termo" OR "birth weight" OR birthweight OR "peso al nacer" OR "peso al nacimiento" OR "peso ao nascer" OR "length of gestation" OR "duration of pregnancy" OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez") AND (mexic$ OR méxico OR SINAC OR "Subsistema de Información sobre Nacimientos" OR "certificado de nacimiento" OR "certificados de nacimiento")
```

S3 · B AND MX AND CERT

```text
(preterm OR "pre-term" OR prematur$ OR "gestational age" OR "edad gestacional" OR "idade gestacional" OR pretérmino OR "pré-termo" OR "birth weight" OR birthweight OR "peso al nacer" OR "peso al nacimiento" OR "peso ao nascer" OR "length of gestation" OR "duration of pregnancy" OR "duración de la gestación" OR "duración del embarazo" OR "duração da gestação" OR "duração da gravidez") AND (mexic$ OR méxico OR SINAC OR "Subsistema de Información sobre Nacimientos" OR "certificado de nacimiento" OR "certificados de nacimiento") AND ("birth certificate" OR "birth certificates" OR SINAC OR "certificado de nacimiento" OR "certificados de nacimiento" OR "Subsistema de Información sobre Nacimientos" OR "birth registry" OR "birth records" OR "Dirección General de Información en Salud" OR DGIS)
```

</details>

### Limits and filters

No query limits the date, language, publication type or study design; language is applied at
screening. The only restriction is the choice of LILACS inside the BVS portal. No published
search filter is used, and no strategy is adapted from an earlier review.

### Citation chasing

- **Backward.** Every reference of each seed and of each included study (OpenAlex
  `referenced_works`; Europe PMC references for records with a PMID).
- **Forward.** Every citing record when the cited work has 100 or fewer citing records in
  OpenAlex (FOR APPROVAL). Above that, the citing records are filtered by the block the cited work
  does not supply: Kotelchuck 1994 (1,175 citing records in OpenAlex) by block C, which leaves 62
  in OpenAlex and 52 in Europe PMC (P08b); Raju 2006 (737) by block A, which leaves 12 and 20
  (P08d), because A AND C leaves none (P08c). An included study above the threshold is filtered
  by block C.
- **Rounds.** Chasing repeats on the studies each round includes, until a round includes none.
  Every record keeps the round that found it.

## Pilot searches

The pilots were run on 2026-10-15, between 18:33 and 18:52 UTC, to refine the strings. They
retrieved hit counts, and in PubMed the PMIDs needed to check the seeds; no record was screened.
All 131 pilot requests are in [`literature_search/pilots.csv`](literature_search/pilots.csv), with
the exact request, its time and what it changed. The syntax and term checks of P01, P03 and P04
were first run without a log and repeated with one; the counts matched. The pilots that changed
the strategy:

| Pilot | Finding | Change |
|---|---|---|
| P01 | Europe PMC ignores a wildcard inside a phrase. Its `KW` field returns 37,475 MEDLINE records for Prenatal Care, against 36,258 for the MeSH heading in PubMed, while `MESH:` returns 1,708. OpenAlex stems words and rejects wildcards | Plurals listed in Europe PMC; `KW` used for headings; stems written as words in OpenAlex |
| P02d, P03 | The task's six bias terms give 184 PubMed records and miss Koroukian & Rimm 2002 | Block C extended |
| P02f | Birth weight in block B adds 31 records (291 → 322) | Birth weight added |
| P02g | bias, biased and Bias[Mesh] add 351 records (322 → 673) | Kept: bias is the concept the search is about |
| P02k, P02m | Latin America: 1,185 records without block C, 33 with it | No separate Latin America search |
| P03a, P03b, P09 | Broad birth-record terms add 407 records outside block A; certificate-specific terms add 41 | S3 with certificate terms |
| P04, P13 | Marginal yield of further terms | Added: rate of visits, visit rate, visits per week, reverse causation, survival analysis, Proportional Hazards Models. Not added: confound* (689 records), Confounding Factors, Epidemiologic (38), Models, Statistical (940), person-time (none) |
| P07 | Spanish and Portuguese strings return 75, 32 and 2 OpenAlex records | Second OpenAlex search |
| P08 | Citing records of the seeds | Forward-chasing filters |
| P10e, P10g, P11c | The BVS portal and SciELO answer scripted requests with a security check or HTTP 403 | Web sources are searched by browser navigation only |
| P11 | SciELO Search returned no results | Retry rule |
| P12 | Final strings, counts only | Sizes above |

## Running the search

- Each query runs once. Its source, exact string, exact request (API or portal URL), date and
  time in UTC and number of hits go to `literature_search/queries.csv`.
- PubMed: `esearch` with the history server, then `efetch` in XML. Europe PMC: `resultType=core`
  with cursor paging. OpenAlex: cursor paging, 200 records per page. LILACS and SciELO: browser
  navigation, 100 records per page, reading the original abstract; the summaries the BVS portal
  marks as created by AI are ignored.
- OpenAlex runs without an API key, on a free daily budget shared by the IP address (USD 0.10,
  with USD 0.001 per search request, as its response headers stated on the pilot date). If the
  budget runs out, the run continues the next day and each query keeps its own date.
- The exact requests in `queries.csv` are the record of the run; no script is versioned
  (FOR APPROVAL). The alternative is a script under `scripts/`, with its pure functions in `src/`
  and their tests (CLAUDE.md rules 6 and 7).
- If SciELO Search returns no results on the run date, it is retried on two more days within a
  week (FOR APPROVAL). If it still fails, SciELO is reported as not searched, with those dates.

## Records, de-duplication and verification

- `literature_search/records.csv` has one row per record: `id`, `sources`, `title`, `year`,
  `doi`, `pmid`, `source_id`, `stage`, `decision`, `reason`. `source_id` holds the LILACS,
  SciELO or OpenAlex identifier.
- No record enters `records.csv` unless a source of this protocol returned it. Nothing is added
  from memory.
- De-duplication runs by DOI (lowercase, without the resolver prefix), then by PMID, then by
  normalised title (lowercase, no diacritics, punctuation or spaces) with years at most one apart;
  a title match with different years is checked by hand. The kept record lists every source that
  returned it. A throwaway Python script does it; no review software is used.
- Every DOI is checked against Crossref (`api.crossref.org/works/{doi}`), or against the DOI
  handle service (`doi.org/api/handles/{doi}`) when it is registered elsewhere, such as DataCite;
  every PMID against PubMed `esummary`. A record whose identifier does not resolve is corrected
  from its source or removed before screening, with the reason ("removed for other reasons" in
  PRISMA 2020).
- A record with neither DOI nor PMID, common in LILACS, SciELO and theses, is kept when its
  source identifier resolves to its record page (FOR APPROVAL). The alternative is to remove every
  such record, whatever its content.

## Screening

1. **Title and abstract**, by one screener. Each record is included, excluded with a code, or
   marked uncertain; an uncertain record goes forward.
2. **Full text** for every record that goes forward, where it is open access (PubMed Central or
   Europe PMC, the open-access location in OpenAlex, the LILACS or SciELO link, the publisher).
   When no open full text is found and the abstract is enough to decide, the decision rests on the
   abstract and says so; otherwise the record is reported as not retrieved and listed.
3. Every exclusion has its code, with a note when the code alone does not explain it.
4. The single screener is the AI assistant (Claude Code) working in this repository. The author
   approves this protocol and re-screens a random sample of the exclusions blind.
5. **Blind re-screen.** When screening ends, 20 records are drawn from all excluded records with
   `random.Random(58).sample(sorted(ids), 20)` in Python; the seed, 58, is the number of the issue
   and is fixed before any record is screened. The author gets their title and abstract
   only, and the assistant's decisions are shown once the author's are recorded. Every
   disagreement is reported, and a record the author would include goes to full text.

## Data extraction

For each included study: the question or questions it answers; country and data source; years;
prenatal-care measures; gestational outcome; how the dependence on the length of gestation was
handled (grade and method) and its size when quantified; a locator (section, page, table or
figure) for each claim it supports; and how close it is to this project on three axes, stated
without judging value:

- **Data:** SINAC 2020–2023 / SINAC in other years / other Mexican data / other Latin American
  data / other.
- **Bias:** truncation of the visit measure by the length of gestation / a related dependence /
  none.
- **Method:** null simulation on a schedule with odds ratios and risk differences / another
  simulation / analytic expectation / landmark or time-dependent design / index adjustment / none.

## Reporting checklist

### PRISMA-S

Items of the PRISMA-S checklist (Rethlefsen et al. 2021, Table 1) and where this document answers
them:

| # | Item | Where |
|---|---|---|
| 1 | Database name, with its platform | [Information sources](#information-sources) |
| 2 | Multi-database searching | [Information sources](#information-sources): Europe PMC searches all its sources; the BVS portal is restricted to LILACS |
| 3 | Study registries | None searched ([Information sources](#information-sources)) |
| 4 | Online resources and browsing | LILACS and SciELO through their web interfaces ([Information sources](#information-sources)) |
| 5 | Citation searching | [Citation chasing](#citation-chasing) |
| 6 | Contacts | None ([Information sources](#information-sources)) |
| 7 | Other methods | [Seeds](#seeds) |
| 8 | Full search strategies | [Full query strings](#full-query-strings); `queries.csv` |
| 9 | Limits and restrictions | [Limits and filters](#limits-and-filters) |
| 10 | Search filters | None ([Limits and filters](#limits-and-filters)) |
| 11 | Prior work | None ([Limits and filters](#limits-and-filters)) |
| 12 | Updates | No update is planned before the submission of 20 November 2026 |
| 13 | Dates of searches | `queries.csv`, date and time of each query |
| 14 | Peer review | No search peer review; the author approves the protocol |
| 15 | Total records | `queries.csv`; [PRISMA 2020 flow counts](#prisma-2020-flow-counts) |
| 16 | Deduplication | [Records, de-duplication and verification](#records-de-duplication-and-verification) |

### PRISMA 2020 flow counts

PENDING. The counts follow the boxes of the PRISMA 2020 flow diagram (Page et al. 2021, Fig 1)
for databases and for other methods:

| Box | Databases | Other methods (seeds and citation chasing) |
|---|---|---|
| Records identified, per source | PENDING | PENDING |
| Duplicate records removed | PENDING | — |
| Records removed for other reasons | PENDING | — |
| Records screened | PENDING | — |
| Records excluded | PENDING | — |
| Reports sought for retrieval | PENDING | PENDING |
| Reports not retrieved | PENDING | PENDING |
| Reports assessed for eligibility | PENDING | PENDING |
| Reports excluded, per reason | PENDING | PENDING |
| Studies included, and their reports | PENDING | PENDING |

## Planned limitations

- **Sources not covered.** Scopus, Web of Science, Embase and Google Scholar.
- **Languages.** English, Spanish and Portuguese only.
- **One screener.** An AI assistant screens every record; the author checks 20 random exclusions.
- **Abstract-level signals.** A study that mentions the bias only in its full text is found only
  when its title or abstract passes screening, so the grade "mentioned" is undercounted.
- **Interfaces.** OpenAlex matches a record without an abstract on its title only. LILACS and
  SciELO are searched through web interfaces whose behaviour can change; SciELO did not answer on
  the pilot date.
- **Full text.** Only where it is open access.

## Points for approval

1. Birth weight in block B (P02f).
2. Block C beyond the six terms of the task (P02d, P03, P04, P13).
3. No separate Latin America search (P02k, P02m).
4. S3, the certificate search for Q4 (P09).
5. The Spanish and Portuguese OpenAlex search (P07).
6. The forward-chasing threshold of 100 citing records and the filter for each seed (P08).
7. Records without DOI or PMID kept when their source identifier resolves.
8. The SciELO retry rule.
9. No versioned script: the exact requests in `queries.csv` are the record of the run.
10. The AI assistant as the single screener, with the author's blind re-screen of 20 exclusions.

## Results

PENDING: written after the run.

### What is known, per question

PENDING.

### What was not found

PENDING.

### Closeness of the closest studies to this project

PENDING.

## Limitations

PENDING: the planned limitations above, updated with what happened during the run.

## References

- Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement: an updated guideline for
  reporting systematic reviews. *BMJ.* 2021:n71. doi:10.1136/bmj.n71
- Rethlefsen ML, Kirtley S, Waffenschmidt S, et al. PRISMA-S: an extension to the PRISMA Statement
  for Reporting Literature Searches in Systematic Reviews. *Syst Rev.* 2021;10:39.
  doi:10.1186/s13643-020-01542-z
- The seeds are listed under [Seeds](#seeds).
