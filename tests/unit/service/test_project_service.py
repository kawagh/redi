from types import SimpleNamespace
from typing import cast

import pytest

from redi.api.exceptions import ProjectNotFoundException
from redi.api.project import Project
from redi.service import project_service

PROJECTS = cast(
    list[Project],
    [
        {"id": 1, "name": "Alpha", "identifier": "alpha"},
        {"id": 2, "name": "Beta", "identifier": "beta"},
    ],
)


@pytest.fixture
def stub_project_api(monkeypatch):
    """プロジェクト一覧を `PROJECTS` で差し替え、取得の呼び出し回数を数える。"""

    state = SimpleNamespace(fetch_count=0)

    def fake_fetch_projects(**kwargs):
        state.fetch_count += 1
        return PROJECTS

    monkeypatch.setattr(
        project_service.project_api, "fetch_projects", fake_fetch_projects
    )
    return state


class TestResolveProjectId:
    """resolve_project_id は identifier や名前を数値 id に解決する"""

    def test_digit_is_returned_without_fetch(self, stub_project_api):
        """数値はプロジェクトを引かずにそのまま返す"""
        assert project_service.resolve_project_id("2") == "2"
        assert stub_project_api.fetch_count == 0

    def test_identifier_is_resolved(self, stub_project_api):
        """identifier は数値 id に解決する"""
        assert project_service.resolve_project_id("beta") == "2"

    def test_name_is_resolved(self, stub_project_api):
        """名前でも数値 id に解決する"""
        assert project_service.resolve_project_id("Alpha") == "1"

    def test_unknown_value_raises(self, stub_project_api):
        """一致するプロジェクトが無ければ例外にする(呼び出し元が表示を決める)"""
        with pytest.raises(ProjectNotFoundException) as e:
            project_service.resolve_project_id("gamma")

        assert e.value.project_id == "gamma"


class TestSortProjectsByIdDesc:
    """sort_projects_by_id_desc は新しいプロジェクトを先頭に並べる"""

    def test_sorted_by_id_desc(self):
        """id の降順に並べ替える"""
        sorted_projects = project_service.sort_projects_by_id_desc(PROJECTS)

        assert [p["id"] for p in sorted_projects] == [2, 1]


class TestSuggestIdentifier:
    """suggest_identifier はプロジェクト名から識別子の候補を作る"""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Alpha", "alpha"),
            ("My New Project", "my-new-project"),
            ("Redmine 6.1 / CLI", "redmine-6-1-cli"),
            ("--Edge--", "edge"),
        ],
        ids=["lowercase", "spaces", "symbols", "trim_hyphens"],
    )
    def test_builds_candidate(self, name: str, expected: str):
        """使えない文字はハイフンに寄せ、前後のハイフンは落とす"""
        assert project_service.suggest_identifier(name) == expected

    @pytest.mark.parametrize(
        ("name", "reason"),
        [("プロジェクト", "no_ascii"), ("2026", "digits_only"), ("", "empty")],
        ids=["no_ascii", "digits_only", "empty"],
    )
    def test_returns_empty_when_unusable(self, name: str, reason: str):
        """Redmine が受け付けない候補しか作れない場合は空文字を返す"""
        assert project_service.suggest_identifier(name) == ""

    def test_truncated_to_max_length(self):
        """識別子の最大長を超えないよう切り詰める"""
        candidate = project_service.suggest_identifier("a" * 150)

        assert len(candidate) == project_service.IDENTIFIER_MAX_LENGTH
