import argparse

import pytest

from redi.cli import search_command
from redi.i18n import messages


def _search_args(**overrides) -> argparse.Namespace:
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
    return argparse.Namespace(**{**defaults, **overrides})


class TestSearchOutput:
    """検索結果は種別・タイトル・URL を 1 行で並べる"""

    def test_prints_results(self, monkeypatch, capsys):
        """結果があれば `[種別] タイトル URL` を出す"""
        monkeypatch.setattr(
            search_command,
            "search",
            lambda **kwargs: {
                "results": [
                    {
                        "type": "issue",
                        "title": "Bug #1: 落ちる",
                        "url": "http://localhost/issues/1",
                    }
                ]
            },
        )

        search_command.handle_search(_search_args())

        assert (
            capsys.readouterr().out
            == "[issue] Bug #1: 落ちる http://localhost/issues/1\n"
        )

    def test_prints_message_when_no_results(self, monkeypatch, capsys):
        """結果が無いときは 0 件と分かるメッセージを出す"""
        monkeypatch.setattr(search_command, "search", lambda **kwargs: {"results": []})

        search_command.handle_search(_search_args())

        assert capsys.readouterr().out == messages.no_search_results + "\n"


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
