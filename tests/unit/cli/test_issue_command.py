import argparse
import json

import pytest

from redi import config
from redi.api.exceptions import ProjectNotFoundException
from redi.cli.issue_command import add_issue_parser
from redi.cli.issue_command import create as create_module
from redi.cli.issue_command import dispatch as dispatch_module
from redi.cli.issue_command import view as view_module
from redi.cli.issue_command.create import IssueCreateArgs, handle_issue_create
from redi.cli.issue_command.update import IssueUpdateArgs
from redi.i18n import messages

CREATED_ISSUE = {"id": 123, "subject": "件名"}


def parse_issue_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_issue_parser(parser.add_subparsers(dest="command"), [])
    return parser.parse_args(argv)


@pytest.fixture
def created_issue(monkeypatch):
    """作成をスタブし、Redmine の URL を固定する"""
    monkeypatch.setattr(
        create_module.issue_service, "create_issue", lambda **kwargs: CREATED_ISSUE
    )
    monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")


class TestIssueCreateOutput:
    """`issue create` の標準出力"""

    def test_prints_id_and_url(self, created_issue, capsys):
        """既定では作成した issue の id と URL を出す"""
        handle_issue_create(
            parse_issue_args(["issue", "create", "件名", "-p", "demo", "-d", "本文"])
        )

        out = capsys.readouterr().out
        assert "123" in out
        assert "http://localhost:3001/issues/123" in out

    def test_full_prints_json(self, created_issue, capsys):
        """--full では作成した issue の JSON だけを出す"""
        handle_issue_create(
            parse_issue_args(
                ["issue", "create", "件名", "-p", "demo", "-d", "本文", "--full"]
            )
        )

        assert json.loads(capsys.readouterr().out) == CREATED_ISSUE


class TestIssueUpdateArgsFromNamespace:
    def test_accepts_parser_output(self):
        """`issue update` のパース結果をそのまま受け取れる

        フィールド名が dest からずれていれば AttributeError で落ちる。
        `--to` と `--add-watcher` は明示的な dest 指定があり、特にずれやすい。
        """
        args = parse_issue_args(
            ["issue", "update", "42", "--to", "43", "--add-watcher", "7"]
        )

        update_args = IssueUpdateArgs.from_namespace(args)

        assert update_args.issue_id == "42"
        assert update_args.relate_to == "43"
        assert update_args.add_watcher_ids == [7]

    def test_accepts_project_id(self):
        """`--project_id` でイシューの移動先プロジェクトを受け取れる"""
        args = parse_issue_args(["issue", "update", "42", "--project_id", "demo"])

        update_args = IssueUpdateArgs.from_namespace(args)

        assert update_args.project_id == "demo"

    def test_short_option_is_not_assigned_to_project_id(self):
        """`-p` は `issue list` のフィルタなので、誤爆を避けて update では受け付けない"""
        with pytest.raises(SystemExit):
            parse_issue_args(["issue", "update", "42", "-p", "demo"])


class TestIssueCreateArgsFromNamespace:
    def test_accepts_parser_output(self):
        """`issue create` のパース結果をそのまま受け取れる

        フィールド名が dest からずれていれば AttributeError で落ちる。
        """
        args = parse_issue_args(["issue", "create", "題名", "-p", "demo"])

        create_args = IssueCreateArgs.from_namespace(args)

        assert create_args.subject == "題名"
        assert create_args.project_id == "demo"

    def test_accepts_full_flag(self):
        """`issue create --full` を受け取れる"""
        args = parse_issue_args(["issue", "create", "題名", "-p", "demo", "--full"])

        create_args = IssueCreateArgs.from_namespace(args)

        assert create_args.full is True


class TestIssueListNotFound:
    """`issue list` で存在しないプロジェクトを指定したとき"""

    def test_prints_guidance_and_exits(self, monkeypatch, capsys):
        """スタックトレースではなく案内を出して exit 1 する"""

        def _raise(**kwargs):
            raise ProjectNotFoundException("missing")

        monkeypatch.setattr(view_module.issue_service, "list_issues", _raise)

        with pytest.raises(SystemExit) as exc_info:
            view_module.list_issues(project_id="missing")

        assert exc_info.value.code == 1
        assert (
            messages.project_not_found.format(id="missing") in capsys.readouterr().out
        )


class TestIssueListQueryIdFilters:
    """`issue list` の `--query_id` と他フィルタの併用

    Redmine はカスタムクエリの条件を優先して他の条件を捨てるため、
    絞り込んだつもりで別の結果を見ないよう、渡させずに落とす。
    """

    @pytest.mark.parametrize(
        ("option", "value", "shown"),
        [
            ("-v", "3", "--version"),
            ("-a", "me", "--assigned_to"),
            ("-s", "closed", "--status_id"),
            ("-t", "1", "--tracker_id"),
            ("--priority_id", "2", "--priority_id"),
        ],
    )
    def test_ignored_filter_exits(self, option, value, shown, capsys):
        """無視されるフィルタ名を示して exit 1 する"""
        args = parse_issue_args(["issue", "list", "-q", "5", option, value])

        with pytest.raises(SystemExit) as exc_info:
            dispatch_module.handle_issue(args)

        assert exc_info.value.code == 1
        assert shown in capsys.readouterr().out

    def test_lists_all_ignored_filters(self, capsys):
        """複数指定した場合はすべての名前を示す"""
        args = parse_issue_args(["issue", "list", "-q", "5", "-s", "closed", "-t", "1"])

        with pytest.raises(SystemExit):
            dispatch_module.handle_issue(args)

        out = capsys.readouterr().out
        assert "--status_id" in out
        assert "--tracker_id" in out

    def test_project_id_is_allowed(self, monkeypatch):
        """`--project_id` は Redmine 側でも併用が効くので通す"""
        called = {}
        monkeypatch.setattr(
            view_module.issue_service,
            "list_issues",
            lambda **kwargs: called.update(kwargs) or [],
        )
        args = parse_issue_args(["issue", "list", "-q", "5", "-p", "demo"])

        dispatch_module.handle_issue(args)

        assert called["query_id"] == "5"
        assert called["project_id"] == "demo"
