import argparse

import pytest

from redi.api.user import UserNotFoundException, UserPermissionDeniedException
from redi.cli import main as main_module
from redi.cli import user_command
from redi.cli.main import build_redi_parser
from redi.i18n import messages


class TestUpdate:
    """`user update` の打ち切り"""

    def test_no_fields_does_not_call_api(self, monkeypatch, capsys):
        """更新するフィールドが 1 つも無ければ API を呼ばずに打ち切る"""
        called = False

        def fake_update_user(**kwargs):
            nonlocal called
            called = True

        monkeypatch.setattr(user_command.user_service, "update_user", fake_update_user)

        with pytest.raises(SystemExit) as e:
            user_command._update_user("2")

        assert e.value.code == 1
        assert called is False
        assert messages.update_canceled_no_changes in capsys.readouterr().out


class TestList:
    """`user list` の権限不足時のふるまい"""

    def test_permission_denied_is_not_an_error_exit(self, monkeypatch, capsys):
        """一覧は管理者権限が要るため、権限不足なら理由を出して正常終了する"""

        def fake_list_users(**kwargs):
            raise UserPermissionDeniedException

        monkeypatch.setattr(user_command.user_service, "list_users", fake_list_users)

        user_command._list_users()

        out = capsys.readouterr().out
        assert messages.user_list_admin_required in out
        assert messages.user_list_member_hint in out


class TestListFilterOptions:
    """`user list` のフィルタオプションがサブコマンドの前後どちらでも効く"""

    @pytest.fixture
    def parser(self, monkeypatch) -> argparse.ArgumentParser:
        monkeypatch.setattr(main_module, "list_profile_names", list)
        return build_redi_parser()

    @pytest.mark.parametrize(
        "argv",
        [
            [
                "user",
                "list",
                "--status",
                "locked",
                "--name",
                "kawagh",
                "--group_id",
                "6",
            ],
            [
                "user",
                "--status",
                "locked",
                "--name",
                "kawagh",
                "--group_id",
                "6",
                "list",
            ],
        ],
        ids=["postfix", "prefix"],
    )
    def test_accepts_filters_on_both_sides(self, parser, argv):
        """`user list --status ...` と `user --status ... list` の両方を受け付ける"""
        args = parser.parse_args(argv)

        assert args.status == "locked"
        assert args.name == "kawagh"
        assert args.group_id == 6

    def test_unknown_status_is_rejected(self, parser):
        """status は Redmine が定める 3 種以外を受け付けない"""
        with pytest.raises(SystemExit):
            parser.parse_args(["user", "list", "--status", "unknown"])

    def test_filters_are_passed_to_service(self, monkeypatch):
        """指定したフィルタをそのままサービス層に渡す"""
        calls: list[dict] = []

        def fake_list_users(**kwargs):
            calls.append(kwargs)
            return []

        monkeypatch.setattr(user_command.user_service, "list_users", fake_list_users)

        user_command._list_users(status="locked", name="kawagh", group_id=6)

        assert calls == [{"status": "locked", "name": "kawagh", "group_id": 6}]


class TestView:
    """`user view` の失敗時のふるまい"""

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (UserNotFoundException("404"), messages.user_not_found.format(id="404")),
            (UserPermissionDeniedException(), messages.user_detail_permission_required),
        ],
        ids=["not_found", "permission_denied"],
    )
    def test_exits_with_reason(self, monkeypatch, capsys, error, expected):
        """存在しない・参照権限が無い場合は理由を出して exit 1 する"""

        def fake_read_user(user_id, detail=False):
            raise error

        monkeypatch.setattr(user_command.user_service, "read_user", fake_read_user)

        with pytest.raises(SystemExit) as e:
            user_command._view_user("404")

        assert e.value.code == 1
        assert expected in capsys.readouterr().out
