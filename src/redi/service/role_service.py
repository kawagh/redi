"""ロール操作のサービス層。

`/roles/:id.json` の permissions は文字列の配列で、権限がどのカテゴリ
(Redmine の admin/roles 画面の区切り) に属するかを返さない。カテゴリは
Redmine 側では `Redmine::AccessControl` の `project_module` ブロックで
決まっていて REST API には出てこないため、対応表をここに持つ。
"""

from collections.abc import Iterable

CATEGORY_OTHER = "other"
"""対応表に無い権限を集めるカテゴリ。"""

PERMISSION_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "project",
        (
            "view_project",
            "search_project",
            "add_project",
            "edit_project",
            "close_project",
            "delete_project",
            "select_project_publicity",
            "select_project_modules",
            "manage_members",
            "manage_versions",
            "add_subprojects",
            "manage_public_queries",
            "save_queries",
            "use_webhooks",
        ),
    ),
    (
        "boards",
        (
            "view_messages",
            "add_messages",
            "edit_messages",
            "edit_own_messages",
            "delete_messages",
            "delete_own_messages",
            "view_message_watchers",
            "add_message_watchers",
            "delete_message_watchers",
            "manage_boards",
        ),
    ),
    (
        "calendar",
        ("view_calendar",),
    ),
    (
        "documents",
        (
            "view_documents",
            "add_documents",
            "edit_documents",
            "delete_documents",
        ),
    ),
    (
        "files",
        (
            "view_files",
            "manage_files",
        ),
    ),
    (
        "gantt",
        ("view_gantt",),
    ),
    (
        "issue_tracking",
        (
            "view_issues",
            "add_issues",
            "edit_issues",
            "edit_own_issues",
            "copy_issues",
            "manage_issue_relations",
            "manage_subtasks",
            "set_issues_private",
            "set_own_issues_private",
            "add_issue_notes",
            "edit_issue_notes",
            "edit_own_issue_notes",
            "view_private_notes",
            "set_notes_private",
            "delete_issues",
            "view_issue_watchers",
            "add_issue_watchers",
            "delete_issue_watchers",
            "import_issues",
            "manage_categories",
        ),
    ),
    (
        "news",
        (
            "view_news",
            "manage_news",
            "comment_news",
        ),
    ),
    (
        "repository",
        (
            "view_changesets",
            "browse_repository",
            "commit_access",
            "manage_related_issues",
            "manage_repository",
        ),
    ),
    (
        "time_tracking",
        (
            "view_time_entries",
            "log_time",
            "edit_time_entries",
            "edit_own_time_entries",
            "manage_project_activities",
            "log_time_for_other_users",
            "import_time_entries",
        ),
    ),
    (
        "wiki",
        (
            "view_wiki_pages",
            "view_wiki_edits",
            "export_wiki_pages",
            "edit_wiki_pages",
            "rename_wiki_pages",
            "delete_wiki_pages",
            "delete_wiki_pages_attachments",
            "view_wiki_page_watchers",
            "add_wiki_page_watchers",
            "delete_wiki_page_watchers",
            "protect_wiki_pages",
            "manage_wiki",
        ),
    ),
)
"""権限のカテゴリ表。並びは Redmine の admin/roles 画面に合わせる。

カテゴリの並びは画面と同じく、モジュールに属さない project を先頭に、
以降はモジュールの内部名の昇順 (画面側は `perms_by_module.keys.sort`)。
カテゴリ内の権限の並びは `Redmine::AccessControl` への登録順。
"""


def group_permissions(permissions: Iterable[str]) -> list[tuple[str, list[str]]]:
    """権限をカテゴリごとにまとめる。空のカテゴリは返さない。

    並びは `PERMISSION_CATEGORIES` に従う。API が返す順序は Redmine の
    バージョンによって変わるため、表の順に揃えることでロール間・インスタンス間で
    出力を突き合わせられるようにする。

    対応表に無い権限 (プラグインが追加したもの、対応バージョン間の差分) は
    落とさず末尾の `CATEGORY_OTHER` に集める。権限漏れの確認に使う出力なので
    黙って消してはいけない。
    """
    remaining = list(permissions)
    grouped: list[tuple[str, list[str]]] = []
    for category, known in PERMISSION_CATEGORIES:
        members = [p for p in known if p in remaining]
        if members:
            grouped.append((category, members))
            remaining = [p for p in remaining if p not in members]
    if remaining:
        grouped.append((CATEGORY_OTHER, remaining))
    return grouped
