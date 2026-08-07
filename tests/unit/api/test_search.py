import pytest

from redi.api import search as search_module


class FakeResponse:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"results": []}


@pytest.fixture
def captured_params(monkeypatch) -> dict:
    """search が client.get に渡した params を捕捉する"""
    captured: dict = {}

    def fake_get(path: str, **kwargs) -> FakeResponse:
        captured["path"] = path
        captured["params"] = kwargs.get("params")
        return FakeResponse()

    monkeypatch.setattr(search_module.client, "get", fake_get)
    return captured


class TestSearchParams:
    """search は指定された条件だけをクエリパラメータに組み立てる"""

    def test_query_only(self, captured_params):
        """クエリのみ指定すると q だけを送る"""
        search_module.search("redi")

        assert captured_params["path"] == "/search.json"
        assert captured_params["params"] == {"q": "redi"}

    @pytest.mark.parametrize(
        ("kwargs", "expected"),
        [
            ({"limit": 10}, {"limit": 10}),
            ({"offset": 20}, {"offset": 20}),
            ({"scope": "my_projects"}, {"scope": "my_projects"}),
            ({"titles_only": True}, {"titles_only": "1"}),
            ({"open_issues": True}, {"open_issues": "1"}),
            ({"attachments": "only"}, {"attachments": "only"}),
        ],
        ids=[
            "limit",
            "offset",
            "scope",
            "titles_only",
            "open_issues",
            "attachments",
        ],
    )
    def test_optional_params(self, captured_params, kwargs, expected):
        """指定した条件が対応するパラメータとして送られる"""
        search_module.search("redi", **kwargs)

        assert captured_params["params"] == {"q": "redi", **expected}

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"limit": None},
            {"offset": None},
            {"scope": None},
            {"all_words": None},
            {"titles_only": False},
            {"open_issues": False},
            {"attachments": None},
            {"types": None},
            {"types": []},
        ],
        ids=[
            "limit",
            "offset",
            "scope",
            "all_words",
            "titles_only",
            "open_issues",
            "attachments",
            "types=None",
            "types=[]",
        ],
    )
    def test_unspecified_params_are_omitted(self, captured_params, kwargs):
        """未指定の条件はパラメータ自体を送らない"""
        search_module.search("redi", **kwargs)

        assert captured_params["params"] == {"q": "redi"}

    def test_all_words_false_sends_empty_value(self, captured_params):
        """all_words の無効化は空値で送る (Redmine は値の有無で真偽を判定する)"""
        search_module.search("redi", all_words=False)

        assert captured_params["params"] == {"q": "redi", "all_words": ""}

    def test_all_words_true_sends_flag(self, captured_params):
        """all_words の有効化は 1 で送る"""
        search_module.search("redi", all_words=True)

        assert captured_params["params"] == {"q": "redi", "all_words": "1"}

    def test_types_are_expanded_to_individual_params(self, captured_params):
        """種別は issues=1 のような個別パラメータへ展開される"""
        search_module.search("redi", types=["issues", "wiki_pages"])

        assert captured_params["params"] == {
            "q": "redi",
            "issues": "1",
            "wiki_pages": "1",
        }

    def test_all_params_combined(self, captured_params):
        """すべての条件を指定しても互いに上書きしない"""
        search_module.search(
            "redi",
            limit=10,
            offset=20,
            scope="my_projects",
            all_words=False,
            titles_only=True,
            open_issues=True,
            attachments="only",
            types=["issues", "wiki_pages"],
        )

        assert captured_params["params"] == {
            "q": "redi",
            "limit": 10,
            "offset": 20,
            "scope": "my_projects",
            "all_words": "",
            "titles_only": "1",
            "open_issues": "1",
            "attachments": "only",
            "issues": "1",
            "wiki_pages": "1",
        }
