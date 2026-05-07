from __future__ import annotations

from typing import Annotated

try:
    from dotenv import load_dotenv

    load_dotenv(".env")
    load_dotenv(".env.local", override=True)
    load_dotenv(".local.env", override=True)
except Exception:
    pass

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from backend.agents.orchestrator import analyze_fixture, analyze_text
from backend.parsing.latex_ingest import (
    ArxivSourceUnavailable,
    LatexIngestError,
    fetch_arxiv_source,
    temporary_source_root,
    unpack_upload,
)
from backend.parsing.latex_to_markdown import LatexConversionError, convert_latex_source
from backend.parsing.paper_parser import extract_pdf_text, list_fixtures, load_fixture_text
from backend.storage.evidence_board import run_store


app = FastAPI(
    title="RefereeOS API",
    description="AG2 + Daytona multi-agent preprint triage and reproducibility assistant.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "RefereeOS"}


@app.get("/api/fixtures")
def fixtures() -> dict:
    return {"fixtures": list_fixtures()}


@app.post("/api/analyze")
async def analyze(
    fixture_id: Annotated[str, Form()] = "clean",
    field_domain: Annotated[str | None, Form()] = None,
    reported_result: Annotated[float | None, Form()] = None,
    arxiv_id: Annotated[str | None, Form()] = None,
    latex_force_compile: Annotated[bool, Form()] = False,
    file: Annotated[UploadFile | None, File()] = None,
    latex_archive: Annotated[UploadFile | None, File()] = None,
    artifact_file: Annotated[UploadFile | None, File()] = None,
    script_file: Annotated[UploadFile | None, File()] = None,
) -> dict:
    custom_artifact = await _read_custom_artifact(artifact_file, script_file, reported_result)

    if arxiv_id and arxiv_id.strip():
        with temporary_source_root("refereeos_arxiv") as tmp:
            try:
                source_dir = fetch_arxiv_source(arxiv_id, dest_root=tmp)
                converted = convert_latex_source(source_dir, force_compile=latex_force_compile)
            except ArxivSourceUnavailable as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            except (LatexIngestError, LatexConversionError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        fixture_meta = _no_artifact_meta(
            fixture_id=f"arxiv:{arxiv_id.strip()}",
            source_format="latex",
            ingest_kind="arxiv",
            arxiv_id=arxiv_id.strip(),
            latex_path=converted.latex_path,
        )
        if custom_artifact:
            fixture_meta.update(custom_artifact)
        board = analyze_text(converted.markdown, source=f"arxiv:{arxiv_id.strip()}", fixture_meta=fixture_meta, field_domain=field_domain)
    elif latex_archive and latex_archive.filename:
        with temporary_source_root("refereeos_latex_upload") as tmp:
            try:
                source_dir = await unpack_upload(latex_archive, dest_root=tmp)
                converted = convert_latex_source(source_dir, force_compile=latex_force_compile)
            except (LatexIngestError, LatexConversionError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        fixture_meta = _no_artifact_meta(
            fixture_id="latex_upload",
            source_format="latex",
            ingest_kind="latex_archive",
            latex_path=converted.latex_path,
        )
        if custom_artifact:
            fixture_meta.update(custom_artifact)
        board = analyze_text(
            converted.markdown,
            source=f"latex_upload:{latex_archive.filename}",
            fixture_meta=fixture_meta,
            field_domain=field_domain,
        )
    elif file and file.filename:
        if file.content_type == "application/pdf" or file.filename.lower().endswith(".pdf"):
            text = extract_pdf_text(file.file)
        else:
            text = (await file.read()).decode("utf-8", errors="ignore")
        fixture_meta = _no_artifact_meta(
            fixture_id="uploaded",
            source_format="pdf" if file.filename.lower().endswith(".pdf") else "markdown",
            ingest_kind="upload",
        )
        if custom_artifact:
            fixture_meta.update(custom_artifact)
        board = analyze_text(text, source=f"uploaded_file:{file.filename}", fixture_meta=fixture_meta, field_domain=field_domain)
    else:
        if custom_artifact:
            text, fixture_meta = load_fixture_text(fixture_id)
            fixture_meta.update(custom_artifact)
            board = analyze_text(
                text,
                source=f"sample_fixture:{fixture_meta['fixture_id']}:custom_repro_artifact",
                fixture_meta=fixture_meta,
                field_domain=field_domain,
            )
        else:
            board = analyze_fixture(fixture_id=fixture_id, field_domain=field_domain)

    run = run_store.create(board)
    return run


def _no_artifact_meta(
    *,
    fixture_id: str,
    source_format: str,
    ingest_kind: str,
    arxiv_id: str | None = None,
    latex_path: str = "n/a",
) -> dict:
    return {
        "fixture_id": fixture_id,
        "source_format": source_format,
        "ingest_kind": ingest_kind,
        "arxiv_id": arxiv_id,
        "latex_path": latex_path,
        "repro_artifact_available": False,
    }


async def _read_custom_artifact(
    artifact_file: UploadFile | None,
    script_file: UploadFile | None,
    reported_result: float | None,
) -> dict | None:
    provided = [bool(artifact_file and artifact_file.filename), bool(script_file and script_file.filename), reported_result is not None]
    if not any(provided):
        return None
    if not all(provided):
        raise HTTPException(
            status_code=400,
            detail="Custom reproducibility needs a CSV artifact, Python script, and reported result.",
        )

    assert artifact_file is not None
    assert script_file is not None
    artifact_text = (await artifact_file.read()).decode("utf-8", errors="ignore")
    script_text = (await script_file.read()).decode("utf-8", errors="ignore")
    if "macro_f1" not in script_text and "metric" not in script_text and "observed_result" not in script_text:
        raise HTTPException(
            status_code=400,
            detail="Metric script should print macro_f1=<number>, metric=<number>, or observed_result=<number>.",
        )

    return {
        "fixture_id": "uploaded_custom",
        "reported_result": reported_result,
        "results_csv_text": artifact_text,
        "metric_script_text": script_text,
        "custom_artifact": True,
        "repro_artifact_available": True,
    }


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict:
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/api/runs/{run_id}/evidence-board")
def get_evidence_board(run_id: str) -> dict:
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run["board"]


@app.get("/api/runs/{run_id}/packet", response_class=PlainTextResponse)
def get_packet(run_id: str) -> str:
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run["packet"]
