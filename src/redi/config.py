import os
import sys
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, NamedTuple

import tomlkit
from tomlkit.items import Table

CONFIG_PATH = Path.home() / ".config" / "redi" / "config.toml"

SUPPORTED_LANGUAGES = ("en", "ja")

# 言語未確定の場面で表示するため、翻訳せず各言語の自称表記を使う
LANGUAGE_LABELS = {"en": "English (en)", "ja": "日本語 (ja)"}


@dataclass(frozen=True)
class Profile:
    """config.toml の 1 プロファイル(`[profile_name]` テーブル)が持つ設定値。

    フィールド名は TOML のキー名と一致させる。未設定の項目は None で表し、
    「書かれていない」ことを保てるようにする(デフォルト値は DEFAULT_PROFILE)。
    """

    redmine_url: str | None = None
    redmine_api_key: str | None = None
    default_project_id: str | None = None
    wiki_project_id: str | None = None
    editor: str | None = None
    language: str | None = None

    @classmethod
    def field_names(cls) -> tuple[str, ...]:
        return tuple(f.name for f in fields(cls))

    @classmethod
    def from_dict(cls, values: Mapping[str, Any]) -> "Profile":
        """TOML から読んだ dict を Profile にする。

        Profile が持たないキーは無視する。falsy な値は未設定とみなす。TOML では
        数値も書けてしまうため、値は文字列に正規化する。
        """
        return cls(
            **{
                name: str(values[name])
                for name in cls.field_names()
                if values.get(name)
            }
        )

    def to_dict(self) -> dict[str, str]:
        """設定済みの項目だけを TOML 書き込み用の dict にする。

        未設定の項目はキーごと省き、config.toml に空の項目を残さない。
        """
        return {
            name: value for name in self.field_names() if (value := getattr(self, name))
        }

    def merge(self, other: "Profile") -> "Profile":
        """other の設定済み項目を自分に重ねた Profile を返す。"""
        return Profile.from_dict({**self.to_dict(), **other.to_dict()})


# プロファイルにも環境変数にも項目が無いときに使う値
DEFAULT_PROFILE = Profile(editor="vim", language="en")


def load_toml(config_path: Path | None = None) -> dict:
    path = config_path or CONFIG_PATH
    if path.exists():
        with open(path, "rb") as f:
            return tomllib.load(f)
    else:
        return {}


def load_env_config() -> Profile:
    return Profile.from_dict(
        {
            "redmine_url": os.environ.get("REDMINE_URL"),
            "redmine_api_key": os.environ.get("REDMINE_API_KEY"),
            "editor": os.environ.get("REDI_EDITOR"),
        }
    )


def resolve_profile_name(toml: dict, argv: list[str]) -> tuple[str | None, bool]:
    """argvに--profileがあればそれを、なければdefault_profileを返す。

    第二要素はCLI(--profile)で明示指定されたかどうかを示す。
    """
    for i, arg in enumerate(argv):
        if arg == "--profile" and i + 1 < len(argv):
            return argv[i + 1], True
        if arg.startswith("--profile="):
            return arg.split("=", 1)[1], True
    return toml.get("default_profile"), False


# 設定値。下の起動時解決で `apply_profile()` が入れる。
current_profile: str | None = None
redmine_url: str = ""
redmine_api_key: str = ""
default_project_id: str | None = None
wiki_project_id: str | None = None
editor: str = ""
language: str = ""


def resolve_merged_config(profile_name: str | None, toml_doc: dict) -> Profile:
    """プロファイルと環境変数をマージした設定値を返す。

    優先順位は デフォルト < プロファイル < 環境変数。未設定の項目は重ねても
    上書きしないため、下位の値がそのまま残る。
    """
    profile_table = toml_doc.get(profile_name) if profile_name else None
    profile = (
        Profile.from_dict(profile_table)
        if isinstance(profile_table, dict)
        else Profile()
    )
    return DEFAULT_PROFILE.merge(profile).merge(load_env_config())


def apply_profile(profile_name: str | None, config_path: Path | None = None) -> None:
    """プロファイルを適用して設定値を貼り替える。起動時も実行時の切替もここを通る。

    各モジュールは `config.X` で都度参照するので貼り替えるだけで伝わるが、`client` は
    接続先を抱えているので呼び出し側で `reconfigure()` も呼ぶこと。
    """
    global current_profile, redmine_url, redmine_api_key
    global default_project_id, wiki_project_id, editor, language

    profile = resolve_merged_config(profile_name, load_toml(config_path))
    current_profile = profile_name
    # 未設定は None だが、参照側が常に文字列を前提にしているため空文字に均す
    redmine_url = profile.redmine_url or ""
    redmine_api_key = profile.redmine_api_key or ""
    default_project_id = profile.default_project_id
    wiki_project_id = profile.wiki_project_id
    editor = profile.editor or ""
    language = profile.language or ""


def profile_has_credentials(profile_name: str, config_path: Path | None = None) -> bool:
    """接続に必要な設定が揃ったプロファイルかを返す。

    `check_config()` は sys.exit するため、TUI からの切り替え前チェックには使えない。
    """
    profile = resolve_merged_config(profile_name, load_toml(config_path))
    return bool(profile.redmine_url) and bool(profile.redmine_api_key)


