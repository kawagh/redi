from dataclasses import dataclass
from datetime import date

import pytest
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

from redi.cli.prompt_util import (
    DueDateValidator,
    UrlValidator,
    digit_and_period_key_bindings,
    digit_only_key_bindings,
)


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
        with pytest.raises(ValidationError, match="入力してください"):
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
        with pytest.raises(ValidationError, match="開始日 2026-04-26 以降"):
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
