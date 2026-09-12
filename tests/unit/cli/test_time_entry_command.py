import argparse

import pytest

from redi import config
from redi.api.exceptions import ProjectNotFoundException
from redi.cli import time_entry_command
from redi.cli.shared_options import OutputFormat
from redi.cli.time_entry_command import add_time_entry_parser, handle_time_entry
from redi.i18n import messages


def parse_time_entry_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_time_entry_parser(parser.add_subparsers(dest="command"), [])
    return parser.parse_args(argv)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    add_time_entry_parser(subparsers, [])
    return parser


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
        assert messages.prompt_select_activity in capsys.readouterr().err
        assert created == {}


class TestDateFilterOption:
    """`--from` / `--to` は実在する YYYY-MM-DD だけを受け付ける"""

    @pytest.mark.parametrize(
        "argv",
        [
            ["time_entry", "--from", "2026-07-01", "list"],
            ["time_entry", "list", "--from", "2026-07-01"],
        ],
    )
    def test_valid_date_is_accepted(self, argv: list[str]):
        """有効な日付は前置・後置のどちらでも from_date に入る"""
        args = _parser().parse_args(argv)

        assert args.from_date == "2026-07-01"

    def test_surrounding_whitespace_is_stripped(self):
        """前後の空白は取り除いて渡す"""
        args = _parser().parse_args(["time_entry", "--to", " 2026-07-01 ", "list"])

        assert args.to_date == "2026-07-01"

    @pytest.mark.parametrize(
        "argv",
        [
            ["time_entry", "--from", "abc", "list"],
            ["time_entry", "--to", "2026-99-99", "list"],
            ["time_entry", "--from", "2026/07/01", "list"],
            ["time_entry", "--from", "20260701", "list"],
            ["time_entry", "list", "--from", "abc"],
            ["time_entry", "list", "--to", "2026-99-99"],
        ],
    )
    def test_invalid_date_exits_with_usage_error(self, argv: list[str]):
        """不正な日付は全件を返さず、argparse の使用方法エラー(終了コード2)で落とす"""
        with pytest.raises(SystemExit) as e:
            _parser().parse_args(argv)

        assert e.value.code == 2


class TestTimeEntryListTsv:
    """`time_entry list --format tsv` は既存列の後ろに activity_id と作成・更新日時を並べる"""

    def test_prints_activity_id_and_timestamps(self, monkeypatch, capsys):
        """activity は activity_name しか無かったので activity_id を揃える"""
        monkeypatch.setattr(
            time_entry_command.time_entry_service,
            "fetch_page",
            lambda **kwargs: {
                "time_entries": [
                    {
                        "id": 9,
                        "spent_on": "2026-09-01",
                        "user": {"id": 5, "name": "kawagh"},
                        "hours": 1.5,
                        "activity": {"id": 8, "name": "開発"},
                        "issue": {"id": 12},
                        "project": {"id": 3, "name": "redi"},
                        "comments": "調査",
                        "created_on": "2026-09-01T01:00:00Z",
                        "updated_on": "2026-09-01T02:00:00Z",
                    }
                ]
            },
        )

        time_entry_command._list_time_entries(fmt=OutputFormat.TSV)

        assert capsys.readouterr().out == (
            "id\tspent_on\tuser_id\tuser_name\thours\tactivity_name\tissue_id"
            "\tproject_id\tproject_name\tcomments\tactivity_id\tcreated_on\tupdated_on\n"
            "9\t2026-09-01\t5\tkawagh\t1.5\t開発\t12\t3\tredi\t調査\t8"
            "\t2026-09-01T01:00:00Z\t2026-09-01T02:00:00Z\n"
        )


class TestTimeEntryListProjectNotFound:
    """`time_entry list` は存在しないプロジェクトを指定すると ID 付きのメッセージで exit 1 する"""

    def test_exits_with_project_id(self, monkeypatch, capsys):
        """create / update と同じく、生の 404 ではなく何が見つからなかったかを出す"""

        def fake_fetch_page(**kwargs):
            raise ProjectNotFoundException(kwargs["project_id"])

        monkeypatch.setattr(
            time_entry_command.time_entry_service, "fetch_page", fake_fetch_page
        )

        with pytest.raises(SystemExit) as e:
            time_entry_command._list_time_entries(project_id="nosuchproject")

        assert e.value.code == 1
        assert (
            messages.project_not_found.format(id="nosuchproject")
            in capsys.readouterr().err
        )
