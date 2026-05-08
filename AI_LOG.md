# AI_LOG.md - C5-AG2 Submission

## Project Metadata

| Field | Value |
|---|---|
| Repo URL | https://github.com/Usernames686/RefereeOS |
| Track | `scientific` |
| Base repo | https://github.com/VJDiPaola/RefereeOS |
| AG2 version | `ag2[openai,gemini] >= 0.9.0` |
| Beta used | Yes: `autogen.beta.Agent` |
| Models | OpenRouter Gemini / DeepSeek / OpenAI / Gemini direct |

## AI Tools Used

| Tool | Purpose |
|---|---|
| Codex | Repo analysis, AG2 Beta upgrade, tests, docs |
| C5-AG2 starter | Challenge rules, rubric, submission checklist |
| RefereeOS sample repo | Base implementation and scientific review workflow |

## Iteration Log

### Iteration 1 - Read challenge and choose base repo

- Prompt summary: Find a GitHub project that fits the C5-AG2 borrow-and-improve requirement.
- Output: Compared Life Sandbox, memo-in-browser-ag2, and RefereeOS.
- Adopted: Chose original `VJDiPaola/RefereeOS`.
- Verification: Confirmed it is a real AG2 hackathon sample with backend, frontend, tests, and scientific track fit.

### Iteration 2 - Inspect original architecture

- Prompt summary: Identify existing agents and safe upgrade points.
- Output: Found deterministic agents: intake, methods/statistics, integrity, novelty, reproducibility, area chair.
- Adopted: Preserve deterministic core and add AG2 Beta reviewer layer.
- Verification: Read `backend/agents/orchestrator.py`, `requirements.txt`, and tests.

### Iteration 3 - Add AG2 Beta reviewer team

- Prompt summary: Add a non-decorative Beta multi-agent workflow.
- Output: Created `backend/agents/beta_review.py`.
- Adopted: Added `claim_extractor`, `method_critic`, and `area_chair`.
- Verification: Tests cover provider detection and parsing helpers.

### Iteration 4 - Add agent-as-tool collaboration

- Prompt summary: Make one agent call another in the main review flow.
- Output: `method_critic.as_tool(name="critique_methods")` is registered on `area_chair`.
- Adopted: Documented in README and attribution.
- Verification: Source contains `autogen.beta.Agent` and `Agent.as_tool` pattern.

### Iteration 5 - Add standalone runner and docs

- Prompt summary: Make the Beta upgrade easy to demo.
- Output: Added `ag2_reviewer.py`, README rewrite, AI_LOG, ATTRIBUTION, and group submission text.
- Adopted: Yes.
- Verification: `python -m unittest discover -s tests -v`.

### Iteration 6 - Provider compatibility

- Prompt summary: Avoid requiring only Google API keys.
- Output: Added support for `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, and `GEMINI_API_KEY`.
- Adopted: Yes.
- Verification: Unit tests verify DeepSeek and OpenRouter config selection.

## Manual Steps And Justification

| Step | Why manual |
|---|---|
| GitHub repo creation | Requires the user's GitHub account |
| API key creation | Private credential; should not be committed |
| Demo video recording | Requires user's screen and final GitHub URL |

## Self-Audit

- [x] At least 5 iterations documented
- [x] Fork source identified
- [x] AG2 Beta used in code
- [x] Agent-as-tool collaboration documented
- [x] Tests included
- [x] No API keys committed
