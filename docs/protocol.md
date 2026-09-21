# Protocol

The question, the data and the methods of the study. The question is stated in
[`proposal_v2.md`](proposal_v2.md); scope changes against it are listed in
[`roadmap.md`](roadmap.md) and argued in [`decisions.md`](decisions.md).

**Draft.** Only the data source and the study period are written. The population, the outcome,
the exposure measures, the base cohort and its attrition, the covariate set (D-007) and the
limitations are PENDING (issue #9).

## Data source

SINAC birth records published by SSA/DGIS as open data, one ZIP per year (D-001). Every file the
project uses is declared in [`../config/sources.yml`](../config/sources.yml) with its URL, its
published version and its sha256, and what each file contains, and how the two catalogue periods
differ, is measured in [`source_inventory.md`](source_inventory.md). The files are served over
HTTP without TLS: the sha256 detects a later change to a file, it does not authenticate the first
download.

### Study period: 2020–2023

| Year | Records | Descriptor | Catalogues |
|---|---|---|---|
| 2020 | 1,747,847 | 2020–2025 | 2020–2023 |
| 2021 | 1,639,479 | 2020–2025 | 2020–2023 |
| 2022 | 1,622,921 | 2020–2025 | 2020–2023 |
| 2023 | 1,521,280 | 2020–2025 | 2020–2023 |
| **Total** | **6,531,527** | | |

Records are the rows of each year's CSV, as measured in the source inventory (table 1). The four
years are one catalogue period: one descriptor, one catalogue set, and CSV headers identical in
names and order. Development and milestone `v0.1-cohort` run on 2023 alone (D-009). Every
pipeline step that reads records takes `--years`, whose default is this period.

**This is a scope change against proposal v2, which committed to 2019–2023 (D-041).** Nothing in
the question needs a pre-pandemic year. Truncation of the gestational window operates within
each pregnancy, in any calendar year. Neither the comparison of the four measures nor the null
simulation depends on the calendar.

Adding 2019 would add 1,868,214 records, at a cost the source inventory measures:

- 74 of its 76 variables are renamed, and the file has another format (LF line endings, no
  quoting) and carries free-text fields.
- DGIS publishes no descriptor for 2015–2019, so the meaning of every 2019 variable rests on
  sources that describe the layout but not that year.
- Maternal education needs a crosswalk with information loss, because the two code systems share
  only `88` and `99`.
- Insurance needs a rule to collapse `DERHAB` and `DERHAB2` into `AFILIACION`.
- Three missing-value codes change role between the periods (`00`, `88`, `99`).

None of these code changes falls on an exposure or the outcome. The project uses eight coded
variables:

- Five change their valid categories: education, insurance, pregnancy multiplicity, newborn sex
  and CLUES.
- Two change only missing-value or peripheral codes: prenatal care received and state.
- The trimester of the first visit keeps all six codes.

Total visits and gestational age have no catalogue in either period. One risk of 2019 does touch
the outcome, and it was not measured. For 2015–2019 DGIS publishes an acceptable range of 13 to
42 weeks for `GESTACH`; for 2020–2023 it publishes only sentinel values. Whether that range was
enforced at capture is unknown.

Restricting the period to 2023 alone was also rejected. 2020–2022 share the format, descriptor
and catalogues of 2023, so they cost no harmonisation. Without them, the year covariate and the
COVID-19 sensitivity axis of the proposal disappear.

### Year of birth

Year of birth enters the analysis in two ways, which answer different questions (D-049):

- **As a categorical covariate** in the adjusted odds ratios. It absorbs differences in level
  between years, in prenatal care and in preterm birth alike. It is categorical rather than
  linear because the pandemic is a shock, not a trend.
- **As the COVID-19 sensitivity axis.** The estimates on 2020–2023 are set against the same
  estimates on 2022–2023 (`--years 2022,2023`), for measures (a) and (c) (D-003). Because the
  period starts in 2020, this sets years of acute disruption against years of recovery, not
  against a pre-pandemic baseline.

### What the period does not allow

- **No pre-pandemic reference.** The secular trend and the effect of the pandemic cannot be told
  apart.
- **2022–2023 is not a baseline.** The health system changed inside the period, as the 2020–2023
  insurance catalogue itself records ("SEGURO POPULAR / INSABI", "IMSS BIENESTAR").
- **Year of birth is a coarse proxy for exposure to the pandemic.** What matters is the window of
  each pregnancy, not the year of the birth. A birth in January 2020 had its prenatal care before
  the pandemic, and a birth in January 2022 had it in 2021.
- **Comparability with the literature is limited by the data, not by the length of the period.**
  The study that showed the APNCU bias used a single state registry (591,403 births in Ohio;
  Koroukian and Rimm, 2002), and 2023 alone holds 1,521,280 records. What limits comparability is
  already stated in the proposal:
  - SINAC records the trimester of the first visit, not the month, so APNCU is approximated.
  - The visit count is declared on the certificate.
  - The health system is a different one.

### Reversal criterion

The decision is reversed only by adding 2019, and only under D-050:

- `v0.2-progress` has been tagged with all of its committed content.
- 2019 then gets a timebox of one week of the budget (6 hours) before work on `v1.0` starts.
- If it does not close within the timebox, 2019 moves to future work.

To keep that cost to the harmonisation itself, the ETL reads each catalogue period through its
own adapter, which maps source column names to canonical names. It also registers each period's
codes as a source vocabulary of its own in `source_to_concept_map`. Adding 2019 then means an
adapter, mapping rows and the 2019 part of the data dictionary, and no change to cohort or
analysis code.
