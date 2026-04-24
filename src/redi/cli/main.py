# PYTHON_ARGCOMPLETE_OK
import argparse
import logging
from datetime import datetime
from importlib.metadata import version

import argcomplete

from redi.cli.attachment_command import add_attachment_parser, handle_attachment
from redi.cli.config_command import add_config_parser, handle_config
from redi.cli.file_command import add_file_parser, handle_file
from redi.cli.enumerations_command import (
    add_custom_field_parser,
    add_document_category_parser,
    add_issue_priority_parser,
    add_issue_status_parser,
    add_query_parser,
    add_time_entry_activity_parser,
    add_tracker_parser,
)
from redi.cli._common import open_editor
from redi.cli.group_command import add_group_parser, handle_group
from redi.cli.issue_category_command import (
    add_issue_category_parser,
    handle_issue_category,
)
from redi.cli.issue_command import (
    add_issue_parser,
    handle_issue,
    handle_issue_create,
    handle_issue_update,
)
from redi.cli.me_command import add_me_parser, handle_me
from redi.cli.membership_command import add_membership_parser, handle_membership
from redi.cli.news_command import add_news_parser, handle_news
from redi.cli.project_command import add_project_parser, handle_project
from redi.cli.relation_command import add_relation_parser, handle_relation
from redi.cli.role_command import add_role_parser, handle_role
from redi.cli.search_command import add_search_parser, handle_search
from redi.cli.time_entry_command import add_time_entry_parser, handle_time_entry
from redi.cli.user_command import add_user_parser, handle_user
from redi.cli.version_command import add_version_parser, handle_version
from redi.cli.wiki_command import add_wiki_parser, handle_wiki
from redi.config import CONFIG_PATH, check_config
from redi.api.custom_field import list_custom_fields
from redi.api.enumeration import (
    list_document_categories,
    list_issue_priorities,
    list_time_entry_activities,
)
from redi.api.issue import add_note
from redi.api.issue_status import list_issue_statuses
from redi.api.query import list_queries
from redi.api.tracker import list_trackers
from redi.tui import TuiState, run_issue_tui


def _build_parser() -> tuple[
    argparse.ArgumentParser, argparse.ArgumentParser, argparse.ArgumentParser
]:
    parser = argparse.ArgumentParser(description="Redmine CLI")
    parser.add_argument(
        "-V", "--version", action="version", version=f"redi {version('redtile')}"
    )
    parser.add_argument("--tui", action="store_true", help="TUI")
    parser.add_argument("--debug", action="store_true", help="デバッグログを有効にする")
    parser.add_argument(
        "--debug-tui",
        action="store_true",
        help="TUI のスクリーン内容を YAML 形式でログ出力する",
    )
    parser.add_argument(
        "--profile",
        help="使用するプロファイル名（config.tomlのdefault_profileを一時的に上書き）",
    )
    subparsers = parser.add_subparsers(dest="command")
    add_project_parser(subparsers)
    add_issue_parser(subparsers)
    add_version_parser(subparsers)
    add_wiki_parser(subparsers)
    add_config_parser(subparsers)
    add_user_parser(subparsers)
    add_me_parser(subparsers)
    add_membership_parser(subparsers)
    add_news_parser(subparsers)
    add_tracker_parser(subparsers)
    add_issue_status_parser(subparsers)
    add_issue_priority_parser(subparsers)
    add_time_entry_activity_parser(subparsers)
    add_document_category_parser(subparsers)
    add_role_parser(subparsers)
    add_group_parser(subparsers)
    add_query_parser(subparsers)
    add_custom_field_parser(subparsers)
    add_issue_category_parser(subparsers)
    add_search_parser(subparsers)
    a_parser = add_attachment_parser(subparsers)
    r_parser = add_relation_parser(subparsers)
    add_time_entry_parser(subparsers)
    add_file_parser(subparsers)
    return parser, a_parser, r_parser


