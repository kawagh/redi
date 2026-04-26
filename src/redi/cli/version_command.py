import argparse

from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.validation import Validator

from redi.cli._common import (
    confirm_delete,
    inline_checkbox,
    inline_choice,
    resolve_alias,
)
from redi.config import default_project_id
from redi.i18n import messages
from redi.api.version import (
    create_version,
    delete_version,
    fetch_version,
    fetch_versions,
    list_versions,
    read_version,
    update_version,
)


def add_version_parser(subparsers: argparse._SubParsersAction) -> None:
    v_parser = subparsers.add_parser(
        "version",
        aliases=["v"],
        help=messages.arg_help_version_command,
    )
    v_parser.add_argument("--project_id", "-p", help=messages.arg_help_project_id)
    v_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    v_subparsers = v_parser.add_subparsers(dest="version_command")
    v_subparsers.add_parser("list", aliases=["l"], help=messages.arg_help_version_list)
    v_view_parser = v_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_version_view
    )
    v_view_parser.add_argument("version_id", help=messages.arg_help_version_view_id)
    v_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    v_view_parser.add_argument(
        "--web", "-w", action="store_true", help=messages.arg_help_open_web
    )
    v_create_parser = v_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_version_create
    )
    v_create_parser.add_argument(
        "name", nargs="?", default=None, help=messages.arg_help_version_name_arg
    )
    v_create_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_project_id
    )
    v_create_parser.add_argument(
        "--status",
        choices=["open", "locked", "closed"],
        help=messages.arg_help_version_status,
    )
    v_create_parser.add_argument("--due_date", help=messages.arg_help_version_due_date)
    v_create_parser.add_argument(
        "--description", "-d", help=messages.arg_help_version_description
    )
    v_create_parser.add_argument(
        "--sharing",
        choices=["none", "descendants", "hierarchy", "tree", "system"],
        help=messages.arg_help_version_sharing,
    )
    v_delete_parser = v_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_version_delete
    )
    v_delete_parser.add_argument("version_id", help=messages.arg_help_version_delete_id)
    v_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )
    v_update_parser = v_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_version_update
    )
    v_update_parser.add_argument(
        "version_id", nargs="?", help=messages.arg_help_version_update_id
    )
    v_update_parser.add_argument(
        "--name", "-n", help=messages.arg_help_version_name_opt
    )
    v_update_parser.add_argument(
        "--status",
        choices=["open", "locked", "closed"],
        help=messages.arg_help_version_status,
    )
    v_update_parser.add_argument("--due_date", help=messages.arg_help_version_due_date)
    v_update_parser.add_argument(
        "--description", "-d", help=messages.arg_help_version_description
    )
    v_update_parser.add_argument(
        "--sharing",
        choices=["none", "descendants", "hierarchy", "tree", "system"],
        help=messages.arg_help_version_sharing,
    )


def _interactive_select_version_id(project_id: str) -> str:
    versions = fetch_versions(project_id)
    if not versions:
        print(messages.no_versions_available)
        exit(1)
    options: list[tuple[str, str]] = [
        (str(v["id"]), f"{v['id']} {v['name']} ({v['status']})") for v in versions
    ]
    labels = dict(options)
    try:
        selected = inline_choice(messages.prompt_select_version_to_update, options)
    except KeyboardInterrupt:
        print(messages.canceled)
        exit(1)
    print(messages.update_target_version.format(label=labels[selected]))
    return selected


