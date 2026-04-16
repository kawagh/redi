# PYTHON_ARGCOMPLETE_OK
import argcomplete
import argparse
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
    set_default_profile,
    show_config,
    update_config,
    wiki_project_id,
    check_config,
)
from redi.enumeration import (
    fetch_issue_priorities,
    fetch_time_entry_activities,
    list_document_categories,
    list_issue_priorities,
    list_time_entry_activities,
)
from redi.issue_status import fetch_issue_statuses, list_issue_statuses
from redi.project import create_project, list_projects, read_project, update_project
from redi.query import list_queries
from redi.role import list_roles, read_role
from redi.search import search
from redi.time_entry import create_time_entry, list_time_entries
from redi.issue import (
    add_note,
    create_issue,
    fetch_issue,
    fetch_issues,
    list_issues,
    read_issue,
    update_issue,
)
from redi.attachment import read_attachment, update_attachment
from redi.issue_relation import create_relation, delete_relation
from redi.custom_field import list_custom_fields
from redi.tracker import fetch_trackers, list_trackers
from redi.user import list_users
from redi.version import (
    create_version,
    fetch_versions,
    list_versions,
    read_version,
    update_version,
)
from redi.wiki import (
    build_children_map,
    create_wiki,
    fetch_wiki,
    fetch_wikis,
    list_wikis,
    normalize_title,
    read_wiki,
    update_wiki,
)
from redi.tui import run_issue_tui


def build_wiki_tree_choices(pages: list[dict]) -> list[questionary.Choice]:
    children_map = build_children_map(pages)
    choices: list[questionary.Choice] = []

    def walk(parent: str | None, depth: int) -> None:
        for title in children_map.get(parent, []):
            choices.append(questionary.Choice("  " * depth + title, value=title))
            walk(title, depth + 1)

    walk(None, 0)
    return choices


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


def _add_project_parser(subparsers: argparse._SubParsersAction) -> None:
    p_parser = subparsers.add_parser(
        "project", aliases=["p"], help="プロジェクト一覧/詳細/作成"
    )
    p_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    p_subparsers = p_parser.add_subparsers(dest="project_command")
    p_view_parser = p_subparsers.add_parser("view", aliases=["v"], help="プロジェクト詳細")
    p_view_parser.add_argument("project_id", help="プロジェクトID")
    p_view_parser.add_argument(
        "--include",
        help="追加情報（trackers,issue_categories,enabled_modules,time_entry_activities,issue_custom_fields）",
    )
    p_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    p_view_parser.add_argument(
        "--web", "-w", action="store_true", help="ブラウザでRedmineのページを開く"
    )
    p_create_parser = p_subparsers.add_parser("create", aliases=["c"], help="プロジェクト作成")
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
    p_update_parser = p_subparsers.add_parser("update", aliases=["u"], help="プロジェクト更新")
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


def _add_issue_parser(subparsers: argparse._SubParsersAction) -> None:
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
    i_create_parser = i_subparsers.add_parser("create", aliases=["c"], help="イシュー作成")
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
    i_update_parser = i_subparsers.add_parser("update", aliases=["u"], help="イシュー更新")
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
    i_comment_parser = i_subparsers.add_parser("comment", aliases=["co"], help="イシューにコメント追加")
    i_comment_parser.add_argument("issue_id", help="イシューID")
    i_comment_parser.add_argument(
        "notes", nargs="?", default="", help="コメント（省略でエディタ起動）"
    )


def _add_version_parser(subparsers: argparse._SubParsersAction) -> None:
    v_parser = subparsers.add_parser("version", aliases=["v"], help="バージョン一覧")
    v_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    v_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    v_subparsers = v_parser.add_subparsers(dest="version_command")
    v_view_parser = v_subparsers.add_parser("view", aliases=["v"], help="バージョン詳細")
    v_view_parser.add_argument("version_id", help="バージョンID")
    v_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    v_view_parser.add_argument(
        "--web", "-w", action="store_true", help="ブラウザでRedmineのページを開く"
    )
    v_create_parser = v_subparsers.add_parser("create", aliases=["c"], help="バージョン作成")
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
    v_update_parser = v_subparsers.add_parser("update", aliases=["u"], help="バージョン更新")
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


