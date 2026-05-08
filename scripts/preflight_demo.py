from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


try:
    from dotenv import load_dotenv

    load_dotenv(".env")
    load_dotenv(".env.local", override=True)
    load_dotenv(".local.env", override=True)
except Exception:
    pass

from backend.repro.daytona_runner import DaytonaOpenAIReproRunner


def _missing_env() -> list[str]:
    missing = []
    for name in ("DAYTONA_API_KEY", "OPENAI_API_KEY"):
        if not os.getenv(name):
            missing.append(name)
    if os.getenv("REFEREEOS_PASS_OPENAI_KEY_TO_DAYTONA", "false").lower() != "true":
        missing.append("REFEREEOS_PASS_OPENAI_KEY_TO_DAYTONA=true")
    return missing


def main() -> int:
    """Verify the exact live demo path: Daytona code run plus OpenAI inside Daytona."""
    missing = _missing_env()
    if missing:
        print("Preflight failed: missing " + ", ".join(missing))
        return 1

    model = os.getenv("OPENAI_MODEL", "gpt-5.5")
    fixture_meta = {
        "fixture_id": "preflight",
        "reported_result": 0.87,
        "results_csv_text": "label,precision,recall\npreflight,0.87,0.87\n",
        "metric_script_text": 'print("macro_f1=0.87")\n',
        "custom_artifact": True,
    }
    paper = {
        "title": "RefereeOS demo preflight",
        "abstract": "Short preflight paper used to verify the live Daytona and OpenAI path.",
    }

    runner = DaytonaOpenAIReproRunner()
    payload = runner._build_payload(fixture_meta, paper)
    try:
        receipt = runner._run_in_daytona(payload)
    except Exception as exc:
        print(f"Preflight failed: Daytona path raised {exc}")
        return 1

    interpretation = receipt.get("llm_interpretation", "")
    failed_openai = (
        "OpenAI API call failed" in interpretation
        or "credentials were not visible" in interpretation
        or "OPENAI_API_KEY" in interpretation
    )
    if receipt.get("sandbox_provider") != "Daytona":
        print(f"Preflight failed: expected Daytona, got {receipt.get('sandbox_provider')}")
        return 1
    if receipt.get("status") != "passed":
        print(f"Preflight failed: expected passed repro status, got {receipt.get('status')}")
        return 1
    if failed_openai:
        print(f"Preflight failed: OpenAI interpretation did not succeed: {interpretation}")
        return 1

    print("Preflight passed")
    print(f"Model: {model}")
    print(f"Status: {receipt.get('status')}")
    print(f"Observed result: {receipt.get('observed_result')}")
    print(f"LLM interpretation: {interpretation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
