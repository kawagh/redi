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
