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

1. Generate synthetic encounters, facilities, stocks, and outbreak truth; optionally download public geography, population, and weather inputs.
2. Use PySpark to load encounter files, retain raw input in a bronze Parquet layer, validate records, quarantine quality failures, and de-identify valid records into silver.
3. Aggregate district, disease, and epidemiological-week counts into gold Parquet data.
4. Create prototype outbreak flags, short-horizon planning estimates, an illustrative allocation, and aggregated JSON for a D3 dashboard.
5. Explore the resulting views using district and disease filters.

Encounter, facility, stock, and injected-outbreak data are synthetic. With --with-public-data, the project downloads real ADM2 boundaries from geoBoundaries, 2022 modelled population/age-sex estimates from WorldPop, and daily 2021-2025 ERA5-Land weather from Open-Meteo. WorldPop values are modelled estimates, not official BBS census counts. The public-data download has not yet been run in this workspace; the first run needs internet access.

## Dashboard

The dashboard includes:

- District choropleth using public ADM2 geometry when public data is enabled; otherwise a clearly labelled schematic tile view.
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

The local pipeline uses Spark in local mode and Parquet files on disk. When public data is enabled, daily district weather is aggregated into weekly gold records and lagged weather signals are used by the district forecast prototype. MinIO is scaffolded in docker-compose.yml but is not connected to the current pipeline. Streaming and ACID lakehouse tables are not implemented.

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
python -m orchestration.run_all --scale 0.04 --seed 4345 --with-public-data
~~~

The --with-public-data option retrieves S1-S3, caches API responses under data/reference/cache/, and records source URLs, dates, licences, and file checksums in data/reference/source_metadata.json. The first public-data run needs internet access and may take several minutes; reruns reuse cached files. The orchestrator also creates a private local .env for salted ID hashing. It is ignored by Git; keep it private and preserve it between runs.

The default scale factor (SF) is 0.04, which generates 1,000,000 synthetic encounters. The generator is parameterized by `--scale` and `--seed`; with SF=1 it targets exactly 25,000,000 records across 2021–2025. The same seed and population input reproduce the same records. Changing scale replaces the previous numbered generator chunks so stale rows cannot inflate the next run. Use `--with-public-data` to include S1–S3 reference inputs. SF=1 requires substantially more disk space and runtime:

~~~powershell
python -m orchestration.run_all --scale 1 --seed 4345 --with-public-data
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

For scale 0.04 with seed 4345, the project generates 1,000,000 synthetic encounter records. Exact clean/quarantine counts and dashboard aggregates are written to the local pipeline output after each run.

These are run-specific prototype outputs, not public-health estimates or validated detection results. The flags have not been evaluated against the separate outbreak truth file, and runtime/scaling benchmarks have not been completed.

## Methods and prototype boundaries

| Area | Current prototype | Important limitation |
|---|---|---|
| Data sources | Synthetic S4-S6 plus optional public S1-S3 acquisition | Public download still needs to be run and archived locally; S7 is not included |
| Data quality | 15 checks, reason-coded quarantine, duplicate encounter check | Cross-facility deduplication and hidden-drop performance need evaluation |
| Privacy | Patient ID hash in silver; direct ID removed; age converted to bands | Review all export paths and complementary suppression before any wider release |
| Detection | Trailing 8-week mean/standard deviation threshold | Heuristic, not a validated outbreak detector; no completed threshold trade-off evaluation |
| Forecasting | District model uses lagged rain, temperature, and humidity when S3 is present; otherwise seasonal/recent baseline | No rolling-origin backtest or interval-coverage result |
| Allocation | Demand-weighted illustrative heuristic and five budget points | Not the required linear/integer program; not validated against a proportional baseline |
| Calendar | Seasonal planning hypothesis | Not derived from fitted seasonal decomposition |
| Dashboard | D3 v7, five coordinated views, choropleth when S1 is present, district/disease filters | No time brush or documented user study |
| Scale and performance | Local Spark; broadcast facility join and AQE enabled | No SF 0.25/0.5/1 measurements or before/after Spark UI evidence |

## Data and privacy

- Encounter, facility, stock, and outbreak files are synthetic. Population denominators are synthetic in the quick mode and WorldPop modelled estimates in public-data mode.
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
| ING-1 to ING-4 | generator/, pipeline/run.py | Partial: local batch and Parquet layers; incremental behavior needs further evidence |\n| S1-S3 | generator/acquire_public.py, pipeline/run.py | geoBoundaries, WorldPop, and Open-Meteo acquisition and weather integration; run locally to cache the files |
| DQ-1 to DQ-3 | pipeline/run.py | Prototype checks, quarantine, and batch lineage |
| PRV-1 to PRV-2 | pipeline/run.py, analytics/run.py | Hashing and partial suppression; complete export audit still needed |
| AN-1 to AN-9 | analytics/run.py | Baselines and illustrative plan; required quantitative evaluation and LP remain incomplete |
| VIS-1 to VIS-4 | dashboard/, analytics/run.py | D3 views, linked filters, public-boundary choropleth; time brush and usability evidence remain incomplete |
| ENG-1 | orchestration/run_all.py | Local one-command sample run |
| ENG-2 to ENG-4 | Not complete | Scaling evidence, optimization comparison, automated tests and orchestration retries remain to be done |

For a full requirement discussion, see [docs/report.md](docs/report.md) and [docs/proposal.md](docs/proposal.md).

## Development

Python dependency versions are pinned in requirements.txt. Start from the repository root. Generated data, the local environment, virtual environment, and logs are excluded from Git by .gitignore.

Generative AI assistance is disclosed in [AI_USAGE.md](AI_USAGE.md). Team members should review, understand, and be able to explain all submitted code and claims.

## License

Coursework prototype for CSE 4345. No production or clinical use is intended.




