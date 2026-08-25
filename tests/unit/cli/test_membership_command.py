import argparse

import pytest

from redi.api.membership import Membership, MembershipNotFoundException
from redi.cli import membership_command
from redi.cli.membership_command import _format_membership_line, handle_membership


class TestFormatMembershipLine:
    """一覧・詳細の 1 行表示は `id [user|group] <principal> - <roles>` になる"""

    def test_formats_user_membership(self):
        """user のメンバーシップは [user] と principal の id/name を並べる"""
        membership: Membership = {
            "id": 7,
            "user": {"id": 5, "name": "Sandbox Developer"},
            "roles": [{"id": 3, "name": "開発者"}, {"id": 4, "name": "報告者"}],
        }

        assert (
            _format_membership_line(membership)
            == "7 [user] 5 Sandbox Developer - 開発者, 報告者"
        )

    def test_formats_group_membership(self):
        """group のメンバーシップは [group] と表示する"""
        membership: Membership = {
            "id": 8,
            "group": {"id": 9, "name": "開発チーム"},
            "roles": [{"id": 3, "name": "開発者"}],
        }

        assert _format_membership_line(membership) == "8 [group] 9 開発チーム - 開発者"


class TestUpdateWithoutRoleIds:
    """`membership update` はロールが空なら更新せずに終了する

    Redmine は role_ids が空だと更新を受け付けないため、API を呼ぶ前に打ち切る。
    """

    def test_does_not_call_service(self, monkeypatch, capsys):
        """role_ids が空文字なら update を呼ばずに中断したことを伝える"""
        called = []
        monkeypatch.setattr(
            membership_command.membership_service,
            "update_membership",
            lambda *args, **kwargs: called.append(args),
        )

        with pytest.raises(SystemExit) as e:
            handle_membership(
                argparse.Namespace(
                    membership_command="update", membership_id="7", role_ids=" , "
                )
            )

        assert e.value.code is None
        assert called == []
        assert capsys.readouterr().out.strip() != ""


class TestViewMissingMembership:
    """存在しないメンバーシップの表示は見つからないと伝えて exit 1 で終わる"""

    def test_exits_with_error(self, monkeypatch, capsys):
        """MembershipNotFoundException を id 付きのメッセージに変換する"""

        def raise_not_found(membership_id):
            raise MembershipNotFoundException(membership_id)

        monkeypatch.setattr(
            membership_command.membership_service, "read_membership", raise_not_found
        )

        with pytest.raises(SystemExit) as e:
            handle_membership(
                argparse.Namespace(
                    membership_command="view", membership_id="404", full=False
                )
            )

        assert e.value.code == 1
        assert "404" in capsys.readouterr().err
