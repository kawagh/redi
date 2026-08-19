import pytest

from redi.api.exceptions import (
    ProjectNotFoundException,
    ProjectPermissionDeniedException,
)
from redi.cli import project_command
from redi.i18n import messages


class TestView:
    """`project view` の失敗時のふるまい"""

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (
                ProjectNotFoundException("152"),
                messages.project_not_found.format(id="152"),
            ),
            (
                ProjectPermissionDeniedException("152"),
                messages.project_permission_denied.format(id="152"),
            ),
        ],
        ids=["not_found", "permission_denied"],
    )
    def test_exits_with_reason(self, monkeypatch, capsys, error, expected):
        """存在しない・アーカイブ済みや権限不足で参照できない場合は理由を出して exit 1 する"""

        def fake_read_project(project_id, include=""):
            raise error

        monkeypatch.setattr(
            project_command.project_service, "read_project", fake_read_project
        )

        with pytest.raises(SystemExit) as e:
            project_command._view_project("152")

        assert e.value.code == 1
        assert expected in capsys.readouterr().out
