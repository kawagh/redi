import re
from datetime import date

from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.validation import ValidationError, Validator

_URL_PREFIXES = ("http://", "https://")
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_DATE_ERROR_MESSAGE = "YYYY-MM-DD で入力してください（空文字でクリア）"


class UrlValidator(Validator):
    """http:// または https:// で始まるURLを許容するValidator。

    入力途中でも `_URL_PREFIXES` のいずれかのプレフィックスとマッチしている間は
    エラーを出さず、明らかに外れた入力でのみエラーを出す。
    """

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        if not text:
            raise ValidationError(message="入力してください")
        if text.startswith(_URL_PREFIXES):
            return
        if any(p.startswith(text) for p in _URL_PREFIXES):
            return
        raise ValidationError(
            message="http:// または https:// で始まるURLを入力してください"
        )


class DueDateValidator(Validator):
    """期日入力用の Validator。空文字または開始日以降の YYYY-MM-DD のみ許容する。"""

    def __init__(self, start_date: date | None) -> None:
        self.start_date = start_date

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        if text == "":
            return
        if not _DATE_PATTERN.fullmatch(text):
            raise ValidationError(message=_DATE_ERROR_MESSAGE)
        try:
            d = date.fromisoformat(text)
        except ValueError:
            raise ValidationError(message=_DATE_ERROR_MESSAGE)
        if self.start_date and d < self.start_date:
            raise ValidationError(
                message=f"開始日 {self.start_date.isoformat()} 以降の日付を入力してください"
            )


def digit_only_key_bindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add(Keys.Any)
    def _(event) -> None:
        if event.data.isdigit():
            event.current_buffer.insert_text(event.data)

    return kb


def digit_and_period_key_bindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add(Keys.Any)
    def _(event) -> None:
        if event.data.isdigit() or event.data == ".":
            event.current_buffer.insert_text(event.data)

    return kb
