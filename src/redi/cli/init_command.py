import argparse
import sys
import tomllib
from dataclasses import replace

from redi.cli.interactive import canceled_as_exit
from redi.cli.picker import inline_choice
from redi.cli.profile_setup import prompt_connection_profile
from redi.config import (
    CONFIG_PATH,
    LANGUAGE_LABELS,
    SUPPORTED_LANGUAGES,
    Profile,
    create_profile,
)
from redi.i18n import messages, select_messages
from redi.output import eprint

PROFILE_NAME = "default"


def add_init_parser(subparsers: argparse._SubParsersAction) -> None:
    # init は新規プロファイル作成専用で --profile は意味を持たないため parents を受けない
    subparsers.add_parser(
        "init",
        help=messages.arg_help_init_command,
    )


def _has_existing_profile() -> bool:
    if not CONFIG_PATH.exists():
        return False
    with open(CONFIG_PATH, "rb") as f:
        doc = tomllib.load(f)
    return any(isinstance(v, dict) for v in doc.values())


def _select_language() -> str:
    """言語設定の存在に気付けるよう、init の最初に言語を選ばせる。"""
    options = [(code, LANGUAGE_LABELS[code]) for code in SUPPORTED_LANGUAGES]
    with canceled_as_exit():
        return inline_choice(messages.prompt_select_language, options)


def handle_init(_args: argparse.Namespace) -> None:
    if _has_existing_profile():
        eprint(messages.init_profile_already_exists.format(path=CONFIG_PATH))
        sys.exit(1)

    _init_profile(_select_language())


def _init_profile(language: str) -> None:
    # 以降のメッセージは選択された言語で表示する
    messages = select_messages(language)
    print(messages.language_set.format(value=language, suffix=""))

    profile = prompt_connection_profile(Profile(), messages)

    result = create_profile(
        profile_name=PROFILE_NAME,
        profile=replace(profile, language=language),
    )
    if not result.created:
        sys.exit(1)
    print(messages.config_created.format(path=CONFIG_PATH))
