# Literature search

**Status:** protocol v2, approved by the author on 2026-10-15 after the review recorded under
[Approval](#approval) (issue #58). The search ran on 2026-10-15 and 2026-10-16, after that
approval; its results are under [Results](#results). The author's blind re-screen of 20
exclusions is PENDING.

## Purpose

The search finds out what is already known about the dependence of prenatal-care measures on the
length of gestation, so that the project states its contribution accurately. It is not meant to
show that the project is new: it looks as hard for work that makes the project redundant as for
work that supports it. The report writes no novelty claim. An absence is reported as "no study
meeting criterion X was found in sources Y searched on date Z".

Screening uses the design of the project only, as listed below from
[`roadmap.md` §1](roadmap.md#1-core-the-course-deliverable). It does not use
[`protocol.md` §What the run shows](protocol.md#what-the-run-shows) or any result of the project.

| Design element | Content |
|---|---|
| Data | Mexico's live-birth certificates (SINAC, DGIS open data), 2020–2023 |
| Exposures | (a) total prenatal visits; (b) the APNCU index, with Kotelchuck's program and the ACOG schedule; (c) care started in the first trimester; (d) total visits in landmark cohorts at weeks 28, 32 and 34 |
| Outcome | Preterm birth (< 37 weeks) |
| Concern | Pregnancies that end earlier have less time for visits, so visit counts are truncated by the length of gestation |
| Methods | Crude and adjusted odds ratios for each measure, from a binomial model adjusted for maternal age, education, state and year; the landmark cohorts of (d) as a design against truncation; a null simulation of visits on the NOM-007-SSA2-2016 schedule with two adherence scenarios, compared with the observed records on the risk-difference scale and with crude odds ratios; sensitivity analyses of the preterm cut-off (37, 34 and 32 weeks) and of multiple pregnancies; gradients by state and by insurance |

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

- **Journal publications.** Records published in a journal: original articles, reviews, letters,
  comments and editorials. Preprints, theses, conference abstracts and papers, books and
  chapters, reports and datasets are not eligible, because the first aim of the work is a
  peer-reviewed journal article; in the pilots they were at least 189 of the OpenAlex records
  without a PMID (P16c). Errata, retraction notices and records without a title are not reports.
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
the text, a stated limitation included. Q1 has no geographic limit.

Using an index that adjusts for gestational age is not (c) by itself: the record must state,
assess or justify that adjustment as an answer to the dependence.

Each included record is graded **mentioned** (stated only), **addressed** (handled by design or
adjustment) or **quantified** (the size of the bias is estimated).

### Q2 · With data from Mexico or Latin America

Q1, with data collected in Mexico or another country of Latin America and the Caribbean, from any
source (vital records, surveys, institutional records). The region is the set of MeSH headings
Latin America, Central America, South America, Caribbean Region and Mexico. Data on women of
Mexican or Latin American origin collected elsewhere, such as United States vital statistics, do
not count for Q2; such a study is still included through Q1 or Q3 when it meets them.

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

Q4 is limited to Mexico because it maps how the studies of the same data measured prenatal care,
whether or not they dealt with truncation. Similar studies of any other population, the ones that
describe, quantify or simulate the truncation, are included through Q1 and Q3. Mapping the rest of
the world's literature would add, in PubMed alone, 3,700 birth-certificate or vital-record studies
that do not deal with the bias (P15b) and 414 systematic reviews without bias terms (P15c).

### Exclusion reasons

A record is excluded only when it meets no question. The reason recorded is the first that
applies, in this order:

| Code | Reason |
|---|---|
| E1 | Language other than English, Spanish or Portuguese |
| E2 | Not a journal publication (preprint, thesis, conference abstract or paper, book or chapter, report, dataset), or not a report (erratum, retraction notice, record without a title) |
| E3 | Not about human pregnancy or birth |
| E4 | No prenatal-care measure as defined above |
| E5 | No gestational outcome or axis |
| E6 | The dependence on the length of gestation is not described, quantified or addressed, in any population (fails Q1–Q3), and the data are not from Mexican birth certificates (fails Q4) |
| E7 | Duplicate found during screening |

## Information sources

| Source | Platform | Searches | Notes |
|---|---|---|---|
| PubMed | NCBI E-utilities (`esearch`, `efetch`) | S1, S2, S3 | MeSH and title/abstract fields |
| OpenAlex | REST API (`/works`, filters `title_and_abstract.search` and `type`) | S1, S2, S3 in English, and again in Spanish and Portuguese | A record without an abstract is matched on its title only; it covers journals that PubMed does not index: 80 of the 221 OpenAlex records of the Mexico search have no PMID (P16b) |
| LILACS | BVS regional portal (`pesquisa.bvsalud.org`), filter `db:("LILACS")`, opened in the session's built-in browser | S1, S2, S3, in three languages | LILACS is the only database selected in the portal, whose MEDLINE records PubMed covers |
| Citation chasing | OpenAlex (`referenced_works`, filter `cites:`) and Europe PMC (references, `CITES:`) | — | From the seeds and the included studies; Europe PMC also supplies open full texts |

Not searched:

- **Europe PMC as a search source.** Of its 948 records for S1–S3, 927 are MEDLINE records that
  PubMed returns; 19 of the other 21 are preprints, which are not eligible (P16a). It stays as a
  tool for citation chasing and full texts.
- **SciELO.** SciELO Search returned no results on 2026-10-15 (P11). The Spanish and Portuguese
  OpenAlex search and LILACS cover its languages.
- **Scopus, Web of Science and Embase**, which are subscription databases, and **Google
  Scholar**, which has no export or API for a reproducible search.

No study registry is searched: the questions concern observational and methodological work. No
author or expert is contacted.

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

LILACS and the second OpenAlex search add the Spanish and Portuguese terms of each block (for
example *control prenatal*, *atenção pré-natal*, *edad gestacional*, *peso ao nascer*, *sesgo*,
*viés*, *truncamiento*).

### Searches

| Search | Blocks | Serves | Why |
|---|---|---|---|
| S1 | A AND B AND C | Q1, Q3, and Q2 outside Mexico | The bias search, with no geographic limit |
| S2 | A AND B AND MX | Q2 in Mexico, Q4 | Every Mexican study of prenatal care and a gestational outcome, with or without bias terms, because Q4 asks how all of them measured care |
| S3 | B AND MX AND CERT | Q4 | Certificate-based studies whose abstract does not name prenatal care: 41 PubMed records that S2 misses (P09b) |

Latin America outside Mexico has no search of its own. With block C its records are a subset of
S1 (33 PubMed records, P02m); without it, the search would add 1,185 PubMed records on prenatal
care and gestational outcomes in general (P02k), which Q2 does not ask about.

Pilot counts of the final strings before the publication-type filter (P10, P12), as orientation
for the size of the run:

| Source | S1 | S2 | S3 |
|---|---|---|---|
| PubMed | 751 | 193 | 65 |
| OpenAlex, English | 962 | 221 | 81 |
| OpenAlex, Spanish and Portuguese | 75 | 32 | 2 |
| LILACS | 56 | 57 | 42 |

The sum is 2,537 records before de-duplication, the type filter and citation chasing. PubMed
alone returns 979 distinct records for S1–S3 (P14a).

### Full query strings

Each string is copied from the file that ran the final pilots (P10, P12) and is run exactly as
written:

- PubMed: the `term` of `esearch.fcgi?db=pubmed`.
- OpenAlex: the value of `title_and_abstract.search:` in the `filter` of `/works`, followed by
  `,type:article|review|letter|editorial`. OpenAlex stems words and accepts no wildcard (P01), so
  stems are written out as words.
- LILACS: the `q` of `https://pesquisa.bvsalud.org/portal/?lang=en`.

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

### Limits and filters

The OpenAlex queries keep the types article, review, letter and editorial, which hold the journal
publications; the author restricted the search to journal publications on 2026-10-15 because its
first aim is a peer-reviewed journal article. In PubMed and LILACS, records of other types are
excluded at screening (E2). No query limits the date, language or study design; language is
applied at screening. The other restriction is the choice of LILACS inside the BVS portal. No
published search filter is used, and no strategy is adapted from an earlier review.

### Citation chasing

- **Backward.** Every reference of each seed and of each included study (OpenAlex
  `referenced_works`; Europe PMC references for records with a PMID).
- **Forward.** Every citing record when the cited work has 100 or fewer citing records in
  OpenAlex. Above that, the citing records are filtered by the block the cited work does not
  supply: Kotelchuck 1994 (1,175 citing records in OpenAlex) by block C, which leaves 62 in
  OpenAlex and 52 in Europe PMC (P08b); Raju 2006 (737) by block A, which leaves 12 and 20
  (P08d), because A AND C leaves none (P08c). An included study above the threshold is filtered
  by block C.
- **Rounds.** Chasing repeats on the studies each round includes, until a round includes none.
  Every record keeps the round that found it.

## Pilot searches

The pilots were run on 2026-10-15, between 18:33 and 21:14 UTC, to refine the strings and to
price the author's review. They retrieved hit counts, and in PubMed the PMIDs needed to check the
seeds; no record was screened. Every pilot request is in
[`literature_search/pilots.csv`](literature_search/pilots.csv), with the exact request, its time
and what it changed. The syntax and term checks of P01, P03 and P04 were first run without a log
and repeated with one; the counts matched. The pilots that changed the strategy:

| Pilot | Finding | Change |
|---|---|---|
| P01 | Europe PMC ignores a wildcard inside a phrase. Its `KW` field returns 37,475 MEDLINE records for Prenatal Care, against 36,258 for the MeSH heading in PubMed, while `MESH:` returns 1,708. OpenAlex stems words and rejects wildcards | Stems written as words in OpenAlex |
| P02d, P03 | The task's six bias terms give 184 PubMed records and miss Koroukian & Rimm 2002 | Block C extended |
| P02f | Birth weight in block B adds 31 records (291 → 322) | Birth weight added |
| P02g | bias, biased and Bias[Mesh] add 351 records (322 → 673) | Kept: bias is the concept the search is about |
| P02k, P02m | Latin America: 1,185 records without block C, 33 with it | No separate Latin America search |
| P03a, P03b, P09 | Broad birth-record terms add 407 records outside block A; certificate-specific terms add 41 | S3 with certificate terms |
| P04, P13 | Marginal yield of further terms | Added: rate of visits, visit rate, visits per week, reverse causation, survival analysis, Proportional Hazards Models. Not added: confound* (689 records), Confounding Factors, Epidemiologic (38), Models, Statistical (940), person-time (none) |
| P07 | Spanish and Portuguese strings return 75, 32 and 2 OpenAlex records | Second OpenAlex search |
| P08 | Citing records of the seeds | Forward-chasing filters |
| P10e, P10g, P11c | The BVS portal and SciELO answer scripted requests with a security check or HTTP 403 | LILACS searched by browser navigation only |
| P11 | SciELO Search returned no results | SciELO not searched |
| P12 | Final strings, counts only | Sizes above |
| P14 | PubMed returns 979 distinct records for S1–S3, of which 10 are letters, editorials, comments or preprints | Letters, comments and editorials kept |
| P15 | Without the Mexico limit, prenatal care and a gestational outcome give 15,205 PubMed records; birth-certificate or vital-record studies outside the bias search, 3,700; systematic reviews outside it, 414 | Q4 kept to Mexico |
| P16 | Europe PMC: 927 of 948 records are MEDLINE records, and 19 of the other 21 are preprints. OpenAlex: 460 of 1,264 English records and 105 of 109 Spanish and Portuguese records have no PMID; among those without a PMID, 47 preprints, 63 theses, 44 conference items and 35 books, reports, datasets and other items. LILACS (S2): 52 of 57 records are articles | Europe PMC not searched; journal publications only, with the OpenAlex type filter |

## Running the search

- Each query runs once. Its source, exact string, exact request (API or portal URL), date and
  time in UTC and number of hits go to `literature_search/queries.csv`.
- PubMed: `esearch` with the history server, then `efetch` in XML. OpenAlex: cursor paging, 200
  records per page. LILACS: browser navigation, 100 records per page, reading the original
  abstract; the summaries the BVS portal marks as created by AI are ignored.
- OpenAlex runs without an API key, on a free daily budget shared by the IP address (USD 0.10,
  with USD 0.001 per search request, as its response headers stated on the pilot date). If the
  budget runs out, the run continues the next day and each query keeps its own date.
- The exact requests in `queries.csv` are the record of the run; no script is versioned.

## Records, de-duplication and verification

- `literature_search/records.csv` has one row per record: `id`, `sources`, `title`, `year`,
  `doi`, `pmid`, `source_id`, `stage`, `decision`, `reason`. `source_id` holds the LILACS or
  OpenAlex identifier.
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
- A record with neither DOI nor PMID, common in LILACS, is kept when its source identifier
  resolves to its record page.

## Screening

1. **Title and abstract**, by one screener. Each record is included, excluded with a code, or
   marked uncertain; an uncertain record goes forward.
2. **Full text** for every record that goes forward, where it is open access (PubMed Central or
   Europe PMC, the open-access location in OpenAlex, the LILACS link, the publisher). When no open
   full text is found and the abstract is enough to decide, the decision rests on the abstract and
   says so; otherwise the record is reported as not retrieved and listed.
3. Every exclusion has its code, with a note when the code alone does not explain it.
4. The single screener is the AI assistant (Claude Code) working in this repository. The author
   approved this protocol and re-screens a random sample of the exclusions blind.
5. **Blind re-screen.** When screening ends, 20 records are drawn from all excluded records with
   `random.Random(58).sample(sorted(ids), 20)` in Python; the seed, 58, is the number of the issue
   and was fixed before any record was screened. The author gets their title and abstract only,
   and the assistant's decisions are shown once the author's are recorded. Every disagreement is
   reported, and a record the author would include goes to full text.

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
| 2 | Multi-database searching | [Information sources](#information-sources): the BVS portal is restricted to LILACS |
| 3 | Study registries | None searched ([Information sources](#information-sources)) |
| 4 | Online resources and browsing | LILACS through its web interface ([Information sources](#information-sources)) |
| 5 | Citation searching | [Citation chasing](#citation-chasing) |
| 6 | Contacts | None ([Information sources](#information-sources)) |
| 7 | Other methods | [Seeds](#seeds) |
| 8 | Full search strategies | [Full query strings](#full-query-strings); `queries.csv` |
| 9 | Limits and restrictions | [Limits and filters](#limits-and-filters) |
| 10 | Search filters | None ([Limits and filters](#limits-and-filters)) |
| 11 | Prior work | None ([Limits and filters](#limits-and-filters)) |
| 12 | Updates | No update is planned before the submission of 20 November 2026 |
| 13 | Dates of searches | `queries.csv`, date and time of each query |
| 14 | Peer review | No search peer review; the author reviewed and approved the protocol |
| 15 | Total records | `queries.csv`; [PRISMA 2020 flow counts](#prisma-2020-flow-counts) |
| 16 | Deduplication | [Records, de-duplication and verification](#records-de-duplication-and-verification) |

### PRISMA 2020 flow counts

The counts follow the boxes of the PRISMA 2020 flow diagram (Page et al. 2021, Fig 1). Every
count comes from [`literature_search/records.csv`](literature_search/records.csv) and
[`literature_search/queries.csv`](literature_search/queries.csv); the raw responses stay in the
ignored `data/interim/`.

**Identification of studies via databases**

| Box | n | Detail |
|---|---:|---|
| Records identified | 2,314 | PubMed 1,009; OpenAlex in English 1,069; OpenAlex in Spanish and Portuguese 81; LILACS 155 (S1–S3) |
| Duplicate records removed | 676 | Within and across sources, by DOI, PMID and title |
| Records removed for other reasons | 0 | One DOI corrected from its source (R1593) and one PMID that does not resolve removed from its record (R0720), both records kept; five records whose DOI does not resolve kept by their OpenAlex identifier, which resolves (R1306, R1616, R1624, R1625, R1628) |
| Records screened | 1,638 | |
| Records excluded | 1,582 | E1 3, E2 71, E3 59, E4 1,031, E5 239, E6 172, E7 7 |
| Reports sought for retrieval | 56 | |
| Reports not retrieved | 20 | Listed under [What was not found](#what-was-not-found) |
| Reports assessed for eligibility | 36 | 22 on the full text; 11 on the abstract and 3 on the title alone (WIC programme records, E4), because no open full text was found and that was enough to decide |
| Reports excluded | 22 | E4 9, E6 13 |
| Studies included | 14 | |

**Identification of studies via other methods**

| Box | Seeds | Round 1 | Round 2 | Round 3 | Total |
|---|---:|---:|---:|---:|---:|
| Works chased | — | 16 | 11 | 2 | 29 |
| Records identified | 3 | 1,179 | 1,355 | 73 | 2,610 |
| Already found by the databases or an earlier round | 1 | 146 | 307 | 29 | 483 |
| Duplicates within the round | — | 421 | 452 | 16 | 889 |
| Removed for other reasons (no title) | — | 49 | 1 | 0 | 50 |
| Records screened | 2 | 563 | 595 | 28 | 1,188 |
| Records excluded | 1 | 535 | 580 | 22 | 1,138 |
| Reports sought for retrieval | 1 | 28 | 15 | 6 | 50 |
| Reports not retrieved | 0 | 14 | 10 | 3 | 27 |
| Reports assessed for eligibility | 1 | 14 | 5 | 3 | 23 |
| Reports excluded | 0 | 3 | 3 | 3 | 9 |
| Studies included | 1 | 11 | 2 | 0 | 14 |

- Round 1 chased the three seeds and the 13 other studies the databases included; round 2, the 11
  studies round 1 included; round 3, the two studies round 2 included. Round 3 included none, so
  chasing stopped.
- Records excluded at title and abstract, by code: seeds E4 1; round 1 E1 2, E2 59, E3 60, E4 265,
  E5 78, E6 63, E7 8; round 2 E2 47, E3 96, E4 383, E5 30, E6 24; round 3 E1 1, E2 3, E3 3, E4 11,
  E5 3, E6 1. Reports excluded on the full text: round 1 E6 3; round 2 E6 2, E7 1; round 3 E4 1,
  E5 1, E6 1.
- Round 1 holds 28 records from the reference list of R0760 in PubMed Central, for which OpenAlex
  and Europe PMC returned no references; two of them were duplicates found at screening (E7).

**Studies included in the review: 28**, each in one report: 14 via databases and 14 via other
methods.

## Planned limitations

- **Sources not covered.** Europe PMC as a search source, SciELO, Scopus, Web of Science, Embase
  and Google Scholar.
- **Journal publications only.** Preprints, theses and conference material are not eligible, so
  recent work posted only as a preprint is not found.
- **Languages.** English, Spanish and Portuguese only.
- **One screener.** An AI assistant screens every record; the author checks 20 random exclusions.
- **Abstract-level signals.** A study that mentions the bias only in its full text is found only
  when its title or abstract passes screening, so the grade "mentioned" is undercounted.
- **Interfaces.** OpenAlex matches a record without an abstract on its title only, and its types
  can be wrong. LILACS is searched through a web interface whose behaviour can change.
- **Full text.** Only where it is open access.

## Approval

The author reviewed protocol v1 on 2026-10-15 and approved it with these changes:

| Review point | Change in v2 |
|---|---|
| The Method row named the simulation only | The design table lists every method of [`roadmap.md` §1](roadmap.md#1-core-the-course-deliverable): the landmark cohorts and the APNCU adjustment are methods Q1 asks about |
| Publication types | Journal publications only: preprints, theses, conference material, books, reports and datasets are not eligible (P14, P16) |
| Q4 limited to Mexico | Kept, with the text stating that similar studies of any population enter through Q1 and Q3 (P15) |
| Number of sources | Europe PMC is no longer searched (P16a) and SciELO is dropped (P11); PubMed, OpenAlex in two language sets, LILACS and citation chasing remain |

The points listed in v1 for approval were approved as written, except the SciELO retry rule,
which lapsed with SciELO: birth weight in block B; block C beyond the task's six terms; no
separate Latin America search; S3; the Spanish and Portuguese OpenAlex search; the
forward-chasing threshold of 100 citing records and the filter of each seed; records without DOI
or PMID kept when their source identifier resolves; no versioned script; and the AI assistant as
the single screener with the author's blind re-screen.

## Results

PubMed and OpenAlex were searched on 2026-10-15 between 21:14 and 21:23 UTC, and LILACS between
21:23 UTC that day and 00:55 UTC on 2026-10-16. Citation chasing ran on 2026-10-16 in three rounds
(11:48–12:01, 16:25–16:27 and 16:43 UTC). Screening ended on 2026-10-16 at 16:46 UTC. It used the
design table under [Purpose](#purpose) and no result of the project.

Of the 28 included studies, 21 answer Q1, four of them also Q2; none answers Q3; seven answer Q4.
The tables give the extraction and the three closeness axes of
[Data extraction](#data-extraction). Where none of the six methods fits, the method is written as
"other" with what the study did. "abstract" in the locator column means the decision rests on the
abstract, because no open full text was found.

**Q1 and Q2 (21 studies)**

| ID | Study | Data | Bias | Method | Grade | Locator |
|---|---|---|---|---|---|---|
| C2-0004 | Shwartz & Vinyard 1965 | other: District of Columbia birth certificates, 1960 | truncation | landmark or time-dependent: modified life table over the gestation intervals under 28, 28–35 and 36 weeks or more, on the women still pregnant and their women-weeks of care | addressed | pp. 237–238, Table 1; p. 248 |
| C1-0210 | Terris & Glasser 1974 | other: New York City birth certificates, 1961 | truncation | landmark or time-dependent: life table of the month of the first visit, censored at delivery | quantified | p. 870; Table 7, p. 872 |
| C1-0078 | Gortmaker 1979 | other: New York City birth and infant death records, 1968 | truncation | index adjustment | addressed | p. 654 |
| R0238 | Showstack et al. 1984 | other: California birth certificates, 1978 | truncation | index adjustment | addressed | p. 1006, footnote; Tables 4–5 |
| R1637 | Goldberg et al. 1984 | other Latin American: Cali, Colombia, interviews and clinical records, 1981 | truncation | other: visits per month of pregnancy | addressed | p. 157 |
| C1-0242 | Kramer 1987 | other: review of 895 papers, 1970–1984 | truncation | landmark or time-dependent: life tables recommended | addressed | p. 715 |
| R0548 | Tyson et al. 1990 | other: 28,838 deliveries at Parkland Memorial Hospital, Dallas | truncation | landmark or time-dependent: cohorts reaching weeks 26, 30, 34, 38 and 42, with care status by that week | addressed | abstract |
| R0809 | Malloy et al. 1992 | other: Missouri linked birth and death certificates, 1980–1984 | truncation | other: outcome conditioned on the gestational age at delivery | addressed | p. 448; Tables 1–2 |
| R1167 | Kotelchuck 1994a | other: US 1980 National Natality Survey | related dependence | index adjustment | quantified | pp. 1415–1416, Table 5; p. 1417 |
| C1-0002 | Kotelchuck 1994b | other: US 1980 National Natality Survey | truncation | index adjustment | mentioned | p. 1487 |
| C2-0020 | Wise 1994 | other: editorial, no data | related dependence | none | mentioned | p. 1374 |
| C1-0003 | Alexander & Kotelchuck 1996 | other: South Carolina birth files, 1989–1991 | related dependence | index adjustment: five indices compared by gestational-age group | quantified | p. 413, Figure 2; p. 414 |
| R0153 | Koroukian & Rimm 2002 | other: Ohio birth certificates, 1993–1996 | truncation | index adjustment, with a gestational age-specific analysis | quantified | abstract |
| R1366 | Ying 2002 | other: US 1988 National Maternal and Infant Health Survey | truncation | none | mentioned | abstract |
| C1-0024 | Heaman et al. 2008 | other: Winnipeg linked mother-baby and physician claims, 1991–2000 | related dependence | other: analysis by gestational-age category | addressed | Discussion; Conclusion |
| R0333 | Bloch et al. 2009 | other: US nested case-control study of preterm births, 367 mothers | truncation | index adjustment: two indices compared among preterm births | mentioned | abstract |
| C1-0031 | Wehby et al. 2009 | other Latin American: ECLAMC hospital samples, Brazil | truncation | other: preterm birth analysed only with the delay of the first visit | addressed | Methods, study variables |
| C1-0055 | VanderWeele et al. 2013 | other: US linked birth and infant death cohort, 2003 | related dependence | index adjustment | mentioned | Methods, APNCU categories |
| R1306 | Balsa & Triunfo 2015 | other Latin American: Pereira Rossell maternity hospital, Montevideo, 1995–2011 | truncation | index adjustment: preterm births rated against the visits due by their week | addressed | §4.1 and note 7; §3 |
| C1-0041 | Shin & Song 2019 | other: US PRAMS, 2004–2011 | truncation | index adjustment | mentioned | Discussion |
| R0760 | Coelho et al. 2026 | other Latin American: SINASC live-birth records, Central-West Brazil, 2015–2024 | truncation | other: sensitivity analysis replacing the visit count with first-trimester initiation | addressed | Methods, Sensitivity Analyses; Results |

**Q4 (7 studies)**

| ID | Study | Data | Care measure | Outcome | Truncation | Locator |
|---|---|---|---|---|---|---|
| R0114 | Guendelman et al. 2015 | SINAC in other years: 2009, with California certificates | trimester in which care began (covariate) | preterm delivery | not mentioned | Methods, Variables; Table 2 |
| R0152 | Hamilton & Choi 2015 | SINAC in other years: 2008–2009 | trimester of first care against none (control) | birth weight | not mentioned | §3.4; Tables 2–4 |
| R0527 | Ancira-Moreno et al. 2021 | SINAC in other years: 2008–2017 | any care; trimester of the first visit | low birth weight | not mentioned | Table 2 |
| R0542 | Suárez-Idueta et al. 2021 | SINAC in other years: 2017 | trimester of the first contact; number of visits | small for gestational age | not mentioned | Results; table of care by trimester and visits |
| C1-0265 | Avendaño-Alvarez et al. 2022 | SINAC 2020–2023: 2020 | any care; number of visits | macrosomia (4,000 g or more) | not mentioned | Table 3 |
| R0625 | Hayer et al. 2024 | SINAC in other years: 2008–2019, mothers aged 10–24 | adequate care | preterm birth and other perinatal outcomes | not assessed (abstract only) | abstract |
| C1-0268 | Hamilton & Alcay 2025 | SINAC in other years: 2015–2019, with US records | number of visits (covariate) | low birth weight | not mentioned | Tables 2 and 5 |

### What is known, per question

**Q1.** The included studies describe, address or quantify the dependence of the care measure on
the length of gestation from 1965 to 2026, with four groups of means:

- *Exposure time.* Shwartz & Vinyard 1965 (C2-0004) note that only the women still pregnant at
  the start of each gestation interval can begin care in it, and build a modified life table on
  them and on their women-weeks of care (pp. 237–238, Table 1). Terris & Glasser 1974 (C1-0210)
  put the month of the first visit in a life table censored at delivery: the share of premature
  against mature births without care, 20% against 8% when crude, is 11.0% against 9.6% in the
  life table by months 8–9 (p. 870; Table 7, p. 872). Kramer 1987 (C1-0242) names the
  "prematurity artefact" in a methodological assessment of 895 papers and recommends life tables
  (p. 715). Tyson et al. 1990 (R0548) compare care in cohorts reaching weeks 26, 30, 34, 38 and
  42 (abstract). Malloy et al. 1992 (R0809) condition the outcome on the gestational age at
  delivery (p. 448; Tables 1–2).
- *The index.* Gortmaker 1979 (C1-0078) controls the length of gestation in the construction of the
  index (p. 654), and Showstack et al. 1984 (R0238) define adequacy relative to it so that the
  visit count does not stand for the length of gestation (p. 1006, footnote). Kotelchuck 1994a
  (R1167) shows that the Kessner rating rises with the week of delivery beyond 36 because its
  requirement stops at nine visits (pp. 1415–1416, Table 5), and bases APNCU on the visits expected
  for the gestational age at the start of care and at delivery (p. 1417). Alexander & Kotelchuck
  1996 (C1-0003) compare five indices by gestational-age group: APNCU puts over 40% of births at
  20–32 and at 33–36 weeks in its intensive category, against under 5% with GINDEX (p. 413, Figure
  2; p. 414). Koroukian & Rimm 2002 (R0153) report that a shorter gestation lowers the visits APNCU
  expects, so that 61.2% of preterm and 18.9% of term births are rated Adequate Plus, and advise
  against APNCU for studies of low birth weight (abstract). Balsa & Triunfo 2015 (R1306) rate
  preterm births against the visits due by their week (§4.1 and note 7).
- *Another measure or a stratified analysis.* Goldberg et al. 1984 (R1637) count visits per month
  of pregnancy to correct for the variation in the duration of gestation (p. 157). Wehby et al.
  2009 (C1-0031) estimate the effect on preterm birth only for the delay of the first visit,
  which they describe as less affected by gestational age (Methods). Heaman et al. 2008 (C1-0024)
  analyse by gestational-age category and report associations of opposite sign with APNCU and
  R-GINDEX (Discussion). In Coelho et al. 2026 (R0760) the Indigenous odds ratio of preterm birth
  is 1.540 when care enters as first-trimester initiation and 1.337 when it enters as the visit
  count, which the authors read as reverse causation (Results).
- *Statement only.* Kotelchuck 1994b (C1-0002, p. 1487), Wise 1994 (C2-0020, p. 1374), Ying 2002
  (R1366, abstract), Bloch et al. 2009 (R0333, abstract), VanderWeele et al. 2013 (C1-0055,
  Methods) and Shin & Song 2019 (C1-0041, Discussion).

Grades: 4 quantified, 11 addressed, 6 mentioned. Four of the 21 rest on the abstract: R0153,
R0548, R0333 and R1366.

**Q2.** Four Q1 studies use Latin American data: Goldberg et al. 1984 (Cali, Colombia), Wehby et
al. 2009 (ECLAMC hospitals, Brazil), Balsa & Triunfo 2015 (Montevideo, Uruguay) and Coelho et al.
2026 (SINASC, Central-West Brazil). None uses Mexican data.

**Q3.** No included study.

**Q4.** Seven studies of Mexican birth certificates, 2008 to 2020, relate a care measure to a
gestational outcome or birth weight. They measure care as any care, the trimester of the first
visit or contact, the number of visits, or adequate care, and the outcomes are preterm birth, low
birth weight, birth weight, small for gestational age and macrosomia. In five of them care is a
covariate or a descriptive category. None of the six read in full mentions the dependence of the
care measure on the length of gestation; the seventh, Hayer et al. 2024 (R0625), was assessed on
its abstract only.

### What was not found

- **Q3.** No study meeting Q3 (a simulation of visits under a schedule, or an analytic
  expectation, of the association that care without effect on gestation would produce, reported
  as the size of the bias or set against an observed association) was found in PubMed, OpenAlex
  (English; Spanish and Portuguese) and LILACS, searched on 2026-10-15 and 2026-10-16, or in the
  three rounds of citation chasing in OpenAlex and Europe PMC on 2026-10-16. Two simulation studies
  found by citation chasing were excluded as E4 because they simulate no care measure: a
  left-truncation simulation of smoking and preeclampsia (C2-0387) and a collider-stratification
  simulation of the birthweight paradox (C2-0388).
- **Q2, Mexico.** No study meeting Q1 with data collected in Mexico was found in the same sources
  on the same dates. Three Mexican hospital studies read in full keep term births only, as an
  inclusion criterion and not as an answer to the dependence (R0008, R1224, R1466; E6).
- **Q4.** No study of Mexican birth certificates that mentions, addresses or quantifies the
  dependence was found in the same sources on the same dates, among the six read in full.
- **Q1 with SINAC.** No study meeting Q1 with SINAC data of any year was found in the same
  sources on the same dates.

These statements hold for the reports that were read. The 47 reports not retrieved are in
`records.csv` with the decision "not retrieved" and the reason. Those whose abstract or title
bears on a question:

- Mexican data (Q2, Q4): R0121 (Mexico City hospital, 1984, visits judged against gestational
  age), R0589 (Mexican births 2008–2019), R0145, R0349, R1375 and R0023.
- Care measures adjusted for gestation, or the bias named (Q1): R0330, R0790 and R1355 (letter and
  reply on Koroukian & Rimm 2002), R0805, C1-0014, C1-0034, C1-0079 (origin of GINDEX), C1-0219,
  C1-0220, C1-0223, C2-0002 (Terris & Gold 1969), C2-0271, C3-0001 (Shwartz 1962, the method
  source of C2-0004) and C2-0106.
- Seven had an open copy behind a publisher security check, a download check or a bot check,
  which was not bypassed: R0121, R0589, R1159, R1166, C1-0223, C1-0371 and C1-0451; R0625 is
  included on its abstract for the same reason.

### Closeness of the closest studies to this project

On the three axes of [Data extraction](#data-extraction), without judging value:

- **Data.** No Q1 study uses SINAC or other Mexican data; four use other Latin American data and
  17 other data. Among the Q4 studies, one uses SINAC 2020 (C1-0265) and six SINAC in other
  years, and none is graded above "not mentioned".
- **Bias.** 16 of the 21 Q1 studies describe the truncation of the visit measure itself; five
  describe a related dependence, the rating that an index gives a birth according to its
  gestational age (R1167, C2-0020, C1-0003, C1-0024, C1-0055).
- **Method.** Landmark or time-dependent design 4 (C2-0004, C1-0210, C1-0242, R0548); index
  adjustment 10; other 5 (R1637, R0809, C1-0024, C1-0031, R0760); none 2. No study uses a null
  simulation on a schedule, another simulation or an analytic expectation.
- **Two axes at once.** Truncation with a landmark or time-dependent design: C2-0004 and C1-0210
  (prematurity, 1960 and 1961 certificates), C1-0242 (a review) and R0548 (cohorts by week of
  gestation, perinatal mortality and morbidity, one hospital). Truncation with Latin American
  data: R1637, C1-0031, R1306 and R0760; R0760 uses national live-birth records and preterm
  birth. The bias of APNCU quantified: R0153 (low birth weight) and C1-0003 (by gestational-age
  group). SINAC data with a care measure and a gestational outcome: the seven Q4 studies, with
  truncation not mentioned in the six read in full.

### Blind re-screen

The 20 records drawn with `random.Random(58).sample(sorted(ids), 20)` from the 2,751 excluded
records are R1262, C2-0282, C2-0317, R1518, C2-0298, C1-0182, C2-0262, R0714, R0530, R0312,
R0035, C2-0541, R0717, R1409, R0588, R0017, R1258, C1-0453, C1-0062 and R0885. PENDING: the
author's decisions, then every disagreement.

### Deviations from the protocol

- **R0760's references.** OpenAlex and Europe PMC returned no references for R0760, so its
  reference list was read in PubMed Central and the 28 references with a DOI or PMID were looked
  up in OpenAlex (round 1).
- **LILACS** records were screened at title and abstract while they were read in the portal, on
  2026-10-15 and 2026-10-16, and each decision was carried to the de-duplicated record. No record
  received two different decisions.
- **Chasing candidates without a title** (50) were removed before screening, as records that are
  not reports (E2's definition).
- **Letters.** Four letters of round 2 were first coded E2 and then recoded by their topic (E3 1,
  E4 3), because the protocol keeps letters; no other letter, comment or editorial was coded E2.
- **Q4 grade.** R0625 is graded "not assessed", a value the protocol does not list, because its
  full text was not retrieved.
- **Method axis.** "other", with what the study did, was added for the five studies that none of
  the six methods describes.
- **Metadata.** C1-0003 is dated 1996, from PubMed, instead of the 2020 that OpenAlex gives its
  repository copy.

## Limitations

- **Sources not covered.** Europe PMC as a search source, SciELO, Scopus, Web of Science, Embase
  and Google Scholar. The two earliest included studies were found by citation chasing, not by
  the database searches.
- **Journal publications only.** Preprints, theses and conference material were not eligible.
- **Languages.** English, Spanish and Portuguese only; six records were excluded for language
  (E1).
- **One screener.** The AI assistant screened every record; the author's blind re-screen of 20
  exclusions is pending.
- **Abstract-level signals.** A study that names the bias only in its full text passes title and
  abstract screening only through other signals, so "mentioned" is undercounted.
- **Full text.** 47 of the 106 reports sought were not retrieved, 29 of them published before
  2000. Four Q1 inclusions and one Q4 inclusion rest on the abstract, among them Koroukian & Rimm
  2002, the closest study known before the search. Scanned articles were
  read as page images from PubMed Central.
- **Programmes.** The literature on prenatal WIC participation that names a "gestational age
  bias" and handles it by gestational-age strata or the length of gestation (R0077, R0863, R0864,
  R0965) was excluded as E4, because a programme is not a measure of care use under the
  protocol.
- **Interfaces.** OpenAlex dated one repository copy wrongly (C1-0003) and listed some reference
  entries without identifiers; the BVS portal was read through a browser.

## References

- Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement: an updated guideline for
  reporting systematic reviews. *BMJ.* 2021:n71. doi:10.1136/bmj.n71
- Rethlefsen ML, Kirtley S, Waffenschmidt S, et al. PRISMA-S: an extension to the PRISMA Statement
  for Reporting Literature Searches in Systematic Reviews. *Syst Rev.* 2021;10:39.
  doi:10.1186/s13643-020-01542-z
- The seeds are listed under [Seeds](#seeds).

### Included studies

Authors, journal, volume and pages from PubMed `esummary`, or from OpenAlex for the three records
without a PMID. Every PMID resolves in PubMed and every DOI in Crossref or the DOI handle service,
except that of R1306, which is kept by its OpenAlex identifier (W1554081760).

- **C2-0004** · Shwartz S, Vinyard JH Jr. Prenatal Care and Prematurity. *Public Health Rep.* 1965;80(3):237-48. PMID 14265437; doi:10.2307/4592391
- **C1-0210** · Terris M, Glasser M. A life table analysis of the relation of prenatal care to prematurity. *Am J Public Health.* 1974;64(9):869-75. PMID 4420443; doi:10.2105/ajph.64.9.869
- **C1-0078** · Gortmaker SL. The effects of prenatal care upon the health of the newborn. *Am J Public Health.* 1979;69(7):653-60. PMID 453391; doi:10.2105/ajph.69.7.653
- **R1637** · Goldberg MB, Guerrero R, Muñoz Á. Mortalidad neonatal temprana en Cali. Un estudio de casos y controles. *Colombia Médica.* 1984;15(4):156–160. doi:10.25100/cm.v15i.4.2500
- **R0238** · Showstack JA, Budetti PP, Minkler D. Factors associated with birthweight: an exploration of the roles of prenatal care and length of gestation. *Am J Public Health.* 1984;74(9):1003-8. PMID 6465400; doi:10.2105/ajph.74.9.1003
- **C1-0242** · Kramer MS. Determinants of low birth weight: methodological assessment and meta-analysis. *Bull World Health Organ.* 1987;65(5):663-737. PMID 3322602
- **R0548** · Tyson J, Guzick D, Rosenfeld CR, et al. Prenatal care evaluation and cohort analyses. *Pediatrics.* 1990;85(2):195-204. PMID 2296507; doi:10.1542/peds.85.2.195
- **R0809** · Malloy MH, Kao TC, Lee YJ. Analyzing the effect of prenatal care on pregnancy outcome: a conditional approach. *Am J Public Health.* 1992;82(3):448-50. PMID 1536367; doi:10.2105/ajph.82.3.448
- **R1167** · Kotelchuck M. An evaluation of the Kessner Adequacy of Prenatal Care Index and a proposed Adequacy of Prenatal Care Utilization Index. *Am J Public Health.* 1994;84(9):1414-20. PMID 8092364; doi:10.2105/ajph.84.9.1414
- **C1-0002** · Kotelchuck M. The Adequacy of Prenatal Care Utilization Index: its US distribution and association with low birthweight. *Am J Public Health.* 1994;84(9):1486-9. PMID 8092377; doi:10.2105/ajph.84.9.1486
- **C2-0020** · Wise PH. What you measure is what you get: prenatal care and women's health. *Am J Public Health.* 1994;84(9):1374-5. PMID 8092356; doi:10.2105/ajph.84.9.1374
- **C1-0003** · Alexander GR, Kotelchuck M. Quantifying the adequacy of prenatal care: a comparison of indices. *Public Health Rep.* 1996;111(5):408-18; discussion 419. PMID 8837629
- **R0153** · Koroukian SM, Rimm AA. The "Adequacy of Prenatal Care Utilization" (APNCU) index to study low birth weight: is the index biased? *J Clin Epidemiol.* 2002;55(3):296-305. PMID 11864801; doi:10.1016/s0895-4356(01)00471-1
- **R1366** · Ying JC. Content of Prenatal Care and Spontaneous Preterm Birth. *PanPacific Management Review.* 2002;5(2):143–153. doi:10.30166/ppmr.200207.0003
- **C1-0024** · Heaman MI, Newburn-Cook CV, Green CG, et al. Inadequate prenatal care and its association with adverse pregnancy outcomes: A comparison of indices. *BMC Pregnancy Childbirth.* 2008;8:15. PMID 18452623; doi:10.1186/1471-2393-8-15
- **R0333** · Bloch JR, Dawley K, Suplee PD. Application of the Kessner and Kotelchuck prenatal care adequacy indices in a preterm birth population. *Public Health Nurs.* 2009;26(5):449-59. PMID 19706128; doi:10.1111/j.1525-1446.2009.00803.x
- **C1-0031** · Wehby GL, Murray JC, Castilla EE, et al. Prenatal care effectiveness and utilization in Brazil. *Health Policy Plan.* 2009;24(3):175-88. PMID 19282483; doi:10.1093/heapol/czp005
- **C1-0055** · VanderWeele TJ, Lauderdale DS, Lantos JD. Medically induced preterm birth and the associations between prenatal care and infant mortality. *Ann Epidemiol.* 2013;23(7):435-40. PMID 23726822; doi:10.1016/j.annepidem.2013.04.010
- **R1306** · Balsa AI, Triunfo P. THE EFFECTIVENESS OF PRENATAL CARE IN URUGUAY’S LOW-INCOME POPULATION: A PANEL DATA APPROACH. *Latin American Journal of Economics.* 2015;52(2):149–183. doi:10.7764/laje.52.2.149
- **R0114** · Guendelman S, Thornton D, Perez-Cuevas R, et al. Preterm delivery among first-time Mexico-born mothers: a binational population-based comparison of deliveries in California and Mexico. *J Epidemiol Community Health.* 2015;69(1):35-40. PMID 25210076; doi:10.1136/jech-2014-204020
- **R0152** · Hamilton ER, Choi KH. The mixed effects of migration: community-level migration and birthweight in Mexico. *Soc Sci Med.* 2015;132:278-86. PMID 25174770; doi:10.1016/j.socscimed.2014.08.031
- **C1-0041** · Shin D, Song WO. Influence of the Adequacy of the Prenatal Care Utilization Index on Small-For-Gestational-Age Infants and Preterm Births in the United States. *J Clin Med.* 2019;8(6):838. PMID 31212823; doi:10.3390/jcm8060838
- **R0527** · Ancira-Moreno M, Monterrubio-Flores E, Hernández-Cordero S, et al. Incidence of low birth weight in Mexico: A descriptive retrospective study from 2008-2017. *PLoS One.* 2021;16(9):e0256518. PMID 34506506; doi:10.1371/journal.pone.0256518
- **R0542** · Suárez-Idueta L, Bedford HE, Ohuma EO, et al. Maternal Risk Factors for Small-for-Gestational-Age Newborns in Mexico: Analysis of a Nationwide Representative Cohort. *Front Public Health.* 2021;9:707078. PMID 35004559; doi:10.3389/fpubh.2021.707078
- **C1-0265** · Avendaño-Alvarez F, Monterrubio-Flores E, Omaña-Guzmán I, et al. Incidence of macrosomia in Mexico: National and subnational estimations. *PLoS One.* 2022;17(12):e0276518. PMID 36459523; doi:10.1371/journal.pone.0276518
- **R0625** · Hayer S, Fuentes-Rivera E, Schiavon R, et al. Prenatal care utilization and perinatal outcomes among pregnant adolescents in Mexico, 2008-2019. *Int J Gynaecol Obstet.* 2024;165(3):1047-1055. PMID 38180117; doi:10.1002/ijgo.15303
- **C1-0268** · Hamilton ER, Alcay S. Immigrant Health Advantage? The Birth Outcomes of U.S.-Born Women in Mexico and Mexican-Origin Women in the United States. *J Health Soc Behav.* 2025;66(4):452-469. PMID 40590346; doi:10.1177/00221465251343322
- **R0760** · Coelho G, Charles CM, Pacagnella RC, et al. Racial inequalities in preterm birth in Central-West Brazil, 2015-2024: a population-based cross-sectional study. *Rev Saude Publica.* 2026;60:e44. PMID 42848685; doi:10.11606/s1518-8787.2026060007625
