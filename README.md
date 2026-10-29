# EpiScope

> **A student-built prototype for district-level disease surveillance, forecasting, and response planning in Bangladesh.**


[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![Apache Spark](https://img.shields.io/badge/Apache%20Spark-3.5-orange)](https://spark.apache.org/)
[![D3.js](https://img.shields.io/badge/D3.js-v7-f9a03c)](https://d3js.org/)

---

## Project links

- **Repository:** https://github.com/souravdev33/Episcope
- **Presentation video:** Not recorded yet. Add a shareable YouTube or Drive link here.
- **Technical report:** Draft at [docs/report.md](docs/report.md). Add the final report PDF to docs/ before hand-in.
- **Policy brief:** [docs/policy_brief.md](docs/policy_brief.md)
- **Presentation run sheet:** [docs/presentation.md](docs/presentation.md)

## What it does

EpiScope demonstrates a small end-to-end workflow for turning synthetic health-facility encounters into aggregated district-level views:

1. Generate reproducible synthetic facilities, population denominators, encounters, stock snapshots, and a separate outbreak truth file.
2. Use PySpark to load encounter files, retain raw input in a bronze Parquet layer, validate records, quarantine quality failures, and de-identify valid records into silver.
3. Aggregate district, disease, and epidemiological-week counts into gold Parquet data.
4. Create prototype outbreak flags, short-horizon planning estimates, an illustrative allocation, and aggregated JSON for a D3 dashboard.
5. Explore the resulting views using district and disease filters.

All included epidemiology and population values are synthetic. This prototype does not currently retrieve official Bangladesh data, measured weather, or administrative boundary files.

## Dashboard

The dashboard includes:

- District signal tiles. These are schematic tiles, not a geographic map.
- A weekly observed-count and forecast view with an illustrative 80% range.
- A district-by-week seasonal heat view.
- A district resource-planning table.
- A ranked threshold-flag table.
- A data-quality summary.

Selecting a disease or district filters the dashboard. Small-cell suppression is applied to heatmap and forecast values; review the privacy limitations below before using or sharing any exports.

## Architecture

~~~text
Synthetic generator
    |
    v
Bronze: raw encounter fields + load metadata (Parquet)
    |
    v
Silver: quality rules, quarantine, hashed patient ID, age band
    |
    v
Gold: district x disease x epi-week aggregates (Parquet)
    |
    +--> Detection and forecast prototypes
    +--> Illustrative resource plan and calendar
    |
    v
Aggregated dashboard.json
    |
    v
D3.js dashboard
~~~

The local pipeline uses Spark in local mode and Parquet files on disk. MinIO is scaffolded in docker-compose.yml but is not connected to the current pipeline. Streaming and ACID lakehouse tables are not implemented.

## Requirements

- Windows 10/11 or another supported operating system
- Python 3.11
- Java 17 (required by the pinned Spark 3.5 environment)
- Node.js 20+ (only needed to run the dashboard script)
- 8 GB RAM minimum recommended; the full-scale generator requires substantial disk space and runtime

Check Java before starting:

~~~powershell
java -version
~~~

It should report version 17. If Java reports 24 or newer, point this PowerShell session at a Java 17 installation first. Example path below may differ on your computer:

~~~powershell
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-17.0.20.101-hotspot"
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
java -version
~~~

Spark 3.5 can fail at startup on Java 24+ because Java changed the behavior of Subject.getSubject.

## Run on Windows

Run these commands from the repository root, not from the dashboard folder.

### 1. Create the Python environment

~~~powershell
cd "D:\Episcope"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
~~~

### 2. Build the sample pipeline

Set Java 17 for this PowerShell window if needed (see above), then run:

~~~powershell
python -m orchestration.run_all --scale 0.002 --seed 4345
~~~

The orchestrator generates a private local .env file on first run for salted ID hashing. That file is ignored by Git; keep it private and preserve it between runs so the hash salt remains stable.

The sample scale generates 50,000 encounter rows. A scale of 1 targets 25 million rows and can take much longer:

~~~powershell
python -m orchestration.run_all --scale 1 --seed 4345
~~~

### 3. Start the dashboard

After the pipeline finishes, open a second PowerShell window and run:

~~~powershell
cd "D:\Episcope\dashboard"
npm run serve
~~~

Visit **http://localhost:8080/dashboard/**. Leave the server window open while using the dashboard.

## Incremental input

To process an additional encounter CSV, use the same S4 column schema and place the file in:

~~~text
data/input/incremental/
~~~

Then rerun the pipeline and analytics steps from the repository root:

~~~powershell
python -m pipeline.run --input data/input --output data/lake
python -m analytics.run --input data/lake --output data/serving
~~~

The bronze batch key is derived from source file checksums, so replaying an identical source set reuses the same batch partition. Silver and gold are rebuilt from available source files. Keep the incremental file schema consistent with the generated encounter CSV.

## Sample run record

For scale 0.002 with seed 4345, the local sample run generated 50,000 synthetic encounters. Spark reported 47,438 valid rows and 2,562 quarantined rows. The analytics export contained 19,013 district-disease-week rows and 147 threshold flags.

These are run-specific prototype outputs, not public-health estimates or validated detection results. The flags have not been evaluated against the separate outbreak truth file, and runtime/scaling benchmarks have not been completed.

## Methods and prototype boundaries

| Area | Current prototype | Important limitation |
|---|---|---|
| Synthetic data | Seeded records, seasonal/geographic weighting, injected events, reporting-delay episode | No measured weather drivers; no public S1-S3 data |
| Data quality | 15 checks, reason-coded quarantine, duplicate encounter check | Cross-facility deduplication and hidden-drop performance need evaluation |
| Privacy | Patient ID hash in silver; direct ID removed; age converted to bands | Review all export paths and complementary suppression before any wider release |
| Detection | Trailing 8-week mean/standard deviation threshold | Heuristic, not a validated outbreak detector; no completed threshold trade-off evaluation |
| Forecasting | Annual-lag/recent-level blend with an illustrative interval | No weather covariates, trained model, rolling-origin backtest, or coverage result |
| Allocation | Demand-weighted illustrative heuristic and five budget points | Not the required linear/integer program; not validated against a proportional baseline |
| Calendar | Seasonal planning hypothesis | Not derived from fitted seasonal decomposition |
| Dashboard | D3 v7, five coordinated views, district/disease filters | Schematic tiles instead of boundary choropleth; no time brush or user study |
| Scale and performance | Local Spark; broadcast facility join and AQE enabled | No SF 0.25/0.5/1 measurements or before/after Spark UI evidence |

## Data and privacy

- Encounter, facility, stock, and population files created by the generator are synthetic.
- The ground-truth outbreak file is separate from analytics inputs and must not be used by the detector.
- Patient identifiers are present only in the bronze input and are salted/hashed before silver.
- The local salt is stored in the ignored .env file; do not commit it or share it.
- Counts from 1 to 4 are suppressed in heatmap and forecast arrays. The current prototype does not yet implement full complementary suppression across every output.
- No real patient-level or identifiable health data should be added to this repository.

## Repository layout

~~~text
analytics/       Detection, forecast, planning, and serving-data export
dashboard/       D3.js interface and local static server
docs/            Proposal, technical report draft, policy brief, presentation guide
generator/       Seeded synthetic data generator
orchestration/   One-command local run entry point
pipeline/        Spark bronze/silver/gold processing
AI_USAGE.md      Generative AI use disclosure
requirements.txt Pinned Python dependencies
docker-compose.yml Optional MinIO service scaffold
~~~

## Assignment traceability

| Requirement group | Main files | Status |
|---|---|---|
| ING-1 to ING-4 | generator/, pipeline/run.py | Partial: local batch and Parquet layers; incremental behavior needs further evidence |
| DQ-1 to DQ-3 | pipeline/run.py | Prototype checks, quarantine, and batch lineage |
| PRV-1 to PRV-2 | pipeline/run.py, analytics/run.py | Hashing and partial suppression; complete export audit still needed |
| AN-1 to AN-9 | analytics/run.py | Baselines and illustrative plan; required quantitative evaluation and LP remain incomplete |
| VIS-1 to VIS-4 | dashboard/, analytics/run.py | D3 views and filters; actual geographic choropleth and full interaction requirements remain incomplete |
| ENG-1 | orchestration/run_all.py | Local one-command sample run |
| ENG-2 to ENG-4 | Not complete | Scaling evidence, optimization comparison, automated tests and orchestration retries remain to be done |

For a full requirement discussion, see [docs/report.md](docs/report.md) and [docs/proposal.md](docs/proposal.md).

## Development

Python dependency versions are pinned in requirements.txt. Start from the repository root. Generated data, the local environment, virtual environment, and logs are excluded from Git by .gitignore.

Generative AI assistance is disclosed in [AI_USAGE.md](AI_USAGE.md). Team members should review, understand, and be able to explain all submitted code and claims.

## License

Coursework prototype for CSE 4345. No production or clinical use is intended.

