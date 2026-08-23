import json

import pytest

from tests.e2e.utils import requires_redmine_7_0, run_redi


@pytest.mark.e2e
@requires_redmine_7_0
class TestCustomFieldProjects:
    """`redi custom_field --full` は redmine 7.0 で拡張されたフィールドを含む"""

    def test_project_scoped_custom_field_has_projects(self):
        """プロジェクト限定のカスタムフィールドは is_for_all と適用先の projects を持つ"""
        custom_fields = json.loads(run_redi("custom_field", "--full").stdout)
        custom_field = next(
            cf for cf in custom_fields if cf["name"] == "プロジェクト限定メモ"
        )

        assert custom_field["is_for_all"] is False
        assert [p["name"] for p in custom_field["projects"]] == ["reditestプロジェクト"]


@pytest.mark.e2e
class TestCustomFieldView:
    """`redi custom_field view <id>` はカスタムフィールド 1 件の詳細を表示する"""

    def test_prints_detail_of_the_specified_custom_field(self):
        """一覧に載っている id を指定すると、その 1 件の詳細を出す"""
        custom_fields = json.loads(run_redi("custom_field", "--full").stdout)
        custom_field = next(cf for cf in custom_fields if cf["name"] == "バージョン")

        out = run_redi("custom_field", "view", str(custom_field["id"])).stdout

        assert out.startswith(f"{custom_field['id']} バージョン\n")
        assert "redi --version の出力" in out
        assert "issue" in out
        assert "string" in out
        assert "バグ" in out

    def test_full_prints_json_of_the_single_custom_field(self):
        """--full では該当する 1 件だけを JSON で出す"""
        custom_fields = json.loads(run_redi("custom_field", "--full").stdout)
        custom_field = next(cf for cf in custom_fields if cf["name"] == "バージョン")

        out = json.loads(
            run_redi("custom_field", "view", str(custom_field["id"]), "--full").stdout
        )

        assert out["id"] == custom_field["id"]
