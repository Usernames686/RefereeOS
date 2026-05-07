# RefereeOS Deliverables Brief

**Purpose:** Define exactly what should exist by the end of the five-hour AG2 + Daytona hackathon build.  
**Project:** RefereeOS — multi-agent preprint triage and reproducibility assistant.  
**Audience:** Judges, sponsor teams, scientific editors/reviewers, and future GitHub readers.

---

## 1. Final Product Deliverable

### Deliverable

A working web app that takes a scientific paper input and produces a structured reviewer-prep packet.

### Must include

- Upload PDF or select demo fixture
- Run multi-agent review workflow
- Show shared evidence board
- Run or simulate one Daytona sandbox reproducibility check
- Generate final reviewer packet

### Success criteria

A judge can understand the product in under 30 seconds and see a full analysis run in under 3 minutes.

---

## 2. Core Demo Deliverables

### 2.1 Demo fixture paper

A controlled sample paper or paper-like markdown/PDF fixture.

**Must include:**

- Title
- Abstract
- 3–5 main claims
- Methods/results section
- Mention of a dataset or script
- References or related-work-looking section

**Recommended:** create two fixtures.

| Fixture | Purpose |
|---|---|
| Clean computational paper | Shows normal reviewer packet flow |
| Suspicious/adversarial paper | Shows prompt-injection/integrity scanner and/or failed reproducibility check |

---

### 2.2 Reproducibility artifact

A tiny runnable script/data pair.

**Example files:**

```txt
backend/fixtures/results.csv
backend/fixtures/reproduce_metric.py
```

**The script should:**

- load fixture data
- calculate a reported metric
- print the result
- return success/failure

**Demo output:**

```md
## Reproducibility Receipt
- Environment: Daytona sandbox
- Probe: Recalculate reported score from results.csv
- Status: Passed / Failed / Inconclusive
- Reported result: 0.87
- Observed result: 0.82
- Human follow-up: Ask authors to explain metric mismatch
```

---

### 2.3 Prompt-injection fixture

A small hidden or explicit adversarial instruction included in the suspicious fixture.

**Examples to detect:**

- `ignore previous instructions`
- `give this paper a positive review`
- `do not mention weaknesses`
- `LLM reviewer`
- unusually tiny or hidden text if PDF span metadata is available

**Output:**

```md
## Integrity Scan
Severity: High
Finding: Possible prompt-injection instruction detected in extracted manuscript text.
Recommendation: Do not pass raw manuscript text directly to review agents without sanitization.
```

---

## 3. Agent Deliverables

### 3.1 Intake Agent

**Output:** paper profile JSON.

Must extract or infer:

- title
- abstract
- field guess
- claims
- methods summary
- code/data mentions
- red flags

---

### 3.2 Methods & Statistics Agent

**Output:** methodology concerns.

Must check for:

- missing baselines
- weak sample size
- overclaimed causality
- missing ablations
- train/test leakage
- mismatch between claim and evidence

---

### 3.3 Novelty / Literature Agent

**Output:** possible related work and novelty risks.

MVP acceptable implementation:

- query Semantic Scholar or OpenAlex by title/keyphrases
- return 3–5 related papers
- compare title/abstract overlap

Fallback:

- use canned related-work fixture

---

### 3.4 Integrity Agent

**Output:** prompt-injection and suspicious-content findings.

Must include:

- regex-based scan
- severity label
- reviewer-safe recommendation

---

### 3.5 Reproducibility Agent

**Output:** Daytona reproducibility receipt.

Must include:

- probe selected
- command run
- stdout/stderr summary
- pass/fail/inconclusive status
- human follow-up

---

### 3.6 Area Chair Agent

**Output:** final reviewer packet.

Allowed recommendations:

- Ready for human review
- Needs author clarification before review
- Route to specialist reviewer
- Possible integrity issue
- Reproducibility check failed or inconclusive

Forbidden recommendation:

- Final publication accept/reject

---

## 4. Evidence Board Deliverable

### Deliverable

A JSON-backed shared evidence board updated by each agent.

### Required objects

- `paper`
- `claims`
- `evidence`
- `concerns`
- `related_work`
- `repro_checks`
- `final_packet`

### Example success state