def _add_wiki_parser(subparsers: argparse._SubParsersAction) -> None:
    w_parser = subparsers.add_parser("wiki", aliases=["w"], help="Wiki一覧/詳細/作成")
    w_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    w_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    w_subparsers = w_parser.add_subparsers(dest="wiki_command")
    w_view_parser = w_subparsers.add_parser("view", aliases=["v"], help="Wikiページ詳細")
    w_view_parser.add_argument("page_title", help="Wikiページタイトル")
    w_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    w_view_parser.add_argument(
        "--web", "-w", action="store_true", help="ブラウザでRedmineのページを開く"
    )
    w_create_parser = w_subparsers.add_parser("create", aliases=["c"], help="Wikiページ作成")
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
    w_update_parser = w_subparsers.add_parser("update", aliases=["u"], help="Wikiページ更新")
    w_update_parser.add_argument(
        "page_title", nargs="?", help="Wikiページタイトル（省略で対話的に選択）"
    )
    w_update_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help="説明（値省略でエディタ起動）",
    )


def _add_config_parser(subparsers: argparse._SubParsersAction) -> None:
    c_parser = subparsers.add_parser("config", aliases=["c"], help="設定表示/更新")
    c_subparsers = c_parser.add_subparsers(dest="config_command")
    c_update_parser = c_subparsers.add_parser("update", aliases=["u"], help="設定更新")
    c_update_parser.add_argument(
        "profile_name",
        nargs="?",
        help="更新対象のプロファイル名（省略時はdefault_profile）",
    )
    c_update_parser.add_argument("--project_id", help="デフォルトプロジェクトIDを設定")
    c_update_parser.add_argument("--wiki_project_id", help="Wiki用プロジェクトIDを設定")
    c_update_parser.add_argument("--editor", help="エディタを設定")
    c_update_parser.add_argument("--api_key", help="Redmine APIキーを設定")
    c_update_parser.add_argument("--url", help="Redmine URLを設定")
    c_update_parser.add_argument(
        "--default_profile", help="デフォルトプロファイルを設定"
    )


def _add_user_parser(subparsers: argparse._SubParsersAction) -> None:
    u_parser = subparsers.add_parser("user", aliases=["u"], help="ユーザー一覧")
    u_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    u_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")


def _add_tracker_parser(subparsers: argparse._SubParsersAction) -> None:
    tracker_parser = subparsers.add_parser("tracker", help="トラッカー一覧")
    tracker_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def _add_issue_status_parser(subparsers: argparse._SubParsersAction) -> None:
    issue_status_parser = subparsers.add_parser("issue_status", help="ステータス一覧")
    issue_status_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def _add_issue_priority_parser(subparsers: argparse._SubParsersAction) -> None:
    ip_parser = subparsers.add_parser("issue_priority", help="優先度一覧")
    ip_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")


def _add_time_entry_activity_parser(subparsers: argparse._SubParsersAction) -> None:
    tea_parser = subparsers.add_parser("time_entry_activity", help="作業分類一覧")
    tea_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def _add_document_category_parser(subparsers: argparse._SubParsersAction) -> None:
    dc_parser = subparsers.add_parser("document_category", help="文書カテゴリ一覧")
    dc_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")


def _add_role_parser(subparsers: argparse._SubParsersAction) -> None:
    role_parser = subparsers.add_parser("role", help="ロール一覧")
    role_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    role_subparsers = role_parser.add_subparsers(dest="role_command")
    role_view_parser = role_subparsers.add_parser("view", aliases=["v"], help="ロール詳細")
    role_view_parser.add_argument("role_id", help="ロールID")
    role_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def _add_query_parser(subparsers: argparse._SubParsersAction) -> None:
    query_parser = subparsers.add_parser("query", help="カスタムクエリ一覧")
    query_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def _add_custom_field_parser(subparsers: argparse._SubParsersAction) -> None:
    cf_parser = subparsers.add_parser("custom_field", help="カスタムフィールド一覧")
    cf_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")


