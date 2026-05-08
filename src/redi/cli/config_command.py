import argparse

from redi.cli.common import resolve_alias
from redi.cli.prompt_util import inline_choice
from redi.config import (
    SUPPORTED_LANGUAGES,
    create_profile,
    get_default_profile,
    list_profile_names,
    set_default_profile,
    show_config,
    update_config,
)
from redi.i18n import messages, select_messages


def add_config_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    c_parser = subparsers.add_parser(
        "config", aliases=["c"], help=messages.arg_help_config_command, parents=parents
    )
    c_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_profiles
    )
    c_subparsers = c_parser.add_subparsers(dest="config_command")
    c_update_parser = c_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_config_update, parents=parents
    )
    c_update_parser.add_argument(
        "profile_name",
        nargs="?",
        help=messages.arg_help_config_profile_name_optional,
    )
    c_update_parser.add_argument(
        "--project_id", help=messages.arg_help_config_set_default_project_id
    )
    c_update_parser.add_argument(
        "--wiki_project_id", help=messages.arg_help_config_set_wiki_project_id
    )
    c_update_parser.add_argument("--editor", help=messages.arg_help_config_set_editor)
    c_update_parser.add_argument(
        "--language",
        choices=SUPPORTED_LANGUAGES,
        help=messages.arg_help_config_set_language,
    )
    c_update_parser.add_argument("--api_key", help=messages.arg_help_config_set_api_key)
    c_update_parser.add_argument("--url", help=messages.arg_help_config_set_url)
    c_update_parser.add_argument(
        "--default_profile", help=messages.arg_help_config_set_default_profile
    )
    c_create_parser = c_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_config_create, parents=parents
    )
    c_create_parser.add_argument(
        "profile_name", help=messages.arg_help_config_create_profile_name
    )
    c_create_parser.add_argument("--url", help=messages.arg_help_config_url)
    c_create_parser.add_argument("--api_key", help=messages.arg_help_config_api_key)
    c_create_parser.add_argument(
        "--project_id", help=messages.arg_help_config_default_project_id
    )
    c_create_parser.add_argument(
        "--wiki_project_id", help=messages.arg_help_config_wiki_project_id
    )
    c_create_parser.add_argument("--editor", help=messages.arg_help_config_editor)
    c_create_parser.add_argument(
        "--language",
        choices=SUPPORTED_LANGUAGES,
        help=messages.arg_help_config_language,
    )
    c_create_parser.add_argument(
        "--set_default",
        action="store_true",
        help=messages.arg_help_config_set_default_flag,
    )


def _interactive_select_default_profile() -> None:
    profile_names = list_profile_names()
    if not profile_names:
        print(messages.no_profiles_available)
        exit(1)
    current_default = get_default_profile()
    options: list[tuple[str, str]] = [
        (name, f"{name} (default)" if name == current_default else name)
        for name in profile_names
    ]
    try:
        selected = inline_choice(
            messages.prompt_select_default_profile_to_set,
            options,
            default=current_default,
        )
    except KeyboardInterrupt:
        print(messages.canceled)
        exit(1)
    if set_default_profile(selected):
        print(messages.default_profile_set.format(name=selected))


def handle_config(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.config_command)
    if cmd == "create":
        result = create_profile(
            profile_name=args.profile_name,
            redmine_url=args.url,
            redmine_api_key=args.api_key,
            default_project_id=args.project_id,
            wiki_project_id=args.wiki_project_id,
            editor=args.editor,
            language=args.language,
        )
        if not result.created:
            exit(1)
        print(messages.profile_created.format(name=args.profile_name))
        if result.set_as_default:
            print(messages.default_profile_set.format(name=args.profile_name))
        elif args.set_default and set_default_profile(args.profile_name):
            print(messages.default_profile_set.format(name=args.profile_name))
        return
    if cmd != "update":
        show_config(full=args.full)
        return
    no_args_provided = not (
        args.profile_name
        or args.project_id
        or args.wiki_project_id
        or args.editor
        or args.language
        or args.api_key
        or args.url
        or args.default_profile
    )
    if no_args_provided:
        _interactive_select_default_profile()
        return
    updated = False
    profile = args.profile_name
    profile_suffix = (
        messages.config_profile_suffix.format(name=profile) if profile else ""
    )
    if args.project_id:
        update_config("default_project_id", args.project_id, profile)
        print(
            messages.default_project_id_set.format(
                value=args.project_id, suffix=profile_suffix
            )
        )
        updated = True
    if args.wiki_project_id:
        update_config("wiki_project_id", args.wiki_project_id, profile)
        print(
            messages.wiki_project_id_set.format(
                value=args.wiki_project_id, suffix=profile_suffix
            )
        )
        updated = True
    if args.editor:
        update_config("editor", args.editor, profile)
        print(messages.editor_set.format(value=args.editor, suffix=profile_suffix))
        updated = True
    if args.language:
        update_config("language", args.language, profile)
        new_lang_messages = select_messages(args.language)
        print(
            new_lang_messages.language_set.format(
                value=args.language, suffix=profile_suffix
            )
        )
        updated = True
    if args.api_key:
        update_config("redmine_api_key", args.api_key, profile)
        print(messages.redmine_api_key_set.format(suffix=profile_suffix))
        updated = True
    if args.url:
        update_config("redmine_url", args.url, profile)
        print(messages.redmine_url_set.format(value=args.url, suffix=profile_suffix))
        updated = True
    if args.default_profile:
        if set_default_profile(args.default_profile):
            print(messages.default_profile_set.format(name=args.default_profile))
        updated = True
    if not updated:
        show_config()
