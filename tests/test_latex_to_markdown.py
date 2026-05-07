from __future__ import annotations

import unittest
from pathlib import Path

from backend.parsing.latex_ingest import temporary_source_root
from backend.parsing.latex_to_markdown import LatexConversionError, convert_latex_source
from backend.parsing.paper_parser import parse_manuscript_text


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "backend" / "fixtures" / "latex"


class LatexToMarkdownTests(unittest.TestCase):
    def test_preserves_title_abstract_sections_and_claims(self) -> None:
        result = convert_latex_source(FIXTURE_ROOT / "synthetic_clean", allow_compile=False, min_chars=100)
        paper = parse_manuscript_text(result.markdown, source="unit_latex")

        self.assertEqual(result.latex_path, "fast")
        self.assertEqual(paper["title"], "Calibrated Benchmarking of Sparse Cell-State Classifiers")
        self.assertIn("SparseCellNet", paper["abstract"])
        self.assertIn("train/validation/test", paper["methods_summary"])
        self.assertGreaterEqual(len(paper["claims"]), 3)

    def test_resolves_input_files(self) -> None:
        result = convert_latex_source(FIXTURE_ROOT / "synthetic_clean", allow_compile=False, min_chars=100)

        self.assertIn("## Methods", result.markdown)
        self.assertIn("regularized multinomial logistic regression", result.markdown)

    def test_malformed_tex_fails_cleanly_when_compile_disabled(self) -> None:
        with temporary_source_root("test_latex_convert") as source_dir:
            (source_dir / "main.tex").write_text(
                "\\documentclass{article}\\begin{document}\\section{Methods}Too short.\\end{document}",
                encoding="utf-8",
            )

            with self.assertRaises(LatexConversionError):
                convert_latex_source(source_dir, allow_compile=False, min_chars=100)


if __name__ == "__main__":
    unittest.main()
