from __future__ import annotations

import base64
import io
import json
import os
import re
import textwrap
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from backend.parsing.latex_ingest import MainTexNotFound, find_main_tex
from backend.parsing.paper_parser import extract_pdf_text


DEFAULT_FAST_MIN_CHARS = int(os.getenv("REFEREEOS_LATEX_FAST_MIN_CHARS", "500"))
MAX_COMPILE_PACKAGE_BYTES = 80 * 1024 * 1024


class LatexConversionError(RuntimeError):
    """Raised when LaTeX cannot be converted to parser-compatible text."""


class LatexCompileUnavailable(LatexConversionError):
    """Raised when Daytona or a TeX runtime is unavailable for fallback compilation."""


@dataclass(frozen=True)
class LatexConversionResult:
    markdown: str
    latex_path: Literal["fast", "compile"]
    main_tex: str
    diagnostics: list[str] = field(default_factory=list)


def convert_latex_source(
    source_dir: Path,
    *,
    allow_compile: bool = True,
    force_compile: bool = False,
    min_chars: int = DEFAULT_FAST_MIN_CHARS,
) -> LatexConversionResult:
    """Convert an unpacked LaTeX source tree to Markdown shaped for parse_manuscript_text()."""
    source_dir = source_dir.resolve()
    try:
        main_tex = find_main_tex(source_dir)
    except MainTexNotFound as exc:
        raise LatexConversionError(str(exc)) from exc

    diagnostics: list[str] = []
    if not force_compile:
        try:
            markdown = _fast_convert(main_tex, source_dir)
            if _fast_conversion_is_viable(markdown, min_chars):
                return LatexConversionResult(
                    markdown=markdown,
                    latex_path="fast",
                    main_tex=str(main_tex.relative_to(source_dir)),
                    diagnostics=diagnostics,
                )
            diagnostics.append("Fast conversion did not produce enough parser-compatible text.")
        except Exception as exc:
            diagnostics.append(f"Fast conversion failed: {exc}")

    if not allow_compile:
        raise LatexConversionError("; ".join(diagnostics) or "Compile fallback is disabled.")

    try:
        pdf_bytes = DaytonaLatexCompiler().compile(source_dir, main_tex)
        pdf_text = extract_pdf_text(io.BytesIO(pdf_bytes))
        markdown = _pdf_text_to_markdown(pdf_text)
    except LatexConversionError:
        raise
    except Exception as exc:
        raise LatexConversionError(f"Compile fallback failed: {exc}") from exc

    if not markdown.strip():
        raise LatexConversionError("Compile fallback produced no extractable PDF text.")

    return LatexConversionResult(
        markdown=markdown,
        latex_path="compile",
        main_tex=str(main_tex.relative_to(source_dir)),
        diagnostics=diagnostics,
    )


class DaytonaLatexCompiler:
    """Compile LaTeX in Daytona and return rendered PDF bytes."""

    def compile(self, source_dir: Path, main_tex: Path) -> bytes:
        if not os.getenv("DAYTONA_API_KEY"):
            raise LatexCompileUnavailable("DAYTONA_API_KEY is not set; compile fallback is unavailable.")

        try:
            from daytona import Daytona
        except Exception as exc:  # pragma: no cover - depends on sponsor SDK runtime
            raise LatexCompileUnavailable("Daytona SDK is not installed.") from exc

        archive_b64 = base64.b64encode(_zip_source_tree(source_dir)).decode("ascii")
        main_rel = str(main_tex.relative_to(source_dir)).replace("\\", "/")
        daytona = Daytona()
        sandbox = daytona.create()
        try:
            response = sandbox.process.code_run(_sandbox_compile_code(archive_b64, main_rel))
            result_text = getattr(response, "result", str(response))
            receipt = _parse_last_json(result_text)
            if not receipt:
                raise LatexConversionError("Daytona compile did not return receipt JSON.")
            if receipt.get("status") == "unavailable":
                raise LatexCompileUnavailable(receipt.get("error", "TeX runtime is unavailable in Daytona."))
            if receipt.get("status") != "ok":
                detail = receipt.get("error") or receipt.get("stdout_stderr_summary") or "unknown compile failure"
                raise LatexConversionError(f"Daytona compile failed: {detail}")
            return base64.b64decode(receipt["pdf_b64"])
        finally:
            try:
                daytona.delete(sandbox)
            except Exception:
                pass


