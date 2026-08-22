import re
from datetime import date
from typing import cast

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError, Validator

from redi.api.custom_field import CustomField
from redi.cli.validator import (
    CompositeValidator,
    DateValidator,
    DueDateValidator,
    FloatValidator,
    HourValidator,
    IntValidator,
    MaxLengthValidator,
    MinLengthValidator,
    RegexpValidator,
    RequiredValidator,
    UrlValidator,
    build_custom_field_validator,
    check_custom_field_constraints,
)
from redi.i18n import messages


def custom_field(
    min_length: int | None = None,
    max_length: int | None = None,
    regexp: str = "",
) -> CustomField:
    """制約だけを持つカスタムフィールドを組み立てるテスト用ヘルパー。"""
    return cast(
        CustomField,
        {"min_length": min_length, "max_length": max_length, "regexp": regexp},
    )


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


class TestCompositeValidator:
    """CompositeValidator()は複数の Validator を宣言順に適用する"""

    def test_all_pass(self):
        """すべての Validator を満たせば通る"""
        CompositeValidator(RequiredValidator(), MinLengthValidator(3)).validate(
            Document(text="abc")
        )

    def test_first_failure_is_raised(self):
        """複数が違反していても宣言順で最初のものが送出される"""
        composite = CompositeValidator(MinLengthValidator(3), RegexpValidator(r"^\d+$"))
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_min_length.format(min=3))
        ):
            composite.validate(Document(text="a"))

    def test_no_validators_passes(self):
        """Validator が空なら常に通る"""
        CompositeValidator().validate(Document(text="anything"))

    def test_later_validator_is_not_evaluated_after_failure(self):
        """先の Validator が落ちたら後続は評価しない"""

        class ExplodingValidator(Validator):
            def validate(self, document: Document) -> None:
                raise AssertionError("評価されてはいけない")

        composite = CompositeValidator(MinLengthValidator(3), ExplodingValidator())
        with pytest.raises(ValidationError):
            composite.validate(Document(text="a"))


class TestMinLengthValidator:
    """MinLengthValidator()は min_length 以上の長さを要求する"""

    @pytest.mark.parametrize("text", ["abc", "abcd"])
    def test_satisfied_passes(self, text: str):
        """min_length 以上の長さなら通る"""
        MinLengthValidator(3).validate(Document(text=text))

    def test_violation_raises(self):
        """min_length より短ければエラーになる"""
        expected = re.escape(messages.error_min_length.format(min=3))
        with pytest.raises(ValidationError, match=expected):
            MinLengthValidator(3).validate(Document(text="ab"))

    def test_empty_text_passes(self):
        """空文字は未入力として必須チェック側に委ねるため通す"""
        MinLengthValidator(3).validate(Document(text=""))

    def test_none_disables_check(self):
        """min_length が未設定(None)なら短い入力でも通る"""
        MinLengthValidator(None).validate(Document(text="a"))

    def test_surrounding_whitespace_is_stripped(self):
        """前後の空白は除去してから長さを数えるため、空白で長さは稼げない"""
        with pytest.raises(ValidationError):
            MinLengthValidator(3).validate(Document(text="a    "))

    def test_whitespace_only_is_treated_as_empty(self):
        """空白のみは空文字として扱い、制約の対象外にする"""
        MinLengthValidator(3).validate(Document(text="   "))


class TestMaxLengthValidator:
    """MaxLengthValidator()は max_length 以下の長さを要求する"""

    @pytest.mark.parametrize("text", ["abc", "ab"])
    def test_satisfied_passes(self, text: str):
        """max_length 以下の長さなら通る"""
        MaxLengthValidator(3).validate(Document(text=text))

    def test_violation_raises(self):
        """max_length より長ければエラーになる"""
        expected = re.escape(messages.error_max_length.format(max=3))
        with pytest.raises(ValidationError, match=expected):
            MaxLengthValidator(3).validate(Document(text="abcd"))

    def test_empty_text_passes(self):
        """空文字は未入力として必須チェック側に委ねるため通す"""
        MaxLengthValidator(3).validate(Document(text=""))

    def test_none_disables_check(self):
        """max_length が未設定(None)なら長い入力でも通る"""
        MaxLengthValidator(None).validate(Document(text="a" * 100))

    def test_surrounding_whitespace_is_stripped(self):
        """前後の空白は除去してから長さを数える"""
        MaxLengthValidator(3).validate(Document(text="  abc  "))


