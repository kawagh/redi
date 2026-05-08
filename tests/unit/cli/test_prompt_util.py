from dataclasses import dataclass

import pytest
from prompt_toolkit.buffer import Buffer

from redi.cli import prompt_util
from redi.cli.prompt_util import (
    digit_and_period_key_bindings,
    digit_only_key_bindings,
)
from redi.i18n import messages


# prompt_toolkit.key_binding.key_processor.KeyPressEvent の duck-type。
# handler が参照する data と current_buffer のみを持つ最小実装。
@dataclass
class _FakeKeyPressEvent:
    data: str
    current_buffer: Buffer


def _invoke(kb, data: str, initial: str = "") -> str:
    buffer = Buffer()
    if initial:
        buffer.insert_text(initial)
    kb.bindings[0].handler(_FakeKeyPressEvent(data=data, current_buffer=buffer))
    return buffer.text


class TestDigitAndPeriodKeyBindings:
    """digit_and_period_key_bindings()は数字とperiodのみを入力可能にする"""

    @pytest.mark.parametrize("ch", list("0123456789"))
    def test_digits_are_inserted(self, ch: str):
        """数字はすべてバッファに挿入される"""
        assert _invoke(digit_and_period_key_bindings(), ch) == ch

    def test_period_is_inserted(self):
        """periodはバッファに挿入される"""
        assert _invoke(digit_and_period_key_bindings(), ".") == "."

    @pytest.mark.parametrize("ch", ["a", "Z", "-", "+", " ", ",", "/", "*"])
    def test_non_digit_non_period_are_rejected(self, ch: str):
        """数字とperiod以外はバッファに挿入されない"""
        assert _invoke(digit_and_period_key_bindings(), ch) == ""

    def test_appends_to_existing_text(self):
        """既存のバッファ内容の末尾に追加される"""
        assert _invoke(digit_and_period_key_bindings(), "5", initial="1.") == "1.5"

    def test_rejected_input_preserves_existing_text(self):
        """拒否された入力は既存バッファを変更しない"""
        assert _invoke(digit_and_period_key_bindings(), "a", initial="12") == "12"


class TestDigitOnlyKeyBindings:
    """digit_only_key_bindings()は数字のみを入力可能にする"""

    @pytest.mark.parametrize("ch", list("0123456789"))
    def test_digits_are_inserted(self, ch: str):
        """数字はすべてバッファに挿入される"""
        assert _invoke(digit_only_key_bindings(), ch) == ch

    def test_period_is_rejected(self):
        """periodはバッファに挿入されない"""
        assert _invoke(digit_only_key_bindings(), ".") == ""

    @pytest.mark.parametrize("ch", ["a", "Z", "-", "+", " ", ",", "/", "*"])
    def test_non_digit_are_rejected(self, ch: str):
        """数字以外はバッファに挿入されない"""
        assert _invoke(digit_only_key_bindings(), ch) == ""

    def test_appends_to_existing_text(self):
        """既存のバッファ内容の末尾に追加される"""
        assert _invoke(digit_only_key_bindings(), "3", initial="12") == "123"

    def test_rejected_input_preserves_existing_text(self):
        """拒否された入力は既存バッファを変更しない"""
        assert _invoke(digit_only_key_bindings(), ".", initial="12") == "12"


