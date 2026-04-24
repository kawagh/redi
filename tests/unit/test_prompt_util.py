from dataclasses import dataclass

import pytest
from prompt_toolkit.buffer import Buffer

from redi.cli.prompt_util import (
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
