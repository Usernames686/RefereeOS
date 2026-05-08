"""Standalone AG2 Beta reviewer for RefereeOS.

Run:
    python ag2_reviewer.py --fixture clean
    python ag2_reviewer.py --fixture suspicious
    python ag2_reviewer.py --text "paper text..."

Requires one LLM key in .env:
    DEEPSEEK_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from backend.agents.beta_review import beta_review_text
from backend.parsing.paper_parser import load_fixture_text, parse_manuscript_text


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run RefereeOS AG2 Beta peer-review agents.")
    parser.add_argument("--fixture", choices=("clean", "suspicious"), default="clean")
    parser.add_argument("--text", help="Review custom manuscript text instead of a fixture.")
    parser.add_argument("--output-dir", default="outputs/beta_runs")
    args = parser.parse_args()

    if args.text:
        source = "cli:text"
        text = args.text
    else:
        text, meta = load_fixture_text(args.fixture)
        source = f"fixture:{meta['fixture_id']}"

    paper = parse_manuscript_text(text, source=source)
    print("=" * 64)
    print("RefereeOS AG2 Beta Peer Review")
    print(f"Source: {source}")
    print(f"Title: {paper['title']}")
    print("=" * 64)

    try:
        result = asyncio.run(beta_review_text(text, title=paper["title"]))
    except RuntimeError as exc:
        print(f"AG2 Beta reviewer is not configured: {exc}")
        print("For an offline demo, run: python scripts/offline_demo.py")
        return 2
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{args.fixture}.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Engine: {result['engine']}")
    print(f"Model: {result['model']}")
    print("Agents: " + " -> ".join(result["agents"]))
    print("Collaboration: " + result["collaboration"])
    print("\nClaims\n------")
    print(result["claims"][:2000])
    print("\nReview\n------")
    print(result["review"][:3000])
    print(f"\nSaved JSON: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
