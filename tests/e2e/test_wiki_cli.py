import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _unique_wiki_title(prefix: str) -> str:
    """wiki page title 用のユニークな識別子。

    Redmine のページ識別子は英数字とハイフン/アンダースコアに正規化されるので、
    base の prefix もそれに合わせる。
    """
    return f"{prefix}-{unique_identifier('wiki')}"


def _create_wiki(title: str, description: str) -> None:
    result = run_redi("wiki", "create", title, "--description", description)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


@pytest.mark.e2e
class TestWikiList:
    """`redi wiki list` は wiki ページ一覧を表示する"""

    def test_lists_created_wiki(self):
        """事前 create した title が list に含まれる (create は正しい前提)"""
        title = _unique_wiki_title("WikiList")
        _create_wiki(title, "list test content")

        result = run_redi("wiki", "list")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert title in result.stdout


@pytest.mark.e2e
class TestWikiView:
    """`redi wiki view <title>` は指定した wiki ページの内容を表示する"""

    def test_succeeds_for_created_wiki(self):
        """create した wiki を view すると description 内容が含まれる (create は正しい前提)"""
        title = _unique_wiki_title("WikiView")
        description = f"view content {title}"
        _create_wiki(title, description)

        result = run_redi("wiki", "view", title)
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert description in result.stdout


@pytest.mark.e2e
class TestWikiCreate:
    """`redi wiki create` は新しい wiki ページを作成する"""

    def test_creates_then_view_shows_it(self):
        """create した wiki が view で取得できる (view は正しい前提)"""
        title = _unique_wiki_title("WikiCreate")
        description = f"create content {title}"
        _create_wiki(title, description)

        view_result = run_redi("wiki", "view", title)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert description in view_result.stdout


@pytest.mark.e2e
class TestWikiUpdate:
    """`redi wiki update` は既存の wiki ページを更新する"""

    def test_updates_then_view_shows_new_content(self):
        """create→update した後 view で更新後の description が確認できる (create/view は正しい前提)"""
        title = _unique_wiki_title("WikiUpdate")
        original = f"orig content {title}"
        updated = f"new content {title}"
        _create_wiki(title, original)

        update_result = run_redi("wiki", "update", title, "--description", updated)
        assert update_result.returncode == 0, (
            f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
        )

        view_result = run_redi("wiki", "view", title)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert updated in view_result.stdout
        assert original not in view_result.stdout


@pytest.mark.e2e
class TestWikiDelete:
    """`redi wiki delete` は指定した wiki ページを削除する"""

    def test_deletes_then_view_fails(self):
        """create→delete した後 view が失敗する (create/view は正しい前提)"""
        title = _unique_wiki_title("WikiDelete")
        _create_wiki(title, "delete test content")

        delete_result = run_redi("wiki", "delete", title, "-y")
        assert delete_result.returncode == 0, (
            f"stdout:\n{delete_result.stdout}\nstderr:\n{delete_result.stderr}"
        )

        view_result = run_redi("wiki", "view", title)
        assert view_result.returncode != 0, (
            f"削除後 view が成功してしまった\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert "Wiki page not found" in view_result.stdout, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