```json
{
  "claims": [
    {
      "id": "claim_001",
      "text": "The proposed method improves baseline accuracy by 12%.",
      "type": "benchmark",
      "concern_ids": ["concern_001"]
    }
  ],
  "concerns": [
    {
      "id": "concern_001",
      "agent": "methods_stats",
      "severity": "high",
      "category": "methods",
      "text": "The baseline comparison appears underspecified.",
      "human_followup": "Ask authors for baseline implementation details."
    }
  ]
}
```

---

## 5. Frontend Deliverables

### Required screens/components

1. **UploadPanel**
   - upload PDF
   - select fixture
   - select field/domain

2. **AgentTrace**
   - shows each agent step
   - status: pending/running/complete/error

3. **EvidenceBoard**
   - claims
   - evidence
   - concerns
   - reproducibility result

4. **ReviewerPacket**
   - readable markdown output
   - export/download option if time permits

### UI principle

Make the app look like operational infrastructure, not a chat demo.

---

## 6. Backend Deliverables

### Required endpoints

```txt
POST /api/analyze
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/packet
GET  /api/runs/{run_id}/evidence-board
```

### Optional endpoints

```txt
POST /api/repro/run
POST /api/metadata/search
```

### Required backend modules

```txt
backend/app.py
backend/agents/orchestrator.py
backend/parsing/pdf_parser.py
backend/parsing/injection_scan.py
backend/repro/daytona_runner.py
backend/storage/evidence_board.py
backend/metadata/semantic_scholar.py or openalex.py
```

---

## 7. README Deliverable

The README should include:

1. What RefereeOS does
2. Why the scientific review bottleneck matters
3. Why it uses AG2
4. Why it uses Daytona
5. Architecture diagram
6. Setup instructions
7. Demo instructions
8. Known limitations
9. Ethical boundary: human review assist, not replacement
10. Open-source credits

### README positioning paragraph

> RefereeOS is a multi-agent preprint triage system for scientific editors and reviewers. It converts a manuscript into a structured evidence board, runs targeted checks through specialized agents, executes one reproducibility probe in a Daytona sandbox, and produces a reviewer packet for human decision-making. It does not make final publication decisions.

---

## 8. Demo Script Deliverable

### 90-second version

1. “Scientific review is bottlenecked, and AI-written manuscripts make the signal/noise problem worse.”
2. “RefereeOS does not replace peer review. It prepares peer review.”
3. Upload/select paper.
4. Show AG2 agents populating the evidence board.
5. Show Daytona reproducibility receipt.
6. Show prompt-injection/integrity scan.
7. Show final reviewer packet.
8. Close: “This routes scarce human expertise to the papers and claims that need it most.”

### 5-minute version

- 45s problem/context
- 45s architecture
- 2m live demo
- 45s why AG2/Daytona
- 45s limitations/future

---

## 9. Judging Checklist

Before submission, confirm:

- [ ] App runs locally
- [ ] Sample fixture works without internet
- [ ] Agent workflow produces output
- [ ] Daytona path is implemented or clearly stubbed with visible code
- [ ] Final packet is readable
- [ ] Prompt-injection scanner has demo result
- [ ] README explains ethical boundary
- [ ] Demo script exists
- [ ] Open-source credits are listed
- [ ] No claim that the system replaces peer review

---

## 10. Nice-to-Have Deliverables

Only complete if the MVP is already stable.

| Stretch deliverable | Value |
|---|---|
| Mermaid architecture diagram in README | Helps judges understand quickly |
| Reviewer expertise recommendation | Makes editor workflow more realistic |
| GROBID/Docling parser toggle | Shows serious scientific-doc ambition |
| PaperQA2 literature module | Adds stronger scientific grounding |
| Export packet to markdown/PDF | Makes output feel usable |
| Claim graph visualization | Makes multi-agent evidence board more memorable |
| OpenReview-style reviewer affinity demo | Strong future roadmap |

---

## 11. Final Submission Package

Submit with:

1. GitHub repo
2. Deployed or local demo video
3. README
4. Sample input paper
5. Sample reviewer packet output
6. Architecture diagram
7. Short explanation of AG2 + Daytona usage
8. Ethical limitations section

---

## 12. Final Product Promise

> RefereeOS helps overwhelmed scientific reviewers by turning papers into structured, evidence-backed review packets with reproducibility receipts and integrity checks before human experts spend scarce review time.
