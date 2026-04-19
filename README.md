# Multi-Agent App Scaffolder

A demo-ready multi-agent backend system that converts a natural language app idea into structured plans, starter code stubs, validation reports, reviewer feedback, and packaged run artifacts.

## Project Overview
The system orchestrates specialized agents with typed contracts and deterministic tools. It is designed for traceability and demoability rather than full production app generation.

## Architecture
### Core Components
- **FastAPI backend** for run execution and artifact APIs.
- **Orchestrator** for ordered stage execution and bounded correction loop.
- **Agents** for planning, architecture, schema, API plan, frontend plan, codegen, and review.
- **Tools** for retrieval, validation, mapping, packaging.
- **Artifact store** writing all outputs to `runs/{run_id}`.
- **Streamlit demo UI** consuming backend APIs only.

### Workflow
```text
prompt
  -> planner
  -> retrieval
  -> architect
  -> schema
  -> api
  -> frontend
  -> codegen
  -> validation
  -> reviewer
  -> correction (max 1 pass)
  -> package artifacts
```

## Why Multi-Agent Instead of Single-Agent
- Stage-specific responsibilities and typed outputs.
- Better observability via per-stage artifacts.
- Deterministic validation outside the LLM.
- Reviewer-driven bounded correction loop.

## Smart Policy
- Stage-level model routing, cache reuse, and reviewer gating are documented in [smart_policy.md](/Users/saab/Documents/DSBA/Archive/M2/Personal Projects/Multi Agent App Scaffolder/smart_policy.md).

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## Run API
```bash
./scripts/run_api.sh
```
or
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Run Demo UI
```bash
./scripts/run_ui.sh
```
Open `http://127.0.0.1:8501`.

## API Usage
### Start run
```bash
curl -X POST http://127.0.0.1:8000/scaffold/run \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Build a marketplace app for local artisans with orders and reviews"}'
```

### Fetch run state
```bash
curl http://127.0.0.1:8000/scaffold/run/<run_id>
```

### List artifacts
```bash
curl http://127.0.0.1:8000/scaffold/run/<run_id>/artifacts
```

### Read artifact content
```bash
curl "http://127.0.0.1:8000/scaffold/run/<run_id>/artifacts/content?path=<absolute_artifact_path>"
```

## UI Demo Usage
1. Start API.
2. Start Streamlit UI.
3. Enter prompt and click `Run Scaffold`.
4. Inspect pipeline steps, stage outputs, reviewer findings, validation summary.
5. Browse and download artifacts from the artifact panel.

## Evaluation
Benchmark prompts are defined in `evals/cases.json`.

Run:
```bash
python evals/runner.py
```

Outputs:
- `evals/report.json`
- per-case scores + overall score

## Makefile Commands
```bash
make install
make api
make ui
make demo
make eval
make test
```

## Limitations
- Code generation is stub-level only.
- Correction loop is bounded to one pass.
- UI is intentionally minimal.
- No DB/job queue/auth/frontend build pipeline.

## Future Improvements
- Async run execution + live step streaming.
- Stronger stage-specific reviewer heuristics.
- Richer templates and framework-specific codegen packs.
- Better scoring calibration and historical eval tracking.

