import os
import tomllib
from pathlib import Path
from typing import NamedTuple

import tomlkit
from tomlkit.items import Table

CONFIG_PATH = Path.home() / ".config" / "redi" / "config.toml"

_default_config = {
    "redmine_url": "",
    "redmine_api_key": "",
    "editor": "vim",
}


def load_toml(config_path: Path | None = None) -> dict:
    path = config_path or CONFIG_PATH
    if path.exists():
        with open(path, "rb") as f:
            return tomllib.load(f)
    else:
        return {}


def load_env_config() -> dict:
    return {
        "redmine_url": os.environ.get("REDMINE_URL"),
        "redmine_api_key": os.environ.get("REDMINE_API_KEY"),
        "editor": os.environ.get("REDI_EDITOR"),
    }


# 設定値の上書き
merged_config = _default_config
toml = load_toml()
default_profile_name = toml.get("default_profile")
if default_profile_name:
    toml_config = load_toml()[default_profile_name]
    for k, v in toml_config.items():
        if v:
            merged_config[k] = v

env_config = load_env_config()
for k, v in env_config.items():
    if v:
        merged_config[k] = v

redmine_url = merged_config["redmine_url"]
redmine_api_key = merged_config["redmine_api_key"]
default_project_id: str | None = merged_config.get("default_project_id")
wiki_project_id: str | None = merged_config.get("wiki_project_id")
editor: str = merged_config["editor"]


def check_config() -> None:
    if not redmine_url:
        print(f"set REDMINE_URL or add redmine_url to {CONFIG_PATH}")
        exit(1)
    if not redmine_api_key:
        print(f"set REDMINE_API_KEY or add redmine_api_key to {CONFIG_PATH}")
        exit(1)


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
        exit(1)
    profile_table = doc.get(target_profile) if target_profile in doc else None
    if not isinstance(profile_table, Table):
        print(f"profile '{target_profile}' not found in {path}")
        exit(1)

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
        print(f"profile '{profile_name}' は既に存在します")
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


def show_config(full: bool = False) -> None:
    if full:
        show_all_profiles()
        return
    doc = tomlkit.document()
    doc["redmine_url"] = redmine_url
    doc["default_project_id"] = default_project_id or ""
    doc["wiki_project_id"] = wiki_project_id or ""
    doc["editor"] = editor
    print(tomlkit.dumps(doc).rstrip())


def show_all_profiles() -> None:
    if not CONFIG_PATH.exists():
        print(f"config file not found: {CONFIG_PATH}")
        return
    with open(CONFIG_PATH) as f:
        doc = tomlkit.load(f)
    for key in list(doc.keys()):
        value = doc[key]
        if isinstance(value, Table) and "redmine_api_key" in value:
            del value["redmine_api_key"]
    print(tomlkit.dumps(doc).rstrip())
