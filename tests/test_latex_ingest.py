from __future__ import annotations

import io
import tarfile
import unittest
import zipfile

from backend.parsing.latex_ingest import LatexArchiveError, find_main_tex, temporary_source_root, unpack_upload_bytes


class LatexIngestTests(unittest.TestCase):
    def test_rejects_archive_path_traversal(self) -> None:
        with temporary_source_root("test_latex_ingest") as tmp:
            buffer = io.BytesIO()
            payload = b"\\documentclass{article}\\begin{document}Bad\\end{document}"
            with tarfile.open(fileobj=buffer, mode="w") as archive:
                info = tarfile.TarInfo("../evil.tex")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))

            with self.assertRaises(LatexArchiveError):
                unpack_upload_bytes("bad.tar", buffer.getvalue(), dest_root=tmp)

            self.assertFalse((tmp.parent / "evil.tex").exists())

    def test_picks_named_main_tex_over_smaller_supplement(self) -> None:
        with temporary_source_root("test_latex_ingest") as tmp:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr(
                    "supplement.tex",
                    "\\documentclass{article}\\begin{document}Supplement\\end{document}",
                )
                archive.writestr(
                    "paper.tex",
                    "\\documentclass{article}\\title{Main}\\begin{document}"
                    + ("Main body. " * 120)
                    + "\\end{document}",
                )

            source_dir = unpack_upload_bytes("source.zip", buffer.getvalue(), dest_root=tmp)

            self.assertEqual(find_main_tex(source_dir).name, "paper.tex")


if __name__ == "__main__":
    unittest.main()
