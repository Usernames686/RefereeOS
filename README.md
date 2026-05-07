# RefereeOS

RefereeOS is a multi-agent preprint triage prototype for scientific editors and reviewers. It converts a manuscript into a structured evidence board, runs specialized review checks, executes one reproducibility probe in a Daytona sandbox, and produces a reviewer packet for human decision-making.

RefereeOS took first place in the Scientific Track at the AG2 Hackathon on Sunday, May 3, 2026.

This repository is a public prototype snapshot. Further product development may continue privately while the research direction is refined.

RefereeOS prepares human review. It does not make autonomous publication decisions.

## Screenshots

| Review workspace | Reviewer packet |
| --- | --- |
| ![RefereeOS dashboard review workspace](docs/assets/screenshots/refereeos-dashboard-01.png) | ![RefereeOS reviewer packet and evidence board](docs/assets/screenshots/refereeos-dashboard-02.png) |

## Why It Matters

Scientific review is overloaded, and AI-written manuscripts can increase volume while making weak work look polished. RefereeOS helps reviewers and editors spend scarce attention where it matters by surfacing claims, evidence, methodological risks, integrity issues, reproducibility receipts, and recommended reviewer expertise.

## What It Does

- Parses uploaded manuscripts or controlled fixtures into a shared evidence board.
- Flags prompt-injection style text that should not be passed blindly to review agents.
- Runs deterministic review stages for intake, methods/statistics, integrity, novelty, reproducibility, and area-chair packet generation.
- Uses Daytona for isolated reproducibility probes when credentials are available.
- Uses OpenAI GPT-5.5 to interpret Daytona reproducibility receipts.
- Optionally uses AG2 with Gemini for area-chair synthesis when enabled.
- Falls back to clearly labeled deterministic behavior when optional services are unavailable.

## Architecture

```mermaid
flowchart LR
    U["Reviewer or editor"] --> A["Upload manuscript or choose fixture"]
    A --> B["FastAPI analysis endpoint"]
    B --> C["Parser and prompt-injection scanner"]
    C --> D[("Shared evidence board JSON")]

    subgraph WORKFLOW["Review workflow"]
        E["Intake extracts paper profile and claims"]
        F["Methods/statistics flags design risks"]
        G["Integrity records prompt-injection findings"]
        H["Novelty attaches related-work risks"]
        I["Reproducibility prepares executable probe"]
        L["Area chair packet synthesis"]
    end

    D --> E --> D
    D --> F --> D
    D --> G --> D
    D --> H --> D
    D --> I

    I --> J["Daytona sandbox"]
    J --> K["Run uploaded or fixture metric script"]
    K --> O["OpenAI GPT-5.5 interprets receipt"]
    O --> D
    D --> N["Optional AG2 + Gemini synthesis"]
    N --> L
    D --> L --> M["Reviewer packet and dashboard"]
```

## Setup

Use Python 3.13. AG2 currently requires Python `>=3.10, <3.14`.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm install --prefix frontend
```

Create `.env.local` from `.env.example` and set the credentials you want to enable:

```txt
DAYTONA_API_KEY=...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.5
REFEREEOS_PASS_OPENAI_KEY_TO_DAYTONA=true
REFEREEOS_ENABLE_AG2_LLM=false
GEMINI_MODEL=gemini-3.1-pro-preview
GEMINI_API_KEY=...
```

OpenAI keys are not sent into Daytona unless `REFEREEOS_PASS_OPENAI_KEY_TO_DAYTONA=true`.
AG2/Gemini synthesis is disabled unless `REFEREEOS_ENABLE_AG2_LLM=true`; when disabled or unavailable, the packet uses deterministic area-chair synthesis and labels the fallback in the evidence-board metadata.

## Run Locally

Terminal 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Equivalent root launcher:

```powershell
.\.venv\Scripts\python.exe main.py
```

Terminal 2:

```powershell
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`.

To verify the live Daytona and OpenAI path before presenting the prototype:

```powershell
.\.venv\Scripts\python.exe scripts\preflight_demo.py
```

## Demo Flow

1. Select **Suspicious/adversarial paper** and run review.
2. Show the agent trace, prompt-injection findings, Daytona receipt, GPT-5.5 interpretation, optional AG2/Gemini synthesis, and final reviewer packet.
3. Switch to **Clean computational paper** to show the control case where the artifact reproduces.

Expected fixture outcomes:

- Clean fixture: `Ready for human review`, reproducibility `passed`, reported `0.87`, observed `0.87`.
- Suspicious fixture: `Possible integrity issue`, reproducibility `failed`, reported `0.91`, observed about `0.77`.

## Custom Reproducibility Path

For a non-fixture run, upload:

- a manuscript: `.pdf`, `.md`, or `.txt`
- an artifact CSV
- a Python metric script
- the reported metric value

The metric script runs inside Daytona and should print one of these patterns:

```txt
macro_f1=0.87
metric=0.87
observed_result=0.87
```

For custom uploaded scripts, RefereeOS does not run a local fallback. If Daytona fails, the receipt is marked inconclusive instead of executing arbitrary uploaded code locally.

## LaTeX Viability Path

The API also accepts LaTeX sources for prototype stress testing:

- `arxiv_id`: fetches `https://arxiv.org/e-print/{id}` and converts the source package.
- `latex_archive`: accepts `.tex`, `.zip`, `.tar`, `.tar.gz`, `.tgz`, or `.tex.gz` uploads.
- `latex_force_compile=true`: skips fast conversion and tries the Daytona compile fallback.

LaTeX runs without an uploaded CSV/script artifact get a `not_run` reproducibility receipt instead of borrowing fixture artifacts. Batch evaluation is available with:

```powershell
.\.venv\Scripts\python.exe scripts\latex_viability_eval.py --ids-file ids.txt --output outputs\latex_viability.json
```

## API

- `POST /api/analyze`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/packet`
- `GET /api/runs/{run_id}/evidence-board`
- `GET /api/fixtures`
- `GET /api/health`

## Validation

Install test dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Run the frontend checks:

```powershell
npm run lint
npm run build
```

Run the backend tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Examples

Static sample artifacts live in `examples/`:

- `examples/sample_evidence_board.json`
- `examples/sample_reviewer_packet.md`

Generated runtime output is written under `outputs/` and is ignored by git.

## Known Limitations

- Fixture-first flow is hardened; arbitrary PDF extraction is available through PyMuPDF but not deeply section-aware.
- Related-work search uses canned Semantic Scholar/OpenAlex-style fixtures for offline prototype reliability.
- The local reproducibility fallback is for development only and is labeled in the receipt.
- AG2/Gemini synthesis is optional and env-gated; deterministic packet generation remains the fallback.
- The system prepares human review and must not be used as an autonomous publication decision maker.

## Research Contact

Researchers interested in peer review infrastructure, reproducibility triage, or adversarial manuscript screening are welcome to [open a GitHub Issue](https://github.com/VJDiPaola/RefereeOS/issues).

## Credits

- AG2: multi-agent framework
- Daytona: sandbox execution SDK
- OpenAI GPT-5.5: reproducibility receipt interpretation
- FastAPI and Uvicorn: Python API runtime
- PyMuPDF: PDF text extraction
- Vite, React, and Lucide: frontend dashboard