def _add_search_parser(subparsers: argparse._SubParsersAction) -> None:
    search_parser = subparsers.add_parser("search", help="検索")
    search_parser.add_argument("query", help="検索クエリ")
    search_parser.add_argument("--limit", "-l", type=int, help="取得件数")
    search_parser.add_argument("--offset", "-o", type=int, help="オフセット")
    search_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def _add_attachment_parser(
    subparsers: argparse._SubParsersAction,
) -> argparse.ArgumentParser:
    a_parser = subparsers.add_parser("attachment", help="添付ファイル詳細")
    a_subparsers = a_parser.add_subparsers(dest="attachment_command")
    a_view_parser = a_subparsers.add_parser("view", aliases=["v"], help="添付ファイル詳細")
    a_view_parser.add_argument("attachment_id", help="添付ファイルID")
    a_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    a_update_parser = a_subparsers.add_parser("update", aliases=["u"], help="添付ファイル更新")
    a_update_parser.add_argument("attachment_id", help="添付ファイルID")
    a_update_parser.add_argument("--filename", "-f", help="ファイル名")
    a_update_parser.add_argument("--description", "-d", help="説明")
    return a_parser


def _add_time_entry_parser(subparsers: argparse._SubParsersAction) -> None:
    time_entry_parser = subparsers.add_parser("time_entry", help="作業時間一覧/登録")
    time_entry_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    time_entry_parser.add_argument(
        "--user_id", "-u", help="ユーザーIDでフィルタリング（'me'も可）"
    )
    time_entry_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    te_subparsers = time_entry_parser.add_subparsers(dest="time_entry_command")
    te_create_parser = te_subparsers.add_parser("create", aliases=["c"], help="作業時間登録")
    te_create_parser.add_argument("hours", type=float, help="時間（例: 1.5）")
    te_create_parser.add_argument("--issue_id", "-i", help="イシューID")
    te_create_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    te_create_parser.add_argument("--activity_id", "-a", help="作業分類ID")
    te_create_parser.add_argument("--spent_on", help="日付（YYYY-MM-DD、省略で今日）")
    te_create_parser.add_argument("--comments", "-c", help="コメント")


def _build_parser() -> tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    parser = argparse.ArgumentParser(description="Redmine CLI")
    parser.add_argument(
        "-V", "--version", action="version", version=f"redi {version('redi')}"
    )
    parser.add_argument("--tui", action="store_true", help="TUI")
    subparsers = parser.add_subparsers(dest="command")
    _add_project_parser(subparsers)
    _add_issue_parser(subparsers)
    _add_version_parser(subparsers)
    _add_wiki_parser(subparsers)
    _add_config_parser(subparsers)
    _add_user_parser(subparsers)
    _add_tracker_parser(subparsers)
    _add_issue_status_parser(subparsers)
    _add_issue_priority_parser(subparsers)
    _add_time_entry_activity_parser(subparsers)
    _add_document_category_parser(subparsers)
    _add_role_parser(subparsers)
    _add_query_parser(subparsers)
    _add_custom_field_parser(subparsers)
    _add_search_parser(subparsers)
    a_parser = _add_attachment_parser(subparsers)
    _add_time_entry_parser(subparsers)
    return parser, a_parser


_SUBCOMMAND_ALIASES: dict[str, str] = {
    "v": "view",
    "c": "create",
    "u": "update",
    "co": "comment",
}


def _resolve_alias(command: str | None) -> str | None:
    if command is None:
        return None
    return _SUBCOMMAND_ALIASES.get(command, command)


def _handle_config(args: argparse.Namespace) -> None:
    if _resolve_alias(args.config_command) != "update":
        show_config()
        return
    updated = False
    profile = args.profile_name
    profile_suffix = f"（profile: {profile}）" if profile else ""
    if args.project_id:
        update_config("default_project_id", args.project_id, profile)
        print(f"default_project_idを {args.project_id} に設定しました{profile_suffix}")
        updated = True
    if args.wiki_project_id:
        update_config("wiki_project_id", args.wiki_project_id, profile)
        print(
            f"wiki_project_idを {args.wiki_project_id} に設定しました{profile_suffix}"
        )
        updated = True
    if args.editor:
        update_config("editor", args.editor, profile)
        print(f"editorを {args.editor} に設定しました{profile_suffix}")
        updated = True
    if args.api_key:
        update_config("redmine_api_key", args.api_key, profile)
        print(f"redmine_api_keyを設定しました{profile_suffix}")
        updated = True
    if args.url:
        update_config("redmine_url", args.url, profile)
        print(f"redmine_urlを {args.url} に設定しました{profile_suffix}")
        updated = True
    if args.default_profile:
        if set_default_profile(args.default_profile):
            print(f"default_profileを {args.default_profile} に設定しました")
        updated = True
    if not updated:
        show_config()


