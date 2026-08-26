import argparse
import sys

from redi import config
from redi.api.account import verify_connection
from redi.cli.alias import resolve_alias
from redi.cli.interactive import prompt
from redi.cli.picker import inline_checkbox, inline_choice, inline_choice_with_action
from redi.cli.profile_setup import prompt_connection_profile
from redi.cli.validator import ProfileNameValidator, RequiredValidator, UrlValidator
from redi.config import (
    CONFIG_PATH,
    SUPPORTED_LANGUAGES,
    Profile,
    create_profile,
    get_default_profile,
    list_profile_names,
    load_toml,
    read_profile,
    set_default_profile,
    show_config,
    update_profile,
)
from redi.config_schema import (
    Issue,
    Severity,
    active_env_overrides,
    credentials_of,
    has_error,
    profile_names_of,
    validate_profile,
    validate_top_level,
)
from redi.i18n import messages, select_messages
from redi.output import eprint


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
        "profile_name",
        nargs="?",
        help=messages.arg_help_config_create_profile_name,
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
    c_check_parser = c_subparsers.add_parser(
        "check", help=messages.arg_help_config_check, parents=parents
    )
    c_check_parser.add_argument(
        "profile_name",
        nargs="?",
        help=messages.arg_help_config_check_profile_name,
    )
    c_check_parser.add_argument(
        "--all", action="store_true", help=messages.arg_help_config_check_all
    )
    c_check_parser.add_argument(
        "--no-connection",
        dest="no_connection",
        action="store_true",
        help=messages.arg_help_config_check_no_connection,
    )


def _interactive_select_profile(args: argparse.Namespace) -> bool:
    """プロファイル一覧を表示し、Enter でデフォルト設定 / u で項目更新へ分岐する。

    args に更新値を詰めて後続の更新フローへ流す場合 True を返す。
    """
    profile_names = list_profile_names()
    if not profile_names:
        eprint(messages.no_profiles_available)
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
        eprint(messages.canceled)
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
    current = read_profile(profile)
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
                default=current.redmine_url or "",
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
                default=current.default_project_id or "",
                validator=RequiredValidator(),
            ).strip()
        if "wiki_project_id" in selected:
            args.wiki_project_id = prompt(
                messages.prompt_wiki_project_id,
                default=current.wiki_project_id or "",
                validator=RequiredValidator(),
            ).strip()
        if "editor" in selected:
            args.editor = prompt(
                messages.prompt_editor,
                default=current.editor or "",
                validator=RequiredValidator(),
            ).strip()
        if "language" in selected:
            args.language = inline_choice(
                messages.prompt_select_language,
                [(v, v) for v in SUPPORTED_LANGUAGES],
                default=current.language,
            )
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        return False
    if "set_default" in selected:
        args.default_profile = profile
    args.profile_name = profile
    return True


def _print_issues(issues: list[Issue]) -> None:
    for issue in issues:
        prefix = f"{issue.key}: " if issue.key else ""
        print(f"  {issue.severity.value.ljust(7)} {prefix}{issue.message}")


def _check_profile(name: str, values: dict, check_connection: bool) -> bool:
    """プロファイル1つを検証して結果を表示する。ERROR があれば True を返す。"""
    issues = validate_profile(name, values)
    print(f"{name}:")
    _print_issues(issues)
    if has_error(issues):
        # 接続先が確定しないので疎通確認まで進めない
        if check_connection:
            print(f"  {messages.check_connection_skipped}")
        return True
    if not check_connection:
        print(f"  {messages.check_profile_valid}")
        return False
    credentials = credentials_of(values)
    if credentials is None:
        # ERROR が無ければ必須キーは解決できているはずで、ここには来ない。
        # 検証と接続先の解決が食い違ったときに黙って素通りさせないための保険。
        print(f"  {messages.check_connection_skipped}")
        return False
    result = verify_connection(*credentials, messages)
    if not result.ok:
        # verify_connection が返す文言が既に失敗の理由になっているのでそのまま出す
        _print_issues([Issue(Severity.ERROR, name, None, result.error or "")])
        return True
    login = (result.user or {}).get("login", "")
    print(f"  {messages.check_profile_ok.format(login=login)}")
    return False


