"""プロファイル作成の対話部品。

`redi init` と `redi config create` が同じ手順(URL/APIキー入力 → 接続確認 →
プロジェクト選択)を踏むため、両者から共有する。
"""

import sys

import requests
from prompt_toolkit.validation import Validator

from redi.api.me import MyAccount
from redi.api.project import Project, fetch_projects
from redi.cli.connection import verify_connection
from redi.cli.interactive import prompt
from redi.cli.picker import inline_choice
from redi.cli.validator import UrlValidator
from redi.client import RedmineClient
from redi.config import Profile
from redi.i18n import MessagesProto
from redi.output import eprint


def _verify_connection(
    api_client: RedmineClient, messages: MessagesProto
) -> MyAccount | None:
    result = verify_connection(api_client, messages)
    if result.error:
        eprint(result.error)
    return result.user


def _fetch_projects(
    api_client: RedmineClient, messages: MessagesProto
) -> list[Project]:
    try:
        return fetch_projects(api_client)
    except requests.exceptions.RequestException as e:
        eprint(messages.project_list_fetch_failed.format(error=e))
        return []


def _select_project_id(
    prompt_message: str, projects: list[Project], messages: MessagesProto
) -> str:
    options: list[tuple[str, str]] = [
        (str(p["id"]), f"{p['id']} {p['name']}")
        for p in sorted(projects, key=lambda p: p["id"], reverse=True)
    ]
    try:
        return inline_choice(prompt_message, options)
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)


def _prompt_credentials(current: Profile, messages: MessagesProto) -> tuple[str, str]:
    non_empty_validator = Validator.from_callable(
        lambda text: len(text.strip()) > 0,
        error_message=messages.error_input_required,
    )
    try:
        url = (
            current.redmine_url
            or prompt(messages.prompt_redmine_url, validator=UrlValidator()).strip()
        )
        api_key = current.redmine_api_key
        if not api_key:
            print(messages.api_key_url_hint.format(url=url.rstrip("/")))
            api_key = prompt(
                messages.prompt_redmine_api_key,
                validator=non_empty_validator,
                is_password=True,
            ).strip()
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)
    return url, api_key


def _select_project_ids(
    api_client: RedmineClient, current: Profile, messages: MessagesProto
) -> tuple[str | None, str | None]:
    default_project_id = current.default_project_id
    wiki_project_id = current.wiki_project_id
    if default_project_id and wiki_project_id:
        return default_project_id, wiki_project_id

    projects = _fetch_projects(api_client, messages)
    if not projects:
        print(messages.no_project_skip_project_id)
        return default_project_id, wiki_project_id

    projects_by_id = {str(p["id"]): p for p in projects}
    if not default_project_id:
        default_project_id = _select_project_id(
            messages.prompt_select_default_project, projects, messages
        )
        print(
            messages.default_project_label.format(
                name=projects_by_id[default_project_id]["name"]
            )
        )
    if not wiki_project_id:
        wiki_project_id = _select_project_id(
            messages.prompt_select_wiki_project, projects, messages
        )
        print(
            messages.wiki_project_label.format(
                name=projects_by_id[wiki_project_id]["name"]
            )
        )
    return default_project_id, wiki_project_id


def prompt_connection_profile(current: Profile, messages: MessagesProto) -> Profile:
    """接続に必要な項目のうち未設定のものを対話で埋めた Profile を返す。

    current に既に入っている項目は聞き直さない。接続確認に失敗した場合や
    入力が中断された場合は exit 1 する。
    """
    url, api_key = _prompt_credentials(current, messages)
    api_client = RedmineClient(url.rstrip("/"), api_key)

    print(messages.checking_connection)
    user = _verify_connection(api_client, messages)
    if user is None:
        sys.exit(1)
    name = " ".join(filter(None, [user.get("firstname"), user.get("lastname")]))
    print(messages.connection_success.format(login=user.get("login", ""), name=name))

    default_project_id, wiki_project_id = _select_project_ids(
        api_client, current, messages
    )
    return Profile(
        redmine_url=url,
        redmine_api_key=api_key,
        default_project_id=default_project_id,
        wiki_project_id=wiki_project_id,
    )
