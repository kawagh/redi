import pytest

from redi.cli import search_command


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
