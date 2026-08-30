"""`issue_category` サブコマンドの表示整形と引数の検証。

取得や更新は `service.issue_category_service` に任せ、ここでは print と
sys.exit を担当する。
"""

import argparse
import json
import sys

import requests

from redi import config
from redi.api.exceptions import ProjectNotFoundException, print_http_error_body
from redi.api.issue_category import IssueCategory, IssueCategoryNotFoundException
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.shared_options import project_option_parser
from redi.i18n import messages
from redi.output import eprint
from redi.service import issue_category_service


def add_issue_category_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    ic_parser = subparsers.add_parser(
        "issue_category",
        aliases=["ic"],
        help=messages.arg_help_issue_category_command,
        parents=[*parents, project_option_parser()],
    )
    ic_subparsers = ic_parser.add_subparsers(dest="issue_category_command")
    ic_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_issue_category_list,
        parents=[*parents, project_option_parser(postfix=True)],
    )

    ic_view_parser = ic_subparsers.add_parser(
        "view",
        aliases=["v"],
        help=messages.arg_help_issue_category_view,
        parents=parents,
    )
    ic_view_parser.add_argument(
        "category_id", help=messages.arg_help_issue_category_view_id
    )
    ic_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )

    ic_create_parser = ic_subparsers.add_parser(
        "create",
        aliases=["c"],
        help=messages.arg_help_issue_category_create,
        parents=parents,
    )
    ic_create_parser.add_argument("name", help=messages.arg_help_issue_category_name)
    ic_create_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_project_id
    )
    ic_create_parser.add_argument(
        "--assigned_to_id",
        type=int,
        help=messages.arg_help_issue_category_assigned_to_id,
    )

    ic_update_parser = ic_subparsers.add_parser(
        "update",
        aliases=["u"],
        help=messages.arg_help_issue_category_update,
        parents=parents,
    )
    ic_update_parser.add_argument(
        "category_id", help=messages.arg_help_issue_category_update_id
    )
    ic_update_parser.add_argument(
        "--name", "-n", help=messages.arg_help_issue_category_name_opt
    )
    ic_update_parser.add_argument(
        "--assigned_to_id",
        type=int,
        help=messages.arg_help_issue_category_assigned_to_id,
    )

    ic_delete_parser = ic_subparsers.add_parser(
        "delete",
        aliases=["d"],
        help=messages.arg_help_issue_category_delete,
        parents=parents,
    )
    ic_delete_parser.add_argument(
        "category_id", help=messages.arg_help_issue_category_delete_id
    )
    ic_delete_parser.add_argument(
        "--reassign_to_id",
        type=int,
        help=messages.arg_help_issue_category_reassign_to_id,
    )
    ic_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def _list_issue_categories(project_id: str, full: bool = False) -> None:
    """イシューカテゴリ一覧を1行ずつ出す。full=True では取得した JSON をそのまま出す。"""
    try:
        categories = issue_category_service.list_issue_categories(project_id)
    except ProjectNotFoundException:
        eprint(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    if full:
        print(json.dumps(categories, ensure_ascii=False))
        return
    for category in categories:
        assigned = category.get("assigned_to")
        assigned_label = f" [{assigned['id']} {assigned['name']}]" if assigned else ""
        print(f"{category['id']} {category['name']}{assigned_label}")


def _view_issue_category(category_id: str, full: bool = False) -> None:
    """イシューカテゴリの詳細を標準出力に出す。存在しない場合は exit 1。"""
    category = _read_issue_category(category_id)
    if full:
        print(json.dumps(category, ensure_ascii=False))
        return
    print("\n".join(_format_issue_category_detail(category)))


def _format_issue_category_detail(category: IssueCategory) -> list[str]:
    """イシューカテゴリの詳細表示を行のリストに整形する。"""
    project = category["project"]
    lines = [
        f"{category['id']} {category['name']}",
        messages.label_project_field.format(id=project["id"], name=project["name"]),
    ]
    assigned = category.get("assigned_to")
    if assigned:
        lines.append(
            messages.label_default_assignee.format(
                id=assigned["id"], name=assigned["name"]
            )
        )
    return lines


def _read_issue_category(category_id: str) -> IssueCategory:
    """イシューカテゴリを取得する。存在しない場合は exit 1。"""
    try:
        return issue_category_service.read_issue_category(category_id)
    except IssueCategoryNotFoundException:
        eprint(messages.category_not_found.format(id=category_id))
        sys.exit(1)


def _create_issue_category(
    project_id: str, name: str, assigned_to_id: int | None
) -> None:
    """イシューカテゴリを作成し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        created = issue_category_service.create_issue_category(
            project_id=project_id,
            name=name,
            assigned_to_id=assigned_to_id,
        )
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.category_create_failed)
        sys.exit(1)
    print(messages.category_created.format(id=created["id"], name=created["name"]))


def _update_issue_category(
    category_id: str, name: str | None, assigned_to_id: int | None
) -> None:
    """イシューカテゴリを更新し、結果を標準出力に出す。失敗時は exit 1。"""
    if name is None and assigned_to_id is None:
        print(messages.update_canceled)
        sys.exit()
    try:
        issue_category_service.update_issue_category(
            category_id=category_id,
            name=name,
            assigned_to_id=assigned_to_id,
        )
    except IssueCategoryNotFoundException:
        eprint(messages.category_not_found.format(id=category_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.category_update_failed)
        sys.exit(1)
    print(messages.category_updated.format(id=category_id))


def _delete_issue_category(category_id: str, reassign_to_id: int | None) -> None:
    """イシューカテゴリを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        issue_category_service.delete_issue_category(
            category_id=category_id,
            reassign_to_id=reassign_to_id,
        )
    except IssueCategoryNotFoundException:
        eprint(messages.category_not_found.format(id=category_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.category_delete_failed)
        sys.exit(1)
    print(messages.category_deleted.format(id=category_id))


def _resolve_project_id(args: argparse.Namespace) -> str:
    """--project_id か default_project_id を解決する。どちらも無ければ exit 1。"""
    project_id = args.project_id or config.default_project_id
    if not project_id:
        eprint(messages.project_id_required)
        sys.exit(1)
    return project_id


def handle_issue_category(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.issue_category_command)
    if cmd == "view":
        _view_issue_category(args.category_id, full=args.full)
        return
    if cmd == "create":
        _create_issue_category(
            project_id=_resolve_project_id(args),
            name=args.name,
            assigned_to_id=args.assigned_to_id,
        )
        return
    if cmd == "update":
        _update_issue_category(
            category_id=args.category_id,
            name=args.name,
            assigned_to_id=args.assigned_to_id,
        )
        return
    if cmd == "delete":
        if not args.yes:
            category = _read_issue_category(args.category_id)
            confirm_delete(
                messages.delete_target_category.format(
                    id=category["id"], name=category["name"]
                )
            )
        _delete_issue_category(
            category_id=args.category_id,
            reassign_to_id=args.reassign_to_id,
        )
        return
    if cmd == "list" or cmd is None:
        _list_issue_categories(_resolve_project_id(args), full=args.full)
