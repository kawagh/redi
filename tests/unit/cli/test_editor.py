import os
from pathlib import Path

from redi.cli import editor as editor_module
from redi.cli.editor import open_editor, save_body_on_failure, save_text_to_tempfile


class TestOpenEditor:
    """open_editor は何を書くのか分かる名前の一時ファイルをエディタで開く"""

    def _spy_on_editor(self, monkeypatch) -> list[str]:
        """エディタ起動を差し替えて、開かれたファイルのパスを記録する"""
        opened: list[str] = []

        def fake_run(command, *args, **kwargs):
            opened.append(command[-1])

        monkeypatch.setattr(editor_module, "ensure_interactive", lambda *a, **k: None)
        monkeypatch.setattr(editor_module.subprocess, "run", fake_run)
        return opened

    def test_uses_name_as_filename_prefix(self, monkeypatch):
        """name を接頭辞にした .md ファイルを開く"""
        opened = self._spy_on_editor(monkeypatch)

        open_editor(name="issue_description")

        assert len(opened) == 1
        filename = Path(opened[0]).name
        assert filename.startswith("issue_description_")
        assert filename.endswith(".md")

    def test_name_distinguishes_purpose(self, monkeypatch):
        """用途ごとに別の名前を渡せる"""
        opened = self._spy_on_editor(monkeypatch)

        open_editor(name="issue_note")

        assert Path(opened[0]).name.startswith("issue_note_")

    def test_initial_text_is_written_to_the_file(self, monkeypatch):
        """初期テキストを書き込んだ状態でエディタに渡す"""
        written: list[str] = []

        def fake_run(command, *args, **kwargs):
            written.append(Path(command[-1]).read_text())

        monkeypatch.setattr(editor_module, "ensure_interactive", lambda *a, **k: None)
        monkeypatch.setattr(editor_module.subprocess, "run", fake_run)

        result = open_editor(initial_text="編集前の本文", name="issue_description")

        assert written == ["編集前の本文"]
        assert result == "編集前の本文"

    def test_removes_the_tempfile(self, monkeypatch):
        """エディタを閉じたあと一時ファイルは残さない"""
        opened = self._spy_on_editor(monkeypatch)

        open_editor(name="wiki_text")

        assert not Path(opened[0]).exists()


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