def _handle_config_check(args: argparse.Namespace) -> None:
    """プロファイルが有効かを検証する。

    検証するのは config.toml に書かれた生の値で、環境変数はマージしない。
    たまたま設定されている環境変数で結果が変わると、プロファイル単体が妥当かを
    知りたいという目的に合わなくなるため。ただし疎通確認だけは実行時と同じ値で
    行いたいので、必須キーが欠けている場合に限り環境変数で補う。
    """
    doc = load_toml()
    profile_names = profile_names_of(doc)
    if not profile_names:
        eprint(messages.no_profiles_available)
        sys.exit(1)

    if args.all:
        targets = profile_names
    else:
        name = args.profile_name or config.current_profile
        if not name:
            eprint(messages.check_no_target_profile)
            sys.exit(1)
        if name not in profile_names:
            eprint(messages.check_profile_not_found.format(name=name, path=CONFIG_PATH))
            sys.exit(1)
        targets = [name]

    top_level_issues = validate_top_level(doc)
    if top_level_issues:
        print(f"{CONFIG_PATH}:")
        _print_issues(top_level_issues)
    failed = has_error(top_level_issues)

    for name in targets:
        # 複数プロファイルを1つでも落とさず全部見せたいので or の短絡を避ける
        failed = _check_profile(name, doc[name], not args.no_connection) or failed

    overrides = active_env_overrides()
    if overrides:
        print(messages.check_env_override_note.format(names=", ".join(overrides)))
    if failed:
        sys.exit(1)


def _prompt_profile_name() -> str:
    try:
        return prompt(
            messages.prompt_profile_name,
            validator=ProfileNameValidator(list_profile_names()),
        ).strip()
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)


def _confirm_set_default(profile_name: str) -> bool:
    try:
        selected = inline_choice(
            messages.prompt_set_default_profile.format(name=profile_name),
            [("yes", messages.choice_yes), ("no", messages.choice_no)],
            default="no",
        )
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)
    return selected == "yes"


def _handle_config_create(args: argparse.Namespace) -> None:
    profile = Profile(
        redmine_url=args.url,
        redmine_api_key=args.api_key,
        default_project_id=args.project_id,
        wiki_project_id=args.wiki_project_id,
        editor=args.editor,
        language=args.language,
    )
    profile_name = args.profile_name
    set_default = args.set_default
    # プロファイル名と接続情報が揃っていなければ init と同じ手順で対話的に補う
    if not (profile_name and profile.redmine_url and profile.redmine_api_key):
        profile_name = profile_name or _prompt_profile_name()
        profile = profile.merge(prompt_connection_profile(profile, messages))
        # 最初のプロファイルは create_profile が自動でデフォルトにするため聞かない
        if not set_default and list_profile_names():
            set_default = _confirm_set_default(profile_name)

    result = create_profile(profile_name=profile_name, profile=profile)
    if not result.created:
        sys.exit(1)
    print(messages.profile_created.format(name=profile_name))
    if result.set_as_default or (set_default and set_default_profile(profile_name)):
        print(messages.default_profile_set.format(name=profile_name))


def handle_config(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.config_command)
    if cmd == "check":
        _handle_config_check(args)
        return
    if cmd == "create":
        _handle_config_create(args)
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
    # 指定された項目をまとめて書き込み、結果は項目ごとに知らせる
    values = Profile(
        redmine_url=args.url,
        redmine_api_key=args.api_key,
        default_project_id=args.project_id,
        wiki_project_id=args.wiki_project_id,
        editor=args.editor,
        language=args.language,
    )
    if values.to_dict():
        update_profile(values, profile)
        updated = True
    if args.project_id:
        print(
            messages.default_project_id_set.format(
                value=args.project_id, suffix=profile_suffix
            )
        )
    if args.wiki_project_id:
        print(
            messages.wiki_project_id_set.format(
                value=args.wiki_project_id, suffix=profile_suffix
            )
        )
    if args.editor:
        print(messages.editor_set.format(value=args.editor, suffix=profile_suffix))
    if args.language:
        new_lang_messages = select_messages(args.language)
        print(
            new_lang_messages.language_set.format(
                value=args.language, suffix=profile_suffix
            )
        )
    if args.api_key:
        print(messages.redmine_api_key_set.format(suffix=profile_suffix))
    if args.url:
        print(messages.redmine_url_set.format(value=args.url, suffix=profile_suffix))
    if args.default_profile:
        if set_default_profile(args.default_profile):
            print(messages.default_profile_set.format(name=args.default_profile))
        updated = True
    if not updated:
        show_config()
