from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.orchestrator import analyze_fixture


def main() -> int:
    board = analyze_fixture("clean")
    packet = board["final_packet"]
    print("=" * 64)
    print("RefereeOS deterministic offline demo")
    print("=" * 64)
    print(f"Recommendation: {packet['triage_recommendation']}")
    print(f"Claims: {len(board['claims'])}")
    print(f"Concerns: {len(board['concerns'])}")
    print(f"Agent steps: {len(board['agent_trace'])}")
    print("\nAgents:")
    for step in board["agent_trace"]:
        print(f"- {step['agent']}: {step['status']}")
    output_dir = PROJECT_ROOT / "outputs" / "offline_demo"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "evidence_board.json"
    output_path.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved evidence board: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
