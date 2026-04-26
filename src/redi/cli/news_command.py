import argparse

from redi.config import default_project_id
from redi.i18n import messages
from redi.api.news import list_news


def add_news_parser(subparsers: argparse._SubParsersAction) -> None:
    n_parser = subparsers.add_parser("news", help=messages.arg_help_news_command)
    n_parser.add_argument("--project_id", "-p", help=messages.arg_help_project_id)
    n_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def handle_news(args: argparse.Namespace) -> None:
    project_id = args.project_id or default_project_id
    list_news(project_id=project_id, full=args.full)
