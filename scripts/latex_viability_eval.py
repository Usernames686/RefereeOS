from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.agents.orchestrator import analyze_text
from backend.parsing.injection_scan import scan_for_prompt_injection
from backend.parsing.latex_ingest import fetch_arxiv_source, temporary_source_root
from backend.parsing.latex_to_markdown import LatexConversionError, convert_latex_source


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RefereeOS LaTeX intake viability on live arXiv IDs.")
    parser.add_argument("arxiv_ids", nargs="*", help="arXiv IDs to evaluate.")
    parser.add_argument("--ids-file", type=Path, help="Text file with one arXiv ID per line.")
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    parser.add_argument("--no-compile", action="store_true", help="Disable Daytona compile fallback.")
    parser.add_argument("--force-compile", action="store_true", help="Force Daytona compile fallback for every source.")
    args = parser.parse_args()

    ids = _load_ids(args.arxiv_ids, args.ids_file)
    if not ids:
        parser.error("Provide arXiv IDs as arguments or with --ids-file.")

    papers = [_evaluate_one(arxiv_id, allow_compile=not args.no_compile, force_compile=args.force_compile) for arxiv_id in ids]
    report = {"papers": papers, "aggregate": _aggregate(papers)}
    text = json.dumps(report, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


def _load_ids(argv_ids: list[str], ids_file: Path | None) -> list[str]:
    ids = list(argv_ids)
    if ids_file:
        for line in ids_file.read_text(encoding="utf-8").splitlines():
            clean = line.split("#", 1)[0].strip()
            if clean:
                ids.append(clean)
    return ids


def _evaluate_one(arxiv_id: str, *, allow_compile: bool, force_compile: bool) -> dict:
    started = time.perf_counter()
    row = {
        "arxiv_id": arxiv_id,
        "parsed": False,
        "title_extracted": False,
        "abstract_chars": 0,
        "claim_count": 0,
        "sections_found": [],
        "injection_findings": 0,
        "fallback_used": "failed",
        "elapsed_ms": 0,
        "error": None,
    }

    try:
        with temporary_source_root("refereeos_latex_eval") as tmp:
            source_dir = fetch_arxiv_source(arxiv_id, dest_root=tmp)
            converted = convert_latex_source(source_dir, allow_compile=allow_compile, force_compile=force_compile)
            board = analyze_text(
                converted.markdown,
                source=f"arxiv:{arxiv_id}",
                fixture_meta={
                    "fixture_id": f"arxiv:{arxiv_id}",
                    "source_format": "latex",
                    "ingest_kind": "arxiv",
                    "arxiv_id": arxiv_id,
                    "latex_path": converted.latex_path,
                    "repro_artifact_available": False,
                },
            )

        paper = board["paper"]
        row.update(
            {
                "parsed": bool(paper.get("abstract") and board.get("claims")),
                "title_extracted": bool(paper.get("title") and paper["title"] != "Untitled manuscript"),
                "abstract_chars": len(paper.get("abstract", "")),
                "claim_count": len(board.get("claims", [])),
                "sections_found": _sections(converted.markdown),
                "injection_findings": len(scan_for_prompt_injection(converted.markdown)),
                "fallback_used": converted.latex_path,
            }
        )
    except Exception as exc:
        row["error"] = str(exc)
        if isinstance(exc, LatexConversionError):
            row["fallback_used"] = "failed"
    finally:
        row["elapsed_ms"] = round((time.perf_counter() - started) * 1000)

    return row


def _sections(markdown: str) -> list[str]:
    return re.findall(r"^##\s+(.+?)\s*$", markdown, flags=re.MULTILINE)


def _aggregate(papers: list[dict]) -> dict:
    total = len(papers)
    parsed = [paper for paper in papers if paper["parsed"]]
    fallback_counts = {
        "fast": sum(1 for paper in papers if paper["fallback_used"] == "fast"),
        "compile": sum(1 for paper in papers if paper["fallback_used"] == "compile"),
        "failed": sum(1 for paper in papers if paper["fallback_used"] == "failed"),
    }
    return {
        "total": total,
        "parsed": len(parsed),
        "parse_rate": round(len(parsed) / total, 3) if total else 0,
        "mean_claim_count": round(mean([paper["claim_count"] for paper in parsed]), 2) if parsed else 0,
        "mean_elapsed_ms": round(mean([paper["elapsed_ms"] for paper in papers]), 2) if papers else 0,
        "fallback_counts": fallback_counts,
    }


if __name__ == "__main__":
    raise SystemExit(main())
