import argparse
import tomllib

import requests
from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator

from redi.cli._common import inline_choice
from redi.cli.prompt_util import UrlValidator
from redi.config import CONFIG_PATH, create_profile
from redi.i18n import messages

PROFILE_NAME = "default"


def add_init_parser(subparsers: argparse._SubParsersAction) -> None:
    subparsers.add_parser(
        "init",
        help=messages.arg_help_init_command,
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
        print(
            messages.connection_failed_http.format(
                status=e.response.status_code, reason=e.response.reason
            )
        )
    except requests.exceptions.RequestException as e:
        print(messages.connection_failed_other.format(error=e))
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
        print(messages.project_list_fetch_failed.format(error=e))
        return []


def _select_project_id(message: str, projects: list[dict]) -> str:
    options: list[tuple[str, str]] = [
        (str(p["id"]), f"{p['id']} {p['name']}") for p in projects
    ]
    try:
        return inline_choice(message, options)
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)


def _has_existing_profile() -> bool:
    if not CONFIG_PATH.exists():
        return False
    with open(CONFIG_PATH, "rb") as f:
        doc = tomllib.load(f)
    return any(isinstance(v, dict) for v in doc.values())


def handle_init(_args: argparse.Namespace) -> None:
    if _has_existing_profile():
        print(messages.init_profile_already_exists.format(path=CONFIG_PATH))
        exit(1)

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
        print(messages.canceled)
        exit(1)

    print(messages.checking_connection)
    user = _verify_connection(url, api_key)
    if user is None:
        exit(1)
    name = " ".join(filter(None, [user.get("firstname"), user.get("lastname")]))
    print(messages.connection_success.format(login=user.get("login", ""), name=name))

    projects = _fetch_projects(url, api_key)
    default_project_id: str | None = None
    wiki_project_id: str | None = None
    if projects:
        projects_by_id = {str(p["id"]): p for p in projects}
        default_project_id = _select_project_id(
            messages.prompt_select_default_project, projects
        )
        print(
            messages.default_project_label.format(
                name=projects_by_id[default_project_id]["name"]
            )
        )
        wiki_project_id = _select_project_id(
            messages.prompt_select_wiki_project, projects
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
        redmine_url=url,
        redmine_api_key=api_key,
        default_project_id=default_project_id,
        wiki_project_id=wiki_project_id,
    )
    if not result.created:
        exit(1)
    print(messages.config_created.format(path=CONFIG_PATH))
