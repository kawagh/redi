import argparse

from redi.cli._common import confirm_delete, resolve_alias
from redi.config import default_project_id
from redi.api.membership import (
    create_membership,
    delete_membership,
    fetch_membership,
    list_memberships,
    read_membership,
    update_membership,
)


def _parse_role_ids(value: str) -> list[int]:
    return [int(v) for v in value.split(",") if v.strip()]


def add_membership_parser(subparsers: argparse._SubParsersAction) -> None:
    m_parser = subparsers.add_parser(
        "membership", aliases=["m"], help="メンバーシップ一覧/詳細/作成/更新/削除"
    )
    m_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    m_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    m_subparsers = m_parser.add_subparsers(dest="membership_command")

    m_view_parser = m_subparsers.add_parser(
        "view", aliases=["v"], help="メンバーシップ詳細"
    )
    m_view_parser.add_argument("membership_id", help="メンバーシップID")
    m_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )

    m_create_parser = m_subparsers.add_parser(
        "create", aliases=["c"], help="メンバーシップ作成"
    )
    m_create_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    m_create_parser.add_argument("--user_id", "-u", type=int, help="ユーザーID")
    m_create_parser.add_argument("--group_id", "-g", type=int, help="グループID")
    m_create_parser.add_argument(
        "--role_ids",
        "-r",
        required=True,
        help="ロールID（カンマ区切り。例: 3,4）",
    )

    m_update_parser = m_subparsers.add_parser(
        "update", aliases=["u"], help="メンバーシップ更新（ロールのみ変更可能）"
    )
    m_update_parser.add_argument("membership_id", help="メンバーシップID")
    m_update_parser.add_argument(
        "--role_ids",
        "-r",
        required=True,
        help="ロールID（カンマ区切り。例: 3,4）",
    )

    m_delete_parser = m_subparsers.add_parser(
        "delete", aliases=["d"], help="メンバーシップ削除"
    )
    m_delete_parser.add_argument("membership_id", help="メンバーシップID")
    m_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help="確認プロンプトをスキップ"
    )


def handle_membership(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.membership_command)
    if cmd == "view":
        read_membership(args.membership_id, full=args.full)
        return
    if cmd == "create":
        project_id = args.project_id or default_project_id
        if not project_id:
            print("project_idを指定するか、default_project_idを設定してください")
            exit(1)
        if args.user_id is None and args.group_id is None:
            print("--user_id または --group_id を指定してください")
            exit(1)
        create_membership(
            project_id=project_id,
            role_ids=_parse_role_ids(args.role_ids),
            user_id=args.user_id,
            group_id=args.group_id,
        )
        return
    if cmd == "update":
        update_membership(
            membership_id=args.membership_id,
            role_ids=_parse_role_ids(args.role_ids),
        )
        return
    if cmd == "delete":
        if not args.yes:
            m = fetch_membership(args.membership_id)
            principal = m.get("user") or m.get("group") or {}
            kind = "user" if "user" in m else "group"
            roles = ", ".join(r.get("name", "") for r in (m.get("roles") or []))
            confirm_delete(
                f"削除するメンバーシップ: {m['id']} [{kind}] "
                f"{principal.get('id', '?')} {principal.get('name', '')} - {roles}"
            )
        delete_membership(args.membership_id)
        return

    project_id = args.project_id or default_project_id
    if not project_id:
        print("project_idを指定するか、default_project_idを設定してください")
        exit(1)
    list_memberships(project_id, full=args.full)
