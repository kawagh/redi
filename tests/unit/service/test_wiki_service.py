import pytest

from redi import config
from redi.service import wiki_service


@pytest.fixture
def stub_wiki_api(monkeypatch):
    """存在するページを差し替え、作成 PUT の呼び出しを記録する。

    fetch は与えたタイトル集合に含まれるかだけを見て WikiPage 相当を返す。
    """

    existing: set[str] = set()
    calls: list[dict] = []

    def fake_fetch_wiki(project_id, page_title, version=None, full=False):
        if page_title not in existing:
            return None
        return {"title": page_title, "version": 1}

    def fake_create_wiki_page(
        project_id, page_title, text, parent_title=None, comments=""
    ):
        calls.append({"page_title": page_title, "parent_title": parent_title})

    monkeypatch.setattr(wiki_service, "fetch_wiki", fake_fetch_wiki)
    monkeypatch.setattr(wiki_service, "create_wiki_page", fake_create_wiki_page)
    return existing, calls


class TestCreatePage:
    """create_page の作成手順"""

    def test_new_title_is_created(self, stub_wiki_api):
        """存在しないタイトルなら作成として返す"""
        _, calls = stub_wiki_api

        result = wiki_service.create_page("demo", "New", "本文")

        assert result == wiki_service.WikiCreateResult(title="New", created=True)
        assert calls == [{"page_title": "New", "parent_title": None}]

    def test_existing_title_is_update(self, stub_wiki_api):
        """既存タイトルへの作成は PUT が更新になるため created=False で返す"""
        existing, calls = stub_wiki_api
        existing.add("Existing")

        result = wiki_service.create_page("demo", "Existing", "本文")

        assert result.created is False
        assert calls == [{"page_title": "Existing", "parent_title": None}]

    def test_missing_parent_raises_without_put(self, stub_wiki_api):
        """親ページが存在しなければ PUT せず例外にする"""
        _, calls = stub_wiki_api

        with pytest.raises(wiki_service.ParentPageNotFoundException) as e:
            wiki_service.create_page("demo", "Child", "本文", parent_title="Parent")

        assert e.value.title == "Parent"
        assert calls == []

    def test_existing_parent_is_passed_through(self, stub_wiki_api):
        """親ページが存在すれば parent_title を渡して作成する"""
        existing, calls = stub_wiki_api
        existing.add("Parent")

        wiki_service.create_page("demo", "Child", "本文", parent_title="Parent")

        assert calls == [{"page_title": "Child", "parent_title": "Parent"}]


class TestPageUrl:
    """page_url が組み立てる URL"""

    @pytest.fixture(autouse=True)
    def redmine_url(self, monkeypatch):
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")

    def test_latest_version(self):
        """版を指定しなければ最新版の URL になる"""
        assert (
            wiki_service.page_url("demo", "Page")
            == "http://localhost:3001/projects/demo/wiki/Page"
        )

    def test_with_version(self):
        """版を指定するとその版の URL になる"""
        assert (
            wiki_service.page_url("demo", "Page", version=3)
            == "http://localhost:3001/projects/demo/wiki/Page/3"
        )
