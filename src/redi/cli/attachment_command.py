import argparse

from redi.attachment import read_attachment, update_attachment
from redi.cli._common import resolve_alias


def add_attachment_parser(
    subparsers: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    a_parser = subparsers.add_parser("attachment", help="添付ファイル詳細")
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
    else:
        a_parser.print_help()
