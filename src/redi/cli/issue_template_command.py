import argparse
import json
import sys

from redi import config
from redi.api.issue_template import TEMPLATE_KEYS, fetch_issue_templates
from redi.i18n import messages
from redi.output import eprint


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
        "--tracker_id", "-t", help=messages.arg_help_issue_filter_tracker
    )
    it_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def handle_issue_template(args: argparse.Namespace) -> None:
    project_id = args.project_id or config.default_project_id
    if not project_id:
        eprint(messages.project_id_required)
        sys.exit(1)
    templates = fetch_issue_templates(project_id, tracker_id=args.tracker_id)
    if templates is None:
        eprint(messages.issue_template_not_available)
        sys.exit(1)
    if args.full:
        print(json.dumps(templates, ensure_ascii=False))
        return
    for key in TEMPLATE_KEYS:
        section = templates.get(key) or []
        if not section:
            continue
        print(f"# {key}")
        for template in section:
            print(f"{template['id']} {template['title']}")
