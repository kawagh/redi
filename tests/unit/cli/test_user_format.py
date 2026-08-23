from typing import Any, cast

from redi.api.user import User
from redi.cli.user_format import format_user_detail, user_summary
from redi.i18n import messages

USER: dict[str, Any] = {
    "id": 1,
    "login": "admin",
    "firstname": "Redmine",
    "lastname": "Admin",
    "mail": "admin@example.net",
    "created_on": "2026-01-01T00:00:00Z",
    "last_login_on": "2026-01-02T00:00:00Z",
}


def _user(**overrides: Any) -> User:
    return cast(User, {**USER, **overrides})


class TestUserSummary:
    """1 行目の `id login 氏名`"""

    def test_joins_id_login_and_name(self):
        """id・login・氏名を 1 行に並べる"""
        assert user_summary(_user()) == "1 admin Redmine Admin"

    def test_omits_missing_name(self):
        """氏名が取れない場合は詰めて表示する"""
        user = cast(User, {"id": 2, "login": "guest"})

        assert user_summary(user) == "2 guest"


class TestFormatUserDetail:
    """`user view` / `me` の詳細表示"""

    def test_details_are_indented(self):
        """1 行目以外は 2 スペース下げて出す"""
        lines = format_user_detail(_user())

        assert lines[0] == "1 admin Redmine Admin"
        assert all(line.startswith("  ") for line in lines[1:])

    def test_admin_is_yes_or_no(self):
        """admin は Python の bool ではなく yes / no で出す"""
        admin = format_user_detail(_user(admin=True))
        member = format_user_detail(_user(admin=False))

        assert "  " + messages.label_admin.format(value=messages.label_yes) in admin
        assert "  " + messages.label_admin.format(value=messages.label_no) in member

    def test_admin_is_omitted_when_not_returned(self):
        """admin は自分自身か管理者でしか返らないため、キーが無ければ行ごと出さない"""
        admin_label = messages.label_admin.split("{")[0]

        lines = format_user_detail(_user())

        assert not any(line.strip().startswith(admin_label) for line in lines)

    def test_lists_custom_fields_memberships_and_groups(self):
        """カスタムフィールド・メンバーシップ・グループを出す"""
        lines = format_user_detail(
            _user(
                custom_fields=[{"id": 1, "name": "部署", "value": "開発"}],
                memberships=[
                    {
                        "id": 1,
                        "project": {"id": 3, "name": "redi"},
                        "roles": [{"id": 4, "name": "開発者"}],
                    }
                ],
                groups=[{"id": 5, "name": "reviewers"}],
            )
        )

        assert "  " + messages.label_custom_fields_header in lines
        assert "    部署: 開発" in lines
        assert "  " + messages.label_membership_header in lines
        assert "    3 redi - 開発者" in lines
        assert "  " + messages.label_groups_header in lines
        assert "    5 reviewers" in lines
