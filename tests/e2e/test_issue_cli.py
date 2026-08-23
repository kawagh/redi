import json
import subprocess

import pytest

from tests.e2e.utils import (
    GLOBAL_QUERY_NAME,
    OTHER_PROJECT_QUERY_NAME,
    query_named,
    run_redi,
    unique_identifier,
)

# バグトラッカーには必須のカスタムフィールドがあり引数だけで作成できないため、
# 削除の検証には機能トラッカーを使う
FEATURE_TRACKER_ID = "2"
SUPPORT_TRACKER_ID = "3"
BUG_TRACKER_ID = "1"


def _create_issue(
    subject: str,
    tracker_id: str = FEATURE_TRACKER_ID,
    custom_fields: str | None = None,
) -> str:
    """イシューを作成して id を返す。"""
    custom_field_options = ["--custom_fields", custom_fields] if custom_fields else []
    created = json.loads(
        run_redi(
            "issue",
            "create",
            subject,
            "--project_id",
            "reditest",
            "--tracker_id",
            tracker_id,
            "-d",
            "e2e issue body",
            *custom_field_options,
            "--full",
        ).stdout
    )
    return str(created["id"])


def _custom_field_id(name: str) -> str:
    """カスタムフィールドの id を名前で引く。id は初期化のたびに変わるので固定しない。"""
    lines = run_redi("custom_field", "list").stdout.splitlines()
    return next(
        line.split(" ", 1)[0] for line in lines if line.split(" ", 1)[1] == name
    )


def _create_bug_issue(subject: str) -> str:
    """バグトラッカーのイシューを作成して id を返す。

    バグトラッカーには必須のカスタムフィールドがあるので、値を埋めて作成する。
    """
    return _create_issue(
        subject,
        tracker_id=BUG_TRACKER_ID,
        custom_fields=f"{_custom_field_id('バージョン')}=e2e",
    )


@pytest.mark.e2e
class TestIssueView:
    """`redi issue view` はイシューの詳細を表示する"""

    def test_shows_subject_and_description(self):
        """作成したイシューの件名と説明が出る"""
        subject = unique_identifier("e2e-issue-view")
        issue_id = _create_issue(subject)

        viewed = run_redi("issue", "view", issue_id).stdout

        assert subject in viewed
        assert "e2e issue body" in viewed


@pytest.mark.e2e
class TestIssueUpdate:
    """`redi issue update` はイシューを更新する"""

    def test_updated_subject_is_reflected(self):
        """更新した件名が詳細表示に反映される"""
        issue_id = _create_issue(unique_identifier("e2e-issue-update"))
        updated_subject = unique_identifier("e2e-issue-updated")

        run_redi("issue", "update", issue_id, "--subject", updated_subject)

        assert updated_subject in run_redi("issue", "view", issue_id).stdout

    def test_moved_issue_appears_in_destination_project(self):
        """--project_id に identifier を渡すとイシューが移動先プロジェクトの一覧に出る"""
        subject = unique_identifier("e2e-issue-move")
        issue_id = _create_issue(subject)
        destination = unique_identifier("e2e-move-dest")
        run_redi(
            "project",
            "create",
            f"e2e move {destination}",
            destination,
            "--tracker_ids",
            FEATURE_TRACKER_ID,
        )

        run_redi("issue", "update", issue_id, "--project_id", destination)

        assert subject in run_redi("issue", "list", "--project_id", destination).stdout
        assert (
            subject not in run_redi("issue", "list", "--project_id", "reditest").stdout
        )

    def test_exits_with_error_for_missing_destination_project(self):
        """Redmine は存在しない移動先を黙って無視するので、redi 側で弾いて exit 1 にする"""
        issue_id = _create_issue(unique_identifier("e2e-issue-move-missing"))

        with pytest.raises(subprocess.CalledProcessError) as update_error_info:
            run_redi("issue", "update", issue_id, "--project_id", "e2e-no-such-project")

        update_error = update_error_info.value
        assert update_error.returncode == 1
        assert "Project not found: e2e-no-such-project" in update_error.stdout, (
            f"想定外のエラーで update が失敗\n"
            f"stdout:\n{update_error.stdout}\nstderr:\n{update_error.stderr}"
        )


