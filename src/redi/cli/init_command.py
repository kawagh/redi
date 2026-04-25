import argparse
import tomllib

import requests
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator

from redi.cli._common import inline_choice
from redi.config import CONFIG_PATH, create_profile

PROFILE_NAME = "default"


def add_init_parser(subparsers: argparse._SubParsersAction) -> None:
    subparsers.add_parser(
        "init",
        help="初回セットアップ（URL/APIキーの疎通確認後にプロファイルを作成）",
    )


def _verify_connection(url: str, api_key: str) -> dict | None:
    try:
        response = requests.get(
            f"{url}/my/account.json",
            headers={"X-Redmine-API-Key": api_key},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("user")
    except requests.exceptions.HTTPError as e:
        print(f"接続失敗: {e.response.status_code} {e.response.reason}")
    except requests.exceptions.RequestException as e:
        print(f"接続失敗: {e}")
    return None


def _fetch_projects(url: str, api_key: str) -> list[dict]:
    try:
        response = requests.get(
            f"{url}/projects.json",
            headers={"X-Redmine-API-Key": api_key},
            params={"limit": 100},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("projects", [])
    except requests.exceptions.RequestException as e:
        print(f"プロジェクト一覧の取得に失敗しました: {e}")
        return []


def _select_project_id(message: str, projects: list[dict]) -> str:
    options: list[tuple[str, str]] = [
        (str(p["id"]), f"{p['id']} {p['name']}") for p in projects
    ]
    try:
        return inline_choice(message, options)
    except (KeyboardInterrupt, EOFError):
        print("キャンセルしました")
        exit(1)


def _has_existing_profile() -> bool:
    if not CONFIG_PATH.exists():
        return False
    with open(CONFIG_PATH, "rb") as f:
        doc = tomllib.load(f)
    return any(isinstance(v, dict) for v in doc.values())


def handle_init(_args: argparse.Namespace) -> None:
    if _has_existing_profile():
        print(
            f"既にプロファイルが存在します ({CONFIG_PATH})。"
            "追加するプロファイルは `redi config create` で作成してください"
        )
        exit(1)

    non_empty_validator = Validator.from_callable(
        lambda text: len(text.strip()) > 0,
        error_message="入力してください",
    )
    try:
        url = prompt("Redmine URL: ", validator=non_empty_validator).strip()
        print(f"APIキーは {url.rstrip('/')}/my/account で確認できます")
        api_key = prompt(
            "Redmine APIキー: ",
            validator=non_empty_validator,
            is_password=True,
        ).strip()
    except (KeyboardInterrupt, EOFError):
        print("キャンセルしました")
        exit(1)

    print("接続を確認しています...")
    user = _verify_connection(url, api_key)
    if user is None:
        exit(1)
    name = " ".join(filter(None, [user.get("firstname"), user.get("lastname")]))
    print(f"接続成功: {user.get('login', '')} ({name})")

    projects = _fetch_projects(url, api_key)
    default_project_id: str | None = None
    wiki_project_id: str | None = None
    if projects:
        projects_by_id = {str(p["id"]): p for p in projects}
        default_project_id = _select_project_id(
            "普段使用しているプロジェクトを選択してください", projects
        )
        print(f"デフォルトプロジェクト: {projects_by_id[default_project_id]['name']}")
        wiki_project_id = _select_project_id(
            "普段閲覧しているwikiのあるプロジェクトを選択してください", projects
        )
        print(f"wikiプロジェクト: {projects_by_id[wiki_project_id]['name']}")
    else:
        print("プロジェクトが存在しないため project_id の設定をスキップします")

    result = create_profile(
        profile_name=PROFILE_NAME,
        redmine_url=url,
        redmine_api_key=api_key,
        default_project_id=default_project_id,
        wiki_project_id=wiki_project_id,
    )
    if not result.created:
        exit(1)
    print(f"{CONFIG_PATH}に設定が作成されました")