def _handle_project(args: argparse.Namespace) -> None:
    cmd = _resolve_alias(args.project_command)
    if cmd == "view":
        read_project(
            args.project_id,
            include=args.include or "",
            full=args.full,
            web=args.web,
        )
    elif cmd == "create":
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
    elif cmd == "update":
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


def _interactive_select_issue_id() -> str:
    issues = fetch_issues(project_id=default_project_id)
    if not issues:
        print("選択可能なイシューがありません")
        exit(1)
    issue_id = questionary.select(
        "更新するイシューを選択",
        choices=[
            questionary.Choice(f"#{i['id']} {i['subject']}", value=str(i["id"]))
            for i in issues
        ],
    ).ask(kbi_msg="")
    if not issue_id:
        print("イシューが選択されていないためキャンセルしました")
        exit(1)
    return issue_id


def _interactive_fill_issue_update_args(args: argparse.Namespace) -> None:
    current = fetch_issue(args.issue_id)
    field_choices = [
        questionary.Choice("トラッカー (tracker)", value="tracker"),
        questionary.Choice("題名 (subject)", value="subject"),
        questionary.Choice("説明 (description)", value="description"),
        questionary.Choice("ステータス (status)", value="status"),
        questionary.Choice("優先度 (priority)", value="priority"),
        questionary.Choice("対象バージョン (fixed_version)", value="fixed_version"),
        questionary.Choice("コメント (notes)", value="notes"),
        questionary.Choice("作業時間 (time_entry)", value="time_entry"),
    ]
    description_choice = next(c for c in field_choices if c.value == "description")
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
                questionary.Choice(t["name"], value=str(t["id"])) for t in trackers
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
                questionary.Choice(s["name"], value=str(s["id"])) for s in statuses
            ],
        ).ask(kbi_msg="")
    if "priority" in selected:
        priorities = fetch_issue_priorities()
        args.priority_id = questionary.select(
            "優先度",
            choices=[
                questionary.Choice(p["name"], value=str(p["id"])) for p in priorities
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
                questionary.Choice(f"{v['name']} ({v['status']})", value=str(v["id"]))
                for v in versions
            ],
        ).ask(kbi_msg="")
    if "notes" in selected:
        args.notes = questionary.text("コメント").ask(kbi_msg="")
    if "time_entry" in selected:
        hours_str = questionary.text(
            "作業時間（例: 1.5 (h)）",
            validate=lambda v: (
                v.replace(".", "", 1).isdigit() or "数値を入力してください"
            ),
        ).ask(kbi_msg="")
        if hours_str:
            args.hours = float(hours_str)
        activities = fetch_time_entry_activities()
        args.activity_id = questionary.select(
            "作業分類",
            choices=[
                questionary.Choice(a["name"], value=str(a["id"])) for a in activities
            ],
        ).ask(kbi_msg="")
        args.spent_on = (
            questionary.text("作業日（YYYY-MM-DD、省略で今日）", default="").ask(
                kbi_msg=""
            )
            or None
        )
        args.time_comments = (
            questionary.text("作業時間のコメント", default="").ask(kbi_msg="") or None
        )


def _handle_issue_create(args: argparse.Namespace) -> None:
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
            tracker_id = questionary.select("トラッカーを選択", choices=choices).ask(
                kbi_msg=""
            )
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


def _handle_issue_update(args: argparse.Namespace) -> None:
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
    if (
        not should_update_issue
        and not should_update_issue_relation
        and not should_create_time_entry
    ):
        print("更新内容がないので更新をキャンセルしました")
        exit(1)


def _handle_issue(args: argparse.Namespace) -> None:
    cmd = _resolve_alias(args.issue_command)
    if cmd == "view":
        read_issue(
            args.issue_id,
            include=args.include or "",
            full=args.full,
            web=args.web,
        )
    elif cmd == "create":
        _handle_issue_create(args)
    elif cmd == "update":
        _handle_issue_update(args)
    elif cmd == "comment":
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
            status_id=args.status_id,
            tracker_id=args.tracker_id,
            priority_id=args.priority_id,
            query_id=args.query_id,
            limit=args.limit,
            offset=args.offset,
            full=args.full,
        )


def _handle_version(args: argparse.Namespace) -> None:
    cmd = _resolve_alias(args.version_command)
    if cmd == "view":
        read_version(args.version_id, full=args.full, web=args.web)
    elif cmd == "create":
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
    elif cmd == "update":
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


