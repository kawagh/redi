import argparse
import json
import sys

from redi.api.issue_relation import IssueRelation, RelationNotFoundException
from redi.cli.alias import resolve_alias
from redi.cli.shared_options import add_full_argument
from redi.i18n import messages
from redi.service import issue_relation_service, issue_service


def add_relation_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    r_parser = subparsers.add_parser(
        "relation", help=messages.arg_help_relation_command, parents=parents
    )
    r_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    r_subparsers = r_parser.add_subparsers(dest="relation_command")
    r_parser.set_defaults(_print_help=r_parser.print_help)
    r_view_parser = r_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_relation_view, parents=parents
    )
    r_view_parser.add_argument("relation_id", help=messages.arg_help_relation_view_id)
    add_full_argument(r_view_parser, postfix=True)


def format_relation_detail(relation: IssueRelation) -> list[str]:
    """関係性の詳細表示を行のリストに整形する。"""
    lines = [
        f"{relation['id']} #{relation['issue_id']} --[{relation['relation_type']}]--> #{relation['issue_to_id']}",
        f"  {issue_service.issue_url(str(relation['issue_id']))}",
        f"  {issue_service.issue_url(str(relation['issue_to_id']))}",
    ]
    if relation.get("delay") is not None:
        lines.append(f"  delay: {relation['delay']}")
    return lines


def read_relation(relation_id: str, full: bool = False) -> None:
    try:
        relation = issue_relation_service.read_relation(relation_id)
    except RelationNotFoundException:
        print(messages.relation_not_found.format(id=relation_id))
        sys.exit(1)
    if full:
        print(json.dumps(relation, ensure_ascii=False))
        return
    for line in format_relation_detail(relation):
        print(line)


def handle_relation(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.relation_command)
    if cmd == "view":
        read_relation(args.relation_id, full=args.full)
        return
    args._print_help()
