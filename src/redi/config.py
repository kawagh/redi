import os
import tomllib
from pathlib import Path

import tomlkit

CONFIG_PATH = Path.home() / ".config" / "redi" / "config.toml"


def load_toml_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    return {}


_config = load_toml_config()

redmine_url = os.environ.get("REDMINE_URL") or _config.get("redmine_url")
redmine_api_key = os.environ.get("REDMINE_API_KEY") or _config.get("redmine_api_key")
default_project_id: str | None = _config.get("default_project_id")
wiki_project_id: str | None = _config.get("wiki_project_id")
editor: str = os.environ.get("REDI_EDITOR") or _config.get("editor", "vim")

if not redmine_url:
    print(f"set REDMINE_URL or add redmine_url to {CONFIG_PATH}")
    exit(1)
if not redmine_api_key:
    print(f"set REDMINE_API_KEY or add redmine_api_key to {CONFIG_PATH}")
    exit(1)


def update_config(key: str, value: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            doc = tomlkit.load(f)
    else:
        doc = tomlkit.document()
    doc[key] = value
    with open(CONFIG_PATH, "w") as f:
        tomlkit.dump(doc, f)


def show_config() -> None:
    doc = tomlkit.document()
    doc["redmine_url"] = redmine_url
    doc["default_project_id"] = default_project_id or ""
    doc["wiki_project_id"] = wiki_project_id or ""
    doc["editor"] = editor
    print(tomlkit.dumps(doc).rstrip())
