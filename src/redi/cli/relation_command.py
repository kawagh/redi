import argparse

from redi.api.issue_relation import read_relation
from redi.cli._common import resolve_alias


def add_relation_parser(
    subparsers: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    r_parser = subparsers.add_parser("relation", help="イシュー関係性 詳細")
    r_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    r_subparsers = r_parser.add_subparsers(dest="relation_command")
    r_view_parser = r_subparsers.add_parser("view", aliases=["v"], help="関係性詳細")
    r_view_parser.add_argument("relation_id", help="関係性ID")
    r_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    return r_parser


def handle_relation(
    args: argparse.Namespace, r_parser: argparse.ArgumentParser
) -> None:
    cmd = resolve_alias(args.relation_command)
    if cmd == "view":
        read_relation(args.relation_id, full=args.full)
        return
    r_parser.print_help()
