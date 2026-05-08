import re
from datetime import date

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

from redi.cli.validator import (
    DateValidator,
    DueDateValidator,
    FloatValidator,
    HourValidator,
    IntValidator,
    RequiredValidator,
    UrlValidator,
)
from redi.i18n import messages


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

    def test_allow_empty_passes_empty(self):
        """allow_empty=True の場合、空文字は通る"""
        HourValidator(allow_empty=True).validate(Document(text=""))

    def test_allow_empty_still_rejects_invalid(self):
        """allow_empty=True でも数値以外はエラーになる"""
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_numeric_required)
        ):
            HourValidator(allow_empty=True).validate(Document(text="abc"))


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

    def test_allow_empty_passes_empty(self):
        """allow_empty=True の場合、空文字は通る"""
        IntValidator(allow_empty=True).validate(Document(text=""))

    def test_allow_empty_still_rejects_invalid(self):
        """allow_empty=True でも整数以外はエラーになる"""
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_numeric_required)
        ):
            IntValidator(allow_empty=True).validate(Document(text="1.5"))


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

    def test_allow_empty_passes_empty(self):
        """allow_empty=True の場合、空文字は通る"""
        DateValidator(allow_empty=True).validate(Document(text=""))

    def test_allow_empty_still_rejects_invalid_format(self):
        """allow_empty=True でも YYYY-MM-DD 以外は形式エラーになる"""
        with pytest.raises(ValidationError, match="YYYY-MM-DD"):
            DateValidator(allow_empty=True).validate(Document(text="2026/04/26"))


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
