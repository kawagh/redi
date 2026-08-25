import json
import subprocess

import pytest

from tests.e2e.utils import run_redi

PROJECT_ID = "reditest"


def _memberships() -> list[dict]:
    return json.loads(
        run_redi("membership", "list", "--project_id", PROJECT_ID, "--full").stdout
    )


def _role_ids() -> list[str]:
    """ロールの id を並び順に返す。ロールの並びは Redmine の初期データ次第。"""
    return [line.split()[0] for line in run_redi("role", "list").stdout.splitlines()]


def _membership_id_of(user_id: int) -> str | None:
    """指定ユーザーのメンバーシップ id を返す。メンバーでなければ None。"""
    for m in _memberships():
        if m.get("user", {}).get("id") == user_id:
            return str(m["id"])
    return None


@pytest.fixture
def unassigned_user_id() -> int:
    """プロジェクトのメンバーではない状態にした admin の user id を返す。

    テストが途中で落ちてメンバーが残っていても、次回の実行に影響しないよう先に消す。
    """
    user_id = json.loads(run_redi("me", "--full").stdout)["id"]
    membership_id = _membership_id_of(user_id)
    if membership_id is not None:
        run_redi("membership", "delete", membership_id, "--yes")
    return user_id


@pytest.mark.e2e
class TestMembershipLifecycle:
    """`redi membership` はメンバーシップを作成・表示・更新・削除できる"""

    def test_create_view_update_delete(self, unassigned_user_id):
        """作成したメンバーシップを一覧・詳細で確認し、ロールを更新して削除できる"""
        role_ids = _role_ids()
        created_role_id, added_role_id = role_ids[0], role_ids[1]

        run_redi(
            "membership",
            "create",
            "--project_id",
            PROJECT_ID,
            "--user_id",
            str(unassigned_user_id),
            "--role_ids",
            created_role_id,
        )

        membership_id = _membership_id_of(unassigned_user_id)
        assert membership_id is not None

        viewed = json.loads(
            run_redi("membership", "view", membership_id, "--full").stdout
        )
        assert [str(r["id"]) for r in viewed["roles"]] == [created_role_id]

        run_redi(
            "membership",
            "update",
            membership_id,
            "--role_ids",
            f"{created_role_id},{added_role_id}",
        )

        updated = json.loads(
            run_redi("membership", "view", membership_id, "--full").stdout
        )
        assert sorted(str(r["id"]) for r in updated["roles"]) == sorted(
            [created_role_id, added_role_id]
        )

        run_redi("membership", "delete", membership_id, "--yes")

        assert _membership_id_of(unassigned_user_id) is None


@pytest.mark.e2e
class TestMembershipCreateValidationError:
    """Redmine のバリデーションエラー (HTTP 422) は内容を伝えて exit 1 で終わる"""

    def test_exits_with_error_for_existing_member(self):
        """すでにメンバーのユーザーを追加しようとするとエラー内容を出す"""
        member = next(m for m in _memberships() if "user" in m)

        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi(
                "membership",
                "create",
                "--project_id",
                PROJECT_ID,
                "--user_id",
                str(member["user"]["id"]),
                "--role_ids",
                _role_ids()[0],
            )

        assert e.value.returncode == 1
        assert e.value.stderr.strip() != ""


@pytest.mark.e2e
class TestMembershipNotFound:
    """存在しないメンバーシップの操作は exit 1 で終わる"""

    def test_view_exits_with_error(self):
        """view は見つからないと伝えて exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("membership", "view", "9999999")

        assert "9999999" in e.value.stderr

    def test_delete_exits_with_error(self):
        """delete は見つからないと伝えて exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("membership", "delete", "9999999", "--yes")

        assert "9999999" in e.value.stderr
