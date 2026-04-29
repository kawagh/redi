import argparse

from redi.api.attachment import (
    delete_attachment,
    fetch_attachment,
    read_attachment,
    update_attachment,
)
from redi.cli._common import confirm_delete, resolve_alias
from redi.i18n import messages


def add_attachment_parser(subparsers: argparse._SubParsersAction) -> None:
    a_parser = subparsers.add_parser(
        "attachment", help=messages.arg_help_attachment_command
    )
    a_subparsers = a_parser.add_subparsers(dest="attachment_command")
    a_parser.set_defaults(_print_help=a_parser.print_help)
    a_view_parser = a_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_attachment_view
    )
    a_view_parser.add_argument(
        "attachment_id", help=messages.arg_help_attachment_view_id
    )
    a_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    a_update_parser = a_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_attachment_update
    )
    a_update_parser.add_argument(
        "attachment_id", help=messages.arg_help_attachment_update_id
    )
    a_update_parser.add_argument(
        "--filename", "-f", help=messages.arg_help_attachment_filename
    )
    a_update_parser.add_argument(
        "--description", "-d", help=messages.arg_help_attachment_description
    )
    a_delete_parser = a_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_attachment_delete
    )
    a_delete_parser.add_argument(
        "attachment_id", help=messages.arg_help_attachment_delete_id
    )
    a_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def handle_attachment(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.attachment_command)
    if cmd == "view":
        read_attachment(args.attachment_id, full=args.full)
    elif cmd == "update":
        update_attachment(
            attachment_id=args.attachment_id,
            filename=args.filename,
            description=args.description,
        )
    elif cmd == "delete":
        if not args.yes:
            attachment = fetch_attachment(args.attachment_id)
            confirm_delete(
                messages.delete_target_attachment.format(
                    id=attachment["id"], filename=attachment["filename"]
                )
            )
        delete_attachment(args.attachment_id)
    else:
        args._print_help()