@pytest.mark.e2e
class TestIssueComment:
    """`redi issue comment` はイシューにコメントを追加する"""

    def test_added_comment_is_listed_with_note_url(self):
        """追加したコメントは note 番号つき URL で伝えられ、詳細表示にも出る"""
        issue_id = _create_issue(unique_identifier("e2e-issue-comment"))
        notes = unique_identifier("e2e-comment")

        added = run_redi("issue", "comment", issue_id, notes).stdout

        assert f"/issues/{issue_id}#note-1" in added
        assert notes in run_redi("issue", "view", issue_id).stdout


@pytest.mark.e2e
class TestIssueDelete:
    """`redi issue delete` はイシューを削除する"""

    def test_deleted_issue_disappears_from_list(self):
        """削除したイシューは一覧に出てこなくなる"""
        subject = unique_identifier("e2e-issue-delete")
        issue_id = _create_issue(subject)
        assert subject in run_redi("issue", "list", "--project_id", "reditest").stdout

        run_redi("issue", "delete", issue_id, "--yes")

        assert (
            subject not in run_redi("issue", "list", "--project_id", "reditest").stdout
        )

    def test_exits_with_error_for_missing_issue(self):
        """存在しないイシューの削除は見つからないと伝えて exit 1 で終わる"""
        issue_id = _create_issue(unique_identifier("e2e-issue-missing"))
        run_redi("issue", "delete", issue_id, "--yes")

        with pytest.raises(subprocess.CalledProcessError) as delete_error_info:
            run_redi("issue", "delete", issue_id, "--yes")

        delete_error = delete_error_info.value
        assert delete_error.returncode == 1
        assert f"Issue not found: #{issue_id}" in delete_error.stdout, (
            f"想定外のエラーで delete が失敗\n"
            f"stdout:\n{delete_error.stdout}\nstderr:\n{delete_error.stderr}"
        )


@pytest.mark.e2e
class TestIssueQueryId:
    """`redi issue --query_id` はカスタムクエリの条件で絞り込む"""

    def test_filters_by_query_condition(self):
        """トラッカーの or 条件に合うイシューだけが出て、外れたイシューは出ない

        シードしたクエリは「機能 or サポート」で絞っており、
        単一トラッカーしか選べない TUI のフィルタでは表現できない条件になっている。
        """
        marker = unique_identifier("e2e-query-tracker")
        feature_subject = f"{marker}-feature"
        support_subject = f"{marker}-support"
        bug_subject = f"{marker}-bug"
        _create_issue(feature_subject)
        _create_issue(support_subject, tracker_id=SUPPORT_TRACKER_ID)
        _create_bug_issue(bug_subject)

        listed = run_redi(
            "issue", "--query_id", str(query_named(GLOBAL_QUERY_NAME)["id"])
        ).stdout

        assert feature_subject in listed
        assert support_subject in listed
        assert bug_subject not in listed

    def test_exits_with_error_when_combined_with_ignored_filter(self):
        """クエリの条件に負けて無視されるフィルタと併用すると exit 1 で終わる"""
        query_id = str(query_named(GLOBAL_QUERY_NAME)["id"])

        with pytest.raises(subprocess.CalledProcessError) as list_error_info:
            run_redi("issue", "--query_id", query_id, "--status_id", "1")

        list_error = list_error_info.value
        assert list_error.returncode == 1
        assert "--status_id" in list_error.stdout, (
            f"想定外のエラーで list が失敗\n"
            f"stdout:\n{list_error.stdout}\nstderr:\n{list_error.stderr}"
        )

    def test_exits_with_error_for_query_of_another_project(self):
        """他プロジェクトのクエリを渡すと、条件を無視した一覧を返さずエラーで終わる

        Redmine が 404 を返すため。#429 で実測できていなかった挙動。
        """
        query_id = str(query_named(OTHER_PROJECT_QUERY_NAME)["id"])

        with pytest.raises(subprocess.CalledProcessError) as list_error_info:
            run_redi("issue", "--query_id", query_id, "--project_id", "reditest")

        assert list_error_info.value.returncode == 1
