# ATTRIBUTION.md - C5-AG2 Submission

## 1. Fork Source

| Field | Value |
|---|---|
| Base project | RefereeOS |
| Base repo URL | https://github.com/VJDiPaola/RefereeOS |
| Base captain | Vincent DiPaola |
| My repo | https://github.com/Usernames686/RefereeOS |
| Track | `scientific` |

This submission is a fork-and-improve upgrade of the original RefereeOS hackathon project.

## 2. AG2 Documentation References

| Used in | Source | Adaptation |
|---|---|---|
| `backend/agents/beta_review.py` | AG2 Beta Agent API docs | Uses `autogen.beta.Agent` and `agent.ask()` |
| `backend/agents/beta_review.py` | AG2 Beta agent-as-tool examples | Exposes `method_critic` through `Agent.as_tool()` |
| `tests/test_orchestrator.py` | AG2 Beta testing guidance | Keeps Beta config tests offline and deterministic |

## 3. Code Reused From Base Repo

| Base file / module | How it is used |
|---|---|
| `backend/agents/orchestrator.py` | Preserved deterministic peer-review workflow |
| `backend/parsing/*` | Preserved manuscript parsing and injection scanning |
| `backend/storage/evidence_board.py` | Preserved evidence board model |
| `backend/repro/daytona_runner.py` | Preserved reproducibility probe with local fallback |
| `frontend/*` | Preserved dashboard UI |
| `tests/*` | Preserved and extended test suite |

## 4. What I Added

- `backend/agents/beta_review.py`: AG2 Beta reviewer team with claim extractor, method critic, and area chair.
- `ag2_reviewer.py`: standalone CLI for the Beta reviewer pipeline.
- Provider configuration for DeepSeek, OpenRouter, OpenAI, and Gemini.
- C5-AG2 documentation: `README.md`, `AI_LOG.md`, `ATTRIBUTION.md`, `GROUP_SUBMISSION.md`.
- Tests for provider selection and response parsing.

## 5. License Compatibility

| Component | License |
|---|---|
| Original RefereeOS | No explicit license found in base repo |
| My additions | MIT-style educational submission material |
| AG2 framework | Apache 2.0 |

Because the base repo has no explicit license file, this project should be treated as an educational fork for the C5-AG2 challenge unless the base author grants broader reuse rights.
