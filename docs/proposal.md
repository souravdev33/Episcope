# EpiScope proposal (draft)

## Problem and stakeholders

EpiScope is a teaching prototype for turning district-level surveillance signals into reviewable warnings, short-range planning estimates and an illustrative supply plan. It serves Ministry planners, surveillance analysts, district officers and hospital managers. Patients and privacy regulators require that direct identifiers never appear in outputs and that small counts cannot identify people.

## Conflicts and decisions

**C1 sensitivity vs. false alarms:** the initial detector flags weekly counts above the trailing eight-week mean by 2.5 standard deviations. This is only a starting threshold; it has not been tuned or evaluated against independent truth. A future backtest should sweep thresholds and report sensitivity, false alerts per district-year and detection delay, including reporting-completeness adjustment.

**C2 detail vs. privacy:** outputs are district-week aggregates; counts 1–4 are suppressed. A production release must also suppress complementary totals and avoid combinations that permit subtraction. Upazila outputs are not included.

**C3 efficiency vs. equity:** the prototype reserves a 15% population-proportional component in its heuristic stock recommendation, then weights unmet needs toward demand and selected hill districts. The budget curve must be evaluated against proportional allocation before policy use. This is not yet a solved linear programme.

**C4 freshness vs. cost:** daily batch is sufficient for weekly district planning on a student laptop. It does not meet the optional five-minute streaming target.

**C5 accuracy vs. interpretability:** a trailing mean/z-score flag and seasonal-naive blend are transparent baselines. They are not demonstrated to outperform alternatives and do not use weather covariates in this draft.

## Architecture and tools

Python seeded generator → Spark local batch validation / de-identification → Parquet medallion directories → aggregated JSON → D3 v7 dashboard. Spark is chosen for the required distributed transformation interface and local mode supports student laptops. The default local file lake simplifies reproducible coursework; MinIO is included as an optional storage service but is not wired into the batch path. Streaming and Delta/Iceberg are deferred.

## Team roles and risks

The brief states a three-person team, but four names were provided. Proposed work split pending instructor approval: Sourav—problem analysis and quality; Aritra—generator and pipeline; Sakib—analytics and evaluation; Noha—serving, dashboard and policy. Everyone should review and contribute outside their lead area. Risk register: synthetic realism is weak; late/corrected reports distort weeks; small-cell combinations may leak counts; local storage may not scale; thresholds may create alert fatigue; generated results may be mistaken for official estimates. Mitigations: prominent synthetic labels, reproducible seed, quarantine, limited aggregation, threshold review, and group-run evidence before submission.

**Data provenance:** the current generator creates synthetic records and synthetic population denominators. It does not yet fetch/cite real BBS/WorldPop population, geoboundaries or Open-Meteo weather. These must be acquired with source/licence metadata before claiming those requirements complete.
