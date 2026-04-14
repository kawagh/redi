import os
import tomllib
from pathlib import Path

import tomlkit

CONFIG_PATH = Path.home() / ".config" / "redi" / "config.toml"

_default_config = {
    "redmine_url": "",
    "redmine_api_key": "",
    "editor": "vim",
}


def load_toml() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
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


def update_config(key: str, value: str, profile: str | None = None) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            doc = tomlkit.load(f)
    else:
        doc = tomlkit.document()

    target_profile = profile or doc.get("default_profile")
    if not target_profile:
        print("default_profile not found")
        exit(1)
    if target_profile not in doc or not isinstance(doc.get(target_profile), dict):
        print(f"profile '{target_profile}' not found in {CONFIG_PATH}")
        exit(1)

    doc[target_profile][key] = value
    with open(CONFIG_PATH, "w") as f:
        tomlkit.dump(doc, f)


def set_default_profile(profile_name: str) -> bool:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            doc = tomlkit.load(f)
    else:
        doc = tomlkit.document()

    if profile_name not in doc or not isinstance(doc.get(profile_name), dict):
        print(f"profile '{profile_name}' not found in {CONFIG_PATH}")
        return False

    doc["default_profile"] = profile_name
    with open(CONFIG_PATH, "w") as f:
        tomlkit.dump(doc, f)
    return True


def show_config() -> None:
    doc = tomlkit.document()
    doc["redmine_url"] = redmine_url
    doc["default_project_id"] = default_project_id or ""
    doc["wiki_project_id"] = wiki_project_id or ""
    doc["editor"] = editor
    print(tomlkit.dumps(doc).rstrip())
