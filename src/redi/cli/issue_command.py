import argparse

from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator

from redi.cli._common import inline_checkbox, inline_choice, open_editor, resolve_alias
from redi.config import default_project_id
from redi.api.enumeration import fetch_issue_priorities, fetch_time_entry_activities
from redi.api.issue import (
    add_note,
    add_watcher,
    create_issue,
    delete_issue,
    fetch_issue,
    fetch_issues,
    list_issues,
    read_issue,
    remove_watcher,
    update_issue,
)
from redi.api.issue_relation import create_relation, delete_relation
from redi.api.issue_status import fetch_issue_statuses
from redi.api.time_entry import create_time_entry
from redi.api.tracker import fetch_trackers
from redi.api.version import fetch_versions

from redi.api.custom_field import (
    fetch_custom_fields,
    fetch_project_issue_custom_field_ids,
    filter_required_issue_custom_fields,
)


def add_issue_parser(subparsers: argparse._SubParsersAction) -> None:
    i_parser = subparsers.add_parser(
        "issue", aliases=["i"], help="イシュー一覧/詳細/作成/更新/コメント/削除"
    )
    i_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    i_parser.add_argument("--project_id", "-p", help="プロジェクトIDでフィルタリング")
    i_parser.add_argument(
        "--version",
        "-v",
        help="対象バージョンIDでフィルタリング",
    )
    i_parser.add_argument(
        "--assigned_to",
        "-a",
        help="担当者でフィルタリング（ユーザーIDまたは'me'）",
    )
    i_parser.add_argument(
        "--status_id",
        "-s",
        help="ステータスIDでフィルタリング（'open'/'closed'/'*' も可）",
    )
    i_parser.add_argument("--tracker_id", "-t", help="トラッカーIDでフィルタリング")
    i_parser.add_argument("--priority_id", help="優先度IDでフィルタリング")
    i_parser.add_argument(
        "--query_id",
        "-q",
        help="カスタムクエリIDでフィルタリング（`redi query`で取得可）",
    )
    i_parser.add_argument("--limit", "-l", type=int, help="取得件数")
    i_parser.add_argument("--offset", "-o", type=int, help="オフセット")
    i_subparsers = i_parser.add_subparsers(dest="issue_command")
    i_view_parser = i_subparsers.add_parser("view", aliases=["v"], help="イシュー詳細")
    i_view_parser.add_argument("issue_id", help="イシューID")
    i_view_parser.add_argument(
        "--include",
        help="追加情報（children,attachments,relations,changesets,journals,watchers,allowed_statuses）",
    )
    i_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    i_view_parser.add_argument(
        "--web", "-w", action="store_true", help="ブラウザでRedmineのページを開く"
    )
    i_create_parser = i_subparsers.add_parser(
        "create", aliases=["c"], help="イシュー作成"
    )
    i_create_parser.add_argument(
        "subject", nargs="?", help="イシューの題名（省略で対話的に入力）"
    )
    i_create_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    i_create_parser.add_argument("--tracker_id", "-t", help="トラッカーID")
    i_create_parser.add_argument("--priority_id", help="優先度ID")
    i_create_parser.add_argument("--assigned_to_id", "-a", help="担当者ID")
    i_create_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help="説明（フラグ未指定でエディタ起動）",
    )
    i_create_parser.add_argument(
        "--custom_fields",
        help="カスタムフィールド（id=value形式、カンマ区切り。例: 1=foo,2=bar）",
    )
    i_update_parser = i_subparsers.add_parser(
        "update", aliases=["u"], help="イシュー更新"
    )
    i_update_parser.add_argument(
        "issue_id", nargs="?", help="イシューID（省略で対話的に選択）"
    )
    i_update_parser.add_argument("--subject", "-s", help="題名")
    i_update_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help="説明（値省略でエディタ起動）",
    )
    i_update_parser.add_argument("--tracker_id", "-t", help="トラッカーID")
    i_update_parser.add_argument("--status_id", help="ステータスID")
    i_update_parser.add_argument("--priority_id", help="優先度ID")
    i_update_parser.add_argument("--assigned_to_id", "-a", help="担当者ID")
    i_update_parser.add_argument("--fixed_version_id", help="対象バージョンID")
    i_update_parser.add_argument(
        "--parent_issue_id", help="親チケットID（空文字で解除）"
    )
    i_update_parser.add_argument("--notes", "-n", help="コメント")
    i_update_parser.add_argument(
        "--custom_fields",
        help="カスタムフィールド（id=value形式、カンマ区切り。例: 1=foo,2=bar）",
    )
    i_update_parser.add_argument(
        "--relate",
        help="関係性のタイプ（relates, duplicates, blocks, precedes, follows など）",
    )
    i_update_parser.add_argument("--to", dest="relate_to", help="関係先のイシューID")
    i_update_parser.add_argument(
        "--delete-relation",
        action="store_true",
        help="関係性を削除（--to と併用）",
    )
    i_update_parser.add_argument(
        "--attach",
        action="append",
        help="添付ファイルのパス（複数指定可）",
    )
    i_update_parser.add_argument("--hours", type=float, help="作業時間（例: 1.5）")
    i_update_parser.add_argument("--activity_id", help="作業分類ID")
    i_update_parser.add_argument("--spent_on", help="作業日（YYYY-MM-DD、省略で今日）")
    i_update_parser.add_argument("--time_comments", help="作業時間のコメント")
    i_update_parser.add_argument(
        "--add-watcher",
        type=int,
        action="append",
        dest="add_watcher_ids",
        help="ウォッチャーに追加するユーザーID（複数指定可）",
    )
    i_update_parser.add_argument(
        "--remove-watcher",
        type=int,
        action="append",
        dest="remove_watcher_ids",
        help="ウォッチャーから削除するユーザーID（複数指定可）",
    )
    i_comment_parser = i_subparsers.add_parser(
        "comment", aliases=["co"], help="イシューにコメント追加"
    )
    i_comment_parser.add_argument("issue_id", help="イシューID")
    i_comment_parser.add_argument(
        "notes", nargs="?", default="", help="コメント（省略でエディタ起動）"
    )
    i_delete_parser = i_subparsers.add_parser(
        "delete", aliases=["d"], help="イシュー削除"
    )
    i_delete_parser.add_argument("issue_id", help="イシューID")


