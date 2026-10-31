# EpiScope: Big Data Surveillance, Forecasting and Response Planning

**CSE 4345 · Complex Engineering Problem · Draft technical report**  
**Members:** Sourav; Aritra; Sakib; Noha (student IDs and signatures to be added)  
**Repository:** [add repository URL] · **Video:** [add accessible link]

> Draft generated from the assignment brief. This is not a finished IEEE PDF. Replace with evidence from the group’s own runs and user evaluation. Do not submit unverified claims as results.

## Abstract

This draft describes a laptop-oriented prototype for district-level disease surveillance. A deterministic synthetic generator creates encounter and facility inputs. A PySpark batch pipeline stores bronze data and produces de-identified silver and district-week gold Parquet outputs, with invalid rows quarantined. The analytics stage creates transparent baseline flags and short-range projections, and exports aggregated data to a D3 dashboard. An opt-in acquisition module now retrieves geoBoundaries ADM2 geometry, WorldPop 2022 population age/sex estimates, and Open-Meteo historical weather, then carries district weather into weekly gold data and the forecast prototype. The download still needs to be run and archived as project evidence. Weather-aware accuracy, rigorous ground-truth evaluation, an LP solver, scaling evidence and a recorded user study remain incomplete; no performance result is claimed.

## 1. Problem and stakeholder analysis

The client needs early district signals, one-to-four-week planning, limited stock allocation and seasonal preparedness despite incomplete/late reports, constrained compute and privacy needs. Policymakers need defensible national comparisons; surveillance staff need interpretable alerts; district officers and hospitals need local forecasts; patients need protection from exposure or stigma. A wrong alert can waste response resources, while a missed signal can delay response.

## 2. CEP attributes P1–P7 and conflicts C1–C5

P1 is addressed through Spark, Parquet, data-quality rules, baseline epidemiology and coordinated D3 views. P2 appears in alert threshold, suppression and allocation-floor choices. P3 requires comparison against baselines; this draft has not completed that evaluation. P4 is addressed partly by delayed report dates, quarantine and duplicate IDs, but backfill/silence effects are not yet convincingly modeled. P5 requires domain judgement in the prototype’s privacy boundary and resource plan. P6 is represented in the dashboard’s national/district selection and policy brief. P7 is reflected in bronze → silver → gold → analytics → serving dependencies.

C1 uses a transparent 2.5-standard-deviation flag as an initial operating point; threshold trade-off curves must be generated from a held-out truth table before conclusions. C2 suppresses counts 1–4 in district-week exports, but complementary suppression needs stronger implementation before public use. C3 uses an illustrative population floor and demand weighting; the present heuristic must be replaced with a linear programme and evaluated at five budgets. C4 chooses daily batch for weekly planning; it does not satisfy the optional near-real-time target. C5 favors a readable baseline; no claim of superior accuracy is justified.

## 3. Architecture and design

The generator writes CSV/JSON. The pipeline appends raw encounter files to bronze, uses Spark transformations and a facility broadcast join, de-identifies into silver and groups by district/disease/epi-week in gold. Parquet is partitioned by year/week. Aggregated JSON feeds five coordinated dashboard views and a data-quality panel. The design uses local Parquet for low setup cost. MinIO is scaffolded in Docker Compose but must be connected to the pipeline for S-tier object-store compliance. No streaming or ACID table format is implemented.

## 4. Data, quality, lineage and privacy

S4-S6 inputs remain synthetic: 640 fictional facilities, seeded encounters and stocks, seasonal disease patterns, location weighting, injected event windows and a delayed-report episode. In public-data mode the generator replaces synthetic population denominators with WorldPop district estimates and samples district, age band and sex in proportion to those estimates. The pipeline applies checks for null identifiers, age/sex/ICD ranges, facility references, date ordering, district geography, binary flags and duplicate encounter IDs. Invalid rows receive reason codes and are written to quarantine. Silver removes direct patient IDs and stores a salted SHA-256 digest; salt is read from an environment variable. Weekly gold groups include source batch identifiers. The optional S1-S3 acquisition retrieves simplified ADM2 boundaries from geoBoundaries, 2022 age/sex population estimates from WorldPop Global2, and daily 2021-2025 precipitation, temperature and humidity from Open-Meteo ERA5-Land at district centroids. Source URLs, licence notes, retrieval time and SHA-256 checksums are saved with the cached references. The synthetic generator can use the downloaded population denominators and age/sex distribution. WorldPop is a modelled population source, not official BBS counts. The team must run the public-data mode and preserve its logs/metadata as evidence. Privacy outputs must be audited for complementary disclosure.

