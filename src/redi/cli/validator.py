import re
from datetime import date

from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError, Validator

from redi.i18n import messages

_URL_PREFIXES = ("http://", "https://")
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
_FLOAT_PATTERN = re.compile(r"-?\d+(\.\d+)?")
_INT_PATTERN = re.compile(r"-?\d+")


class RequiredValidator(Validator):
    """空文字（空白のみを含む）を拒否する Validator。"""

    def validate(self, document: Document) -> None:
        if not document.text.strip():
            raise ValidationError(message=messages.error_input_required)


class ProfileNameValidator(Validator):
    """プロファイル名用の Validator。空文字と既存プロファイル名を拒否する。

    作成後に「既に存在します」で終わらせず、入力中に気付けるようにする。
    """

    def __init__(self, existing_names: list[str]) -> None:
        self.existing_names = existing_names

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        if not text:
            raise ValidationError(message=messages.error_input_required)
        if text in self.existing_names:
            raise ValidationError(
                message=messages.profile_already_exists.format(name=text)
            )


class UrlValidator(Validator):
    """http:// または https:// で始まるURLを許容するValidator。

    入力途中でも `_URL_PREFIXES` のいずれかのプレフィックスとマッチしている間は
    エラーを出さず、明らかに外れた入力でのみエラーを出す。
    """

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        if not text:
            raise ValidationError(message=messages.error_input_required)
        if text.startswith(_URL_PREFIXES):
            return
        if any(p.startswith(text) for p in _URL_PREFIXES):
            return
        raise ValidationError(message=messages.error_url_format)


class HourValidator(Validator):
    """工数入力用の Validator。整数または小数1個を含む数値のみ許容する。

    allow_empty=True の場合は空文字も許容する。
    """

    def __init__(self, allow_empty: bool = False) -> None:
        self.allow_empty = allow_empty

    def validate(self, document: Document) -> None:
        text = document.text
        if text == "" and self.allow_empty:
            return
        if not text.replace(".", "", 1).isdigit():
            raise ValidationError(message=messages.error_numeric_required)


class FloatValidator(Validator):
    """カスタムフィールド float 形式用の Validator。

    符号付き整数または小数（負の値も許容）を受け付ける。
    """

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        if not _FLOAT_PATTERN.fullmatch(text):
            raise ValidationError(message=messages.error_numeric_required)


class IntValidator(Validator):
    """カスタムフィールド int 形式用の Validator。

    符号付き整数（負の値も許容）を受け付ける。
    allow_empty=True の場合は空文字も許容する。
    """

    def __init__(self, allow_empty: bool = False) -> None:
        self.allow_empty = allow_empty

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        if text == "" and self.allow_empty:
            return
        if not _INT_PATTERN.fullmatch(text):
            raise ValidationError(message=messages.error_numeric_required)


class DateValidator(Validator):
    """YYYY-MM-DD 形式の日付のみを許容する Validator。

    allow_empty=True の場合は空文字も許容する。
    """

    def __init__(self, allow_empty: bool = False) -> None:
        self.allow_empty = allow_empty

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        if text == "":
            if self.allow_empty:
                return
            raise ValidationError(message=messages.error_input_required)
        if not _DATE_PATTERN.fullmatch(text):
            raise ValidationError(message=messages.error_date_format)
        try:
            date.fromisoformat(text)
        except ValueError:
            raise ValidationError(message=messages.error_date_format)


class DueDateValidator(Validator):
    """期日入力用の Validator。空文字または開始日以降の YYYY-MM-DD のみ許容する。"""

    def __init__(self, start_date: date | None) -> None:
        self.start_date = start_date
        self._date_validator = DateValidator(allow_empty=True)

    def validate(self, document: Document) -> None:
        self._date_validator.validate(document)
        text = document.text.strip()
        if text == "":
            return
        d = date.fromisoformat(text)
        if self.start_date and d < self.start_date:
            raise ValidationError(
                message=messages.error_date_after_start.format(
                    date=self.start_date.isoformat()
                )
            )