def _interactive_select_issue_id() -> str:
    issues = fetch_issues(project_id=default_project_id)
    if not issues:
        print("選択可能なイシューがありません")
        exit(1)
    options: list[tuple[str, str]] = [
        (str(i["id"]), f"#{i['id']} {i['subject']}") for i in issues
    ]
    labels = dict(options)
    try:
        issue_id = inline_choice("更新するイシューを選択", options)
    except KeyboardInterrupt:
        print("キャンセルしました")
        exit(1)
    print(f"更新するイシュー: {labels[issue_id]}")
    return issue_id


def _interactive_fill_issue_update_args(args: argparse.Namespace) -> None:
    current = fetch_issue(args.issue_id)
    field_values: list[tuple[str, str]] = [
        ("tracker", "トラッカー (tracker)"),
        ("subject", "題名 (subject)"),
        ("description", "説明 (description)"),
        ("status", "ステータス (status)"),
        ("priority", "優先度 (priority)"),
        ("fixed_version", "対象バージョン (fixed_version)"),
        ("notes", "コメント (notes)"),
        ("time_entry", "作業時間 (time_entry)"),
    ]
    try:
        selected = inline_checkbox(
            "更新する項目を選択 (Spaceで選択、Enterで確定)",
            field_values,
            initial_value="description",
        )
    except KeyboardInterrupt:
        print("キャンセルしました")
        exit(1)
    if not selected:
        print("更新する項目が選択されていないためキャンセルしました")
        exit(1)
    labels = dict(field_values)
    print(f"更新する項目: {', '.join(labels[v] for v in selected)}")
    try:
        if "tracker" in selected:
            trackers = fetch_trackers()
            tracker_options: list[tuple[str, str]] = [
                (str(t["id"]), t["name"]) for t in trackers
            ]
            tracker_labels = dict(tracker_options)
            args.tracker_id = inline_choice("トラッカー", tracker_options)
            print(f"トラッカー: {tracker_labels[args.tracker_id]}")
        if "subject" in selected:
            args.subject = prompt(
                "題名: ", default=current.get("subject") or ""
            ).strip()
        if "description" in selected:
            args.description = ""
        if "status" in selected:
            statuses = fetch_issue_statuses()
            status_options: list[tuple[str, str]] = [
                (str(s["id"]), s["name"]) for s in statuses
            ]
            status_labels = dict(status_options)
            args.status_id = inline_choice("ステータス", status_options)
            print(f"ステータス: {status_labels[args.status_id]}")
        if "priority" in selected:
            priorities = fetch_issue_priorities()
            priority_options: list[tuple[str, str]] = [
                (str(p["id"]), p["name"]) for p in priorities
            ]
            priority_labels = dict(priority_options)
            args.priority_id = inline_choice("優先度", priority_options)
            print(f"優先度: {priority_labels[args.priority_id]}")
        if "fixed_version" in selected:
            project_id = (current.get("project") or {}).get("id")
            if not project_id:
                print("プロジェクトが特定できないためキャンセルしました")
                exit(1)
            versions = fetch_versions(str(project_id))
            version_options: list[tuple[str, str]] = [
                (str(v["id"]), f"{v['name']} ({v['status']})") for v in versions
            ]
            version_labels = dict(version_options)
            args.fixed_version_id = inline_choice("対象バージョン", version_options)
            print(f"対象バージョン: {version_labels[args.fixed_version_id]}")
        if "notes" in selected:
            args.notes = prompt("コメント: ").strip()
        if "time_entry" in selected:
            hours_validator = Validator.from_callable(
                lambda v: v.replace(".", "", 1).isdigit(),
                error_message="数値を入力してください",
            )
            hours_str = prompt(
                "作業時間（例: 1.5 (h)）: ", validator=hours_validator
            ).strip()
            if hours_str:
                args.hours = float(hours_str)
            activities = fetch_time_entry_activities()
            activity_options: list[tuple[str, str]] = [
                (str(a["id"]), a["name"]) for a in activities
            ]
            activity_labels = dict(activity_options)
            args.activity_id = inline_choice("作業分類", activity_options)
            print(f"作業分類: {activity_labels[args.activity_id]}")
            args.spent_on = prompt("作業日（YYYY-MM-DD、省略で今日）: ").strip() or None
            args.time_comments = prompt("作業時間のコメント: ").strip() or None
    except (KeyboardInterrupt, EOFError):
        print("キャンセルしました")
        exit(1)


