import re
from datetime import date

from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError, Validator

from redi.api.custom_field import CustomField
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


class CompositeValidator(Validator):
    """複数の Validator を宣言順に適用し、最初に失敗したものを送出する Validator。"""

    def __init__(self, *validators: Validator) -> None:
        self.validators = validators

    def validate(self, document: Document) -> None:
        for validator in self.validators:
            validator.validate(document)


class MinLengthValidator(Validator):
    """min_length 以上の長さを要求する Validator。空文字は必須チェックに委ねて通す。"""

    def __init__(self, min_length: int | None) -> None:
        self.min_length = min_length or None

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        if text == "" or self.min_length is None:
            return
        if len(text) < self.min_length:
            raise ValidationError(
                message=messages.error_min_length.format(min=self.min_length)
            )


class MaxLengthValidator(Validator):
    """max_length 以下の長さを要求する Validator。空文字は必須チェックに委ねて通す。"""

    def __init__(self, max_length: int | None) -> None:
        self.max_length = max_length or None

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        if text == "" or self.max_length is None:
            return
        if len(text) > self.max_length:
            raise ValidationError(
                message=messages.error_max_length.format(max=self.max_length)
            )


class RegexpValidator(Validator):
    """regexp への部分一致 (re.search) を要求する Validator。

    正規表現として不正な文字列は検証不能とみなして無視する。
    空文字は必須チェックに委ねて通す。
    """

    def __init__(self, regexp: str | None) -> None:
        self._regex = _compile_regexp(regexp)

    def validate(self, document: Document) -> None:
        text = document.text.strip()
        if text == "" or self._regex is None:
            return
        if not self._regex.search(text):
            raise ValidationError(message=messages.error_regexp_mismatch)


def _compile_regexp(regexp: str | None) -> re.Pattern[str] | None:
    if not regexp:
        return None
    try:
        return re.compile(regexp)
    except re.error:
        return None


def _custom_field_constraints(custom_field: CustomField) -> list[Validator]:
    return [
        MinLengthValidator(custom_field.get("min_length")),
        MaxLengthValidator(custom_field.get("max_length")),
        RegexpValidator(custom_field.get("regexp")),
    ]


def build_custom_field_validator(
    custom_field: CustomField, base: Validator | None = None
) -> Validator:
    """カスタムフィールドの制約を送信前に検証する Validator を組み立てる。

    base（必須チェックや field_format ごとの Validator）は制約より先に適用する。
    """
    base_validators = [base] if base is not None else []
    return CompositeValidator(
        *base_validators, *_custom_field_constraints(custom_field)
    )


def check_custom_field_constraints(custom_field: CustomField, text: str) -> str | None:
    """prompt を介さないフロー（エディタ入力など）で制約を検証し、違反メッセージを返す。"""
    try:
        CompositeValidator(*_custom_field_constraints(custom_field)).validate(
            Document(text=text)
        )
    except ValidationError as e:
        return e.message
    return None
