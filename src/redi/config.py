import os
import tomllib
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "redi" / "config.toml"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    return {}


_config = load_config()

redmine_url = os.environ.get("REDMINE_URL") or _config.get("redmine_url")
redmine_api_key = os.environ.get("REDMINE_API_KEY") or _config.get("redmine_api_key")

if not redmine_url:
    print(f"set REDMINE_URL or add redmine_url to {CONFIG_PATH}")
    exit(1)
if not redmine_api_key:
    print(f"set REDMINE_API_KEY or add redmine_api_key to {CONFIG_PATH}")
    exit(1)
