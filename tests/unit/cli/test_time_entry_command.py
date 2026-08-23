import argparse

import pytest

from redi import config
from redi.cli import time_entry_command
from redi.cli.time_entry_command import add_time_entry_parser, handle_time_entry
from redi.i18n import messages


def parse_time_entry_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_time_entry_parser(parser.add_subparsers(dest="command"), [])
    return parser.parse_args(argv)


@pytest.fixture
def created(monkeypatch):
    """作成をスタブし、送信されたパラメータを記録する"""
    sent: dict = {}

    def _create(**kwargs):
        sent.update(kwargs)
        return {"id": 1, "hours": kwargs["hours"], "spent_on": "2026-01-01"}

    monkeypatch.setattr(
        time_entry_command.time_entry_service, "create_time_entry", _create
    )
    monkeypatch.setattr(config, "default_project_id", None)
    return sent


@pytest.fixture
def activities(monkeypatch):
    """作業分類の一覧取得をスタブする"""
    monkeypatch.setattr(
        time_entry_command,
        "fetch_time_entry_activities",
        lambda: [{"id": 8, "name": "設計"}, {"id": 9, "name": "開発"}],
    )


class TestTimeEntryCreateInteractiveFill:
    """`time_entry create` は引数で足りない必須項目を対話で補う"""

    def test_asks_activity_when_hours_given(
        self, created, activities, tty_stdin, monkeypatch
    ):
        """hours を引数で渡しても、未指定の作業分類は選ばせる

        Redmine は activity_id を必須とするため、聞かずに送ると英語のエラーで失敗する。
        """
        monkeypatch.setattr(time_entry_command, "inline_choice", lambda *a, **kw: "9")
        monkeypatch.setattr(time_entry_command, "prompt", lambda *a, **kw: "")

        handle_time_entry(
            parse_time_entry_args(
                ["time_entry", "create", "1.5", "--issue_id", "42", "-c", "検証"]
            )
        )

        assert created["hours"] == 1.5
        assert created["activity_id"] == "9"
        assert created["comments"] == "検証"

    def test_keeps_given_hours(self, created, activities, tty_stdin, monkeypatch):
        """対話に入っても、引数で渡した hours は聞き直さない"""
        monkeypatch.setattr(time_entry_command, "inline_choice", lambda *a, **kw: "9")
        asked: list[str] = []

        def _prompt(message, **kwargs):
            asked.append(message)
            return ""

        monkeypatch.setattr(time_entry_command, "prompt", _prompt)

        handle_time_entry(
            parse_time_entry_args(["time_entry", "create", "1.5", "--issue_id", "42"])
        )

        assert messages.prompt_hours not in asked
        assert created["hours"] == 1.5

    def test_skips_interaction_when_required_args_given(self, created, monkeypatch):
        """必須項目が揃っていれば対話に入らない

        エージェントやCIが引数だけで作成できるよう、任意項目は聞かない。
        """
        monkeypatch.setattr(
            time_entry_command,
            "prompt",
            lambda *a, **kw: pytest.fail("対話に入ってはいけない"),
        )

        handle_time_entry(
            parse_time_entry_args(
                ["time_entry", "create", "1.5", "-i", "42", "-a", "9"]
            )
        )

        assert created["activity_id"] == "9"
        assert created["spent_on"] is None

    def test_uses_default_project_as_target(self, created, activities, monkeypatch):
        """イシューもプロジェクトも未指定でも、設定の既定プロジェクトがあれば対象は揃っている"""
        monkeypatch.setattr(config, "default_project_id", "demo")
        monkeypatch.setattr(
            time_entry_command,
            "prompt",
            lambda *a, **kw: pytest.fail("対話に入ってはいけない"),
        )

        handle_time_entry(
            parse_time_entry_args(["time_entry", "create", "1.5", "-a", "9"])
        )

        assert created["project_id"] == "demo"


class TestTimeEntryCreateNonInteractive:
    """非TTY環境では何の入力が足りないかを示して終了する"""

    def test_exits_showing_activity_is_required(self, created, activities, capsys):
        """hours と issue_id だけ渡した場合、作業分類を求めて exit 1 する"""
        with pytest.raises(SystemExit) as exc:
            handle_time_entry(
                parse_time_entry_args(
                    ["time_entry", "create", "1.5", "--issue_id", "42"]
                )
            )

        assert exc.value.code == 1
        assert messages.prompt_select_activity in capsys.readouterr().out
        assert created == {}
