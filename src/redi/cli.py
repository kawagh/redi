# PYTHON_ARGCOMPLETE_OK
import argcomplete
import argparse
from collections import defaultdict
import os
import subprocess
import tempfile
from importlib.metadata import version

import questionary
import questionary.prompts.common

questionary.prompts.common.INDICATOR_SELECTED = "[x]"  # pyright: ignore[reportPrivateImportUsage]
questionary.prompts.common.INDICATOR_UNSELECTED = "[ ]"  # pyright: ignore[reportPrivateImportUsage]

from redi.config import (
    default_project_id,
    editor,
    show_config,
    update_config,
    wiki_project_id,
    check_config,
)
from redi.enumeration import (
    fetch_issue_priorities,
    list_document_categories,
    list_issue_priorities,
    list_time_entry_activities,
)
from redi.issue_status import fetch_issue_statuses, list_issue_statuses
from redi.project import create_project, list_projects, read_project, update_project
from redi.query import list_queries
from redi.role import list_roles
from redi.time_entry import create_time_entry, list_time_entries
from redi.issue import (
    add_note,
    create_issue,
    fetch_issue,
    list_issues,
    read_issue,
    update_issue,
)
from redi.issue_relation import create_relation, delete_relation
from redi.custom_field import list_custom_fields
from redi.tracker import fetch_trackers, list_trackers
from redi.user import list_users
from redi.version import create_version, fetch_versions, list_versions, update_version
from redi.wiki import (
    create_wiki,
    fetch_wiki,
    fetch_wikis,
    list_wikis,
    read_wiki,
    update_wiki,
)


