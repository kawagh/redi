import argparse

from redi.api.file import create_file, list_files
from redi.cli._common import resolve_alias
from redi.config import default_project_id


def add_file_parser(subparsers: argparse._SubParsersAction) -> None:
    f_parser = subparsers.add_parser(
        "file", help="プロジェクトファイル 一覧/アップロード"
    )
    f_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    f_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    f_subparsers = f_parser.add_subparsers(dest="file_command")
    f_create_parser = f_subparsers.add_parser(
        "create", aliases=["c"], help="ファイルアップロード"
    )
    f_create_parser.add_argument("file_path", help="アップロードするファイルのパス")
    f_create_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    f_create_parser.add_argument("--version_id", type=int, help="バージョンID")
    f_create_parser.add_argument("--description", "-d", help="説明")


def handle_file(args: argparse.Namespace) -> None:
    project_id = args.project_id or default_project_id
    if not project_id:
        print("project_idを指定するか、default_project_idを設定してください")
        exit(1)
    cmd = resolve_alias(args.file_command)
    if cmd == "create":
        create_file(
            project_id=project_id,
            file_path=args.file_path,
            version_id=args.version_id,
            description=args.description,
        )
        return
    list_files(project_id, full=args.full)
