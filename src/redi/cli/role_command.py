import argparse
import json
import sys

from redi.api.role import fetch_role, fetch_roles
from redi.cli.alias import resolve_alias
from redi.cli.shared_options import full_option_parser
from redi.i18n import messages
from redi.service.role_service import CATEGORY_OTHER, group_permissions


def _print_roles(full: bool) -> None:
    roles = fetch_roles()
    if full:
        print(json.dumps(roles, ensure_ascii=False))
        return
    for role in roles:
        print(f"{role['id']} {role['name']}")


def _category_labels() -> dict[str, str]:
    """カテゴリ名の表示ラベルを返す。"""
    return {
        "project": messages.permission_category_project,
        "issue_tracking": messages.permission_category_issue_tracking,
        "time_tracking": messages.permission_category_time_tracking,
        "news": messages.permission_category_news,
        "documents": messages.permission_category_documents,
        "files": messages.permission_category_files,
        "wiki": messages.permission_category_wiki,
        "repository": messages.permission_category_repository,
        "boards": messages.permission_category_boards,
        "calendar": messages.permission_category_calendar,
        "gantt": messages.permission_category_gantt,
        CATEGORY_OTHER: messages.permission_category_other,
    }


def _print_role(role_id: str, full: bool) -> None:
    role = fetch_role(role_id)
    if role is None:
        print(messages.role_not_found.format(id=role_id))
        sys.exit(1)
    if full:
        print(json.dumps(role, ensure_ascii=False))
        return
    lines = [f"{role['id']} {role['name']}"]
    if "assignable" in role:
        lines.append(messages.label_assignable.format(value=role["assignable"]))
    if role.get("issues_visibility"):
        lines.append(
            messages.label_issues_visibility.format(value=role["issues_visibility"])
        )
    if role.get("time_entries_visibility"):
        lines.append(
            messages.label_time_entries_visibility.format(
                value=role["time_entries_visibility"]
            )
        )
    if role.get("users_visibility"):
        lines.append(
            messages.label_users_visibility.format(value=role["users_visibility"])
        )
    permissions = role.get("permissions") or []
    if permissions:
        lines.append(messages.label_permissions_header.format(count=len(permissions)))
        labels = _category_labels()
        for category, members in group_permissions(permissions):
            lines.append(f"  [{labels[category]}]")
            for p in members:
                # 公式画面と突き合わせられるよう、権限も内部名ではなく表示名で出す。
                # 表に無い権限 (プラグイン由来など) は内部名のまま出す
                lines.append(f"    {messages.permission_labels.get(p, p)}")
    print("\n".join(lines))


def add_role_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    role_parser = subparsers.add_parser(
        "role",
        aliases=["r"],
        help=messages.arg_help_role_command,
        parents=[*parents, full_option_parser()],
    )
    role_subparsers = role_parser.add_subparsers(dest="role_command")
    role_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_role_list,
        parents=[*parents, full_option_parser(postfix=True)],
    )
    role_view_parser = role_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_role_view, parents=parents
    )
    role_view_parser.add_argument("role_id", help=messages.arg_help_role_view_id)
    role_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def handle_role(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.role_command)
    if cmd == "view":
        _print_role(args.role_id, full=args.full)
    elif cmd == "list" or cmd is None:
        _print_roles(full=args.full)
