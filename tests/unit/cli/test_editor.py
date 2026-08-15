import os
from pathlib import Path

from redi.cli import editor as editor_module
from redi.cli.editor import save_body_on_failure, save_text_to_tempfile


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


class TestSaveBodyOnFailure:
    """save_body_on_failure は本文を退避し、保存先を通知する"""

    def test_saves_non_empty_body(self, monkeypatch, capsys):
        """本文があれば一時ファイルへ保存し、パスを出力する"""
        saved: list[str] = []

        def fake_save(text: str) -> str:
            saved.append(text)
            return "/tmp/redi-test.md"

        monkeypatch.setattr(editor_module, "save_text_to_tempfile", fake_save)
        save_body_on_failure("失われたくない本文")

        assert saved == ["失われたくない本文"]
        assert "/tmp/redi-test.md" in capsys.readouterr().out

    def test_skips_empty_body(self, monkeypatch, capsys):
        """本文が空なら保存もせず、何も出力しない"""
        called = False

        def fake_save(text: str) -> str:
            nonlocal called
            called = True
            return "x"

        monkeypatch.setattr(editor_module, "save_text_to_tempfile", fake_save)
        save_body_on_failure("")

        assert called is False
        assert capsys.readouterr().out == ""

    def test_round_trip_with_real_helper(self):
        """実際の save_text_to_tempfile 経由で本文がファイルに残る"""
        path = save_text_to_tempfile("round trip")
        try:
            assert Path(path).read_text() == "round trip"
        finally:
            os.unlink(path)