def _prompt_custom_field_value(cf: dict) -> str | None:
    name = cf.get("name", "")
    fmt = cf.get("field_format", "string")
    label = f"{name}（必須）"
    # not support All formats
    if fmt == "list":
        possible = cf.get("possible_values") or []
        options: list[tuple[str, str]] = [
            (str(pv.get("value", "")), str(pv.get("value", "")))
            for pv in possible
            if pv.get("value", "") != ""
        ]
        if options:
            try:
                value = inline_choice(label, options)
            except KeyboardInterrupt:
                return None
            print(f"{name}: {value}")
            return value
    try:
        return prompt(f"{label}: ").strip() or None
    except (KeyboardInterrupt, EOFError):
        return None


def _interactive_fill_required_custom_fields(
    project_id: str, tracker_id: str | None, existing: str | None
) -> str | None:
    custom_fields = fetch_custom_fields()
    if custom_fields is None:
        # 非管理者はあらかじめ渡されているパラメータを使うしかない
        return existing
    project_cf_ids = fetch_project_issue_custom_field_ids(project_id)
    required = filter_required_issue_custom_fields(
        custom_fields, project_cf_ids, tracker_id
    )
    if not required:
        return existing

    existing_ids: set[int] = set()
    if existing:
        for pair in existing.split(","):
            key = pair.split("=")[0]
            existing_ids.add(int(key))

    added: list[str] = []
    for cf in required:
        if cf["id"] in existing_ids:
            continue
        value = _prompt_custom_field_value(cf)
        if value is None:
            print("キャンセルしました")
            exit(1)
        added.append(f"{cf['id']}={value}")
    if not added:
        return existing
    if existing:
        return existing + "," + ",".join(added)
    return ",".join(added)


