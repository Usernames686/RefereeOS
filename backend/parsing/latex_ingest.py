from __future__ import annotations

import gzip
import io
import os
import re
import shutil
import tarfile
import urllib.error
import urllib.request
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote


MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_EXTRACTED_BYTES = 200 * 1024 * 1024
MAX_EXTRACTED_FILES = 800

MAIN_TEX_NAMES = {
    "main.tex",
    "paper.tex",
    "ms.tex",
    "manuscript.tex",
    "article.tex",
}


class LatexIngestError(RuntimeError):
    """Base class for LaTeX source intake failures."""


class ArxivSourceUnavailable(LatexIngestError):
    """Raised when arXiv does not provide usable TeX source for an ID."""


class LatexArchiveError(LatexIngestError):
    """Raised when an uploaded or fetched source package cannot be unpacked safely."""


class MainTexNotFound(LatexIngestError):
    """Raised when no likely root TeX file can be found."""


def fetch_arxiv_source(arxiv_id: str, dest_root: Path | None = None) -> Path:
    """Fetch and unpack an arXiv e-print source package into a temporary directory."""
    normalized_id = _normalize_arxiv_id(arxiv_id)
    source_dir = _new_source_dir(dest_root, f"arxiv_{_safe_name(normalized_id)}")
    url = f"https://arxiv.org/e-print/{quote(normalized_id, safe='/')}"
    request = urllib.request.Request(url, headers={"User-Agent": "RefereeOS-LaTeX-Prototype/0.1"})

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            blob = response.read(MAX_ARCHIVE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code in {403, 404, 410}:
            raise ArxivSourceUnavailable(f"arXiv source is unavailable for {normalized_id}") from exc
        raise ArxivSourceUnavailable(f"arXiv source fetch failed for {normalized_id}: HTTP {exc.code}") from exc
    except Exception as exc:
        raise ArxivSourceUnavailable(f"arXiv source fetch failed for {normalized_id}: {exc}") from exc

    if len(blob) > MAX_ARCHIVE_BYTES:
        raise LatexArchiveError("arXiv source package is too large for the prototype intake limit.")

    _unpack_source_blob(blob, source_dir, fallback_name=f"{_safe_name(normalized_id)}.tex")
    find_main_tex(source_dir)
    return source_dir


async def unpack_upload(file, dest_root: Path | None = None) -> Path:
    """Unpack a FastAPI UploadFile containing .tex, .zip, .tar, .tar.gz, or .tex.gz."""
    filename = file.filename or "latex_upload.tex"
    data = await file.read()
    return unpack_upload_bytes(filename, data, dest_root=dest_root)


def unpack_upload_bytes(filename: str, data: bytes, dest_root: Path | None = None) -> Path:
    source_dir = _new_source_dir(dest_root, f"upload_{_safe_name(Path(filename).stem or 'latex')}")
    if len(data) > MAX_ARCHIVE_BYTES:
        raise LatexArchiveError("Uploaded LaTeX package is too large for the prototype intake limit.")

    lowered = filename.lower()
    if lowered.endswith(".tex"):
        _write_single_tex(source_dir, "main.tex", data)
    elif lowered.endswith((".tar", ".tar.gz", ".tgz", ".zip", ".gz")):
        _unpack_source_blob(data, source_dir, fallback_name="main.tex")
    elif b"\\documentclass" in data[:20000]:
        _write_single_tex(source_dir, "main.tex", data)
    else:
        raise LatexArchiveError("Upload must be a .tex file or a .zip/.tar/.tar.gz source archive.")

    find_main_tex(source_dir)
    return source_dir


def find_main_tex(source_dir: Path) -> Path:
    """Pick the most likely root .tex file from an unpacked source tree."""
    source_root = source_dir.resolve()
    candidates: list[tuple[float, Path]] = []

    for tex_path in source_root.rglob("*.tex"):
        if not tex_path.is_file():
            continue
        try:
            text = tex_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "\\documentclass" not in text:
            continue

        name = tex_path.name.lower()
        score = float(min(tex_path.stat().st_size, 200_000))
        if name in MAIN_TEX_NAMES:
            score += 1_000_000
        if "\\begin{document}" in text:
            score += 250_000
        if "\\title" in text:
            score += 50_000
        candidates.append((score, tex_path))

    if not candidates:
        raise MainTexNotFound("No TeX file containing \\documentclass was found.")

    candidates.sort(key=lambda item: (item[0], -len(item[1].parts)), reverse=True)
    return candidates[0][1]


def _normalize_arxiv_id(arxiv_id: str) -> str:
    value = arxiv_id.strip()
    value = re.sub(r"^arxiv:\s*", "", value, flags=re.IGNORECASE)
    value = value.rstrip("/")
    if "/abs/" in value:
        value = value.rsplit("/abs/", 1)[1]
    if "/pdf/" in value:
        value = value.rsplit("/pdf/", 1)[1].removesuffix(".pdf")
    if not value or re.search(r"\s", value) or len(value) > 80:
        raise ArxivSourceUnavailable("Invalid arXiv ID.")
    return value


def _new_source_dir(dest_root: Path | None, prefix: str) -> Path:
    if dest_root is None:
        dest_root = default_temp_root()
    dest_root.mkdir(parents=True, exist_ok=True)
    return make_temp_dir(prefix, dest_root)


def default_temp_root() -> Path:
    root = Path(os.getenv("REFEREEOS_TMP_DIR", "outputs/tmp"))
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


@contextmanager
def temporary_source_root(prefix: str):
    root = make_temp_dir(prefix, default_temp_root())
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def make_temp_dir(prefix: str, parent: Path | None = None) -> Path:
    parent = (parent or default_temp_root()).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    for _ in range(20):
        candidate = parent / f"{_safe_name(prefix)}_{uuid.uuid4().hex[:10]}"
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            continue
    raise LatexArchiveError("Could not create a temporary LaTeX source directory.")


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return cleaned.strip("._")[:50] or "source"


def _unpack_source_blob(blob: bytes, source_dir: Path, fallback_name: str) -> None:
    if blob.startswith(b"%PDF"):
        raise ArxivSourceUnavailable("The source package is PDF-only, not LaTeX source.")

    if _try_extract_tar(blob, source_dir):
        return

    if zipfile.is_zipfile(io.BytesIO(blob)):
        _extract_zip(blob, source_dir)
        return

    if blob.startswith(b"\x1f\x8b"):
        try:
            inflated = gzip.decompress(blob)
        except OSError as exc:
            raise LatexArchiveError("Could not decompress gzipped source.") from exc
        if inflated.startswith(b"%PDF"):
            raise ArxivSourceUnavailable("The source package is PDF-only, not LaTeX source.")
        if _try_extract_tar(inflated, source_dir):
            return
        _write_single_tex(source_dir, fallback_name, inflated)
        return

    if b"\\documentclass" in blob[:20000]:
        _write_single_tex(source_dir, fallback_name, blob)
        return

    raise LatexArchiveError("Source package is not a supported LaTeX archive or TeX file.")


def _try_extract_tar(blob: bytes, source_dir: Path) -> bool:
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as archive:
            _extract_tar(archive, source_dir)
        return True
    except tarfile.ReadError:
        return False


def _extract_tar(archive: tarfile.TarFile, source_dir: Path) -> None:
    file_count = 0
    total_bytes = 0

    for member in archive.getmembers():
        target = _safe_target(source_dir, member.name)
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if not member.isfile():
            raise LatexArchiveError("Archive contains links or special files, which are not accepted.")

        file_count += 1
        total_bytes += max(member.size, 0)
        _enforce_extract_limits(file_count, total_bytes)
        target.parent.mkdir(parents=True, exist_ok=True)
        extracted = archive.extractfile(member)
        if extracted is None:
            raise LatexArchiveError(f"Could not read archive member {member.name!r}.")
        target.write_bytes(extracted.read())


def _extract_zip(blob: bytes, source_dir: Path) -> None:
    file_count = 0
    total_bytes = 0
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        for info in archive.infolist():
            target = _safe_target(source_dir, info.filename)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            file_count += 1
            total_bytes += info.file_size
            _enforce_extract_limits(file_count, total_bytes)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))


def _write_single_tex(source_dir: Path, filename: str, data: bytes) -> None:
    target = _safe_target(source_dir, filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def _safe_target(source_dir: Path, member_name: str) -> Path:
    normalized = member_name.replace("\\", "/")
    path = Path(normalized)
    if path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", normalized):
        raise LatexArchiveError(f"Unsafe archive path rejected: {member_name!r}")

    root = source_dir.resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise LatexArchiveError(f"Unsafe archive path rejected: {member_name!r}")
    return target


def _enforce_extract_limits(file_count: int, total_bytes: int) -> None:
    if file_count > MAX_EXTRACTED_FILES:
        raise LatexArchiveError("Source package contains too many files for prototype intake.")
    if total_bytes > MAX_EXTRACTED_BYTES:
        raise LatexArchiveError("Source package expands beyond the prototype intake limit.")