def _fast_convert(main_tex: Path, source_dir: Path) -> str:
    expanded = _expand_inputs(main_tex, source_dir, seen=set())
    expanded = _strip_comments(expanded)

    title = _extract_command_arg(expanded, "title") or "Untitled manuscript"
    abstract = _extract_environment(expanded, "abstract")
    body = _document_body(expanded)
    body = _remove_environment(body, "abstract")
    body = _drop_display_only_environments(body)
    body = _prepare_lists_and_references(body)
    body = _replace_heading_commands(body)
    body = _replace_common_macros(body)

    title_text = _inline_latex_to_text(title)
    abstract_text = _inline_latex_to_text(abstract)
    body_text = _block_latex_to_text(body)

    parts = [f"# {title_text or 'Untitled manuscript'}"]
    if abstract_text:
        parts.append(f"## Abstract\n{abstract_text}")
    parts.append(body_text)
    return _cleanup_markdown("\n\n".join(part for part in parts if part.strip()))


def _expand_inputs(tex_path: Path, source_dir: Path, seen: set[Path], depth: int = 0) -> str:
    resolved = tex_path.resolve()
    root = source_dir.resolve()
    if not resolved.is_relative_to(root):
        raise LatexConversionError(f"Input path escapes source tree: {tex_path}")
    if resolved in seen:
        return ""
    if depth > 12:
        raise LatexConversionError("LaTeX input nesting is too deep.")

    seen.add(resolved)
    text = resolved.read_text(encoding="utf-8", errors="ignore")

    def replace(match: re.Match[str]) -> str:
        raw_name = match.group(1).strip()
        if not raw_name:
            return ""
        rel = Path(raw_name)
        if rel.suffix == "":
            rel = rel.with_suffix(".tex")
        child = (resolved.parent / rel).resolve()
        if not child.exists():
            return f"\n[Missing LaTeX input: {raw_name}]\n"
        return "\n" + _expand_inputs(child, source_dir, seen, depth + 1) + "\n"

    return re.sub(r"\\(?:input|include)\s*\{([^}]+)\}", replace, text)


def _strip_comments(text: str) -> str:
    stripped_lines = []
    for line in text.splitlines():
        cut_at = None
        for idx, char in enumerate(line):
            if char != "%":
                continue
            backslashes = 0
            cursor = idx - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                cut_at = idx
                break
        stripped_lines.append(line[:cut_at] if cut_at is not None else line)
    return "\n".join(stripped_lines)


def _extract_command_arg(text: str, command: str) -> str:
    pattern = re.compile(rf"\\{re.escape(command)}\*?(?:\[[^\]]*\])?\s*\{{")
    match = pattern.search(text)
    if not match:
        return ""
    value, _ = _read_braced_group(text, match.end() - 1)
    return value.strip()


def _extract_environment(text: str, env: str) -> str:
    match = re.search(rf"\\begin\{{{re.escape(env)}\}}([\s\S]*?)\\end\{{{re.escape(env)}\}}", text)
    return match.group(1).strip() if match else ""


def _document_body(text: str) -> str:
    match = re.search(r"\\begin\{document\}([\s\S]*?)\\end\{document\}", text)
    return match.group(1) if match else text


def _remove_environment(text: str, env: str) -> str:
    return re.sub(rf"\\begin\{{{re.escape(env)}\}}[\s\S]*?\\end\{{{re.escape(env)}\}}", "\n", text)


