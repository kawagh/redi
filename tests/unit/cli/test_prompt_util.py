from dataclasses import dataclass
from datetime import date

import pytest
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

import re

from redi.cli import prompt_util
from redi.cli.prompt_util import (
    DateValidator,
    DueDateValidator,
    FloatValidator,
    HourValidator,
    IntValidator,
    RequiredValidator,
    UrlValidator,
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


class TestRequiredValidator:
    """RequiredValidator()は空文字（空白のみ）を拒否する"""

    @pytest.mark.parametrize("text", ["a", "  hello  ", "0", "あ"])
    def test_non_empty_passes(self, text: str):
        """非空白文字を含む入力は通る"""
        RequiredValidator().validate(Document(text=text))

    @pytest.mark.parametrize("text", ["", " ", "   ", "\t"])
    def test_empty_or_whitespace_raises_required(self, text: str):
        """空文字や空白のみは『入力してください』でエラーになる"""
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_input_required)
        ):
            RequiredValidator().validate(Document(text=text))


class TestUrlValidator:
    """UrlValidator()はhttp(s)://で始まるURLを検証する"""

    @pytest.mark.parametrize(
        "text",
        [
            "http://example.com",
            "https://example.com",
            "https://example.com:3000/redmine",
            "http://localhost:3000",
        ],
    )
    def test_complete_url_passes(self, text: str):
        """http(s)://で始まる完成形URLはエラーにならない"""
        UrlValidator().validate(Document(text=text))

    @pytest.mark.parametrize(
        "text",
        [
            "h",
            "ht",
            "htt",
            "http",
            "http:",
            "http:/",
            "https",
            "https:",
            "https:/",
        ],
    )
    def test_prefix_in_progress_passes(self, text: str):
        """プレフィックス入力途中はエラーにならない"""
        UrlValidator().validate(Document(text=text))

    def test_surrounding_whitespace_is_stripped(self):
        """前後の空白は無視して評価される"""
        UrlValidator().validate(Document(text="  http://example.com  "))

    @pytest.mark.parametrize("text", ["", " "])
    def test_empty_or_whitespace_raises_required(self, text: str):
        """空文字や空白のみは『入力してください』でエラーになる"""
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_input_required)
        ):
            UrlValidator().validate(Document(text=text))

    @pytest.mark.parametrize(
        "text",
        [
            "http:/example.com",
            "http//example.com",
        ],
    )
    def test_invalid_prefix_raises(self, text: str):
        """プレフィックスがhttp(s)://以外ならURLメッセージでエラーになる"""
        with pytest.raises(ValidationError, match="http://"):
            UrlValidator().validate(Document(text=text))


class TestHourValidator:
    """HourValidator()は工数入力を整数または小数1個までの数値に制限する"""

    @pytest.mark.parametrize("text", ["0", "1", "1.5", "12.34", "100", "0.5"])
    def test_valid_numbers_pass(self, text: str):
        """整数・小数の数値は通る"""
        HourValidator().validate(Document(text=text))

    @pytest.mark.parametrize("text", ["", "abc", "1.5h", "1,5", "-1", "1..5", "1.2.3"])
    def test_invalid_inputs_raise(self, text: str):
        """空文字や数値以外（記号・複数小数点・単位付きなど）はエラーになる"""
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_numeric_required)
        ):
            HourValidator().validate(Document(text=text))


class TestIntValidator:
    """IntValidator()は符号付き整数を許容する"""

    @pytest.mark.parametrize("text", ["0", "1", "100", "-1", "-100"])
    def test_valid_numbers_pass(self, text: str):
        """正負の整数は通る"""
        IntValidator().validate(Document(text=text))

    def test_surrounding_whitespace_is_stripped(self):
        """前後の空白は無視して評価される"""
        IntValidator().validate(Document(text="  -1  "))

    @pytest.mark.parametrize(
        "text",
        ["", " ", "abc", "1.5", "1,5", "+1", "--1", "1-"],
    )
    def test_invalid_inputs_raise(self, text: str):
        """空文字や数値以外、小数や不正な符号位置はエラーになる"""
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_numeric_required)
        ):
            IntValidator().validate(Document(text=text))


