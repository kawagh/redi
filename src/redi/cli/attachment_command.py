import argparse
import json
import sys
from pathlib import Path

import requests

from redi.api.attachment import AttachmentNotFoundException
from redi.api.exceptions import print_http_error_body
from redi.api.types import Attachment
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete, confirm_overwrite
from redi.i18n import messages
from redi.service import attachment_service


def _fetch_attachment(attachment_id: str) -> Attachment:
    """添付ファイルのメタ情報を取得する。存在しない場合は exit 1。"""
    try:
        return attachment_service.read_attachment(attachment_id)
    except AttachmentNotFoundException:
        print(messages.attachment_not_found.format(id=attachment_id))
        sys.exit(1)


def _view_attachment(attachment_id: str, full: bool = False) -> None:
    """添付ファイルの詳細を標準出力に出す。full=True では取得した JSON をそのまま出す。"""
    attachment = _fetch_attachment(attachment_id)
    if full:
        print(json.dumps(attachment, ensure_ascii=False))
        return
    lines = [
        f"{attachment['id']} {attachment['filename']}",
        messages.label_size.format(value=attachment.get("filesize", "")),
        messages.label_kind.format(value=attachment.get("content_type", "")),
    ]
    author = attachment.get("author") or {}
    if author:
        lines.append(messages.label_author.format(value=author.get("name", "")))
    if attachment.get("created_on"):
        lines.append(messages.label_created_on.format(value=attachment["created_on"]))
    if attachment.get("description"):
        lines.append(
            messages.label_description_field.format(value=attachment["description"])
        )
    if attachment.get("content_url"):
        lines.append(messages.label_url_field.format(value=attachment["content_url"]))
    print("\n".join(lines))


def _download_attachment(attachment: Attachment, path: Path) -> None:
    """添付ファイルを保存し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        attachment_service.download_attachment(attachment, path)
    except attachment_service.UnexpectedContentUrlException as e:
        print(messages.attachment_content_url_unexpected.format(url=e.url))
        sys.exit(1)
    except AttachmentNotFoundException as e:
        print(messages.attachment_not_found.format(id=e.attachment_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.attachment_download_failed)
        sys.exit(1)
    except OSError as e:
        print(e)
        print(messages.attachment_download_failed)
        sys.exit(1)
    print(messages.attachment_downloaded.format(path=path))


def _update_attachment(
    attachment_id: str,
    filename: str | None = None,
    description: str | None = None,
) -> None:
    """添付ファイルを更新し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        attachment_service.update_attachment(
            attachment_id, filename=filename, description=description
        )
    except AttachmentNotFoundException:
        print(messages.attachment_not_found.format(id=attachment_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.attachment_update_failed)
        sys.exit(1)
    print(
        messages.attachment_updated.format(
            url=attachment_service.attachment_url(attachment_id)
        )
    )


def _delete_attachment(attachment_id: str) -> None:
    """添付ファイルを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        attachment_service.delete_attachment(attachment_id)
    except AttachmentNotFoundException:
        print(messages.attachment_not_found.format(id=attachment_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.attachment_delete_failed)
        sys.exit(1)
    print(messages.attachment_deleted.format(id=attachment_id))


def add_attachment_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    a_parser = subparsers.add_parser(
        "attachment",
        aliases=["a"],
        help=messages.arg_help_attachment_command,
        parents=parents,
    )
    a_subparsers = a_parser.add_subparsers(dest="attachment_command")
    a_parser.set_defaults(_print_help=a_parser.print_help)
    a_view_parser = a_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_attachment_view, parents=parents
    )
    a_view_parser.add_argument(
        "attachment_id", help=messages.arg_help_attachment_view_id
    )
    a_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    a_download_parser = a_subparsers.add_parser(
        "download",
        aliases=["dl"],
        help=messages.arg_help_attachment_download,
        parents=parents,
    )
    a_download_parser.add_argument(
        "attachment_id", help=messages.arg_help_attachment_download_id
    )
    a_download_parser.add_argument(
        "--output", "-o", help=messages.arg_help_attachment_output
    )
    a_download_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )
    a_update_parser = a_subparsers.add_parser(
        "update",
        aliases=["u"],
        help=messages.arg_help_attachment_update,
        parents=parents,
    )
    a_update_parser.add_argument(
        "attachment_id", help=messages.arg_help_attachment_update_id
    )
    a_update_parser.add_argument(
        "--filename", "-f", help=messages.arg_help_attachment_filename
    )
    a_update_parser.add_argument(
        "--description", "-d", help=messages.arg_help_attachment_description
    )
    a_delete_parser = a_subparsers.add_parser(
        "delete",
        aliases=["d"],
        help=messages.arg_help_attachment_delete,
        parents=parents,
    )
    a_delete_parser.add_argument(
        "attachment_id", help=messages.arg_help_attachment_delete_id
    )
    a_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def handle_attachment(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.attachment_command)
    if cmd == "view":
        _view_attachment(args.attachment_id, full=args.full)
    elif cmd == "download":
        attachment = _fetch_attachment(args.attachment_id)
        path = attachment_service.resolve_download_path(attachment, args.output)
        if path.exists() and not args.yes:
            confirm_overwrite(messages.overwrite_target_file.format(path=path))
        _download_attachment(attachment, path)
    elif cmd == "update":
        if args.filename is None and args.description is None:
            print(messages.update_canceled)
            sys.exit()
        _update_attachment(
            attachment_id=args.attachment_id,
            filename=args.filename,
            description=args.description,
        )
    elif cmd == "delete":
        if not args.yes:
            attachment = _fetch_attachment(args.attachment_id)
            confirm_delete(
                messages.delete_target_attachment.format(
                    id=attachment["id"], filename=attachment["filename"]
                )
            )
        _delete_attachment(args.attachment_id)
    else:
        args._print_help()
