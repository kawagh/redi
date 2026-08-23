import json

import pytest

from tests.e2e.utils import run_redi, unique_identifier


@pytest.mark.e2e
class TestMeView:
    """`redi me` は自分のアカウントを取得する"""

    def test_full_prints_account_without_api_key(self):
        """--full の JSON に api_key は含めない"""
        account = json.loads(run_redi("me", "--full").stdout)

        assert account["login"]
        assert "api_key" not in account

    def test_prints_id_login_and_name(self):
        """既定では 1 行目に id と login と氏名を出す"""
        account = json.loads(run_redi("me", "--full").stdout)

        first_line = run_redi("me").stdout.splitlines()[0]

        expected = (
            f"{account['id']} {account['login']}"
            f" {account['firstname']} {account['lastname']}"
        )
        assert first_line == expected

    def test_matches_user_view_current(self):
        """`user view current` と同じ書式・同じ項目で出す"""
        assert run_redi("me").stdout == run_redi("user", "view", "current").stdout


@pytest.mark.e2e
class TestMeUpdate:
    """`redi me update` は自分のアカウントを更新する"""

    def test_updated_firstname_is_reflected(self):
        """更新した firstname が取得結果に反映される"""
        original = json.loads(run_redi("me", "--full").stdout)["firstname"]
        firstname = unique_identifier("e2e-me")
        try:
            run_redi("me", "update", "--firstname", firstname)

            updated = json.loads(run_redi("me", "--full").stdout)
            assert updated["firstname"] == firstname
        finally:
            # 他の E2E が同じアカウントを見るので元に戻す
            run_redi("me", "update", "--firstname", original)
