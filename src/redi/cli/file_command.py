import argparse
import json
import sys

import requests

from redi import config
from redi.api.exceptions import print_http_error_body
from redi.api.file import ProjectNotFoundException
from redi.cli.alias import resolve_alias
from redi.cli.shared_options import project_option_parser
from redi.i18n import messages
from redi.service import file_service


def add_file_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    f_parser = subparsers.add_parser(
        "file",
        aliases=["f"],
        help=messages.arg_help_file_command,
        parents=[*parents, project_option_parser()],
    )
    f_subparsers = f_parser.add_subparsers(dest="file_command")
    f_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_file_list,
        parents=[*parents, project_option_parser(postfix=True)],
    )
    f_create_parser = f_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_file_create, parents=parents
    )
    f_create_parser.add_argument("file_path", help=messages.arg_help_file_path)
    f_create_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_project_id
    )
    f_create_parser.add_argument(
        "--version_id", type=int, help=messages.arg_help_file_version_id
    )
    f_create_parser.add_argument(
        "--description", "-d", help=messages.arg_help_file_description
    )


def _list_files(project_id: str, full: bool = False) -> None:
    """プロジェクトのファイル一覧を標準出力に出す。プロジェクトが無い場合は exit 1。"""
    try:
        files = file_service.list_files(project_id)
    except ProjectNotFoundException:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    if full:
        print(json.dumps(files, ensure_ascii=False))
        return
    for f in files:
        version = f.get("version") or {}
        version_label = f" [{version.get('name')}]" if version else ""
        size = f.get("filesize", "")
        print(f"{f['id']} {f['filename']} ({size}B){version_label}")


def _create_file(
    project_id: str,
    file_path: str,
    version_id: int | None = None,
    description: str | None = None,
) -> None:
    """ファイルをプロジェクトに登録し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        filename = file_service.create_file(
            project_id,
            file_path,
            version_id=version_id,
            description=description,
        )
    except ProjectNotFoundException:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.file_upload_failed)
        sys.exit(1)
    print(messages.file_uploaded.format(filename=filename))


def handle_file(args: argparse.Namespace) -> None:
    project_id = args.project_id or config.default_project_id
    if not project_id:
        print(messages.project_id_required)
        sys.exit(1)
    cmd = resolve_alias(args.file_command)
    if cmd == "create":
        _create_file(
            project_id=project_id,
            file_path=args.file_path,
            version_id=args.version_id,
            description=args.description,
        )
        return
    if cmd == "list" or cmd is None:
        _list_files(project_id, full=args.full)
