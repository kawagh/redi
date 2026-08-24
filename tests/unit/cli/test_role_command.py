import json

import pytest

from redi.cli import role_command
from redi.i18n import messages
from redi.service.role_service import CATEGORY_OTHER, PERMISSION_CATEGORIES


class TestPrintRole:
    """role view は権限を含めて表示する"""

    def test_exits_when_not_found(self, monkeypatch, capsys):
        """存在しないロール (取得結果が None) は理由を示して終了する"""
        monkeypatch.setattr(role_command, "fetch_role", lambda role_id: None)

        with pytest.raises(SystemExit) as e:
            role_command._print_role("999", full=False)

        assert e.value.code == 1
        assert messages.role_not_found.format(id="999") in capsys.readouterr().out

    def test_prints_permissions_grouped_by_category(self, monkeypatch, capsys):
        """permissions はカテゴリ見出しの下に表示名でインデントして並べる"""
        monkeypatch.setattr(
            role_command,
            "fetch_role",
            lambda role_id: {
                "id": 3,
                "name": "Manager",
                "permissions": ["add_issues", "manage_wiki", "edit_issues"],
            },
        )

        role_command._print_role("3", full=False)

        out = capsys.readouterr().out
        labels = role_command._category_labels()
        permissions = messages.permission_labels
        assert out.startswith("3 Manager\n")
        assert (
            f"  [{labels['issue_tracking']}]\n"
            f"    {permissions['add_issues']}\n"
            f"    {permissions['edit_issues']}"
        ) in out
        assert f"  [{labels['wiki']}]\n    {permissions['manage_wiki']}" in out

    def test_prints_permission_count(self, monkeypatch, capsys):
        """権限の見出しには件数を出す(カテゴリ分けで落ちていないことを数で確かめられる)"""
        monkeypatch.setattr(
            role_command,
            "fetch_role",
            lambda role_id: {
                "id": 3,
                "name": "Manager",
                "permissions": ["add_issues", "manage_wiki", "plugin_permission"],
            },
        )

        role_command._print_role("3", full=False)

        out = capsys.readouterr().out
        assert messages.label_permissions_header.format(count=3) in out

    def test_prints_unknown_permission_in_other_category(self, monkeypatch, capsys):
        """カテゴリ表に無い権限も「その他」に内部名のまま必ず出す

        プラグイン由来の権限には表示名を持てないが、権限漏れの確認に使う
        出力なので落とさず内部名で出す。
        """
        monkeypatch.setattr(
            role_command,
            "fetch_role",
            lambda role_id: {
                "id": 3,
                "name": "Manager",
                "permissions": ["view_issues", "plugin_permission"],
            },
        )

        role_command._print_role("3", full=False)

        out = capsys.readouterr().out
        labels = role_command._category_labels()
        assert f"  [{labels[CATEGORY_OTHER]}]\n    plugin_permission" in out

    def test_has_label_for_every_category(self):
        """カテゴリ表の全カテゴリと other に表示ラベルがある"""
        labels = role_command._category_labels()

        missing = [c for c, _ in PERMISSION_CATEGORIES if c not in labels]
        assert not missing, missing
        assert CATEGORY_OTHER in labels

    def test_keeps_full_json_as_is(self, monkeypatch, capsys):
        """--full は API のレスポンスをそのまま JSON で出す(グルーピングしない)"""
        role = {
            "id": 3,
            "name": "Manager",
            "permissions": ["manage_wiki", "add_issues"],
        }
        monkeypatch.setattr(role_command, "fetch_role", lambda role_id: role)

        role_command._print_role("3", full=True)

        assert json.loads(capsys.readouterr().out) == role
