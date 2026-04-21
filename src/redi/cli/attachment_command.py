import argparse

from redi.api.attachment import (
    delete_attachment,
    fetch_attachment,
    read_attachment,
    update_attachment,
)
from redi.cli._common import confirm_delete, resolve_alias


def add_attachment_parser(
    subparsers: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    a_parser = subparsers.add_parser("attachment", help="添付ファイル詳細/更新/削除")
    a_subparsers = a_parser.add_subparsers(dest="attachment_command")
    a_view_parser = a_subparsers.add_parser(
        "view", aliases=["v"], help="添付ファイル詳細"
    )
    a_view_parser.add_argument("attachment_id", help="添付ファイルID")
    a_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    a_update_parser = a_subparsers.add_parser(
        "update", aliases=["u"], help="添付ファイル更新"
    )
    a_update_parser.add_argument("attachment_id", help="添付ファイルID")
    a_update_parser.add_argument("--filename", "-f", help="ファイル名")
    a_update_parser.add_argument("--description", "-d", help="説明")
    a_delete_parser = a_subparsers.add_parser(
        "delete", aliases=["d"], help="添付ファイル削除"
    )
    a_delete_parser.add_argument("attachment_id", help="添付ファイルID")
    a_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help="確認プロンプトをスキップ"
    )
    return a_parser


def handle_attachment(
    args: argparse.Namespace, a_parser: argparse.ArgumentParser
) -> None:
    cmd = resolve_alias(args.attachment_command)
    if cmd == "view":
        read_attachment(args.attachment_id, full=args.full)
    elif cmd == "update":
        update_attachment(
            attachment_id=args.attachment_id,
            filename=args.filename,
            description=args.description,
        )
    elif cmd == "delete":
        if not args.yes:
            attachment = fetch_attachment(args.attachment_id)
            confirm_delete(
                f"削除する添付ファイル: {attachment['id']} {attachment['filename']}"
            )
        delete_attachment(args.attachment_id)
    else:
        a_parser.print_help()