def _drop_display_only_environments(text: str) -> str:
    for env in ("figure", "figure*", "table", "table*"):
        text = re.sub(
            rf"\\begin\{{{re.escape(env)}\}}[\s\S]*?\\end\{{{re.escape(env)}\}}",
            "\n[Figure or table omitted]\n",
            text,
        )
    return text


def _prepare_lists_and_references(text: str) -> str:
    text = re.sub(r"\\begin\{(?:itemize|enumerate)\}", "\n", text)
    text = re.sub(r"\\end\{(?:itemize|enumerate)\}", "\n", text)
    text = re.sub(r"\\item(?:\[[^\]]*\])?", "\n- ", text)
    text = re.sub(r"\\begin\{thebibliography\}(?:\{[^}]*\})?", "\n\n## References\n", text)
    text = re.sub(r"\\end\{thebibliography\}", "\n", text)
    text = re.sub(r"\\bibitem(?:\[[^\]]*\])?\{[^}]*\}", "\n- ", text)
    return text


def _replace_heading_commands(text: str) -> str:
    pattern = re.compile(r"\\(section|subsection|subsubsection)\*?(?:\[[^\]]*\])?\s*\{")
    pieces = []
    cursor = 0
    for match in pattern.finditer(text):
        pieces.append(text[cursor : match.start()])
        heading, end = _read_braced_group(text, match.end() - 1)
        heading_text = _normalize_section_title(_inline_latex_to_text(heading))
        prefix = {"section": "##", "subsection": "###", "subsubsection": "####"}[match.group(1)]
        pieces.append(f"\n\n{prefix} {heading_text}\n\n")
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def _replace_common_macros(text: str) -> str:
    text = re.sub(r"\\(?:label|ref|eqref|pageref)\s*\{[^}]*\}", "", text)
    text = re.sub(r"\\(?:cite|citet|citep|citealp|citeauthor|citeyear)\*?(?:\[[^\]]*\]){0,2}\s*\{([^}]*)\}", r"[citation: \1]", text)
    text = re.sub(r"\\(?:maketitle|tableofcontents)\b", "", text)
    text = re.sub(r"\\bibliography\s*\{([^}]*)\}", "\n\n## References\nBibliography files: \\1\n", text)
    text = re.sub(r"\\bibliographystyle\s*\{[^}]*\}", "", text)
    return text


def _inline_latex_to_text(text: str) -> str:
    return _cleanup_inline(_latex_to_text(_replace_common_macros(text)))


def _block_latex_to_text(text: str) -> str:
    return _latex_to_text(text)


def _latex_to_text(text: str) -> str:
    try:
        from pylatexenc.latex2text import LatexNodes2Text

        return LatexNodes2Text().latex_to_text(text)
    except Exception:
        return _regex_latex_to_text(text)


def _regex_latex_to_text(text: str) -> str:
    text = re.sub(r"\\(?:textbf|textit|emph|texttt|underline)\s*\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?", lambda m: m.group(1) or "", text)
    text = text.replace("~", " ")
    text = text.replace("$", "")
    text = re.sub(r"[{}]", "", text)
    return text


def _read_braced_group(text: str, open_brace_index: int) -> tuple[str, int]:
    if open_brace_index >= len(text) or text[open_brace_index] != "{":
        return "", open_brace_index
    depth = 0
    start = open_brace_index + 1
    cursor = open_brace_index
    while cursor < len(text):
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:cursor], cursor + 1
        cursor += 1
    return text[start:], len(text)


def _normalize_section_title(title: str) -> str:
    cleaned = _cleanup_inline(title).strip(" .:")
    key = cleaned.lower()
    mapping = {
        "method": "Methods",
        "methods": "Methods",
        "methodology": "Methods",
        "experimental setup": "Methods",
        "experiments": "Results",
        "evaluation": "Results",
        "results": "Results",
        "data availability": "Data And Code",
        "code availability": "Data And Code",
        "data and code availability": "Data And Code",
        "data and code": "Data And Code",
        "main claims": "Main Claims",
        "claims": "Main Claims",
        "references": "References",
        "related work": "References",
    }
    return mapping.get(key, cleaned or "Section")