## 5. Analytics methods

The alert baseline uses the previous eight weeks’ mean and standard deviation, with a 2.5 z-score trigger. When public weather data is present, the forecast prototype fits per-district ridge regression using prior cases plus four-week rainfall/humidity and six-week temperature lags; without S3 it falls back to an annual-lag/recent-level blend. This is a prototype model, not yet validated with rolling-origin backtests. Resource demand is a stated placeholder proportional to recent cases plus population; the allocation is an illustrative weighted heuristic, not the assignment’s LP. The calendar is a seasonal planning hypothesis. Ground truth is written separately by the generator and must never be fed into detection.

## 6. Evaluation plan and current status

The rubric requires alert sensitivity, false alerts per district-year, median delay, threshold curves, artefact comparison, rolling-origin MAE and 80% interval coverage, proportional-allocation comparison, five budget levels, scaling at three SF levels and before/after Spark optimization evidence. This draft does not report those numbers because they have not been measured. Run the pipeline at SF .25/.5/1 on documented hardware, capture Spark UI, compare at least two optimizations and add result tables/screenshots. For forecasting, ensure folds are chronological and compare the same horizon against seasonal naïve. For detection, match alerts to the separate truth file using a declared spatial/time tolerance. Do not tune on test periods.

## 7. Dashboard and usability

The D3 dashboard offers a GeoBoundaries ADM2 choropleth when public data is enabled, with a schematic-tile fallback, observed/forecast line, district-week heat view, resource table, warning table and processing-quality summaries. Disease and district filters coordinate views. Synthetic case data remains labelled, small cells are suppressed in selected views, and the choropleth shows incidence per 100,000 using the selected population denominator. Obtain two non-CS user walkthroughs and document tasks, findings and resulting changes; none are claimed in this draft.

## 8. Ethics, society and sustainability

No real patient data is present. The synthetic prototype keeps direct identifiers out of silver and limits serving data to district aggregates. Actual deployment would require access control, secure secret management, retention policy, audit trails, community engagement and independent privacy review. Forecast uncertainty and suppression are visible, and local experts must interpret warnings. Local-mode Spark and batch cadence keep student compute modest, but the claimed 25M scale has not been run.

## 9. Limitations and future work

Run and archive the public S1-S3 acquisition; enrich generator seasonality, weather lags, reporting artefact and outbreak dynamics; make incremental upserts idempotent with 21-day revision handling; implement stronger complementary suppression; fit and backtest Spark-parallel forecasts; solve allocation with a documented LP and proportional baseline; wire MinIO; build an actual district choropleth; and record scalability, usability and presentation evidence. Team size differs from the brief (four versus three); obtain instructor direction and document the approved arrangement.

## References\n\n[11] geoBoundaries, Bangladesh ADM2 gbOpen boundary metadata and simplified geometry, retrieved through the geoBoundaries API. [12] WorldPop, Global2 API v2, Bangladesh 2022 district age/sex estimates (1 km). [13] Open-Meteo, Historical Weather API, ERA5-Land daily data at Bangladesh district centroids, 2021-2025. See data/reference/source_metadata.json for exact retrieval metadata and checksums after acquisition.

Use and cite the references listed in the assignment brief: EARS (Hutwagner et al., 2003); Farrington et al. (1996); Bracher et al. (2021); Lazer et al. (2014); Spark (Zaharia et al., 2016); Delta Lake (Armbrust et al., 2020); D3 (Bostock et al., 2011); Sweeney (2002); and WHO IDSR 3rd edition. Add full IEEE bibliographic details and dataset citations when public data is added.

## Appendix A. Policy brief

See [policy_brief.md](policy_brief.md); format as exactly two pages when creating the final report PDF.

## Appendix B. Contribution matrix (for group agreement)

| Work area | Sourav | Aritra | Sakib | Noha |
|---|---|---|---|---|
| Problem analysis, proposal, conflict analysis |  |  |  |  |
| Synthetic generator and public data |  |  |  |  |
| Ingestion, lakehouse, incremental loads |  |  |  |  |
| Quality, lineage and privacy |  |  |  |  |
| Detection and evaluation |  |  |  |  |
| Forecasting and demand conversion |  |  |  |  |
| Optimisation and preparedness calendar |  |  |  |  |
| Serving and D3 dashboard |  |  |  |  |
| Scale experiment and Spark optimization |  |  |  |  |
| Report/policy brief |  |  |  |  |
| Video production |  |  |  |  |
| Agreed share (must sum to 100%) |  |  |  |  |
| Signatures |  |  |  |  |




