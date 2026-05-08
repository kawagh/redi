import pytest

from redi.cli import _common
from redi.i18n import messages


class TestConfirmDelete:
    """confirm_delete()はyes/Noプロンプトで削除可否を確認する"""

    def test_accepts_yes(self, monkeypatch, capsys):
        """'yes'の入力なら例外なく処理が続行する"""
        monkeypatch.setattr(_common, "prompt", lambda _msg: "yes")
        _common.confirm_delete("削除するX: 1")
        out = capsys.readouterr().out
        assert "削除するX: 1" in out

    def test_accepts_yes_case_insensitive(self, monkeypatch):
        """大文字小文字と前後空白を許容する"""
        monkeypatch.setattr(_common, "prompt", lambda _msg: "  YES  ")
        _common.confirm_delete("summary")

    def test_rejects_no(self, monkeypatch, capsys):
        """'no'ならexit(1)してキャンセルメッセージを出力する"""
        monkeypatch.setattr(_common, "prompt", lambda _msg: "no")
        with pytest.raises(SystemExit) as exc:
            _common.confirm_delete("summary")
        assert exc.value.code == 1
        assert messages.canceled in capsys.readouterr().out

    def test_rejects_empty_input(self, monkeypatch):
        """空入力はキャンセル扱い（デフォルトNoの挙動）"""
        monkeypatch.setattr(_common, "prompt", lambda _msg: "")
        with pytest.raises(SystemExit) as exc:
            _common.confirm_delete("summary")
        assert exc.value.code == 1

    def test_rejects_other_inputs(self, monkeypatch):
        """'y'単体や関係ない文字列はキャンセル扱い"""
        for value in ["y", "ye", "n", "abc"]:
            monkeypatch.setattr(_common, "prompt", lambda _msg, v=value: v)
            with pytest.raises(SystemExit) as exc:
                _common.confirm_delete("summary")
            assert exc.value.code == 1

    def test_keyboard_interrupt_cancels(self, monkeypatch, capsys):
        """Ctrl-Cはキャンセル扱い"""

        def raise_interrupt(_msg):
            raise KeyboardInterrupt

        monkeypatch.setattr(_common, "prompt", raise_interrupt)
        with pytest.raises(SystemExit) as exc:
            _common.confirm_delete("summary")
        assert exc.value.code == 1
        assert messages.canceled in capsys.readouterr().out

    def test_eof_error_cancels(self, monkeypatch):
        """EOF(Ctrl-D)もキャンセル扱い"""

        def raise_eof(_msg):
            raise EOFError

        monkeypatch.setattr(_common, "prompt", raise_eof)
        with pytest.raises(SystemExit) as exc:
            _common.confirm_delete("summary")
        assert exc.value.code == 1


class TestConfirmDeleteWithIdentifier:
    """confirm_delete_with_identifier()は識別子の再入力で削除可否を確認する"""

    def test_accepts_matching_identifier(self, monkeypatch, capsys):
        """識別子が一致すれば例外なく処理が続行する"""
        monkeypatch.setattr(_common, "prompt", lambda _msg: "my-project")
        _common.confirm_delete_with_identifier(
            "削除するプロジェクト: 1 My Project", "my-project", "プロジェクト識別子"
        )
        assert "削除するプロジェクト: 1 My Project" in capsys.readouterr().out

    def test_trims_whitespace(self, monkeypatch):
        """前後空白は無視する"""
        monkeypatch.setattr(_common, "prompt", lambda _msg: "  my-project  ")
        _common.confirm_delete_with_identifier(
            "summary", "my-project", "プロジェクト識別子"
        )

    def test_is_case_sensitive(self, monkeypatch):
        """識別子の比較は大文字小文字を区別する"""
        monkeypatch.setattr(_common, "prompt", lambda _msg: "MY-PROJECT")
        with pytest.raises(SystemExit) as exc:
            _common.confirm_delete_with_identifier(
                "summary", "my-project", "プロジェクト識別子"
            )
        assert exc.value.code == 1

    def test_rejects_mismatched_identifier(self, monkeypatch, capsys):
        """識別子が一致しなければexit(1)してメッセージを出力する"""
        monkeypatch.setattr(_common, "prompt", lambda _msg: "wrong-id")
        with pytest.raises(SystemExit) as exc:
            _common.confirm_delete_with_identifier(
                "summary", "my-project", "プロジェクト識別子"
            )
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert (
            messages.canceled_field_mismatch.format(field="プロジェクト識別子") in out
        )

    def test_rejects_empty_input(self, monkeypatch):
        """空入力は不一致扱い"""
        monkeypatch.setattr(_common, "prompt", lambda _msg: "")
        with pytest.raises(SystemExit) as exc:
            _common.confirm_delete_with_identifier(
                "summary", "my-project", "プロジェクト識別子"
            )
        assert exc.value.code == 1

    def test_keyboard_interrupt_cancels(self, monkeypatch, capsys):
        """Ctrl-Cはキャンセル扱い"""

        def raise_interrupt(_msg):
            raise KeyboardInterrupt

        monkeypatch.setattr(_common, "prompt", raise_interrupt)
        with pytest.raises(SystemExit) as exc:
            _common.confirm_delete_with_identifier(
                "summary", "my-project", "プロジェクト識別子"
            )
        assert exc.value.code == 1
        assert messages.canceled in capsys.readouterr().out

    def test_prompt_message_includes_identifier_and_label(self, monkeypatch):
        """プロンプト文字列に識別子とフィールドラベルが含まれる"""
        captured: dict[str, str] = {}

        def capture_prompt(msg: str) -> str:
            captured["msg"] = msg
            return "my-project"

        monkeypatch.setattr(_common, "prompt", capture_prompt)
        _common.confirm_delete_with_identifier(
            "summary", "my-project", "プロジェクト識別子"
        )
        assert "プロジェクト識別子" in captured["msg"]
        assert "my-project" in captured["msg"]
