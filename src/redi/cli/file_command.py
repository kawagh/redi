import argparse

from redi.api.file import create_file, list_files
from redi.cli._common import resolve_alias
from redi.config import default_project_id
from redi.i18n import messages


def add_file_parser(subparsers: argparse._SubParsersAction) -> None:
    f_parser = subparsers.add_parser("file", help=messages.arg_help_file_command)
    f_parser.add_argument("--project_id", "-p", help=messages.arg_help_project_id)
    f_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    f_subparsers = f_parser.add_subparsers(dest="file_command")
    f_subparsers.add_parser("list", aliases=["l"], help=messages.arg_help_file_list)
    f_create_parser = f_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_file_create
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


def handle_file(args: argparse.Namespace) -> None:
    project_id = args.project_id or default_project_id
    if not project_id:
        print(messages.project_id_required)
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
    if cmd == "list" or cmd is None:
        list_files(project_id, full=args.full)
