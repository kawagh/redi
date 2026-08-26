"""`redi project` の表示整形と入力の検証。

取得や更新の手順は `service.project_service` に任せ、ここでは print と sys.exit を担当する。
"""

import argparse
import json
import sys
import webbrowser

import requests

from redi.api.custom_field import fetch_custom_fields
from redi.api.exceptions import (
    ProjectNotFoundException,
    ProjectPermissionDeniedException,
    print_http_error_body,
)
from redi.api.membership import fetch_project_users
from redi.api.project import Project
from redi.api.tracker import fetch_trackers
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete_with_identifier
from redi.cli.editor import open_editor, shorten_to_oneline
from redi.cli.interactive import canceled_as_exit, ensure_interactive, prompt
from redi.cli.picker import inline_checkbox, inline_choice
from redi.cli.shared_options import full_option_parser
from redi.cli.validator import ProjectIdentifierValidator, RequiredValidator
from redi.i18n import messages
from redi.output import eprint
from redi.service import project_service, version_service


def _list_projects(full: bool = False) -> None:
    """プロジェクト一覧を1行ずつ出す。full=True では取得した JSON をそのまま出す。"""
    projects = project_service.list_projects()
    if full:
        print(json.dumps(projects, ensure_ascii=False))
        return
    for project in projects:
        print(f"{project['id']} {project['name']}")


def _view_project(
    project_id: str, include: str = "", full: bool = False, web: bool = False
) -> None:
    """プロジェクトの詳細を標準出力に出す。存在しない場合は exit 1。"""
    if web:
        url = project_service.project_url(project_id)
        print(url)
        webbrowser.open(url)
        return
    project = _read_project_or_exit(project_id, include=include)
    if full:
        print(json.dumps(project, ensure_ascii=False))
        return
    print("\n".join(format_project_detail(project)))