class TestRegexpValidator:
    """RegexpValidator()は regexp への部分一致を要求する"""

    def test_match_passes(self):
        """regexp に一致すれば通る"""
        RegexpValidator(r"^\d+$").validate(Document(text="12345"))

    def test_mismatch_raises(self):
        """regexp に一致しなければエラーになる"""
        expected = re.escape(messages.error_regexp_mismatch.format(regexp=r"^\d+$"))
        with pytest.raises(ValidationError, match=expected):
            RegexpValidator(r"^\d+$").validate(Document(text="abc"))

    def test_message_includes_the_pattern(self):
        """何を入力すべきか分かるよう、エラーメッセージにパターンを含める"""
        with pytest.raises(ValidationError, match=re.escape(r"^[0-9]{3,5}$")):
            RegexpValidator(r"^[0-9]{3,5}$").validate(Document(text="12"))

    def test_uses_search_not_fullmatch(self):
        """regexp は部分一致 (re.search) で評価される"""
        RegexpValidator(r"foo").validate(Document(text="xxfooxx"))

    def test_empty_text_passes(self):
        """空文字は未入力として必須チェック側に委ねるため通す"""
        RegexpValidator(r"^\d+$").validate(Document(text=""))

    @pytest.mark.parametrize("regexp", ["", None])
    def test_blank_regexp_disables_check(self, regexp: str | None):
        """regexp が未設定なら任意の入力が通る"""
        RegexpValidator(regexp).validate(Document(text="anything"))

    def test_invalid_regexp_is_ignored(self):
        """正規表現として不正な文字列が来ても例外にせず無視する"""
        RegexpValidator("[unclosed").validate(Document(text="anything"))

    def test_surrounding_whitespace_is_stripped(self):
        """前後の空白は除去してから照合する"""
        RegexpValidator(r"^\d+$").validate(Document(text="  123  "))


class TestBuildCustomFieldValidator:
    """build_custom_field_validator()はカスタムフィールドの制約を Validator に組み立てる"""

    def test_no_constraints_passes_any_text(self):
        """制約なしの場合は任意の入力が通る"""
        build_custom_field_validator(custom_field()).validate(Document(text="hello"))

    def test_constraints_are_checked_in_min_max_regexp_order(self):
        """複数違反しているときは min_length -> max_length -> regexp の順で報告される"""
        validator = build_custom_field_validator(
            custom_field(min_length=3, max_length=10, regexp=r"^\d+$")
        )
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_min_length.format(min=3))
        ):
            validator.validate(Document(text="a"))

    def test_regexp_violation_raises(self):
        """min/max を満たしていても regexp 違反はエラーになる"""
        validator = build_custom_field_validator(
            custom_field(min_length=3, max_length=10, regexp=r"^\d+$")
        )
        with pytest.raises(
            ValidationError,
            match=re.escape(messages.error_regexp_mismatch.format(regexp=r"^\d+$")),
        ):
            validator.validate(Document(text="abcd"))

    def test_surrounding_whitespace_is_stripped(self):
        """prompt は strip した値を送るため、strip 後の値で制約を評価する"""
        validator = build_custom_field_validator(custom_field(min_length=3))
        with pytest.raises(ValidationError):
            validator.validate(Document(text="  ab  "))

    def test_base_validator_is_applied_first(self):
        """base Validator が指定されていれば制約より先に適用される（必須チェックなど）"""
        validator = build_custom_field_validator(
            custom_field(min_length=3), base=RequiredValidator()
        )
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_input_required)
        ):
            validator.validate(Document(text=""))

    def test_base_validator_passes_then_constraint_checks(self):
        """base Validator を通過したあとに長さ等の制約が評価される"""
        validator = build_custom_field_validator(
            custom_field(min_length=3), base=RequiredValidator()
        )
        validator.validate(Document(text="abc"))
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_min_length.format(min=3))
        ):
            validator.validate(Document(text="ab"))

    def test_empty_text_passes_without_base_validator(self):
        """base が無ければ空文字は呼び出し側のキャンセル扱いとして通す"""
        build_custom_field_validator(
            custom_field(min_length=5, max_length=10, regexp=r"^\d+$")
        ).validate(Document(text=""))


class TestCheckCustomFieldConstraints:
    """check_custom_field_constraints() は editor 経由など prompt を介さないフローで制約を検証する"""

    def test_empty_text_returns_none(self):
        """空文字は呼び出し側に委ねるため常に None"""
        assert (
            check_custom_field_constraints(
                custom_field(min_length=3, max_length=10, regexp=r"^\d+$"), ""
            )
            is None
        )

    def test_no_constraints_returns_none(self):
        """制約がなければ None"""
        assert check_custom_field_constraints(custom_field(), "anything") is None

    def test_min_length_violation_returns_message(self):
        """min_length 違反でエラーメッセージを返す"""
        assert check_custom_field_constraints(
            custom_field(min_length=3), "ab"
        ) == messages.error_min_length.format(min=3)

    def test_max_length_violation_returns_message(self):
        """max_length 違反でエラーメッセージを返す"""
        assert check_custom_field_constraints(
            custom_field(max_length=3), "abcd"
        ) == messages.error_max_length.format(max=3)

    def test_regexp_violation_returns_message(self):
        """regexp 違反でエラーメッセージを返す"""
        assert check_custom_field_constraints(
            custom_field(regexp=r"^\d+$"), "abc"
        ) == messages.error_regexp_mismatch.format(regexp=r"^\d+$")

    def test_all_satisfied_returns_none(self):
        """すべて満たしていれば None"""
        assert (
            check_custom_field_constraints(
                custom_field(min_length=3, max_length=10, regexp=r"^[a-z]+$"), "abcd"
            )
            is None
        )

    def test_invalid_regexp_is_ignored(self):
        """不正な正規表現は無視して None を返す"""
        assert (
            check_custom_field_constraints(custom_field(regexp="[unclosed"), "anything")
            is None
        )
