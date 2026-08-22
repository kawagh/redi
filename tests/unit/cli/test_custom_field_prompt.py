import re
from typing import Any, cast

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError, Validator

from redi.api.custom_field import CustomField
from redi.cli import custom_field_prompt
from redi.cli.custom_field_prompt import prompt_custom_field_value
from redi.i18n import messages


def custom_field(field_format: str, **constraints: Any) -> CustomField:
    """指定した field_format と制約を持つカスタムフィールドを組み立てる。"""
    return cast(
        CustomField,
        {
            "name": "cf",
            "field_format": field_format,
            "multiple": False,
            "default_value": "",
            "min_length": constraints.get("min_length"),
            "max_length": constraints.get("max_length"),
            "regexp": constraints.get("regexp", ""),
        },
    )


@pytest.fixture
def captured_validator(monkeypatch: pytest.MonkeyPatch):
    """prompt に渡された Validator を捕まえて返すフィクスチャ。"""
    captured: list[Validator] = []

    def fake_prompt(_message: str, validator: Validator, default: str = "") -> str:
        captured.append(validator)
        return default

    monkeypatch.setattr(custom_field_prompt, "prompt", fake_prompt)

    def run(cf: CustomField) -> Validator:
        prompt_custom_field_value(cf, project_id="1")
        return captured[-1]

    return run


# field_format 自体は満たすが制約に触れる入力
FORMAT_AND_TEXT = [
    ("string", "1234"),
    ("link", "1234"),
    ("int", "1234"),
    ("float", "1234"),
]


class TestFreeInputFormatsUseConstraints:
    """自由入力の field_format は min_length/max_length/regexp を送信前に検証する"""

    @pytest.mark.parametrize(("field_format", "text"), FORMAT_AND_TEXT)
    def test_max_length_is_checked(
        self, captured_validator, field_format: str, text: str
    ):
        """max_length を超える入力はエラーになる"""
        validator = captured_validator(custom_field(field_format, max_length=3))
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_max_length.format(max=3))
        ):
            validator.validate(Document(text=text))

    @pytest.mark.parametrize(("field_format", "text"), FORMAT_AND_TEXT)
    def test_min_length_is_checked(
        self, captured_validator, field_format: str, text: str
    ):
        """min_length に満たない入力はエラーになる"""
        validator = captured_validator(custom_field(field_format, min_length=10))
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_min_length.format(min=10))
        ):
            validator.validate(Document(text=text))

    @pytest.mark.parametrize(
        ("field_format", "text"),
        [*FORMAT_AND_TEXT, ("date", "2026-04-26")],
    )
    def test_regexp_is_checked(self, captured_validator, field_format: str, text: str):
        """regexp に一致しない入力はエラーになる"""
        validator = captured_validator(custom_field(field_format, regexp=r"^9"))
        with pytest.raises(
            ValidationError,
            match=re.escape(messages.error_regexp_mismatch.format(regexp=r"^9")),
        ):
            validator.validate(Document(text=text))

    def test_format_check_precedes_constraints(self, captured_validator):
        """field_format 自体の検証は制約より先に効く"""
        validator = captured_validator(custom_field("int", min_length=3))
        with pytest.raises(
            ValidationError, match=re.escape(messages.error_numeric_required)
        ):
            validator.validate(Document(text="abc"))

    def test_valid_input_passes(self, captured_validator):
        """format と制約の両方を満たす入力は通る"""
        validator = captured_validator(
            custom_field("int", min_length=3, max_length=5, regexp=r"^\d+$")
        )
        validator.validate(Document(text="1234"))


class TestTextFormatUsesConstraints:
    """text はエディタ入力のため、閉じたあとに制約を検証して開き直す"""

    def test_violating_input_reopens_editor(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        """max_length を超えていたらエラーを出してエディタを開き直す"""
        inputs = iter(["1234", "12"])
        monkeypatch.setattr(
            custom_field_prompt, "open_editor", lambda initial_text="": next(inputs)
        )

        value = prompt_custom_field_value(
            custom_field("text", max_length=3), project_id="1"
        )

        assert value == "12"
        assert messages.error_max_length.format(max=3) in capsys.readouterr().out
