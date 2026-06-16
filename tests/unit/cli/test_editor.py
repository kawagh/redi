import os
from pathlib import Path

from redi.cli.editor import save_text_to_tempfile


class TestSaveTextToTempfile:
    """save_text_to_tempfile はテキストを削除されない一時ファイルへ保存する"""

    def test_writes_text_and_returns_path(self):
        """書き込んだ内容が保存され、パスが返る"""
        text = "保存したい本文\n複数行"
        path = save_text_to_tempfile(text)
        try:
            assert Path(path).read_text() == text
            assert path.endswith(".md")
        finally:
            os.unlink(path)

    def test_file_is_not_deleted(self):
        """呼び出し後もファイルが残っている(open_editor と異なり削除しない)"""
        path = save_text_to_tempfile("残るべき内容")
        try:
            assert Path(path).exists()
        finally:
            os.unlink(path)
