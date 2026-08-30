import json
import subprocess

import pytest

from tests.e2e.utils import assert_paginates, run_redi, unique_identifier


def _create_news(title: str, description: str = "e2e news body") -> str:
    """ニュースを作成し、出力された URL から id を取り出して返す。"""
    stdout = run_redi("news", "create", title, "-d", description).stdout
    return stdout.strip().rsplit("/", 1)[1]


@pytest.mark.e2e
class TestNewsList:
    """`redi news list` はニュース一覧を表示する"""

    def test_slices_list_with_limit_and_offset(self):
        """3件以上にしてから絞り込む"""
        for _ in range(3):
            _create_news(unique_identifier("e2e-page-news"))

        assert_paginates("news", "list")


@pytest.mark.e2e
class TestNewsView:
    """`redi news view` は作成したニュースを取得できる"""

    def test_created_news_is_viewable(self):
        """作成したニュースを id で引くと入力した内容が返る"""
        title = unique_identifier("e2e-news")
        news_id = _create_news(title, "e2e news body")

        news = json.loads(run_redi("news", "view", news_id, "--full").stdout)

        assert news["title"] == title
        assert news["description"] == "e2e news body"

    def test_created_news_appears_in_list(self):
        """作成したニュースは一覧に出てくる"""
        title = unique_identifier("e2e-news-list")
        _create_news(title)

        assert title in run_redi("news", "list").stdout

    def test_exits_with_error_for_missing_news(self):
        """存在しないニュースの取得は exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("news", "view", "999999")

        assert e.value.returncode == 1


@pytest.mark.e2e
class TestNewsUpdate:
    """`redi news update` は指定した項目だけを更新する"""

    def test_updates_specified_fields_only(self):
        """指定しなかった項目は元の値のまま残る"""
        title = unique_identifier("e2e-news-update")
        news_id = _create_news(title, "before")

        run_redi("news", "update", news_id, "-t", f"{title}-updated")

        news = json.loads(run_redi("news", "view", news_id, "--full").stdout)
        assert news["title"] == f"{title}-updated"
        assert news["description"] == "before"

    def test_exits_with_error_for_missing_news(self):
        """存在しないニュースの更新は exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("news", "update", "999999", "-t", "updated")

        assert e.value.returncode == 1


@pytest.mark.e2e
class TestNewsDelete:
    """`redi news delete` はニュースを削除する"""

    def test_deleted_news_disappears_from_list(self):
        """削除したニュースは一覧に出てこなくなる"""
        title = unique_identifier("e2e-news-delete")
        news_id = _create_news(title)
        assert title in run_redi("news", "list").stdout

        run_redi("news", "delete", news_id, "--yes")

        assert title not in run_redi("news", "list").stdout

    def test_exits_with_error_for_missing_news(self):
        """存在しないニュースの削除は exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("news", "delete", "999999", "--yes")

        assert e.value.returncode == 1
