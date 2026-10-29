# EpiScope — Bangladesh disease surveillance prototype

> **Video:** not recorded yet. Add the shareable link here before submission.

Teaching prototype for the CSE 4345 Big Data Analytics CEP. The included sample is synthetic; no patient data is included. The assignment specifies three members, while this team has four (Sourav, Aritra, Sakib and Noha). Confirm the allowed group size and the extra role with the instructor before submission. Do not claim generated evaluation metrics as real evidence.

## Run locally

Requires Python 3.11, Java 17, Node.js 20+, and the pinned Python dependencies. Spark runs in local mode; `docker-compose.yml` provides an optional MinIO object store profile for extension work.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m orchestration.run_all --scale 0.002 --seed 4345
cd dashboard; npm run serve
```

The orchestrator creates a private, ignored .env with a local random hash salt on first run; preserve it between runs. Open http://localhost:8080/dashboard/. The sample scale is deliberately small for laptops; --scale 1 targets 25M encounters and needs substantial storage/time. Use python -m generator.generate --help for options. To replay a compatible incremental CSV drop, put it in data/input/incremental/ with the S4 schema and rerun the pipeline and analytics stages; source checksums make an identical batch rerun idempotent, and weekly output is rebuilt from source. Keep all generated data out of Git.

## Architecture

Seeded generator → immutable bronze JSON/CSV with load metadata → Spark validation, de-identification and Parquet silver → weekly gold marts → detection, forecasting, resource planning and calendar → suppressed JSON consumed by D3 v7. Outputs contain district-week aggregates, never person-level records. Small cells 1–4 are suppressed; district totals are withheld where subtraction could recover suppressed values. This compact laptop prototype uses local Parquet as its default lake; MinIO/S3 and streaming are extension targets.

## Evidence status

Code and dashboard are a prototype. Quantitative performance, Spark UI screenshots, real-data provenance, two-user usability findings, member signatures/contributions, repository sharing/tag, and the required 15–20 minute video must be completed by the group using its own run and evidence. The project brief requires exactly three handover items and says groups have three members; the fourth member requires instructor guidance. No contribution history or test evidence is fabricated here.

## Requirement traceability

| IDs | Implementation | Report section |
|---|---|---|
| ING-1–4, DQ-1–3, PRV-1 | `generator/`, `pipeline/` | 3–4 |
| AN-1–9 | `analytics/` | 5–6 |
| PRV-2, VIS-1–4 | `analytics/run.py`, `dashboard/` | 7–8 |
| C1–C5, P1–P7 | `docs/proposal.md`, `docs/report.md` | 2 |
| ENG-1–4 | `Makefile`, `requirements.txt`, `docker-compose.yml` | 3, 6 |

## Presentation chapters (15–20 minutes)

Prepare a shareable recording and add its URL/timestamps above. Every member needs a named, voiced segment of at least four minutes. Suggested ownership: Sourav—problem/data quality; Aritra—pipeline/privacy; Sakib—analytics/evaluation; Noha—allocation/dashboard/policy. Record real runs including an incremental rerun, quarantine example, baselines, dashboard interactions, ethics and limitations. This plan is not a recording or proof of contribution. See docs/presentation.md for the run sheet.

See `docs/report.md`, `docs/policy_brief.md`, `docs/proposal.md`, `docs/presentation.md`, and `AI_USAGE.md`.
