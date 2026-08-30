import argparse

import pytest

from redi.cli import issue_template_command
from redi.i18n import messages


class TestHandleIssueTemplate:
    """issue_template はプラグインが入っている前提の機能である"""

    def test_exits_when_plugin_not_available(self, monkeypatch, capsys):
        """プラグイン未インストール (取得結果が None) は理由を示して終了する"""
        monkeypatch.setattr(
            issue_template_command,
            "fetch_issue_templates",
            lambda project_id, tracker_id=None: None,
        )

        with pytest.raises(SystemExit) as e:
            issue_template_command.handle_issue_template(
                argparse.Namespace(project_id="reditest", tracker_id=None, full=False)
            )

        assert e.value.code == 1
        assert messages.issue_template_not_available in capsys.readouterr().err

    def test_prints_templates_by_section(self, monkeypatch, capsys):
        """テンプレートは種別を見出しにして `{id} {title}` で並べる"""
        monkeypatch.setattr(
            issue_template_command,
            "fetch_issue_templates",
            lambda project_id, tracker_id=None: {
                "issue_templates": [{"id": 1, "title": "バグ報告"}],
                "inherit_templates": [],
                "global_issue_templates": [{"id": 2, "title": "共通"}],
            },
        )

        issue_template_command.handle_issue_template(
            argparse.Namespace(project_id="reditest", tracker_id=None, full=False)
        )

        assert capsys.readouterr().out == (
            "# issue_templates\n1 バグ報告\n# global_issue_templates\n2 共通\n"
        )