class TestConfirmDelete:
    """confirm_delete()はyes/Noプロンプトで削除可否を確認する"""

    def test_accepts_yes(self, monkeypatch, capsys):
        """'yes'の入力なら例外なく処理が続行する"""
        monkeypatch.setattr(prompt_util, "prompt", lambda _msg: "yes")
        prompt_util.confirm_delete("削除するX: 1")
        out = capsys.readouterr().out
        assert "削除するX: 1" in out

    def test_accepts_yes_case_insensitive(self, monkeypatch):
        """大文字小文字と前後空白を許容する"""
        monkeypatch.setattr(prompt_util, "prompt", lambda _msg: "  YES  ")
        prompt_util.confirm_delete("summary")

    def test_rejects_no(self, monkeypatch, capsys):
        """'no'ならexit(1)してキャンセルメッセージを出力する"""
        monkeypatch.setattr(prompt_util, "prompt", lambda _msg: "no")
        with pytest.raises(SystemExit) as exc:
            prompt_util.confirm_delete("summary")
        assert exc.value.code == 1
        assert messages.canceled in capsys.readouterr().out

    def test_rejects_empty_input(self, monkeypatch):
        """空入力はキャンセル扱い（デフォルトNoの挙動）"""
        monkeypatch.setattr(prompt_util, "prompt", lambda _msg: "")
        with pytest.raises(SystemExit) as exc:
            prompt_util.confirm_delete("summary")
        assert exc.value.code == 1

    def test_rejects_other_inputs(self, monkeypatch):
        """'y'単体や関係ない文字列はキャンセル扱い"""
        for value in ["y", "ye", "n", "abc"]:
            monkeypatch.setattr(prompt_util, "prompt", lambda _msg, v=value: v)
            with pytest.raises(SystemExit) as exc:
                prompt_util.confirm_delete("summary")
            assert exc.value.code == 1

    def test_keyboard_interrupt_cancels(self, monkeypatch, capsys):
        """Ctrl-Cはキャンセル扱い"""

        def raise_interrupt(_msg):
            raise KeyboardInterrupt

        monkeypatch.setattr(prompt_util, "prompt", raise_interrupt)
        with pytest.raises(SystemExit) as exc:
            prompt_util.confirm_delete("summary")
        assert exc.value.code == 1
        assert messages.canceled in capsys.readouterr().out

    def test_eof_error_cancels(self, monkeypatch):
        """EOF(Ctrl-D)もキャンセル扱い"""

        def raise_eof(_msg):
            raise EOFError

        monkeypatch.setattr(prompt_util, "prompt", raise_eof)
        with pytest.raises(SystemExit) as exc:
            prompt_util.confirm_delete("summary")
        assert exc.value.code == 1


class TestConfirmDeleteWithIdentifier:
    """confirm_delete_with_identifier()は識別子の再入力で削除可否を確認する"""

    def test_accepts_matching_identifier(self, monkeypatch, capsys):
        """識別子が一致すれば例外なく処理が続行する"""
        monkeypatch.setattr(prompt_util, "prompt", lambda _msg: "my-project")
        prompt_util.confirm_delete_with_identifier(
            "削除するプロジェクト: 1 My Project", "my-project", "プロジェクト識別子"
        )
        assert "削除するプロジェクト: 1 My Project" in capsys.readouterr().out

    def test_trims_whitespace(self, monkeypatch):
        """前後空白は無視する"""
        monkeypatch.setattr(prompt_util, "prompt", lambda _msg: "  my-project  ")
        prompt_util.confirm_delete_with_identifier(
            "summary", "my-project", "プロジェクト識別子"
        )

    def test_is_case_sensitive(self, monkeypatch):
        """識別子の比較は大文字小文字を区別する"""
        monkeypatch.setattr(prompt_util, "prompt", lambda _msg: "MY-PROJECT")
        with pytest.raises(SystemExit) as exc:
            prompt_util.confirm_delete_with_identifier(
                "summary", "my-project", "プロジェクト識別子"
            )
        assert exc.value.code == 1

    def test_rejects_mismatched_identifier(self, monkeypatch, capsys):
        """識別子が一致しなければexit(1)してメッセージを出力する"""
        monkeypatch.setattr(prompt_util, "prompt", lambda _msg: "wrong-id")
        with pytest.raises(SystemExit) as exc:
            prompt_util.confirm_delete_with_identifier(
                "summary", "my-project", "プロジェクト識別子"
            )
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert (
            messages.canceled_field_mismatch.format(field="プロジェクト識別子") in out
        )

    def test_rejects_empty_input(self, monkeypatch):
        """空入力は不一致扱い"""
        monkeypatch.setattr(prompt_util, "prompt", lambda _msg: "")
        with pytest.raises(SystemExit) as exc:
            prompt_util.confirm_delete_with_identifier(
                "summary", "my-project", "プロジェクト識別子"
            )
        assert exc.value.code == 1

    def test_keyboard_interrupt_cancels(self, monkeypatch, capsys):
        """Ctrl-Cはキャンセル扱い"""

        def raise_interrupt(_msg):
            raise KeyboardInterrupt

        monkeypatch.setattr(prompt_util, "prompt", raise_interrupt)
        with pytest.raises(SystemExit) as exc:
            prompt_util.confirm_delete_with_identifier(
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

        monkeypatch.setattr(prompt_util, "prompt", capture_prompt)
        prompt_util.confirm_delete_with_identifier(
            "summary", "my-project", "プロジェクト識別子"
        )
        assert "プロジェクト識別子" in captured["msg"]
        assert "my-project" in captured["msg"]