class TestFloatValidator:
    """FloatValidator()は符号付き整数・小数を許容する"""

    @pytest.mark.parametrize(
        "text", ["0", "1", "1.5", "12.34", "100", "0.5", "-1", "-1.5", "-0.5"]
    )
    def test_valid_numbers_pass(self, text: str):
        """正負の整数・小数は通る"""
        FloatValidator().validate(Document(text=text))

    def test_surrounding_whitespace_is_stripped(self):
        """前後の空白は無視して評価される"""
        FloatValidator().validate(Document(text="  -1.5  "))

    @pytest.mark.parametrize(
        "text",
        ["", " ", "abc", "1.5h", "1,5", "1..5", "1.2.3", "+1", ".5", "1.", "--1"],
    )
    def test_invalid_inputs_raise(self, text: str):
        """空文字や数値以外、不完全な数値表記はエラーになる"""
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_numeric_required)
        ):
            FloatValidator().validate(Document(text=text))


class TestDateValidator:
    """DateValidator()は YYYY-MM-DD 形式の日付を許容する"""

    def test_empty_string_raises(self):
        """空文字は入力必須エラーになる"""
        with pytest.raises(ValidationError):
            DateValidator().validate(Document(text=""))

    def test_surrounding_whitespace_is_stripped(self):
        """前後の空白は無視して評価される"""
        DateValidator().validate(Document(text="  2026-04-26  "))

    @pytest.mark.parametrize("text", ["2026-04-26", "2026-12-31", "1999-01-01"])
    def test_valid_date_passes(self, text: str):
        """任意の YYYY-MM-DD は通る"""
        DateValidator().validate(Document(text=text))

    @pytest.mark.parametrize(
        "text",
        ["2026/04/26", "26-04-26", "2026-4-26", "abc", "2026-04"],
    )
    def test_invalid_format_raises(self, text: str):
        """YYYY-MM-DD 形式に合わない入力は形式エラーになる"""
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            DateValidator().validate(Document(text=text))

    @pytest.mark.parametrize(
        "text",
        ["2026-13-01", "2026-02-30", "2026-00-10"],
    )
    def test_calendar_invalid_date_raises(self, text: str):
        """形式は合っていてもカレンダー上不正な日付は形式エラーになる"""
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            DateValidator().validate(Document(text=text))


class TestDueDateValidator:
    """DueDateValidator()は期日入力を YYYY-MM-DD 形式かつ開始日以降に制限する"""

    def test_empty_string_passes(self):
        """空文字は『クリア』として常に通る"""
        DueDateValidator(start_date=date(2026, 4, 26)).validate(Document(text=""))

    def test_surrounding_whitespace_is_stripped(self):
        """前後の空白は無視して評価される"""
        DueDateValidator(start_date=None).validate(Document(text="  2026-04-26  "))

    @pytest.mark.parametrize(
        "text",
        ["2026-04-26", "2026-12-31", "1999-01-01"],
    )
    def test_valid_date_without_start_date_passes(self, text: str):
        """開始日が無ければ任意の YYYY-MM-DD は通る"""
        DueDateValidator(start_date=None).validate(Document(text=text))

    def test_date_after_start_date_passes(self):
        """開始日より後の日付は通る"""
        DueDateValidator(start_date=date(2026, 4, 26)).validate(
            Document(text="2026-04-27")
        )

    def test_date_equal_to_start_date_passes(self):
        """開始日と同日は通る（境界値）"""
        DueDateValidator(start_date=date(2026, 4, 26)).validate(
            Document(text="2026-04-26")
        )

    def test_date_before_start_date_raises(self):
        """開始日より前の日付は『開始日 ... 以降』エラーになる"""
        expected = re.escape(messages.error_date_after_start.format(date="2026-04-26"))
        with pytest.raises(ValidationError, match=expected):
            DueDateValidator(start_date=date(2026, 4, 26)).validate(
                Document(text="2026-04-25")
            )

    @pytest.mark.parametrize(
        "text",
        ["2026/04/26", "26-04-26", "2026-4-26", "abc", "2026-04"],
    )
    def test_invalid_format_raises(self, text: str):
        """YYYY-MM-DD 形式に合わない入力は形式エラーになる"""
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            DueDateValidator(start_date=None).validate(Document(text=text))

    @pytest.mark.parametrize(
        "text",
        ["2026-13-01", "2026-02-30", "2026-00-10"],
    )
    def test_calendar_invalid_date_raises(self, text: str):
        """形式は合っていてもカレンダー上不正な日付は形式エラーになる"""
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            DueDateValidator(start_date=None).validate(Document(text=text))


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
