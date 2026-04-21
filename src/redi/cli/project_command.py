import argparse

from redi.cli._common import resolve_alias
from redi.api.project import (
    archive_project,
    create_project,
    delete_project,
    list_projects,
    read_project,
    unarchive_project,
    update_project,
)


def add_project_parser(subparsers: argparse._SubParsersAction) -> None:
    p_parser = subparsers.add_parser(
        "project", aliases=["p"], help="プロジェクト一覧/詳細/作成/更新/削除"
    )
    p_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    p_subparsers = p_parser.add_subparsers(dest="project_command")
    p_view_parser = p_subparsers.add_parser(
        "view", aliases=["v"], help="プロジェクト詳細"
    )
    p_view_parser.add_argument("project_id", help="プロジェクトID")
    p_view_parser.add_argument(
        "--include",
        help="追加情報（trackers,issue_categories,enabled_modules,time_entry_activities,issue_custom_fields）",
    )
    p_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    p_view_parser.add_argument(
        "--web", "-w", action="store_true", help="ブラウザでRedmineのページを開く"
    )
    p_create_parser = p_subparsers.add_parser(
        "create", aliases=["c"], help="プロジェクト作成"
    )
    p_create_parser.add_argument("name", help="プロジェクト名")
    p_create_parser.add_argument(
        "identifier", help="プロジェクト識別子（英数字とハイフン）"
    )
    p_create_parser.add_argument("--description", "-d", help="説明")
    p_create_parser.add_argument(
        "--is_public",
        choices=["true", "false"],
        help="公開設定",
    )
    p_create_parser.add_argument("--parent_id", help="親プロジェクトID")
    p_create_parser.add_argument(
        "--tracker_ids", help="トラッカーID（カンマ区切り。例: 1,2,3）"
    )
    p_delete_parser = p_subparsers.add_parser(
        "delete", aliases=["d"], help="プロジェクト削除"
    )
    p_delete_parser.add_argument("project_id", help="プロジェクトID")
    p_update_parser = p_subparsers.add_parser(
        "update", aliases=["u"], help="プロジェクト更新"
    )
    p_update_parser.add_argument("project_id", help="プロジェクトID")
    p_update_parser.add_argument("--name", "-n", help="プロジェクト名")
    p_update_parser.add_argument("--description", "-d", help="説明")
    p_update_parser.add_argument(
        "--is_public",
        choices=["true", "false"],
        help="公開設定",
    )
    p_update_parser.add_argument("--parent_id", help="親プロジェクトID")
    p_update_parser.add_argument(
        "--tracker_ids", help="トラッカーID（カンマ区切り。例: 1,2,3）"
    )
    p_update_parser.add_argument(
        "--archive",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="アーカイブ (--no-archive で解除)",
    )


def handle_project(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.project_command)
    if cmd == "view":
        read_project(
            args.project_id,
            include=args.include or "",
            full=args.full,
            web=args.web,
        )
    elif cmd == "create":
        is_public = None
        if args.is_public is not None:
            is_public = args.is_public == "true"
        tracker_ids = None
        if args.tracker_ids:
            tracker_ids = [int(x) for x in args.tracker_ids.split(",")]
        create_project(
            name=args.name,
            identifier=args.identifier,
            description=args.description,
            is_public=is_public,
            parent_id=args.parent_id,
            tracker_ids=tracker_ids,
        )
    elif cmd == "delete":
        delete_project(args.project_id)
    elif cmd == "update":
        is_public = None
        if args.is_public is not None:
            is_public = args.is_public == "true"
        tracker_ids = None
        if args.tracker_ids:
            tracker_ids = [int(x) for x in args.tracker_ids.split(",")]
        should_update = (
            args.name is not None
            or args.description is not None
            or is_public is not None
            or args.parent_id is not None
            or tracker_ids is not None
        )
        if should_update:
            update_project(
                project_id=args.project_id,
                name=args.name,
                description=args.description,
                is_public=is_public,
                parent_id=args.parent_id,
                tracker_ids=tracker_ids,
            )
        if args.archive is True:
            archive_project(args.project_id)
        elif args.archive is False:
            unarchive_project(args.project_id)
        elif not should_update:
            print("更新をキャンセルしました")
            exit()
    else:
        list_projects(full=args.full)