def handle_issue_create(args: argparse.Namespace) -> None:
    project_id = args.project_id or default_project_id
    if not project_id:
        print("project_idを指定するか、default_project_idを設定してください")
        exit(1)
    subject = args.subject
    tracker_id = args.tracker_id
    custom_fields = args.custom_fields
    if subject is None:
        if tracker_id is None:
            trackers = fetch_trackers()
            tracker_options: list[tuple[str, str]] = [
                (str(t["id"]), t["name"]) for t in trackers
            ]
            labels = dict(tracker_options)
            try:
                tracker_id = inline_choice("トラッカーを選択", tracker_options)
            except KeyboardInterrupt:
                print("キャンセルしました")
                exit(1)
            print(f"トラッカー: {labels[tracker_id]}")
        try:
            subject = prompt("題名: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("キャンセルしました")
            exit(1)
        if not subject:
            print("題名が空のためキャンセルしました")
            exit(1)
        # 必要なカスタムフィールドを対話的に入力
        custom_fields = _interactive_fill_required_custom_fields(
            project_id=project_id,
            tracker_id=tracker_id,
            existing=args.custom_fields,
        )
    if args.description is None:
        description = open_editor()
    else:
        description = args.description
    create_issue(
        project_id=project_id,
        subject=subject,
        description=description,
        tracker_id=tracker_id,
        priority_id=args.priority_id,
        assigned_to_id=args.assigned_to_id,
        custom_fields=custom_fields,
    )


def handle_issue_update(args: argparse.Namespace) -> None:
    if not args.issue_id:
        args.issue_id = _interactive_select_issue_id()
    no_args_provided = not (
        args.subject
        or args.description is not None
        or args.tracker_id
        or args.status_id
        or args.priority_id
        or args.assigned_to_id
        or args.fixed_version_id
        or args.parent_issue_id is not None
        or args.notes
        or args.custom_fields
        or args.relate
        or args.relate_to
        or args.delete_relation
        or args.attach
        or args.hours is not None
        or args.add_watcher_ids
        or args.remove_watcher_ids
    )
    if no_args_provided:
        _interactive_fill_issue_update_args(args)
    description = args.description
    if description is not None and description == "":
        current = fetch_issue(args.issue_id)
        description = open_editor(current.get("description") or "")
    should_update_issue = (
        args.subject
        or description is not None
        or args.tracker_id
        or args.status_id
        or args.priority_id
        or args.assigned_to_id
        or args.fixed_version_id
        or args.parent_issue_id is not None
        or args.notes
        or args.custom_fields
        or args.attach
    )
    should_update_issue_relation = args.delete_relation or (
        args.relate and args.relate_to
    )
    should_create_time_entry = args.hours is not None
    if should_update_issue:
        update_issue(
            issue_id=args.issue_id,
            subject=args.subject,
            description=description if description else None,
            tracker_id=args.tracker_id,
            status_id=args.status_id,
            priority_id=args.priority_id,
            assigned_to_id=args.assigned_to_id,
            fixed_version_id=args.fixed_version_id,
            parent_issue_id=args.parent_issue_id,
            notes=args.notes or "",
            custom_fields=args.custom_fields,
            attachments=args.attach,
        )
    if args.delete_relation:
        if not args.relate_to:
            print("--delete-relation には --to が必要です")
            exit(1)
        delete_relation(
            issue_id=args.issue_id,
            issue_to_id=args.relate_to,
        )
    elif args.relate and args.relate_to:
        create_relation(
            issue_id=args.issue_id,
            issue_to_id=args.relate_to,
            relation_type=args.relate,
        )
    elif args.relate or args.relate_to:
        print("--relate と --to は両方指定してください")
        exit(1)
    if should_create_time_entry:
        create_time_entry(
            issue_id=args.issue_id,
            hours=args.hours,
            activity_id=args.activity_id,
            spent_on=args.spent_on,
            comments=args.time_comments,
        )
    for user_id in args.add_watcher_ids or []:
        add_watcher(args.issue_id, user_id)
    for user_id in args.remove_watcher_ids or []:
        remove_watcher(args.issue_id, user_id)
    should_update_watchers = bool(args.add_watcher_ids or args.remove_watcher_ids)
    if (
        not should_update_issue
        and not should_update_issue_relation
        and not should_create_time_entry
        and not should_update_watchers
    ):
        print("更新内容がないので更新をキャンセルしました")
        exit(1)


def handle_issue(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.issue_command)
    if cmd == "view":
        read_issue(
            args.issue_id,
            include=args.include or "",
            full=args.full,
            web=args.web,
        )
    elif cmd == "create":
        handle_issue_create(args)
    elif cmd == "update":
        handle_issue_update(args)
    elif cmd == "comment":
        if args.notes:
            add_note(args.issue_id, args.notes)
        else:
            notes = open_editor()
            if notes:
                add_note(args.issue_id, notes)
            else:
                print("コメントが空のためキャンセルしました")
    elif cmd == "delete":
        issue = fetch_issue(args.issue_id)
        print(f"削除するイシュー: #{issue['id']} {issue['subject']}")
        try:
            confirm = prompt("削除してもよろしいですか? (yes/No): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("キャンセルしました")
            exit(1)
        if confirm != "yes":
            print("キャンセルしました")
            exit(1)
        delete_issue(args.issue_id)
    else:
        list_issues(
            project_id=args.project_id or default_project_id,
            fixed_version_id=args.version,
            assigned_to=args.assigned_to,
            status_id=args.status_id,
            tracker_id=args.tracker_id,
            priority_id=args.priority_id,
            query_id=args.query_id,
            limit=args.limit,
            offset=args.offset,
            full=args.full,
        )
