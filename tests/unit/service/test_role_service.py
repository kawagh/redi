import pytest

from redi.service.role_service import (
    CATEGORY_OTHER,
    PERMISSION_CATEGORIES,
    group_permissions,
)

REDMINE_7_0_ADMIN_PERMISSIONS = [
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
    "view_time_entries",
    "log_time",
    "edit_time_entries",
    "edit_own_time_entries",
    "manage_project_activities",
    "log_time_for_other_users",
    "import_time_entries",
    "view_news",
    "manage_news",
    "comment_news",
    "view_documents",
    "add_documents",
    "edit_documents",
    "delete_documents",
    "view_files",
    "manage_files",
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
    "view_changesets",
    "browse_repository",
    "commit_access",
    "manage_related_issues",
    "manage_repository",
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
    "view_calendar",
    "view_gantt",
]
"""Redmine 7.0 の管理者ロール (id=3, 既定データ ja) が持つ権限。

docker image `redmine:7.0` で実測した (`GET /roles/3.json` と同じ 77 件)。
"""

REDMINE_6_1_ADMIN_PERMISSIONS = [
    p for p in REDMINE_7_0_ADMIN_PERMISSIONS if p != "use_webhooks"
]
"""Redmine 6.1 の管理者ロールが持つ権限。

docker image `redmine:6.1` で実測したところ、7.0 との差は 7.0 で追加された
`use_webhooks` の 1 件だけで、他の権限名もカテゴリ
(`Redmine::AccessControl` の `project_module`) も一致していたため、7.0 の
リストから引いて表している。
"""


class TestGroupPermissions:
    """権限を admin/roles 画面と同じカテゴリ単位にまとめる"""

    def test_groups_by_category(self):
        """権限はカテゴリごとにまとまる"""
        grouped = group_permissions(
            ["view_issues", "view_wiki_pages", "add_issues", "manage_wiki"]
        )

        assert grouped == [
            ("issue_tracking", ["view_issues", "add_issues"]),
            ("wiki", ["view_wiki_pages", "manage_wiki"]),
        ]

    def test_orders_by_category_table(self):
        """API が返す順序によらずカテゴリ表の順に並べる"""
        grouped = group_permissions(["view_gantt", "view_issues", "add_project"])

        assert [c for c, _ in grouped] == ["project", "issue_tracking", "gantt"]

    def test_orders_members_by_category_table(self):
        """カテゴリ内の権限もカテゴリ表の順に並べる"""
        grouped = group_permissions(["edit_issues", "view_issues", "add_issues"])

        assert grouped == [
            ("issue_tracking", ["view_issues", "add_issues", "edit_issues"])
        ]

    def test_omits_empty_categories(self):
        """該当する権限が無いカテゴリは出さない"""
        grouped = group_permissions(["view_calendar"])

        assert grouped == [("calendar", ["view_calendar"])]

    def test_collects_unknown_permissions_into_other(self):
        """カテゴリ表に無い権限は落とさず末尾の other に集める

        プラグインが追加する権限や対応 Redmine バージョン間の差分があるため、
        表から漏れた権限を黙って消すと「権限漏れはないか」の確認で嘘をつく。
        """
        grouped = group_permissions(["view_issues", "plugin_permission", "another_one"])

        assert grouped == [
            ("issue_tracking", ["view_issues"]),
            (CATEGORY_OTHER, ["plugin_permission", "another_one"]),
        ]

    def test_keeps_all_permissions(self):
        """入力した権限は 1 つも欠けない"""
        permissions = ["manage_wiki", "unknown_one", "view_issues", "view_gantt"]

        grouped = group_permissions(permissions)

        assert sorted(p for _, ps in grouped for p in ps) == sorted(permissions)

    def test_returns_empty_for_no_permissions(self):
        """権限が空なら空を返す"""
        assert group_permissions([]) == []


class TestPermissionCategories:
    """カテゴリ表そのものの整合性"""

    def test_no_duplicated_permission(self):
        """同じ権限が複数のカテゴリに属さない"""
        names = [p for _, ps in PERMISSION_CATEGORIES for p in ps]

        assert len(names) == len(set(names))

    def test_has_no_other_category(self):
        """other は表には持たず、表から漏れた権限の受け皿としてのみ使う"""
        assert CATEGORY_OTHER not in [c for c, _ in PERMISSION_CATEGORIES]

    @pytest.mark.parametrize(
        ("version", "permissions"),
        [
            ("6.1", REDMINE_6_1_ADMIN_PERMISSIONS),
            ("7.0", REDMINE_7_0_ADMIN_PERMISSIONS),
        ],
    )
    def test_covers_permissions_of_redmine_admin_role(self, version, permissions):
        """対応 Redmine の管理者ロールが持つ権限を表が網羅している

        対応バージョン (6.1 / 7.0) すべてで確かめる。表に漏れがあると other に
        落ちて、公式画面と並びが揃わなくなる。
        """
        grouped = group_permissions(permissions)

        assert CATEGORY_OTHER not in [c for c, _ in grouped]