def open_editor(initial_text: str = "") -> str:
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", delete=False) as f:
        if initial_text:
            f.write(initial_text)
        tmp_path = f.name
    try:
        if editor == "code":
            # wait to close file
            editor_command = ["code", "--wait"]
        else:
            editor_command = [editor]

        subprocess.run([*editor_command, tmp_path], check=True)
        with open(tmp_path) as f:
            return f.read().strip()
    finally:
        os.unlink(tmp_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Redmine CLI")
    parser.add_argument(
        "-V", "--version", action="version", version=f"redi {version('redi')}"
    )
    subparsers = parser.add_subparsers(dest="command")
    p_parser = subparsers.add_parser(
        "project", aliases=["p"], help="プロジェクト一覧/詳細/作成"
    )
    p_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    p_subparsers = p_parser.add_subparsers(dest="project_command")
    p_view_parser = p_subparsers.add_parser("view", help="プロジェクト詳細")
    p_view_parser.add_argument("project_id", help="プロジェクトID")
    p_view_parser.add_argument(
        "--include",
        help="追加情報（trackers,issue_categories,enabled_modules,time_entry_activities,issue_custom_fields）",
    )
    p_create_parser = p_subparsers.add_parser("create", help="プロジェクト作成")
    p_create_parser.add_argument("name", help="プロジェクト名")
    p_create_parser.add_argument(
        "identifier", help="プロジェクト識別子（英数字とハイフン）"
    )
    p_create_parser.add_argument("--description", "-d", help="説明")
    p_create_parser.add_argument(
        "--is_public",
        choices=["true", "false"],
        help="公開設定",
    )
    p_create_parser.add_argument("--parent_id", help="親プロジェクトID")
    p_create_parser.add_argument(
        "--tracker_ids", help="トラッカーID（カンマ区切り。例: 1,2,3）"
    )
    p_update_parser = p_subparsers.add_parser("update", help="プロジェクト更新")
    p_update_parser.add_argument("project_id", help="プロジェクトID")
    p_update_parser.add_argument("--name", "-n", help="プロジェクト名")
    p_update_parser.add_argument("--description", "-d", help="説明")
    p_update_parser.add_argument(
        "--is_public",
        choices=["true", "false"],
        help="公開設定",
    )
    p_update_parser.add_argument("--parent_id", help="親プロジェクトID")
    p_update_parser.add_argument(
        "--tracker_ids", help="トラッカーID（カンマ区切り。例: 1,2,3）"
    )
    i_parser = subparsers.add_parser(
        "issue", aliases=["i"], help="イシュー一覧/詳細/作成/コメント"
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
    i_subparsers = i_parser.add_subparsers(dest="issue_command")
    i_view_parser = i_subparsers.add_parser("view", help="イシュー詳細")
    i_view_parser.add_argument("issue_id", help="イシューID")
    i_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    i_create_parser = i_subparsers.add_parser("create", help="イシュー作成")
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
    i_update_parser = i_subparsers.add_parser("update", help="イシュー更新")
    i_update_parser.add_argument("issue_id", help="イシューID")
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
    i_comment_parser = i_subparsers.add_parser("comment", help="イシューにコメント追加")
    i_comment_parser.add_argument("issue_id", help="イシューID")
    i_comment_parser.add_argument(
        "notes", nargs="?", default="", help="コメント（省略でエディタ起動）"
    )
    v_parser = subparsers.add_parser("version", aliases=["v"], help="バージョン一覧")
    v_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    v_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    v_subparsers = v_parser.add_subparsers(dest="version_command")
    v_create_parser = v_subparsers.add_parser("create", help="バージョン作成")
    v_create_parser.add_argument("name", help="バージョン名")
    v_create_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    v_create_parser.add_argument(
        "--status", choices=["open", "locked", "closed"], help="ステータス"
    )
    v_create_parser.add_argument("--due_date", help="期日（YYYY-MM-DD）")
    v_create_parser.add_argument("--description", "-d", help="説明")
    v_create_parser.add_argument(
        "--sharing",
        choices=["none", "descendants", "hierarchy", "tree", "system"],
        help="共有設定",
    )
    v_update_parser = v_subparsers.add_parser("update", help="バージョン更新")
    v_update_parser.add_argument("version_id", help="バージョンID")
    v_update_parser.add_argument("--name", "-n", help="バージョン名")
    v_update_parser.add_argument(
        "--status", choices=["open", "locked", "closed"], help="ステータス"
    )
    v_update_parser.add_argument("--due_date", help="期日（YYYY-MM-DD）")
    v_update_parser.add_argument("--description", "-d", help="説明")
    v_update_parser.add_argument(
        "--sharing",
        choices=["none", "descendants", "hierarchy", "tree", "system"],
        help="共有設定",
    )
    w_parser = subparsers.add_parser("wiki", aliases=["w"], help="Wiki一覧/詳細/作成")
    w_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    w_subparsers = w_parser.add_subparsers(dest="wiki_command")
    w_view_parser = w_subparsers.add_parser("view", help="Wikiページ詳細")
    w_view_parser.add_argument("page_title", help="Wikiページタイトル")
    w_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    w_create_parser = w_subparsers.add_parser("create", help="Wikiページ作成")
    w_create_parser.add_argument(
        "page_title", nargs="?", help="Wikiページタイトル（省略で対話的に入力）"
    )
    w_create_parser.add_argument("--parent_title", help="親ページタイトル")
    w_create_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help="説明（値省略でエディタ起動）",
    )
    w_update_parser = w_subparsers.add_parser("update", help="Wikiページ更新")
    w_update_parser.add_argument("page_title", help="Wikiページタイトル")
    w_update_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help="説明（値省略でエディタ起動）",
    )
    c_parser = subparsers.add_parser("config", aliases=["c"], help="設定更新")
    c_parser.add_argument("--project_id", help="デフォルトプロジェクトIDを設定")
    c_parser.add_argument("--wiki_project_id", help="Wiki用プロジェクトIDを設定")
    c_parser.add_argument("--editor", help="エディタを設定")
    c_parser.add_argument("--api_key", help="Redmine APIキーを設定")
    c_parser.add_argument("--url", help="Redmine URLを設定")
    u_parser = subparsers.add_parser("user", aliases=["u"], help="ユーザー一覧")
    u_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    u_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    tracker_parser = subparsers.add_parser("tracker", help="トラッカー一覧")
    tracker_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    issue_status_parser = subparsers.add_parser("issue_status", help="ステータス一覧")
    issue_status_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    ip_parser = subparsers.add_parser("issue_priority", help="優先度一覧")
    ip_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    tea_parser = subparsers.add_parser("time_entry_activity", help="作業分類一覧")
    tea_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    dc_parser = subparsers.add_parser("document_category", help="文書カテゴリ一覧")
    dc_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    role_parser = subparsers.add_parser("role", help="ロール一覧")
    role_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    query_parser = subparsers.add_parser("query", help="カスタムクエリ一覧")
    query_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    cf_parser = subparsers.add_parser("custom_field", help="カスタムフィールド一覧")
    cf_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    time_entry_parser = subparsers.add_parser("time_entry", help="作業時間一覧/登録")
    time_entry_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    time_entry_parser.add_argument(
        "--user_id", "-u", help="ユーザーIDでフィルタリング（'me'も可）"
    )
    time_entry_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    te_subparsers = time_entry_parser.add_subparsers(dest="time_entry_command")
    te_create_parser = te_subparsers.add_parser("create", help="作業時間登録")
    te_create_parser.add_argument("hours", type=float, help="時間（例: 1.5）")
    te_create_parser.add_argument("--issue_id", "-i", help="イシューID")
    te_create_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    te_create_parser.add_argument("--activity_id", "-a", help="作業分類ID")
    te_create_parser.add_argument("--spent_on", help="日付（YYYY-MM-DD、省略で今日）")
    te_create_parser.add_argument("--comments", "-c", help="コメント")
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.command in ("config", "c"):
        updated = False
        if args.project_id:
            update_config("default_project_id", args.project_id)
            print(f"default_project_idを {args.project_id} に設定しました")
            updated = True
        if args.wiki_project_id:
            update_config("wiki_project_id", args.wiki_project_id)
            print(f"wiki_project_idを {args.wiki_project_id} に設定しました")
            updated = True
        if args.editor:
            update_config("editor", args.editor)
            print(f"editorを {args.editor} に設定しました")
            updated = True
        if args.api_key:
            update_config("redmine_api_key", args.api_key)
            print("redmine_api_keyを設定しました")
            updated = True
        if args.url:
            update_config("redmine_url", args.url)
            print(f"redmine_urlを {args.url} に設定しました")
            updated = True
        if not updated:
            show_config()
        return

    check_config()

    if args.command in ("project", "p"):
        if args.project_command == "view":
            read_project(args.project_id, include=args.include or "")
        elif args.project_command == "create":
            is_public = None
            if args.is_public is not None:
                is_public = args.is_public == "true"
            tracker_ids = None
            if args.tracker_ids:
                tracker_ids = [int(x) for x in args.tracker_ids.split(",")]
            create_project(
                name=args.name,
                identifier=args.identifier,
                description=args.description,
                is_public=is_public,
                parent_id=args.parent_id,
                tracker_ids=tracker_ids,
            )
        elif args.project_command == "update":
            is_public = None
            if args.is_public is not None:
                is_public = args.is_public == "true"
            tracker_ids = None
            if args.tracker_ids:
                tracker_ids = [int(x) for x in args.tracker_ids.split(",")]
            update_project(
                project_id=args.project_id,
                name=args.name,
                description=args.description,
                is_public=is_public,
                parent_id=args.parent_id,
                tracker_ids=tracker_ids,
            )
        else:
            list_projects(full=args.full)
    elif args.command in ("issue", "i"):
        if args.issue_command == "view":
            read_issue(args.issue_id, full=args.full)
        elif args.issue_command == "create":
            project_id = args.project_id or default_project_id
            if not project_id:
                print("project_idを指定するか、default_project_idを設定してください")
                exit(1)
            subject = args.subject
            tracker_id = args.tracker_id
            if subject is None:
                if tracker_id is None:
                    trackers = fetch_trackers()
                    choices = [
                        questionary.Choice(title=t["name"], value=str(t["id"]))
                        for t in trackers
                    ]
                    tracker_id = questionary.select(
                        "トラッカーを選択", choices=choices
                    ).ask(kbi_msg="")
                    if tracker_id is None:
                        print("キャンセルしました")
                        exit(1)
                subject = questionary.text("題名").ask(kbi_msg="")
                if not subject:
                    print("題名が空のためキャンセルしました")
                    exit(1)
                subject = subject.strip()
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
                custom_fields=args.custom_fields,
            )
        elif args.issue_command == "update":
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
            )
            if no_args_provided:
                current = fetch_issue(args.issue_id)
                field_choices = [
                    questionary.Choice("トラッカー (tracker)", value="tracker"),
                    questionary.Choice("題名 (subject)", value="subject"),
                    questionary.Choice("説明 (description)", value="description"),
                    questionary.Choice("ステータス (status)", value="status"),
                    questionary.Choice("優先度 (priority)", value="priority"),
                    questionary.Choice(
                        "対象バージョン (fixed_version)", value="fixed_version"
                    ),
                    questionary.Choice("コメント (notes)", value="notes"),
                ]
                description_choice = next(
                    c for c in field_choices if c.value == "description"
                )
                selected = questionary.checkbox(
                    "更新する項目を選択",
                    choices=field_choices,
                    style=questionary.Style([("selected", "noreverse")]),
                    initial_choice=description_choice,
                ).ask(kbi_msg="")
                if not selected:
                    print("更新する項目が選択されていないためキャンセルしました")
                    exit(1)
                if "tracker" in selected:
                    trackers = fetch_trackers()
                    args.tracker_id = questionary.select(
                        "トラッカー",
                        choices=[
                            questionary.Choice(t["name"], value=str(t["id"]))
                            for t in trackers
                        ],
                    ).ask(kbi_msg="")
                if "subject" in selected:
                    args.subject = questionary.text(
                        "題名", default=current.get("subject") or ""
                    ).ask(kbi_msg="")
                if "description" in selected:
                    args.description = ""
                if "status" in selected:
                    statuses = fetch_issue_statuses()
                    args.status_id = questionary.select(
                        "ステータス",
                        choices=[
                            questionary.Choice(s["name"], value=str(s["id"]))
                            for s in statuses
                        ],
                    ).ask(kbi_msg="")
                if "priority" in selected:
                    priorities = fetch_issue_priorities()
                    args.priority_id = questionary.select(
                        "優先度",
                        choices=[
                            questionary.Choice(p["name"], value=str(p["id"]))
                            for p in priorities
                        ],
                    ).ask(kbi_msg="")
                if "fixed_version" in selected:
                    project_id = (current.get("project") or {}).get("id")
                    if not project_id:
                        print("プロジェクトが特定できないためキャンセルしました")
                        exit(1)
                    versions = fetch_versions(str(project_id))
                    args.fixed_version_id = questionary.select(
                        "対象バージョン",
                        choices=[
                            questionary.Choice(
                                f"{v['name']} ({v['status']})", value=str(v["id"])
                            )
                            for v in versions
                        ],
                    ).ask(kbi_msg="")
                if "notes" in selected:
                    args.notes = questionary.text("コメント").ask(kbi_msg="")
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
            )
            should_update_issue_relation = args.delete_relation or (
                args.relate and args.relate_to
            )
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
            if not should_update_issue and not should_update_issue_relation:
                print("更新内容がないので更新をキャンセルしました")
                exit(1)
        elif args.issue_command == "comment":
            if args.notes:
                add_note(args.issue_id, args.notes)
            else:
                notes = open_editor()
                if notes:
                    add_note(args.issue_id, notes)
                else:
                    print("コメントが空のためキャンセルしました")
        else:
            list_issues(
                project_id=args.project_id or default_project_id,
                fixed_version_id=args.version,
                assigned_to=args.assigned_to,
                full=args.full,
            )
    elif args.command in ("version", "v"):
        if args.version_command == "create":
            project_id = args.project_id or default_project_id
            if not project_id:
                print("project_idを指定するか、default_project_idを設定してください")
                exit(1)
            create_version(
                project_id=project_id,
                name=args.name,
                status=args.status,
                due_date=args.due_date,
                description=args.description,
                sharing=args.sharing,
            )
        elif args.version_command == "update":
            update_version(
                version_id=args.version_id,
                name=args.name,
                status=args.status,
                due_date=args.due_date,
                description=args.description,
                sharing=args.sharing,
            )
        else:
            project_id = args.project_id or default_project_id
            if not project_id:
                print("project_idを指定するか、default_project_idを設定してください")
                exit(1)
            list_versions(project_id, full=args.full)
    elif args.command in ("wiki", "w"):
        project_id = args.project_id or wiki_project_id or default_project_id
        if not project_id:
            print(
                "project_idを指定するか、wiki_project_idまたはdefault_project_idを設定してください"
            )
            exit(1)
        if args.wiki_command == "view":
            read_wiki(project_id, args.page_title, full=args.full)
        elif args.wiki_command == "create":
            page_title = args.page_title
            parent_title = args.parent_title
            if page_title is None:
                page_title = questionary.text("ページタイトル").ask(kbi_msg="")
                if not page_title:
                    print("ページタイトルが空のためキャンセルしました")
                    exit(1)
                page_title = page_title.strip()
                if parent_title is None:
                    pages = fetch_wikis(project_id)

                    children_map: dict[str | None, list[str]] = defaultdict(list)
                    for page in pages:
                        parent = (
                            page.get("parent", {}).get("title")
                            if "parent" in page
                            else None
                        )
                        children_map[parent].append(page["title"])
                    parent_choices = []

                    def add_choices(parent: str | None, depth: int) -> None:
                        for title in sorted(children_map.get(parent, [])):
                            parent_choices.append(
                                questionary.Choice("  " * depth + title, value=title)
                            )
                            add_choices(title, depth + 1)

                    add_choices(None, 0)
                    parent_title = questionary.select(
                        "親ページ",
                        choices=parent_choices,
                    ).ask(kbi_msg="")
            if args.description and args.description != "":
                text = args.description
            else:
                text = open_editor()
            if text:
                create_wiki(project_id, page_title, text, parent_title=parent_title)
            else:
                print("テキストが空のためキャンセルしました")
        elif args.wiki_command == "update":
            if args.description and args.description != "":
                text = args.description
            else:
                current = fetch_wiki(project_id, args.page_title)
                text = open_editor(current.get("text") or "")
            if text:
                update_wiki(project_id, args.page_title, text)
            else:
                print("テキストが空のためキャンセルしました")
        else:
            list_wikis(project_id)
    elif args.command in ("user", "u"):
        project_id = args.project_id or default_project_id
        list_users(project_id=project_id, full=args.full)
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
        list_roles(full=args.full)
    elif args.command == "query":
        list_queries(full=args.full)
    elif args.command == "custom_field":
        list_custom_fields(full=args.full)
    elif args.command == "time_entry":
        if args.time_entry_command == "create":
            project_id = args.project_id or default_project_id
            create_time_entry(
                issue_id=args.issue_id,
                project_id=project_id,
                hours=args.hours,
                activity_id=args.activity_id,
                spent_on=args.spent_on,
                comments=args.comments,
            )
        else:
            project_id = args.project_id or default_project_id
            list_time_entries(
                project_id=project_id, user_id=args.user_id, full=args.full
            )
    else:
        parser.print_help()