# 起動時のプロファイル解決。`redi.i18n` が import 時に `language` を読むなど、
# 設定値は import された時点で確定していることを前提にしている。
_toml = load_toml()
_profile_name, _profile_explicit = resolve_profile_name(_toml, sys.argv)
if (
    _profile_name
    and _profile_explicit
    and not isinstance(_toml.get(_profile_name), dict)
):
    print(f"profile '{_profile_name}' not found in {CONFIG_PATH}", file=sys.stderr)
    sys.exit(1)
apply_profile(_profile_name)


def check_config() -> None:
    if not redmine_url:
        print(f"set REDMINE_URL or add redmine_url to {CONFIG_PATH}")
        sys.exit(1)
    if not redmine_api_key:
        print(f"set REDMINE_API_KEY or add redmine_api_key to {CONFIG_PATH}")
        sys.exit(1)


def update_config(
    key: str,
    value: str,
    profile: str | None = None,
    config_path: Path | None = None,
) -> None:
    path = config_path or CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with open(path) as f:
            doc = tomlkit.load(f)
    else:
        doc = tomlkit.document()

    target_profile = profile or doc.get("default_profile")
    if not target_profile:
        print("default_profile not found")
        sys.exit(1)
    profile_table = doc.get(target_profile) if target_profile in doc else None
    if not isinstance(profile_table, Table):
        print(f"profile '{target_profile}' not found in {path}")
        sys.exit(1)

    profile_table[key] = value
    with open(path, "w") as f:
        tomlkit.dump(doc, f)


class CreateProfileResult(NamedTuple):
    created: bool
    set_as_default: bool


def create_profile(
    profile_name: str,
    redmine_url: str | None = None,
    redmine_api_key: str | None = None,
    default_project_id: str | None = None,
    wiki_project_id: str | None = None,
    editor: str | None = None,
    language: str | None = None,
    config_path: Path | None = None,
) -> CreateProfileResult:
    path = config_path or CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with open(path) as f:
            doc = tomlkit.load(f)
    else:
        doc = tomlkit.document()

    if profile_name in doc:
        from redi.i18n import messages

        print(messages.profile_already_exists.format(name=profile_name))
        return CreateProfileResult(created=False, set_as_default=False)

    table = tomlkit.table()
    if redmine_url is not None:
        table["redmine_url"] = redmine_url
    if redmine_api_key is not None:
        table["redmine_api_key"] = redmine_api_key
    if default_project_id is not None:
        table["default_project_id"] = default_project_id
    if wiki_project_id is not None:
        table["wiki_project_id"] = wiki_project_id
    if editor is not None:
        table["editor"] = editor
    if language is not None:
        table["language"] = language
    doc[profile_name] = table

    profile_names = [k for k, v in doc.items() if isinstance(v, Table)]
    set_as_default = profile_names == [profile_name]
    if set_as_default:
        doc["default_profile"] = profile_name

    with open(path, "w") as f:
        tomlkit.dump(doc, f)
    return CreateProfileResult(created=True, set_as_default=set_as_default)


def set_default_profile(profile_name: str, config_path: Path | None = None) -> bool:
    path = config_path or CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with open(path) as f:
            doc = tomlkit.load(f)
    else:
        doc = tomlkit.document()

    if profile_name not in doc or not isinstance(doc.get(profile_name), dict):
        print(f"profile '{profile_name}' not found in {path}")
        return False

    doc["default_profile"] = profile_name
    with open(path, "w") as f:
        tomlkit.dump(doc, f)
    return True


def list_profile_names(config_path: Path | None = None) -> list[str]:
    path = config_path or CONFIG_PATH
    if not path.exists():
        return []
    with open(path) as f:
        doc = tomlkit.load(f)
    return [k for k, v in doc.items() if isinstance(v, Table)]


def get_default_profile(config_path: Path | None = None) -> str | None:
    path = config_path or CONFIG_PATH
    if not path.exists():
        return None
    with open(path) as f:
        doc = tomlkit.load(f)
    value = doc.get("default_profile")
    return str(value) if value is not None else None


def read_profile_values(
    profile_name: str, config_path: Path | None = None
) -> dict[str, str]:
    """指定プロファイルの設定値を返す。存在しない場合は空 dict を返す。

    prompt() の default に渡せるよう値は文字列に正規化する。
    """
    path = config_path or CONFIG_PATH
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        doc = tomllib.load(f)
    value = doc.get(profile_name)
    if not isinstance(value, dict):
        return {}
    return {k: str(v) for k, v in value.items()}


def show_config(full: bool = False, config_path: Path | None = None) -> None:
    if full:
        show_all_profiles(config_path=config_path)
        return
    doc = tomlkit.document()
    doc["redmine_url"] = redmine_url
    doc["default_project_id"] = default_project_id or ""
    doc["wiki_project_id"] = wiki_project_id or ""
    doc["editor"] = editor
    doc["language"] = language
    print(tomlkit.dumps(doc).rstrip())


def show_all_profiles(config_path: Path | None = None) -> None:
    path = config_path or CONFIG_PATH
    if not path.exists():
        print(f"config file not found: {path}")
        return
    with open(path) as f:
        doc = tomlkit.load(f)
    for key in list(doc.keys()):
        value = doc[key]
        if isinstance(value, Table) and "redmine_api_key" in value:
            del value["redmine_api_key"]
    print(tomlkit.dumps(doc).rstrip())
