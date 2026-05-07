from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


OUTPUT_DIR = Path(os.getenv("REFEREEOS_OUTPUT_DIR", "outputs/runs"))


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, board: dict[str, Any]) -> dict[str, Any]:
        run_id = f"run_{uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        run = {
            "run_id": run_id,
            "status": "complete",
            "created_at": now,
            "updated_at": now,
            "board": board,
            "packet": board.get("final_packet", {}).get("markdown", ""),
        }
        with self._lock:
            self._runs[run_id] = run
        self._persist(run)
        return deepcopy(run)

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            run = self._runs.get(run_id)
        if run:
            return deepcopy(run)

        disk_path = OUTPUT_DIR / f"{run_id}.json"
        if disk_path.exists():
            return json.loads(disk_path.read_text(encoding="utf-8"))
        return None

    def _persist(self, run: dict[str, Any]) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{run['run_id']}.json"
        path.write_text(json.dumps(run, indent=2), encoding="utf-8")


run_store = RunStore()


def build_empty_board(paper: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "metadata": {
            "project": "RefereeOS",
            "workflow_engine": metadata.get("workflow_engine", "AG2-compatible workflow"),
            "sandbox_provider": metadata.get("sandbox_provider", "Daytona"),
            "llm_provider": metadata.get("llm_provider", "OpenAI"),
            "llm_model": metadata.get("llm_model"),
            "fixture_id": metadata.get("fixture_id"),
            "ag2_status": metadata.get("ag2_status"),
            "ag2_model": metadata.get("ag2_model"),
            "source_format": metadata.get("source_format", "markdown"),
            "ingest_kind": metadata.get("ingest_kind", "fixture"),
            "arxiv_id": metadata.get("arxiv_id"),
            "latex_path": metadata.get("latex_path", "n/a"),
        },
        "paper": {
            "title": paper["title"],
            "abstract": paper["abstract"],
            "field_guess": paper["field_guess"],
            "source": paper["source"],
            "methods_summary": paper["methods_summary"],
            "datasets_or_code_mentions": paper["datasets_or_code_mentions"],
            "citations_or_related_work": paper["citations_or_related_work"],
        },
        "claims": [],
        "evidence": [],
        "concerns": [],
        "related_work": [],
        "repro_checks": [],
        "final_packet": {},
        "agent_trace": [],
    }
