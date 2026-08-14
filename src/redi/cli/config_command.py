import argparse
import sys

from redi.cli.alias import resolve_alias
from redi.cli.interactive import prompt
from redi.cli.picker import inline_checkbox, inline_choice, inline_choice_with_action
from redi.cli.validator import RequiredValidator, UrlValidator
from redi.config import (
    SUPPORTED_LANGUAGES,
    create_profile,
    get_default_profile,
    list_profile_names,
    read_profile_values,
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


def _interactive_select_profile(args: argparse.Namespace) -> bool:
    """プロファイル一覧を表示し、Enter でデフォルト設定 / u で項目更新へ分岐する。

    args に更新値を詰めて後続の更新フローへ流す場合 True を返す。
    """
    profile_names = list_profile_names()
    if not profile_names:
        print(messages.no_profiles_available)
        sys.exit(1)
    current_default = get_default_profile()
    options: list[tuple[str, str]] = [
        (name, f"{name} (default)" if name == current_default else name)
        for name in profile_names
    ]
    try:
        action, selected = inline_choice_with_action(
            messages.prompt_select_profile,
            options,
            default=current_default,
            action_keys={"u": "update"},
        )
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)
    if action == "update":
        return _interactive_fill_config_update_args(args, selected)
    if set_default_profile(selected):
        print(messages.default_profile_set.format(name=selected))
    return False


def _update_field_values(profile: str) -> list[tuple[str, str]]:
    """更新項目の選択肢を返す。既にデフォルトのプロファイルには set_default を出さない。"""
    field_values: list[tuple[str, str]] = [
        ("url", messages.field_redmine_url),
        ("api_key", messages.field_redmine_api_key),
        ("project_id", messages.field_default_project_id),
        ("wiki_project_id", messages.field_wiki_project_id),
        ("editor", messages.field_editor),
        ("language", messages.field_language),
    ]
    if profile != get_default_profile():
        field_values.append(("set_default", messages.field_set_default_profile))
    return field_values


def _interactive_fill_config_update_args(
    args: argparse.Namespace, profile: str
) -> bool:
    """更新する項目を選ばせて値を入力し、args に反映する。

    後続の更新フローへ流す場合 True を返す。キャンセル時は False。
    """
    current = read_profile_values(profile)
    field_values = _update_field_values(profile)
    try:
        selected = inline_checkbox(messages.prompt_select_update_items, field_values)
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        return False
    if not selected:
        print(messages.canceled_no_items_selected)
        return False
    labels = dict(field_values)
    print(messages.update_items.format(items=", ".join(labels[v] for v in selected)))
    # 後続の更新フローは falsy な値をスキップするため、選択した項目は必須入力とする
    try:
        if "url" in selected:
            args.url = prompt(
                messages.prompt_redmine_url,
                default=current.get("redmine_url", ""),
                validator=UrlValidator(),
            ).strip()
        if "api_key" in selected:
            # 現在値は秘匿するため default には出さない
            args.api_key = prompt(
                messages.prompt_redmine_api_key,
                validator=RequiredValidator(),
                is_password=True,
            ).strip()
        if "project_id" in selected:
            args.project_id = prompt(
                messages.prompt_default_project_id,
                default=current.get("default_project_id", ""),
                validator=RequiredValidator(),
            ).strip()
        if "wiki_project_id" in selected:
            args.wiki_project_id = prompt(
                messages.prompt_wiki_project_id,
                default=current.get("wiki_project_id", ""),
                validator=RequiredValidator(),
            ).strip()
        if "editor" in selected:
            args.editor = prompt(
                messages.prompt_editor,
                default=current.get("editor", ""),
                validator=RequiredValidator(),
            ).strip()
        if "language" in selected:
            args.language = inline_choice(
                messages.prompt_select_language,
                [(v, v) for v in SUPPORTED_LANGUAGES],
                default=current.get("language"),
            )
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        return False
    if "set_default" in selected:
        args.default_profile = profile
    args.profile_name = profile
    return True


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
            sys.exit(1)
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
        if not _interactive_select_profile(args):
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