def main() -> None:
    parser, a_parser, r_parser = _build_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.debug_tui:
        args.tui = True

    if args.debug:
        log_path = CONFIG_PATH.parent / "redi-debug.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_path)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s")
        )
        redi_logger = logging.getLogger("redi")
        redi_logger.setLevel(logging.DEBUG)
        redi_logger.addHandler(handler)

    if args.command in ("config", "c"):
        handle_config(args)
        return

    check_config()

    if args.tui and args.command is None:
        tui_state = TuiState()
        debug_log_path = None
        if args.debug_tui:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            debug_log_path = CONFIG_PATH.parent / f"redi-debug-tui-{timestamp}.yaml"
            debug_log_path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            tui_result = run_issue_tui(state=tui_state, debug_log_path=debug_log_path)
            if tui_result is None:
                return
            tui_state = TuiState(last_result=tui_result)
            if tui_result.action == "update" and tui_result.tab == "issues":
                update_args = argparse.Namespace(
                    issue_id=tui_result.issue_id,
                    subject=None,
                    description=None,
                    tracker_id=None,
                    status_id=None,
                    priority_id=None,
                    assigned_to_id=None,
                    fixed_version_id=None,
                    parent_issue_id=None,
                    notes=None,
                    custom_fields=None,
                    relate=None,
                    relate_to=None,
                    delete_relation=False,
                    attach=None,
                    hours=None,
                    activity_id=None,
                    spent_on=None,
                    time_comments=None,
                    add_watcher_ids=None,
                    remove_watcher_ids=None,
                )
                handle_issue_update(update_args)
            elif tui_result.action == "create" and tui_result.tab == "issues":
                create_args = argparse.Namespace(
                    subject=None,
                    project_id=None,
                    tracker_id=None,
                    priority_id=None,
                    assigned_to_id=None,
                    description=None,
                    custom_fields=None,
                )
                handle_issue_create(create_args)
            elif tui_result.action == "comment":
                if tui_result.issue_id is None:
                    continue
                notes = open_editor()
                if notes:
                    add_note(tui_result.issue_id, notes)
            elif tui_result.action == "create" and tui_result.tab == "wiki":
                handle_wiki(
                    argparse.Namespace(
                        wiki_command="create",
                        project_id=None,
                        full=False,
                        page_title=None,
                        parent_title=tui_result.parent_wiki_title,
                        description=None,
                    )
                )
            elif tui_result.action == "update" and tui_result.tab == "wiki":
                handle_wiki(
                    argparse.Namespace(
                        wiki_command="update",
                        project_id=None,
                        full=False,
                        page_title=tui_result.wiki_title,
                        description=None,
                    )
                )
            elif tui_result.action == "create" and tui_result.tab == "time_entries":
                handle_time_entry(
                    argparse.Namespace(
                        time_entry_command="create",
                        project_id=None,
                        user_id=None,
                        full=False,
                        hours=None,
                        issue_id=None,
                        activity_id=None,
                        spent_on=None,
                        comments=None,
                    )
                )

    if args.command in ("project", "p"):
        handle_project(args)
    elif args.command in ("issue", "i"):
        handle_issue(args)
    elif args.command in ("version", "v"):
        handle_version(args)
    elif args.command in ("wiki", "w"):
        handle_wiki(args)
    elif args.command in ("user", "u"):
        handle_user(args)
    elif args.command == "me":
        handle_me(args)
    elif args.command in ("membership", "m"):
        handle_membership(args)
    elif args.command == "news":
        handle_news(args)
    elif args.command == "tracker":
        list_trackers(full=args.full)
    elif args.command == "issue_status":
        list_issue_statuses(full=args.full)
    elif args.command == "issue_priority":
        list_issue_priorities(full=args.full)
    elif args.command == "time_entry_activity":
        list_time_entry_activities(full=args.full)
    elif args.command == "document_category":
        list_document_categories(full=args.full)
    elif args.command == "role":
        handle_role(args)
    elif args.command == "group":
        handle_group(args)
    elif args.command == "query":
        list_queries(full=args.full)
    elif args.command == "custom_field":
        list_custom_fields(full=args.full)
    elif args.command == "issue_category":
        handle_issue_category(args)
    elif args.command == "search":
        handle_search(args)
    elif args.command == "attachment":
        handle_attachment(args, a_parser)
    elif args.command == "relation":
        handle_relation(args, r_parser)
    elif args.command == "time_entry":
        handle_time_entry(args)
    elif args.command == "file":
        handle_file(args)
    else:
        parser.print_help()
