import subprocess

import pytest


@pytest.mark.e2e
class TestProjectView:
    """`redi project view <id>` は指定したプロジェクトの情報を表示する"""

    def test_succeeds_for_existing_project_id(self):
        """init-redmine.sh で作成された id=1 のプロジェクト(reditest)を表示すると exit 0 で成功する"""
        result = subprocess.run(
            ["redi", "project", "view", "1"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "reditest" in result.stdout
