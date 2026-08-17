import pytest

from redi.cli import role_command
from redi.i18n import messages


class TestPrintRole:
    """role view は権限を含めて表示する"""

    def test_exits_when_not_found(self, monkeypatch, capsys):
        """存在しないロール (取得結果が None) は理由を示して終了する"""
        monkeypatch.setattr(role_command, "fetch_role", lambda role_id: None)

        with pytest.raises(SystemExit) as e:
            role_command._print_role("999", full=False)

        assert e.value.code == 1
        assert messages.role_not_found.format(id="999") in capsys.readouterr().out

    def test_prints_permissions(self, monkeypatch, capsys):
        """permissions は 1 行ずつインデントして並べる"""
        monkeypatch.setattr(
            role_command,
            "fetch_role",
            lambda role_id: {
                "id": 3,
                "name": "Manager",
                "permissions": ["add_issues", "edit_issues"],
            },
        )

        role_command._print_role("3", full=False)

        out = capsys.readouterr().out
        assert out.startswith("3 Manager\n")
        assert "  add_issues\n  edit_issues" in out