def _read_project_or_exit(project_id: str, include: str = "") -> Project:
    """プロジェクトを取得する。存在しない・参照できない場合は exit 1。"""
    try:
        return project_service.read_project(project_id, include=include)
    except ProjectNotFoundException:
        eprint(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except ProjectPermissionDeniedException:
        eprint(messages.project_permission_denied.format(id=project_id))
        sys.exit(1)


def format_project_detail(project: Project) -> list[str]:
    """プロジェクトの詳細表示を行のリストに整形する。"""
    lines = []
    lines.append(f"{project['id']} {project['name']} ({project['identifier']})")
    description = project.get("description")
    if description:
        lines.append("")
        lines.append(description)
    parent = project.get("parent")
    if parent:
        lines.append("")
        lines.append(
            messages.label_parent_project.format(
                id=parent.get("id"), name=parent.get("name", "")
            )
        )
    default_assignee = project.get("default_assignee")
    if default_assignee:
        lines.append("")
        lines.append(
            messages.label_default_assignee.format(
                id=default_assignee.get("id"), name=default_assignee.get("name", "")
            )
        )
    default_version = project.get("default_version")
    if default_version:
        lines.append("")
        lines.append(
            messages.label_default_version.format(
                id=default_version.get("id"), name=default_version.get("name", "")
            )
        )
    trackers = project.get("trackers") or []
    if trackers:
        lines.append("")
        lines.append(messages.label_trackers_header)
        for t in trackers:
            lines.append(f"  {t['id']} {t['name']}")
    issue_categories = project.get("issue_categories") or []
    if issue_categories:
        lines.append("")
        lines.append(messages.label_issue_categories_header)
        for c in issue_categories:
            lines.append(f"  {c['id']} {c['name']}")
    enabled_modules = project.get("enabled_modules") or []
    if enabled_modules:
        lines.append("")
        lines.append(messages.label_enabled_modules_header)
        for m in enabled_modules:
            lines.append(f"  {m.get('name')}")
    return lines


def _create_project(
    name: str,
    identifier: str,
    description: str | None = None,
    homepage: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    inherit_members: bool | None = None,
    tracker_ids: list[int] | None = None,
    enabled_module_names: list[str] | None = None,
    issue_custom_field_ids: list[int] | None = None,
) -> None:
    """プロジェクトを作成し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        created = project_service.create_project(
            name=name,
            identifier=identifier,
            description=description,
            homepage=homepage,
            is_public=is_public,
            parent_id=parent_id,
            inherit_members=inherit_members,
            tracker_ids=tracker_ids,
            enabled_module_names=enabled_module_names,
            issue_custom_field_ids=issue_custom_field_ids,
        )
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        sys.exit(1)
    print(f"{created['id']} {created['name']} ({created['identifier']})")


def _update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    homepage: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    inherit_members: bool | None = None,
    tracker_ids: list[int] | None = None,
    enabled_module_names: list[str] | None = None,
    issue_custom_field_ids: list[int] | None = None,
    default_assigned_to_id: str | None = None,
    default_version_id: str | None = None,
) -> None:
    """プロジェクトを更新し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        project_service.update_project(
            project_id,
            name=name,
            description=description,
            homepage=homepage,
            is_public=is_public,
            parent_id=parent_id,
            inherit_members=inherit_members,
            tracker_ids=tracker_ids,
            enabled_module_names=enabled_module_names,
            issue_custom_field_ids=issue_custom_field_ids,
            default_assigned_to_id=default_assigned_to_id,
            default_version_id=default_version_id,
        )
    except ProjectNotFoundException:
        eprint(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.project_update_failed)
        sys.exit(1)
    print(messages.project_updated.format(id=project_id))


def _archive_project(project_id: str) -> None:
    """プロジェクトをアーカイブし、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        project_service.archive_project(project_id)
    except ProjectNotFoundException:
        eprint(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.project_archive_failed)
        sys.exit(1)
    print(messages.project_archived.format(id=project_id))


def _unarchive_project(project_id: str) -> None:
    """プロジェクトのアーカイブを解除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        project_service.unarchive_project(project_id)
    except ProjectNotFoundException:
        eprint(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.project_unarchive_failed)
        sys.exit(1)
    print(messages.project_unarchived.format(id=project_id))


def _delete_project(project_id: str) -> None:
    """プロジェクトを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        project_service.delete_project(project_id)
    except ProjectNotFoundException:
        eprint(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.project_delete_failed)
        sys.exit(1)
    print(messages.project_deleted.format(id=project_id))


def _split_int_ids(value: str | None) -> list[int] | None:
    """カンマ区切りの id 文字列を int のリストにする。未指定なら None を返す。"""
    if not value:
        return None
    return [int(x) for x in value.split(",")]


def _split_names(value: str | None) -> list[str] | None:
    """カンマ区切りの名前を strip したリストにする。未指定なら None を返す。

    空文字は「モジュールを全て無効にする」の意味になるため空リストを返す。
    """
    if value is None:
        return None
    return [x.strip() for x in value.split(",") if x.strip()]


def _interactive_select_parent_id(current: str | None) -> str | None:
    """親プロジェクトを一覧から選ばせる。「なし」を選んだ場合は None を返す。"""
    options: list[tuple[str, str]] = [
        ("", messages.prompt_select_parent_project_none)
    ] + [
        (str(project["id"]), f"{project['id']} {project['name']}")
        for project in project_service.list_projects()
    ]
    labels = dict(options)
    selected = inline_choice(
        messages.prompt_select_parent_project, options, default=current
    )
    print(
        messages.prompt_field_value.format(
            name=messages.field_parent_project, value=labels[selected]
        )
    )
    return selected or None


def _interactive_select_tracker_ids(current: str | None) -> str | None:
    """トラッカーを複数選ばせ、カンマ区切りの id 文字列を返す。"""
    trackers = fetch_trackers()
    options: list[tuple[str, str]] = [(str(t["id"]), t["name"]) for t in trackers]
    labels = dict(options)
    selected = inline_checkbox(
        messages.prompt_select_trackers,
        options,
        initial_checked=current.split(",") if current else None,
    )
    if not selected:
        return None
    print(
        messages.prompt_field_value.format(
            name=messages.field_trackers,
            value=", ".join(labels[v] for v in selected),
        )
    )
    return ",".join(selected)


def _interactive_select_enabled_module_names(current: str | None) -> str | None:
    """有効化するモジュールを複数選ばせ、カンマ区切りの名前を返す。

    有効化できるモジュールを返す REST API が無いため、選択肢は Redmine 標準の
    モジュール名を並べた `MODULE_NAME_CHOICES` から出す。プラグインが追加した
    モジュール名はここに出ないので、その場合は引数で直接渡す。
    """
    options: list[tuple[str, str]] = [
        (name, name) for name in project_service.MODULE_NAME_CHOICES
    ]
    selected = inline_checkbox(
        messages.prompt_select_enabled_modules,
        options,
        initial_checked=current.split(",") if current else None,
    )
    if not selected:
        return None
    print(
        messages.prompt_field_value.format(
            name=messages.field_enabled_modules, value=", ".join(selected)
        )
    )
    return ",".join(selected)


def _issue_custom_field_options() -> list[tuple[str, str]]:
    """イシューのカスタムフィールドの選択肢を返す。

    一覧の取得には管理者権限が要る。キャッシュも無く取得できない場合は空リストを
    返し、呼び出し側で任意項目そのものから外す。
    """
    custom_fields = fetch_custom_fields()
    if custom_fields is None:
        return []
    return [
        (str(cf["id"]), f"{cf['id']} {cf['name']}")
        for cf in custom_fields
        # 全プロジェクトに適用されるものはプロジェクト側で選ぶ意味がない。
        # is_for_all は Redmine 7.0 以降でのみ返るため、無い場合は候補に残す
        if cf.get("customized_type") == "issue" and not cf.get("is_for_all")
    ]


def _interactive_select_issue_custom_field_ids(
    options: list[tuple[str, str]], current: str | None
) -> str | None:
    """イシューのカスタムフィールドを複数選ばせ、カンマ区切りの id 文字列を返す。"""
    labels = dict(options)
    selected = inline_checkbox(
        messages.prompt_select_issue_custom_fields,
        options,
        initial_checked=current.split(",") if current else None,
    )
    if not selected:
        return None
    print(
        messages.prompt_field_value.format(
            name=messages.field_issue_custom_fields,
            value=", ".join(labels[v] for v in selected),
        )
    )
    return ",".join(selected)


def _interactive_select_default_assigned_to_id(
    project_id: str, current: str | None
) -> str:
    """既定の担当者をプロジェクトのメンバーから選ばせ、id を返す。

    「なし」を選んだ場合は空文字を返す。Redmine は空文字を受けて設定を解除する。
    """
    options: list[tuple[str, str]] = [
        ("", messages.prompt_select_default_assignee_none)
    ] + [(str(u["id"]), u.get("name", "")) for u in fetch_project_users(project_id)]
    labels = dict(options)
    selected = inline_choice(
        messages.prompt_select_default_assignee, options, default=current
    )
    print(
        messages.prompt_field_value.format(
            name=messages.field_default_assignee, value=labels[selected]
        )
    )
    return selected


def _interactive_select_default_version_id(project_id: str, current: str | None) -> str:
    """既定のバージョンをプロジェクトのバージョンから選ばせ、id を返す。

    「なし」を選んだ場合は空文字を返す。Redmine は空文字を受けて設定を解除する。
    """
    options: list[tuple[str, str]] = [
        ("", messages.prompt_select_default_version_none)
    ] + [
        (str(v["id"]), f"{v['name']} ({v['status']})")
        for v in version_service.list_versions(project_id)
    ]
    labels = dict(options)
    selected = inline_choice(
        messages.prompt_select_default_version, options, default=current
    )
    print(
        messages.prompt_field_value.format(
            name=messages.field_default_version, value=labels[selected]
        )
    )
    return selected


def _interactive_fill_optional_create_fields(args: argparse.Namespace) -> None:
    """アクションメニューで「任意項目を入力する」を選んだときの入力フロー。

    入力結果は argparse が渡す形式のまま args へ書き戻し、
    送信前の変換は `handle_project` の一箇所に閉じる。
    """
    field_options: list[tuple[str, str]] = [
        ("description", messages.field_description),
        ("homepage", messages.field_homepage),
        ("is_public", messages.field_is_public),
        ("parent_id", messages.field_parent_project),
        ("inherit_members", messages.field_inherit_members),
        ("tracker_ids", messages.field_trackers),
        ("enabled_module_names", messages.field_enabled_modules),
    ]
    # 選べない (管理者権限もキャッシュも無い) 場合は任意項目にも出さない
    custom_field_options = _issue_custom_field_options()
    if custom_field_options:
        field_options.append(
            ("issue_custom_field_ids", messages.field_issue_custom_fields)
        )
    with canceled_as_exit():
        selected = inline_checkbox(
            messages.prompt_select_create_optional_items, field_options
        )
        if not selected:
            return
        if "description" in selected:
            args.description = open_editor(initial_text=args.description or "")
            if args.description:
                print(
                    messages.prompt_field_value.format(
                        name=messages.field_description,
                        value=shorten_to_oneline(args.description),
                    )
                )
        if "homepage" in selected:
            args.homepage = prompt(
                messages.prompt_project_homepage, default=args.homepage or ""
            ).strip()
        if "is_public" in selected:
            is_public_options: list[tuple[str, str]] = [
                ("true", messages.label_project_public),
                ("false", messages.label_project_private),
            ]
            labels = dict(is_public_options)
            args.is_public = inline_choice(
                messages.prompt_select_is_public,
                is_public_options,
                default=args.is_public,
            )
            print(
                messages.prompt_field_value.format(
                    name=messages.field_is_public, value=labels[args.is_public]
                )
            )
        if "parent_id" in selected:
            args.parent_id = _interactive_select_parent_id(args.parent_id)
        if "inherit_members" in selected:
            inherit_options: list[tuple[str, str]] = [
                ("true", messages.label_bool_true),
                ("false", messages.label_bool_false),
            ]
            inherit_labels = dict(inherit_options)
            args.inherit_members = inline_choice(
                messages.prompt_select_inherit_members,
                inherit_options,
                default=args.inherit_members,
            )
            print(
                messages.prompt_field_value.format(
                    name=messages.field_inherit_members,
                    value=inherit_labels[args.inherit_members],
                )
            )
        if "tracker_ids" in selected:
            args.tracker_ids = _interactive_select_tracker_ids(args.tracker_ids)
        if "enabled_module_names" in selected:
            args.enabled_module_names = _interactive_select_enabled_module_names(
                args.enabled_module_names
            )
        if "issue_custom_field_ids" in selected:
            args.issue_custom_field_ids = _interactive_select_issue_custom_field_ids(
                custom_field_options, args.issue_custom_field_ids
            )


def _interactive_fill_create_args(args: argparse.Namespace) -> None:
    """`project create` の必須項目を対話で埋め、送信前に任意項目の入力機会を挟む。"""
    with canceled_as_exit():
        if args.name is None:
            args.name = prompt(
                messages.prompt_project_name, validator=RequiredValidator()
            ).strip()
        if args.identifier is None:
            args.identifier = prompt(
                messages.prompt_project_identifier,
                default=project_service.suggest_identifier(args.name),
                validator=ProjectIdentifierValidator(),
            ).strip()
    action_options: list[tuple[str, str]] = [
        ("submit", messages.action_submit),
        ("optional", messages.action_fill_optional),
    ]
    while True:
        with canceled_as_exit():
            action = inline_choice(messages.prompt_what_next, action_options)
        if action != "optional":
            return
        _interactive_fill_optional_create_fields(args)


def _current_update_defaults(project: Project) -> dict[str, str]:
    """対話の初期値にする現在値を、argparse が渡すのと同じ形の文字列で返す。"""
    parent = project.get("parent")
    default_assignee = project.get("default_assignee")
    default_version = project.get("default_version")
    return {
        "name": project["name"],
        "description": project.get("description") or "",
        "homepage": project.get("homepage") or "",
        "is_public": "true" if project.get("is_public") else "false",
        "parent_id": str(parent["id"]) if parent else "",
        "inherit_members": "true" if project.get("inherit_members") else "false",
        "tracker_ids": ",".join(str(t["id"]) for t in project.get("trackers") or []),
        "enabled_module_names": ",".join(
            str(m["name"]) for m in project.get("enabled_modules") or []
        ),
        "issue_custom_field_ids": ",".join(
            str(cf["id"]) for cf in project.get("issue_custom_fields") or []
        ),
        "default_assigned_to_id": (
            str(default_assignee["id"]) if default_assignee else ""
        ),
        "default_version_id": str(default_version["id"]) if default_version else "",
    }


def _interactive_fill_project_update_args(args: argparse.Namespace) -> None:
    """更新する項目を選ばせ、選ばれた分だけ現在値を初期値にして聞く。

    更新項目が 1 つも指定されずに呼ばれる。issue / news / version の update と同じく
    `prompt_select_update_items` で項目を選ばせる形に揃えている。
    入力結果は argparse が渡す形式のまま args へ書き戻し、
    送信前の変換は `handle_project` の一箇所に閉じる。

    アーカイブは値を送るフィールドではなく操作のトリガーなので、選択肢に出さない。
    """
    # 選択肢の組み立てにも Redmine を引くため、その前に非TTYを弾く
    ensure_interactive(messages.prompt_select_update_items)
    field_options: list[tuple[str, str]] = [
        ("name", messages.field_project_name),
        ("description", messages.field_description),
        ("homepage", messages.field_homepage),
        ("is_public", messages.field_is_public),
        ("parent_id", messages.field_parent_project),
        ("inherit_members", messages.field_inherit_members),
        ("tracker_ids", messages.field_trackers),
        ("enabled_module_names", messages.field_enabled_modules),
        ("default_assigned_to_id", messages.field_default_assignee),
        ("default_version_id", messages.field_default_version),
    ]
    # 選べない (管理者権限もキャッシュも無い) 場合は更新項目にも出さない
    custom_field_options = _issue_custom_field_options()
    if custom_field_options:
        field_options.append(
            ("issue_custom_field_ids", messages.field_issue_custom_fields)
        )
    with canceled_as_exit():
        selected = inline_checkbox(messages.prompt_select_update_items, field_options)
    if not selected:
        eprint(messages.canceled_no_items_selected)
        sys.exit(1)
    labels = dict(field_options)
    print(messages.update_items.format(items=", ".join(labels[v] for v in selected)))
    # trackers / enabled_modules / issue_custom_fields は include 指定でしか返らない
    current = _current_update_defaults(
        _read_project_or_exit(
            args.project_id, include="trackers,enabled_modules,issue_custom_fields"
        )
    )
    with canceled_as_exit():
        if "name" in selected:
            args.name = prompt(
                messages.prompt_project_name,
                default=current["name"],
                validator=RequiredValidator(),
            ).strip()
        if "description" in selected:
            args.description = open_editor(initial_text=current["description"])
            print(
                messages.prompt_field_value.format(
                    name=messages.field_description,
                    value=shorten_to_oneline(args.description),
                )
            )
        if "homepage" in selected:
            args.homepage = prompt(
                messages.prompt_project_homepage, default=current["homepage"]
            ).strip()
        if "is_public" in selected:
            is_public_options: list[tuple[str, str]] = [
                ("true", messages.label_project_public),
                ("false", messages.label_project_private),
            ]
            is_public_labels = dict(is_public_options)
            args.is_public = inline_choice(
                messages.prompt_select_is_public,
                is_public_options,
                default=current["is_public"],
            )
            print(
                messages.prompt_field_value.format(
                    name=messages.field_is_public,
                    value=is_public_labels[args.is_public],
                )
            )
        if "parent_id" in selected:
            args.parent_id = _interactive_select_parent_id(current["parent_id"])
        if "inherit_members" in selected:
            inherit_options: list[tuple[str, str]] = [
                ("true", messages.label_bool_true),
                ("false", messages.label_bool_false),
            ]
            inherit_labels = dict(inherit_options)
            args.inherit_members = inline_choice(
                messages.prompt_select_inherit_members,
                inherit_options,
                default=current["inherit_members"],
            )
            print(
                messages.prompt_field_value.format(
                    name=messages.field_inherit_members,
                    value=inherit_labels[args.inherit_members],
                )
            )
        if "tracker_ids" in selected:
            args.tracker_ids = _interactive_select_tracker_ids(current["tracker_ids"])
        if "enabled_module_names" in selected:
            args.enabled_module_names = _interactive_select_enabled_module_names(
                current["enabled_module_names"]
            )
        if "default_assigned_to_id" in selected:
            args.default_assigned_to_id = _interactive_select_default_assigned_to_id(
                args.project_id, current["default_assigned_to_id"]
            )
        if "default_version_id" in selected:
            args.default_version_id = _interactive_select_default_version_id(
                args.project_id, current["default_version_id"]
            )
        if "issue_custom_field_ids" in selected:
            args.issue_custom_field_ids = _interactive_select_issue_custom_field_ids(
                custom_field_options, current["issue_custom_field_ids"]
            )


def _update_fields(args: argparse.Namespace) -> dict:
    """`project update` の引数を service に渡す形へ変換する。"""
    return {
        "name": args.name,
        "description": args.description,
        "homepage": args.homepage,
        "is_public": None if args.is_public is None else args.is_public == "true",
        "parent_id": args.parent_id,
        "inherit_members": (
            None if args.inherit_members is None else args.inherit_members == "true"
        ),
        "tracker_ids": _split_int_ids(args.tracker_ids),
        "enabled_module_names": _split_names(args.enabled_module_names),
        "issue_custom_field_ids": _split_int_ids(args.issue_custom_field_ids),
        "default_assigned_to_id": args.default_assigned_to_id,
        "default_version_id": args.default_version_id,
    }


def add_project_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    p_parser = subparsers.add_parser(
        "project",
        aliases=["p"],
        help=messages.arg_help_project_command,
        parents=[*parents, full_option_parser()],
    )
    p_subparsers = p_parser.add_subparsers(dest="project_command")
    p_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_project_list,
        parents=[*parents, full_option_parser(postfix=True)],
    )
    p_view_parser = p_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_project_view, parents=parents
    )
    p_view_parser.add_argument("project_id", help=messages.arg_help_project_view_id)
    p_view_parser.add_argument(
        "--include",
        help=messages.arg_help_project_include,
    )
    p_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    p_view_parser.add_argument(
        "--web", "-w", action="store_true", help=messages.arg_help_open_web
    )
    p_create_parser = p_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_project_create, parents=parents
    )
    p_create_parser.add_argument(
        "name", nargs="?", help=messages.arg_help_project_name_arg
    )
    p_create_parser.add_argument(
        "identifier", nargs="?", help=messages.arg_help_project_identifier
    )
    p_create_parser.add_argument(
        "--description", "-d", help=messages.arg_help_description
    )
    p_create_parser.add_argument("--homepage", help=messages.arg_help_project_homepage)
    p_create_parser.add_argument(
        "--is_public",
        choices=["true", "false"],
        help=messages.arg_help_project_is_public,
    )
    p_create_parser.add_argument("--parent_id", help=messages.arg_help_parent_id)
    p_create_parser.add_argument(
        "--inherit_members",
        choices=["true", "false"],
        help=messages.arg_help_project_inherit_members,
    )
    p_create_parser.add_argument("--tracker_ids", help=messages.arg_help_tracker_ids)
    p_create_parser.add_argument(
        "--enabled_module_names", help=messages.arg_help_enabled_module_names
    )
    p_create_parser.add_argument(
        "--issue_custom_field_ids", help=messages.arg_help_issue_custom_field_ids
    )
    p_delete_parser = p_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_project_delete, parents=parents
    )
    p_delete_parser.add_argument("project_id", help=messages.arg_help_project_delete_id)
    p_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )
    p_update_parser = p_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_project_update, parents=parents
    )
    p_update_parser.add_argument("project_id", help=messages.arg_help_project_update_id)
    p_update_parser.add_argument("--name", "-n", help=messages.arg_help_project_name)
    p_update_parser.add_argument(
        "--description", "-d", help=messages.arg_help_description
    )
    p_update_parser.add_argument("--homepage", help=messages.arg_help_project_homepage)
    p_update_parser.add_argument(
        "--is_public",
        choices=["true", "false"],
        help=messages.arg_help_project_is_public,
    )
    p_update_parser.add_argument("--parent_id", help=messages.arg_help_parent_id)
    p_update_parser.add_argument(
        "--inherit_members",
        choices=["true", "false"],
        help=messages.arg_help_project_inherit_members,
    )
    p_update_parser.add_argument("--tracker_ids", help=messages.arg_help_tracker_ids)
    p_update_parser.add_argument(
        "--enabled_module_names", help=messages.arg_help_enabled_module_names
    )
    p_update_parser.add_argument(
        "--issue_custom_field_ids", help=messages.arg_help_issue_custom_field_ids
    )
    p_update_parser.add_argument(
        "--default_assigned_to_id",
        help=messages.arg_help_project_default_assigned_to_id,
    )
    p_update_parser.add_argument(
        "--default_version_id", help=messages.arg_help_project_default_version_id
    )
    p_update_parser.add_argument(
        "--archive",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=messages.arg_help_project_archive,
    )


def handle_project(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.project_command)
    if cmd == "view":
        _view_project(
            args.project_id,
            include=args.include or "",
            full=args.full,
            web=args.web,
        )
    elif cmd == "create":
        if args.name is None or args.identifier is None:
            _interactive_fill_create_args(args)
        is_public = None
        if args.is_public is not None:
            is_public = args.is_public == "true"
        inherit_members = None
        if args.inherit_members is not None:
            inherit_members = args.inherit_members == "true"
        _create_project(
            name=args.name,
            identifier=args.identifier,
            description=args.description,
            homepage=args.homepage,
            is_public=is_public,
            parent_id=args.parent_id,
            inherit_members=inherit_members,
            tracker_ids=_split_int_ids(args.tracker_ids),
            enabled_module_names=_split_names(args.enabled_module_names),
            issue_custom_field_ids=_split_int_ids(args.issue_custom_field_ids),
        )
    elif cmd == "delete":
        if not args.yes:
            project = _read_project_or_exit(args.project_id)
            summary = (
                messages.delete_target_project.format(
                    id=project["id"],
                    name=project["name"],
                    identifier=project["identifier"],
                )
                + "\n"
                + messages.delete_project_warning
            )
            confirm_delete_with_identifier(
                summary, project["identifier"], messages.label_project_identifier
            )
        _delete_project(args.project_id)
    elif cmd == "update":
        fields = _update_fields(args)
        # --archive だけの指定は「更新項目が無い」ではなくアーカイブの依頼なので、
        # 対話には入らずそのまま通す
        if not project_service.has_update_fields(**fields) and args.archive is None:
            _interactive_fill_project_update_args(args)
            fields = _update_fields(args)
        should_update = project_service.has_update_fields(**fields)
        if should_update:
            _update_project(args.project_id, **fields)
        if args.archive is True:
            _archive_project(args.project_id)
        elif args.archive is False:
            _unarchive_project(args.project_id)
        elif not should_update:
            print(messages.update_canceled)
            sys.exit()
    elif cmd == "list" or cmd is None:
        _list_projects(full=args.full)
