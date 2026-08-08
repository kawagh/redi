import argparse

import pytest

from redi.cli import search_command


def _args(**overrides) -> argparse.Namespace:
    """handle_search が参照する属性を埋めた Namespace を作る"""
    defaults = {
        "query": "redi",
        "limit": None,
        "offset": None,
        "project_id": None,
        "scope": None,
        "all_words": True,
        "titles_only": False,
        "open_issues": False,
        "attachments": None,
        "type": None,
        "full": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


@pytest.fixture
def captured_search(monkeypatch) -> dict:
    """handle_search が search に渡した引数を捕捉する"""
    captured: dict = {}

    def fake_search(**kwargs) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(search_command, "search", fake_search)
    return captured


class TestValidateScope:
    """--scope と --project_id の矛盾する組み合わせを弾く"""

    @pytest.mark.parametrize("scope", ["all", "my_projects", "bookmarks"])
    def test_rejects_project_id(self, scope, capsys):
        """subprojects 以外の scope に --project_id を付けるとエラーになる"""
        with pytest.raises(SystemExit) as e:
            search_command._validate_scope(scope, "reditest")

        assert e.value.code == 1
        assert scope in capsys.readouterr().out

    def test_subprojects_requires_project_id(self, capsys):
        """subprojects に --project_id がないとエラーになる"""
        with pytest.raises(SystemExit) as e:
            search_command._validate_scope("subprojects", None)

        assert e.value.code == 1
        assert "subprojects" in capsys.readouterr().out

    @pytest.mark.parametrize(
        ("scope", "project_id"),
        [
            (None, None),
            (None, "reditest"),
            ("all", None),
            ("my_projects", None),
            ("bookmarks", None),
            ("subprojects", "reditest"),
        ],
        ids=[
            "scope_none",
            "project_id_only",
            "all",
            "my_projects",
            "bookmarks",
            "subprojects_with_project_id",
        ],
    )
    def test_accepts_valid_combinations(self, scope, project_id):
        """矛盾しない組み合わせは素通しする"""
        search_command._validate_scope(scope, project_id)


class TestHandleSearch:
    """handle_search は検証を通してから search を呼ぶ"""

    def test_passes_valid_args(self, captured_search):
        """矛盾しない組み合わせは search にそのまま渡る"""
        search_command.handle_search(_args(scope="subprojects", project_id="reditest"))

        assert captured_search["scope"] == "subprojects"
        assert captured_search["project_id"] == "reditest"

    def test_stops_before_search(self, captured_search):
        """矛盾する組み合わせでは search を呼ばずに終了する"""
        with pytest.raises(SystemExit):
            search_command.handle_search(_args(scope="all", project_id="reditest"))

        assert captured_search == {}