def _cleanup_inline(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _cleanup_markdown(text: str) -> str:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").splitlines():
        line = re.sub(r"[ \t]+", " ", raw).strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if line.startswith("#") and lines and lines[-1] != "":
            lines.append("")
        lines.append(line)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines).strip() + "\n"


def _fast_conversion_is_viable(markdown: str, min_chars: int) -> bool:
    if len(markdown.strip()) < min_chars:
        return False
    return bool(re.search(r"^##\s+Abstract\s*$", markdown, flags=re.MULTILINE | re.IGNORECASE))


def _pdf_text_to_markdown(text: str) -> str:
    lines = [_cleanup_inline(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return ""

    title = lines[0]
    output = [f"# {title}"]
    for line in lines[1:]:
        lowered = line.lower().strip(" .:")
        if lowered in {"abstract", "introduction", "methods", "methodology", "results", "discussion", "references"}:
            output.append(f"## {_normalize_section_title(line)}")
        else:
            output.append(line)
    return _cleanup_markdown("\n".join(output))


def _zip_source_tree(source_dir: Path) -> bytes:
    buffer = io.BytesIO()
    total = 0
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in source_dir.rglob("*"):
            if not path.is_file():
                continue
            total += path.stat().st_size
            if total > MAX_COMPILE_PACKAGE_BYTES:
                raise LatexConversionError("LaTeX source tree is too large for Daytona compile fallback.")
            archive.write(path, path.relative_to(source_dir).as_posix())
    return buffer.getvalue()


def _sandbox_compile_code(archive_b64: str, main_rel: str) -> str:
    return textwrap.dedent(
        f"""
        import base64
        import json
        import shutil
        import subprocess
        import zipfile
        from pathlib import Path

        Path("source.zip").write_bytes(base64.b64decode("{archive_b64}"))
        source_dir = Path("src")
        with zipfile.ZipFile("source.zip") as archive:
            archive.extractall(source_dir)

        main_rel = Path({main_rel!r})
        main_path = source_dir / main_rel
        work_dir = main_path.parent
        main_name = main_path.name

        if shutil.which("latexmk"):
            command = ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", main_name]
            completed = subprocess.run(command, cwd=work_dir, capture_output=True, text=True, timeout=90, check=False)
        elif shutil.which("pdflatex"):
            command = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", main_name]
            first = subprocess.run(command, cwd=work_dir, capture_output=True, text=True, timeout=90, check=False)
            second = subprocess.run(command, cwd=work_dir, capture_output=True, text=True, timeout=90, check=False)
            completed = second
            completed.stdout = first.stdout + "\\n" + second.stdout
            completed.stderr = first.stderr + "\\n" + second.stderr
        else:
            print(json.dumps({{"status": "unavailable", "error": "No latexmk or pdflatex executable is installed."}}))
            raise SystemExit(0)

        pdf_path = work_dir / Path(main_name).with_suffix(".pdf").name
        summary = (completed.stdout + completed.stderr)[-4000:]
        if completed.returncode != 0 or not pdf_path.exists():
            print(json.dumps({{
                "status": "failed",
                "exit_code": completed.returncode,
                "command": command,
                "stdout_stderr_summary": summary,
            }}))
            raise SystemExit(0)

        print(json.dumps({{
            "status": "ok",
            "exit_code": completed.returncode,
            "command": command,
            "stdout_stderr_summary": summary,
            "pdf_b64": base64.b64encode(pdf_path.read_bytes()).decode("ascii"),
        }}))
        """
    )


def _parse_last_json(result_text: str) -> dict | None:
    for line in reversed(result_text.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None
