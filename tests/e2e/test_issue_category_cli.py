import json
import subprocess

import pytest

from tests.e2e.utils import run_redi, unique_identifier

PROJECT_ID = "reditest"
# 作成されることのない id (存在しないカテゴリの扱いの検証に使う)
MISSING_CATEGORY_ID = "999999"


def _create_category(name: str) -> str:
    """イシューカテゴリを作成して id を返す。"""
    run_redi("issue_category", "create", name, "-p", PROJECT_ID)
    categories = json.loads(
        run_redi("issue_category", "list", "-p", PROJECT_ID, "--full").stdout
    )
    return str(next(c for c in categories if c["name"] == name)["id"])


@pytest.mark.e2e
class TestIssueCategoryView:
    """`redi issue_category view` はカテゴリの詳細を表示する"""

    def test_shows_id_and_name(self):
        """作成したカテゴリの id と name が出る"""
        name = unique_identifier("e2e-ic-view")
        category_id = _create_category(name)

        viewed = run_redi("issue_category", "view", category_id).stdout

        assert category_id in viewed
        assert name in viewed

    def test_exits_with_error_for_missing_category(self):
        """存在しないカテゴリの表示は exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("issue_category", "view", MISSING_CATEGORY_ID)

        assert e.value.returncode == 1


@pytest.mark.e2e
class TestIssueCategoryUpdate:
    """`redi issue_category update` はカテゴリを更新する"""

    def test_updated_name_is_reflected(self):
        """更新した名前が詳細表示に反映される"""
        category_id = _create_category(unique_identifier("e2e-ic-update"))
        updated_name = unique_identifier("e2e-ic-updated")

        run_redi("issue_category", "update", category_id, "--name", updated_name)

        assert updated_name in run_redi("issue_category", "view", category_id).stdout

    def test_exits_with_error_for_missing_category(self):
        """存在しないカテゴリの更新は exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi(
                "issue_category", "update", MISSING_CATEGORY_ID, "--name", "更新後"
            )

        assert e.value.returncode == 1


@pytest.mark.e2e
class TestIssueCategoryDelete:
    """`redi issue_category delete` はカテゴリを削除する"""

    def test_deleted_category_disappears_from_list(self):
        """削除したカテゴリは一覧に出てこなくなる"""
        name = unique_identifier("e2e-ic-delete")
        category_id = _create_category(name)
        assert name in run_redi("issue_category", "list", "-p", PROJECT_ID).stdout

        run_redi("issue_category", "delete", category_id, "--yes")

        assert name not in run_redi("issue_category", "list", "-p", PROJECT_ID).stdout

    def test_deletes_with_reassign_to_id(self):
        """付け替え先を指定した削除も成功する"""
        reassign_to_id = _create_category(unique_identifier("e2e-ic-reassign-to"))
        name = unique_identifier("e2e-ic-reassign-from")
        category_id = _create_category(name)

        run_redi(
            "issue_category",
            "delete",
            category_id,
            "--reassign_to_id",
            reassign_to_id,
            "--yes",
        )

        listed = run_redi("issue_category", "list", "-p", PROJECT_ID).stdout
        assert name not in listed
        assert reassign_to_id in listed

    def test_exits_with_error_for_missing_category(self):
        """存在しないカテゴリの削除は exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("issue_category", "delete", MISSING_CATEGORY_ID, "--yes")

        assert e.value.returncode == 1