def _handle_wiki(args: argparse.Namespace) -> None:
    project_id = args.project_id or wiki_project_id or default_project_id
    if not project_id:
        print(
            "project_idを指定するか、wiki_project_idまたはdefault_project_idを設定してください"
        )
        exit(1)
    cmd = _resolve_alias(args.wiki_command)
    if cmd == "view":
        read_wiki(project_id, args.page_title, full=args.full, web=args.web)
    elif cmd == "create":
        page_title = args.page_title
        parent_title = args.parent_title
        if page_title is None:
            pages = fetch_wikis(project_id)
            existing_titles = {normalize_title(p["title"]) for p in pages}

            def validate_page_title(value: str) -> bool | str:
                stripped = value.strip()
                if not stripped:
                    return "ページタイトルを入力してください"
                if normalize_title(stripped) in existing_titles:
                    return "既存のページタイトルと重複しています"
                return True

            page_title = questionary.text(
                "ページタイトル",
                validate=validate_page_title,
            ).ask(kbi_msg="")
            if not page_title:
                print("ページタイトルが空のためキャンセルしました")
                exit(1)
            if parent_title is None:
                parent_title = questionary.select(
                    "親ページ",
                    choices=build_wiki_tree_choices(pages),
                ).ask(kbi_msg="")
        if args.description and args.description != "":
            text = args.description
        else:
            text = open_editor()
        if text:
            page_title = normalize_title(page_title)
            if parent_title:
                parent_title = normalize_title(parent_title)
            create_wiki(project_id, page_title, text, parent_title=parent_title)
        else:
            print("テキストが空のためキャンセルしました")
    elif cmd == "update":
        page_title = args.page_title
        if page_title is None:
            pages = fetch_wikis(project_id)
            if not pages:
                print("Wikiページが存在しません")
                exit(1)
            page_title = questionary.select(
                "編集するページ",
                choices=build_wiki_tree_choices(pages),
            ).ask(kbi_msg="")
            if not page_title:
                print("キャンセルしました")
                exit(1)
        if args.description and args.description != "":
            text = args.description
        else:
            current = fetch_wiki(project_id, page_title)
            text = open_editor(current.get("text") or "")
        if text:
            update_wiki(project_id, page_title, text)
        else:
            print("テキストが空のためキャンセルしました")
    else:
        list_wikis(project_id, full=args.full)


def _handle_user(args: argparse.Namespace) -> None:
    project_id = args.project_id or default_project_id
    list_users(project_id=project_id, full=args.full)


def _handle_role(args: argparse.Namespace) -> None:
    if _resolve_alias(args.role_command) == "view":
        read_role(args.role_id, full=args.full)
    else:
        list_roles(full=args.full)


def _handle_search(args: argparse.Namespace) -> None:
    search(
        query=args.query,
        limit=args.limit,
        offset=args.offset,
        full=args.full,
    )


def _handle_attachment(
    args: argparse.Namespace, a_parser: argparse.ArgumentParser
) -> None:
    cmd = _resolve_alias(args.attachment_command)
    if cmd == "view":
        read_attachment(args.attachment_id, full=args.full)
    elif cmd == "update":
        update_attachment(
            attachment_id=args.attachment_id,
            filename=args.filename,
            description=args.description,
        )
    else:
        a_parser.print_help()


def _handle_time_entry(args: argparse.Namespace) -> None:
    if _resolve_alias(args.time_entry_command) == "create":
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
        list_time_entries(project_id=project_id, user_id=args.user_id, full=args.full)


def main() -> None:
    parser, a_parser = _build_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.command in ("config", "c"):
        _handle_config(args)
        return

    check_config()

    if args.tui and args.command is None:
        run_issue_tui()
        return

    if args.command in ("project", "p"):
        _handle_project(args)
    elif args.command in ("issue", "i"):
        _handle_issue(args)
    elif args.command in ("version", "v"):
        _handle_version(args)
    elif args.command in ("wiki", "w"):
        _handle_wiki(args)
    elif args.command in ("user", "u"):
        _handle_user(args)
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
        _handle_role(args)
    elif args.command == "query":
        list_queries(full=args.full)
    elif args.command == "custom_field":
        list_custom_fields(full=args.full)
    elif args.command == "search":
        _handle_search(args)
    elif args.command == "attachment":
        _handle_attachment(args, a_parser)
    elif args.command == "time_entry":
        _handle_time_entry(args)
    else:
        parser.print_help()