def _interactive_fill_version_update_args(args: argparse.Namespace) -> None:
    current = fetch_version(args.version_id)
    field_values: list[tuple[str, str]] = [
        ("name", messages.field_version_name),
        ("status", messages.field_status),
        ("due_date", messages.field_due_date),
        ("description", messages.field_description),
        ("sharing", messages.field_sharing),
    ]
    try:
        selected = inline_checkbox(messages.prompt_select_update_items, field_values)
    except KeyboardInterrupt:
        print(messages.canceled)
        exit(1)
    if not selected:
        print(messages.canceled_no_items_selected)
        exit(1)
    labels = dict(field_values)
    print(messages.update_items.format(items=", ".join(labels[v] for v in selected)))
    try:
        if "name" in selected:
            args.name = prompt(
                messages.prompt_version_name, default=current.get("name", "")
            ).strip()

        if "status" in selected:
            status_options: list[tuple[str, str]] = [
                ("open", "open"),
                ("locked", "locked"),
                ("closed", "closed"),
            ]
            args.status = inline_choice(
                messages.prompt_select_status,
                status_options,
                default=current.get("status", "open"),
            )
            print(messages.status_label.format(value=args.status))

        if "due_date" in selected:
            args.due_date = prompt(
                messages.prompt_due_date_optional, default=current.get("due_date", "")
            ).strip()

        if "description" in selected:
            args.description = prompt(
                messages.prompt_description_optional,
                default=current.get("description", ""),
            ).strip()

        if "sharing" in selected:
            sharing_options: list[tuple[str, str]] = [
                ("none", "none"),
                ("descendants", "descendants"),
                ("hierarchy", "hierarchy"),
                ("tree", "tree"),
                ("system", "system"),
            ]
            args.sharing = inline_choice(
                messages.prompt_select_sharing,
                sharing_options,
                default=current.get("sharing", "none"),
            )
            print(messages.sharing_label.format(value=args.sharing))
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)


def _interactive_create_version(project_id: str, args: argparse.Namespace) -> None:
    non_empty_validator = Validator.from_callable(
        lambda text: len(text.strip()) > 0,
        error_message=messages.error_input_required,
    )
    try:
        name = prompt(
            messages.prompt_version_name, validator=non_empty_validator
        ).strip()
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)

    try:
        due_date = prompt(messages.prompt_due_date_optional).strip() or None
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)

    try:
        description = prompt(messages.prompt_description_optional).strip() or None
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)

    sharing_options: list[tuple[str, str]] = [
        ("none", messages.sharing_none),
        ("descendants", messages.sharing_descendants),
        ("hierarchy", messages.sharing_hierarchy),
        ("tree", messages.sharing_tree),
        ("system", messages.sharing_system),
    ]
    choice_kb = KeyBindings()

    @choice_kb.add("c-p")
    def _move_up(event):
        event.app.key_processor.feed(KeyPress(Keys.Up))

    @choice_kb.add("c-n")
    def _move_down(event):
        event.app.key_processor.feed(KeyPress(Keys.Down))

    try:
        sharing_input = choice(
            messages.prompt_select_sharing,
            options=sharing_options,
            default="none",
            key_bindings=choice_kb,
        )
    except KeyboardInterrupt:
        print(messages.canceled)
        exit(1)
    sharing = sharing_input if sharing_input != "none" else None

    create_version(
        project_id=project_id,
        name=name,
        due_date=due_date,
        description=description,
        sharing=sharing,
    )


def handle_version(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.version_command)
    if cmd == "view":
        read_version(args.version_id, full=args.full, web=args.web)
    elif cmd == "create":
        project_id = args.project_id or default_project_id
        if not project_id:
            print(messages.project_id_required)
            exit(1)
        if args.name is None:
            _interactive_create_version(project_id, args)
        else:
            create_version(
                project_id=project_id,
                name=args.name,
                status=args.status,
                due_date=args.due_date,
                description=args.description,
                sharing=args.sharing,
            )
    elif cmd == "delete":
        if not args.yes:
            version = fetch_version(args.version_id)
            confirm_delete(
                messages.delete_target_version.format(
                    id=version["id"], name=version["name"]
                )
            )
        delete_version(args.version_id)
    elif cmd == "update":
        if not args.version_id:
            project_id = args.project_id or default_project_id
            if not project_id:
                print(messages.project_id_required)
                exit(1)
            args.version_id = _interactive_select_version_id(project_id)
        no_args_provided = not (
            args.name
            or args.status
            or args.due_date
            or args.description
            or args.sharing
        )
        if no_args_provided:
            _interactive_fill_version_update_args(args)
        update_version(
            version_id=args.version_id,
            name=args.name,
            status=args.status,
            due_date=args.due_date,
            description=args.description,
            sharing=args.sharing,
        )
    elif cmd == "list" or cmd is None:
        project_id = args.project_id or default_project_id
        if not project_id:
            print(messages.project_id_required)
            exit(1)
        list_versions(project_id, full=args.full)
