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
from redi.cli.util import open_editor
from redi.cli.group_command import add_group_parser, handle_group
from redi.cli.init_command import add_init_parser, handle_init
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
from redi.api.exceptions import RedmineValidationException
from redi.api.issue import add_note
from redi.api.issue_status import list_issue_statuses
from redi.api.query import list_queries
from redi.api.tracker import list_trackers
from redi.api.wiki import WikiUpdateConflictException
from redi.i18n import messages
from redi.tui import TuiState, run_issue_tui


def _format_validation_error(e: RedmineValidationException) -> str:
    action_label = {
        "create": messages.action_create,
        "update": messages.action_update,
    }[e.action]
    return messages.validation_failed.format(
        resource=e.resource,
        action=action_label,
        errors="\n".join(f"- {err}" for err in e.errors),
    )


def _profile_parser() -> argparse.ArgumentParser:
    """--profile を後置するためのパーサ"""
    parser = argparse.ArgumentParser(
        # 親子でヘルプを衝突させない
        add_help=False,
    )
    parser.add_argument(
        "--profile",
        # 下流のパーサでprofileが未指定の場合に上流パーサの値を上書きするのを防ぐ
        default=argparse.SUPPRESS,
        help=messages.arg_help_profile,
    )
    return parser


def build_redi_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=messages.arg_help_root_description)
    parser.add_argument(
        "-V", "--version", action="version", version=f"redi {version('redtile')}"
    )
    parser.add_argument("--tui", action="store_true", help=messages.arg_help_tui)
    parser.add_argument("--debug", action="store_true", help=messages.arg_help_debug)
    parser.add_argument(
        "--debug-tui",
        action="store_true",
        help=messages.arg_help_debug_tui,
    )
    parser.add_argument(
        "--profile",
        help=messages.arg_help_profile,
    )
    parents = [_profile_parser()]
    subparsers = parser.add_subparsers(dest="command")
    add_project_parser(subparsers, parents)
    add_issue_parser(subparsers, parents)
    add_version_parser(subparsers, parents)
    add_wiki_parser(subparsers, parents)
    add_config_parser(subparsers, parents)
    add_init_parser(subparsers)
    add_user_parser(subparsers, parents)
    add_me_parser(subparsers, parents)
    add_membership_parser(subparsers, parents)
    add_news_parser(subparsers, parents)
    add_tracker_parser(subparsers, parents)
    add_issue_status_parser(subparsers, parents)
    add_issue_priority_parser(subparsers, parents)
    add_time_entry_activity_parser(subparsers, parents)
    add_document_category_parser(subparsers, parents)
    add_role_parser(subparsers, parents)
    add_group_parser(subparsers, parents)
    add_query_parser(subparsers, parents)
    add_custom_field_parser(subparsers, parents)
    add_issue_category_parser(subparsers, parents)
    add_search_parser(subparsers, parents)
    add_attachment_parser(subparsers, parents)
    add_relation_parser(subparsers, parents)
    add_time_entry_parser(subparsers, parents)
    add_file_parser(subparsers, parents)
    return parser


def main() -> None:
    parser = build_redi_parser()
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

    if args.command == "init":
        handle_init(args)
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
            try:
                if tui_result.action == "update" and tui_result.tab == "issues":
                    handle_issue_update(
                        argparse.Namespace(
                            issue_id=tui_result.issue_id,
                            subject=None,
                            description=None,
                            tracker_id=None,
                            status_id=None,
                            priority_id=None,
                            assigned_to_id=None,
                            fixed_version_id=None,
                            parent_issue_id=None,
                            start_date=None,
                            due_date=None,
                            done_ratio=None,
                            estimated_hours=None,
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
                    )
                elif tui_result.action == "create" and tui_result.tab == "issues":
                    handle_issue_create(
                        argparse.Namespace(
                            subject=None,
                            project_id=None,
                            tracker_id=None,
                            priority_id=None,
                            assigned_to_id=None,
                            description=None,
                            custom_fields=None,
                        )
                    )
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
                            comments="",
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
                            comments="",
                        )
                    )
                elif tui_result.action == "create_time_entry":
                    if not tui_result.issue_id:
                        continue
                    handle_time_entry(
                        argparse.Namespace(
                            time_entry_command="create",
                            project_id=None,
                            user_id=None,
                            full=False,
                            hours=None,
                            issue_id=tui_result.issue_id,
                            activity_id=None,
                            spent_on=None,
                            comments=None,
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
                            default_issue_id=tui_result.issue_id,
                            activity_id=None,
                            spent_on=None,
                            comments=None,
                        )
                    )
                elif tui_result.action == "update" and tui_result.tab == "time_entries":
                    if tui_result.time_entry_id is None:
                        continue
                    handle_time_entry(
                        argparse.Namespace(
                            time_entry_command="update",
                            time_entry_id=tui_result.time_entry_id,
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
            except RedmineValidationException as e:
                tui_state.error_modal = _format_validation_error(e)
            except WikiUpdateConflictException as e:
                tui_state.error_modal = messages.wiki_page_update_conflict.format(
                    title=e.title
                )

    if args.command in ("project", "p"):
        handle_project(args)
    elif args.command in ("issue", "i"):
        try:
            handle_issue(args)
        except RedmineValidationException as e:
            print(_format_validation_error(e))
            exit(1)
    elif args.command in ("version", "v"):
        handle_version(args)
    elif args.command in ("wiki", "w"):
        try:
            handle_wiki(args)
        except WikiUpdateConflictException as e:
            print(messages.wiki_page_update_conflict.format(title=e.title))
            exit(1)
        except RedmineValidationException as e:
            print(_format_validation_error(e))
            exit(1)
    elif args.command in ("user", "u"):
        handle_user(args)
    elif args.command == "me":
        handle_me(args)
    elif args.command in ("membership", "m"):
        handle_membership(args)
    elif args.command in ("news", "n"):
        handle_news(args)
    elif args.command in ("tracker", "t"):
        list_trackers(full=args.full)
    elif args.command in ("issue_status", "is"):
        list_issue_statuses(full=args.full)
    elif args.command in ("issue_priority", "ip"):
        list_issue_priorities(full=args.full)
    elif args.command in ("time_entry_activity", "tea"):
        list_time_entry_activities(full=args.full)
    elif args.command in ("document_category", "dc"):
        list_document_categories(full=args.full)
    elif args.command in ("role", "r"):
        handle_role(args)
    elif args.command in ("group", "g"):
        handle_group(args)
    elif args.command in ("query", "q"):
        list_queries(full=args.full)
    elif args.command in ("custom_field", "cf"):
        list_custom_fields(full=args.full)
    elif args.command in ("issue_category", "ic"):
        handle_issue_category(args)
    elif args.command in ("search", "s"):
        handle_search(args)
    elif args.command in ("attachment", "a"):
        handle_attachment(args)
    elif args.command == "relation":
        handle_relation(args)
    elif args.command in ("time_entry", "te"):
        try:
            handle_time_entry(args)
        except RedmineValidationException as e:
            print(_format_validation_error(e))
            exit(1)
    elif args.command in ("file", "f"):
        handle_file(args)
    else:
        parser.print_help()
