import pytest

from redi.api.group import (
    GroupAdminRequiredException,
    GroupNotFoundException,
    GroupUserNotFoundException,
)
from redi.cli import group_command
from redi.i18n import messages

GROUP = {
    "id": 7,
    "name": "開発チーム",
    "users": [{"id": 3, "name": "山田 太郎"}],
    "memberships": [
        {
            "id": 1,
            "project": {"id": 2, "name": "デモ"},
            "roles": [{"id": 4, "name": "Developer"}],
        }
    ],
}


def raise_exception(exception: Exception):
    def _raise(*args, **kwargs):
        raise exception

    return _raise


class TestViewGroup:
    """`group view` の標準出力"""

    def test_prints_users_and_memberships(self, monkeypatch, capsys):
        """所属ユーザーと参加プロジェクトを見出し付きで出す"""
        monkeypatch.setattr(
            group_command.group_service, "read_group", lambda *a, **kw: GROUP
        )

        group_command._view_group("7")

        out = capsys.readouterr().out
        assert "7 開発チーム" in out
        assert messages.label_users_header in out
        assert "3 山田 太郎" in out
        assert messages.label_membership_header in out
        assert "2 デモ [Developer]" in out


class TestGroupErrorMessages:
    """api の例外を CLI のメッセージと終了コードに変換する"""

    def test_view_missing_group(self, monkeypatch, capsys):
        """存在しないグループの表示は group_not_found を出して exit 1"""
        monkeypatch.setattr(
            group_command.group_service,
            "read_group",
            raise_exception(GroupNotFoundException("7")),
        )

        with pytest.raises(SystemExit) as e:
            group_command._view_group("7")

        assert e.value.code == 1
        assert messages.group_not_found.format(id="7") in capsys.readouterr().err

    def test_delete_without_admin(self, monkeypatch, capsys):
        """管理者権限が無い削除は操作に対応した案内を出して exit 1"""
        monkeypatch.setattr(
            group_command.group_service,
            "delete_group",
            raise_exception(GroupAdminRequiredException()),
        )

        with pytest.raises(SystemExit) as e:
            group_command._delete_group("7")

        assert e.value.code == 1
        assert messages.group_delete_admin_required in capsys.readouterr().err

    def test_remove_user_missing_group_or_user(self, monkeypatch, capsys):
        """ユーザー削除の 404 はグループとユーザーのどちらが無いか分からない旨を出して exit 1"""
        monkeypatch.setattr(
            group_command.group_service,
            "remove_group_user",
            raise_exception(GroupUserNotFoundException("7", 3)),
        )

        with pytest.raises(SystemExit) as e:
            group_command._remove_group_user("7", 3)

        assert e.value.code == 1
        assert (
            messages.group_or_user_not_found.format(group_id="7", user_id=3)
            in capsys.readouterr().err
        )
