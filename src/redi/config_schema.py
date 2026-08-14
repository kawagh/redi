"""config.toml のプロファイルが妥当かを静的に検証する。

検証対象は config.toml に書かれた生の値で、環境変数はマージしない。
プロファイル単体が妥当かを知りたいのに、たまたま設定されている環境変数で結果が
変わると troubleshooting の役に立たないため。ただし必須キーが環境変数で補われる
運用 (シークレット管理ツール経由で API キーを渡すなど) は実在するので、
その場合だけ ERROR ではなく WARNING に落とす。
"""

import os
from collections.abc import Callable
from enum import StrEnum
from typing import Any, NamedTuple

from redi.config import SUPPORTED_LANGUAGES
from redi.i18n import messages

_URL_PREFIXES = ("http://", "https://")

# 必須キーがプロファイルに無くても、これらが設定されていれば実行時には値が入る
ENV_FALLBACK = {
    "redmine_url": "REDMINE_URL",
    "redmine_api_key": "REDMINE_API_KEY",
}


class Severity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class Issue(NamedTuple):
    """検証で見つかった問題。`key` はトップレベルの問題では None になりうる。"""

    severity: Severity
    profile: str | None
    key: str | None
    message: str


# 値に問題があれば (severity, 表示文言) を返し、問題なければ None を返す
Check = Callable[[Any], tuple[Severity, str] | None]


class FieldSpec(NamedTuple):
    key: str
    required: bool
    check: Check


def _check_str(value: Any) -> tuple[Severity, str] | None:
    if not isinstance(value, str):
        return (Severity.ERROR, messages.check_must_be_string)
    if not value.strip():
        return (Severity.ERROR, messages.check_must_not_be_empty)
    return None


def _check_url(value: Any) -> tuple[Severity, str] | None:
    if issue := _check_str(value):
        return issue
    if not value.startswith(_URL_PREFIXES):
        return (Severity.ERROR, messages.check_invalid_url)
    return None


def _check_project_id(value: Any) -> tuple[Severity, str] | None:
    # 手編集で `default_project_id = 1` と書かれることがある。README の表記は
    # 文字列なので揃えたいが、実行できなくなるわけではないので警告に留める。
    if isinstance(value, int) and not isinstance(value, bool):
        return (Severity.WARNING, messages.check_project_id_should_be_string)
    return _check_str(value)


def _check_language(value: Any) -> tuple[Severity, str] | None:
    if issue := _check_str(value):
        return issue
    if value not in SUPPORTED_LANGUAGES:
        # 未対応の言語は en にフォールバックして動くので警告に留める
        return (
            Severity.WARNING,
            messages.check_unknown_language.format(
                value=value, expected=", ".join(SUPPORTED_LANGUAGES)
            ),
        )
    return None


PROFILE_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("redmine_url", True, _check_url),
    FieldSpec("redmine_api_key", True, _check_str),
    FieldSpec("default_project_id", False, _check_project_id),
    FieldSpec("wiki_project_id", False, _check_project_id),
    FieldSpec("editor", False, _check_str),
    FieldSpec("language", False, _check_language),
)

PROFILE_KEYS = frozenset(field.key for field in PROFILE_FIELDS)


def validate_profile(name: str, values: dict) -> list[Issue]:
    """プロファイル1つ分のテーブルを検証する。"""
    issues: list[Issue] = []
    for field in PROFILE_FIELDS:
        if field.key not in values:
            if not field.required:
                continue
            env_name = ENV_FALLBACK.get(field.key)
            if env_name and os.environ.get(env_name):
                issues.append(
                    Issue(
                        Severity.WARNING,
                        name,
                        field.key,
                        messages.check_supplied_by_env.format(name=env_name),
                    )
                )
            else:
                issues.append(
                    Issue(
                        Severity.ERROR, name, field.key, messages.check_required_missing
                    )
                )
            continue
        if result := field.check(values[field.key]):
            severity, message = result
            issues.append(Issue(severity, name, field.key, message))
    # 未知のキーは警告に留める。ERROR にすると将来キーが増えたとき、
    # 新しい config.toml を古い redi で読んだだけで無効判定になってしまう。
    issues.extend(
        Issue(Severity.WARNING, name, key, messages.check_unknown_key)
        for key in values
        if key not in PROFILE_KEYS
    )
    return issues


def validate_top_level(doc: dict) -> list[Issue]:
    """プロファイルに属さないトップレベルの記述を検証する。"""
    issues: list[Issue] = []
    profile_names = profile_names_of(doc)
    for key, value in doc.items():
        if isinstance(value, dict):
            continue
        if key == "default_profile":
            if not isinstance(value, str):
                issues.append(
                    Issue(Severity.ERROR, None, key, messages.check_must_be_string)
                )
            elif value not in profile_names:
                issues.append(
                    Issue(
                        Severity.ERROR,
                        None,
                        key,
                        messages.check_default_profile_not_found.format(name=value),
                    )
                )
            continue
        issues.append(
            Issue(Severity.WARNING, None, key, messages.check_unknown_top_level_key)
        )
    return issues


def profile_names_of(doc: dict) -> list[str]:
    """テーブルとして書かれたキーをプロファイル名として返す。"""
    return [key for key, value in doc.items() if isinstance(value, dict)]


def has_error(issues: list[Issue]) -> bool:
    return any(issue.severity is Severity.ERROR for issue in issues)


def credentials_of(values: dict) -> tuple[str, str] | None:
    """疎通確認に使う URL と API キーを返す。揃わなければ None。

    必須キーは環境変数で補われることがあるので、実行時と同じ解決をする。
    """
    url = values.get("redmine_url") or os.environ.get(ENV_FALLBACK["redmine_url"])
    api_key = values.get("redmine_api_key") or os.environ.get(
        ENV_FALLBACK["redmine_api_key"]
    )
    if not isinstance(url, str) or not isinstance(api_key, str):
        return None
    if not url or not api_key:
        return None
    return url, api_key


def active_env_overrides() -> list[str]:
    """プロファイルを上書きしている環境変数名を返す。"""
    return [name for name in ENV_FALLBACK.values() if os.environ.get(name)]
