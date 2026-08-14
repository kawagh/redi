import argparse
import sys

from redi import config
from redi.api.issue_template import list_issue_templates
from redi.i18n import messages


def add_issue_template_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    it_parser = subparsers.add_parser(
        "issue_template",
        aliases=["it"],
        help=messages.arg_help_issue_template_command,
        parents=parents,
    )
    it_parser.add_argument("--project_id", "-p", help=messages.arg_help_project_id)
    it_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def handle_issue_template(args: argparse.Namespace) -> None:
    project_id = args.project_id or config.default_project_id
    if not project_id:
        print(messages.project_id_required)
        sys.exit(1)
    list_issue_templates(project_id, full=args.full)
