import argparse
import sys
import tomllib

import requests
from prompt_toolkit.validation import Validator

from redi.api.project import Project, fetch_projects
from redi.cli.interactive import prompt
from redi.cli.picker import inline_choice
from redi.cli.validator import UrlValidator
from redi.client import RedmineClient
from redi.config import (
    CONFIG_PATH,
    LANGUAGE_LABELS,
    SUPPORTED_LANGUAGES,
    Profile,
    create_profile,
)
from redi.i18n import MessagesProto, messages, select_messages
from redi.output import eprint

PROFILE_NAME = "default"


def add_init_parser(subparsers: argparse._SubParsersAction) -> None:
    # init は新規プロファイル作成専用で --profile は意味を持たないため parents を受けない
    subparsers.add_parser(
        "init",
        help=messages.arg_help_init_command,
    )


def _verify_connection(url: str, api_key: str, messages: MessagesProto) -> dict | None:
    try:
        response = requests.get(
            f"{url}/my/account.json",
            headers={"X-Redmine-API-Key": api_key},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("user")
    except requests.exceptions.HTTPError as e:
        if e.response is not None:
            eprint(
                messages.connection_failed_http.format(
                    status=e.response.status_code, reason=e.response.reason
                )
            )
        else:
            eprint(messages.connection_failed_other.format(error=e))
    except requests.exceptions.RequestException as e:
        eprint(messages.connection_failed_other.format(error=e))
    return None


def _fetch_projects(url: str, api_key: str, messages: MessagesProto) -> list[Project]:
    try:
        return fetch_projects(RedmineClient(url.rstrip("/"), api_key))
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


def _has_existing_profile() -> bool:
    if not CONFIG_PATH.exists():
        return False
    with open(CONFIG_PATH, "rb") as f:
        doc = tomllib.load(f)
    return any(isinstance(v, dict) for v in doc.values())


def _select_language() -> str:
    """言語設定の存在に気付けるよう、init の最初に言語を選ばせる。"""
    options = [(code, LANGUAGE_LABELS[code]) for code in SUPPORTED_LANGUAGES]
    try:
        return inline_choice(messages.prompt_select_language, options)
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)


def handle_init(_args: argparse.Namespace) -> None:
    if _has_existing_profile():
        eprint(messages.init_profile_already_exists.format(path=CONFIG_PATH))
        sys.exit(1)

    _init_profile(_select_language())


def _init_profile(language: str) -> None:
    # 以降のメッセージは選択された言語で表示する
    messages = select_messages(language)
    print(messages.language_set.format(value=language, suffix=""))

    non_empty_validator = Validator.from_callable(
        lambda text: len(text.strip()) > 0,
        error_message=messages.error_input_required,
    )
    try:
        url = prompt(messages.prompt_redmine_url, validator=UrlValidator()).strip()
        print(messages.api_key_url_hint.format(url=url.rstrip("/")))
        api_key = prompt(
            messages.prompt_redmine_api_key,
            validator=non_empty_validator,
            is_password=True,
        ).strip()
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)

    print(messages.checking_connection)
    user = _verify_connection(url, api_key, messages)
    if user is None:
        sys.exit(1)
    name = " ".join(filter(None, [user.get("firstname"), user.get("lastname")]))
    print(messages.connection_success.format(login=user.get("login", ""), name=name))

    projects = _fetch_projects(url, api_key, messages)
    default_project_id: str | None = None
    wiki_project_id: str | None = None
    if projects:
        projects_by_id = {str(p["id"]): p for p in projects}
        default_project_id = _select_project_id(
            messages.prompt_select_default_project, projects, messages
        )
        print(
            messages.default_project_label.format(
                name=projects_by_id[default_project_id]["name"]
            )
        )
        wiki_project_id = _select_project_id(
            messages.prompt_select_wiki_project, projects, messages
        )
        print(
            messages.wiki_project_label.format(
                name=projects_by_id[wiki_project_id]["name"]
            )
        )
    else:
        print(messages.no_project_skip_project_id)

    result = create_profile(
        profile_name=PROFILE_NAME,
        profile=Profile(
            redmine_url=url,
            redmine_api_key=api_key,
            default_project_id=default_project_id,
            wiki_project_id=wiki_project_id,
            language=language,
        ),
    )
    if not result.created:
        sys.exit(1)
    print(messages.config_created.format(path=CONFIG_PATH))
