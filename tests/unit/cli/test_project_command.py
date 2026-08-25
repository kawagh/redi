import argparse

import pytest

from redi.api.exceptions import (
    ProjectNotFoundException,
    ProjectPermissionDeniedException,
)
from redi.cli import project_command
from redi.cli.project_command import add_project_parser, handle_project
from redi.i18n import messages

CREATED_PROJECT = {"id": 7, "name": "新プロジェクト", "identifier": "new-project"}


def parse_project_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_project_parser(parser.add_subparsers(dest="command"), [])
    return parser.parse_args(argv)


@pytest.fixture
def updated_project(monkeypatch):
    """更新をスタブし、service に渡された引数を記録する。

    Redmine に値が正しく届くかは E2E (`tests/e2e/test_project_cli.py`) で見る。
    """

    calls: list[dict] = []

    def fake_update_project(project_id, **kwargs):
        calls.append({"project_id": project_id, **kwargs})

    monkeypatch.setattr(
        project_command.project_service, "update_project", fake_update_project
    )
    return calls


@pytest.fixture
def created_project(monkeypatch):
    """作成をスタブし、service に渡された引数を記録する。

    Redmine に値が正しく届くかは E2E (`tests/e2e/test_project_cli.py`) で見る。
    """

    calls: list[dict] = []

    def fake_create_project(**kwargs):
        calls.append(kwargs)
        return CREATED_PROJECT

    monkeypatch.setattr(
        project_command.project_service, "create_project", fake_create_project
    )
    return calls


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


class TestCreate:
    """`project create` は引数が足りなければ対話で補う"""

    def test_arguments_only_skips_interaction(self, created_project, capsys):
        """name と identifier が揃っていれば対話に入らず作成する"""
        handle_project(
            parse_project_args(["project", "create", "新プロジェクト", "new-project"])
        )

        assert created_project == [
            {
                "name": "新プロジェクト",
                "identifier": "new-project",
                "description": None,
                "homepage": None,
                "is_public": None,
                "parent_id": None,
                "inherit_members": None,
                "tracker_ids": None,
                "enabled_module_names": None,
                "issue_custom_field_ids": None,
            }
        ]
        assert "7 新プロジェクト (new-project)" in capsys.readouterr().out

    def test_options_are_passed(self, created_project):
        """--is_public と --tracker_ids は送信できる形に変換して渡す"""
        handle_project(
            parse_project_args(
                [
                    "project",
                    "create",
                    "新プロジェクト",
                    "new-project",
                    "--is_public",
                    "false",
                    "--tracker_ids",
                    "1,2",
                ]
            )
        )

        assert created_project[0]["is_public"] is False
        assert created_project[0]["tracker_ids"] == [1, 2]

    def test_additional_fields_are_passed(self, created_project):
        """homepage / inherit_members / モジュール / カスタムフィールドも送信できる形で渡す"""
        handle_project(
            parse_project_args(
                [
                    "project",
                    "create",
                    "新プロジェクト",
                    "new-project",
                    "--homepage",
                    "https://example.com",
                    "--inherit_members",
                    "true",
                    "--enabled_module_names",
                    "issue_tracking,wiki",
                    "--issue_custom_field_ids",
                    "1,2",
                ]
            )
        )

        assert created_project[0]["homepage"] == "https://example.com"
        assert created_project[0]["inherit_members"] is True
        assert created_project[0]["enabled_module_names"] == ["issue_tracking", "wiki"]
        assert created_project[0]["issue_custom_field_ids"] == [1, 2]

    @pytest.mark.parametrize(
        "option", ["--default_assigned_to_id", "--default_version_id"]
    )
    def test_create_has_no_default_fields(self, option):
        """create には既定の担当者・バージョンを用意しない

        作成時点ではそのプロジェクトのメンバーもバージョンもまだ無い。
        存在しないIDを渡しても Redmine は 201 を返してそのまま保存するため、
        指定できるのは update だけにする。
        """
        with pytest.raises(SystemExit):
            parse_project_args(
                ["project", "create", "新プロジェクト", "new-project", option, "3"]
            )

    def test_empty_enabled_module_names_disables_all(self, created_project):
        """--enabled_module_names "" は空リストとして渡し、全モジュールの無効化を表す"""
        handle_project(
            parse_project_args(
                [
                    "project",
                    "create",
                    "新プロジェクト",
                    "new-project",
                    "--enabled_module_names",
                    "",
                ]
            )
        )

        assert created_project[0]["enabled_module_names"] == []

    def test_missing_identifier_is_prompted(
        self, created_project, tty_stdin, monkeypatch
    ):
        """identifier だけ足りない場合は identifier のみ聞き直す"""
        asked: list[str] = []

        def fake_prompt(message, **kwargs):
            asked.append(message)
            return "new-project"

        monkeypatch.setattr(project_command, "prompt", fake_prompt)
        monkeypatch.setattr(project_command, "inline_choice", lambda *_, **__: "submit")

        handle_project(parse_project_args(["project", "create", "新プロジェクト"]))

        assert asked == [messages.prompt_project_identifier]
        assert created_project[0]["identifier"] == "new-project"

    def test_optional_items_are_filled(self, created_project, tty_stdin, monkeypatch):
        """アクションメニューで任意項目を選ぶと、その値を添えて作成する"""
        actions = iter(["optional", "submit"])
        monkeypatch.setattr(project_command, "prompt", lambda *_, **__: "new-project")
        monkeypatch.setattr(
            project_command, "inline_choice", lambda *_, **__: next(actions)
        )
        monkeypatch.setattr(
            project_command, "inline_checkbox", lambda *_, **__: ["tracker_ids"]
        )
        monkeypatch.setattr(
            project_command, "_interactive_select_tracker_ids", lambda _current: "3"
        )

        handle_project(parse_project_args(["project", "create", "新プロジェクト"]))

        assert created_project[0]["tracker_ids"] == [3]

    def test_optional_inherit_members_is_filled(
        self, created_project, tty_stdin, monkeypatch
    ):
        """任意項目で inherit_members を選ぶと bool に変換して作成する"""
        choices = iter(["optional", "true", "submit"])
        monkeypatch.setattr(project_command, "prompt", lambda *_, **__: "new-project")
        monkeypatch.setattr(
            project_command, "inline_choice", lambda *_, **__: next(choices)
        )
        monkeypatch.setattr(
            project_command, "inline_checkbox", lambda *_, **__: ["inherit_members"]
        )

        handle_project(parse_project_args(["project", "create", "新プロジェクト"]))

        assert created_project[0]["inherit_members"] is True

    def test_optional_enabled_module_names_is_filled(
        self, created_project, tty_stdin, monkeypatch
    ):
        """任意項目でモジュールを選ぶとカンマ区切りをリストに変換して作成する"""
        choices = iter(["optional", "submit"])
        monkeypatch.setattr(project_command, "prompt", lambda *_, **__: "new-project")
        monkeypatch.setattr(
            project_command, "inline_choice", lambda *_, **__: next(choices)
        )
        checkbox_results = iter([["enabled_module_names"], ["issue_tracking", "wiki"]])
        monkeypatch.setattr(
            project_command, "inline_checkbox", lambda *_, **__: next(checkbox_results)
        )

        handle_project(parse_project_args(["project", "create", "新プロジェクト"]))

        assert created_project[0]["enabled_module_names"] == ["issue_tracking", "wiki"]

    def test_optional_issue_custom_field_ids_is_filled(
        self, created_project, tty_stdin, monkeypatch
    ):
        """任意項目でカスタムフィールドを選ぶと id のリストに変換して作成する"""
        monkeypatch.setattr(
            project_command,
            "fetch_custom_fields",
            lambda *_, **__: [
                {"id": 1, "name": "限定メモ", "customized_type": "issue"},
                {
                    "id": 2,
                    "name": "全体メモ",
                    "customized_type": "issue",
                    "is_for_all": True,
                },
                {"id": 3, "name": "工数メモ", "customized_type": "time_entry"},
            ],
        )
        choices = iter(["optional", "submit"])
        monkeypatch.setattr(project_command, "prompt", lambda *_, **__: "new-project")
        monkeypatch.setattr(
            project_command, "inline_choice", lambda *_, **__: next(choices)
        )
        offered: list[list[tuple[str, str]]] = []

        def fake_checkbox(_message, options, **__):
            offered.append(options)
            return ["issue_custom_field_ids"] if len(offered) == 1 else ["1"]

        monkeypatch.setattr(project_command, "inline_checkbox", fake_checkbox)

        handle_project(parse_project_args(["project", "create", "新プロジェクト"]))

        # 全プロジェクト適用 (is_for_all) とイシュー以外は選択肢に出さない
        assert offered[1] == [("1", "1 限定メモ")]
        assert created_project[0]["issue_custom_field_ids"] == [1]

    def test_optional_issue_custom_field_ids_is_hidden_without_admin(
        self, created_project, tty_stdin, monkeypatch
    ):
        """一覧を取得できなければ、任意項目の選択肢にカスタムフィールドを出さない

        取得には管理者権限が要る。キャッシュも無い場合は選ばせようがないため、
        選んでから失敗させるのではなく最初から出さない。
        """
        monkeypatch.setattr(
            project_command, "fetch_custom_fields", lambda *_, **__: None
        )
        choices = iter(["optional", "submit"])
        monkeypatch.setattr(project_command, "prompt", lambda *_, **__: "new-project")
        monkeypatch.setattr(
            project_command, "inline_choice", lambda *_, **__: next(choices)
        )
        offered: list[list[tuple[str, str]]] = []

        def fake_checkbox(_message, options, **__):
            offered.append(options)
            return []

        monkeypatch.setattr(project_command, "inline_checkbox", fake_checkbox)

        handle_project(parse_project_args(["project", "create", "新プロジェクト"]))

        assert "issue_custom_field_ids" not in [value for value, _ in offered[0]]
        assert created_project[0]["issue_custom_field_ids"] is None

    def test_module_choices_are_redmine_standard_modules(self):
        """対話の選択肢は Redmine 標準のモジュール名を出す"""
        assert project_command.project_service.MODULE_NAME_CHOICES == [
            "boards",
            "calendar",
            "documents",
            "files",
            "gantt",
            "issue_tracking",
            "news",
            "repository",
            "time_tracking",
            "wiki",
        ]

    def test_non_interactive_names_missing_input(self, capsys):
        """非TTY環境では対話に入らず、求めた入力を示して exit 1 する"""
        with pytest.raises(SystemExit) as e:
            handle_project(parse_project_args(["project", "create"]))

        assert e.value.code == 1
        assert (
            messages.non_interactive_input_required.format(
                message=messages.prompt_project_name.strip().rstrip(":").strip()
            )
            in capsys.readouterr().out
        )


class TestUpdate:
    """`project update` は create と同じフィールドを更新できる"""

    def test_additional_fields_are_passed(self, updated_project):
        """homepage / inherit_members / モジュール / カスタムフィールドを送信できる形で渡す"""
        handle_project(
            parse_project_args(
                [
                    "project",
                    "update",
                    "7",
                    "--homepage",
                    "https://example.com",
                    "--inherit_members",
                    "false",
                    "--enabled_module_names",
                    "issue_tracking,wiki",
                    "--issue_custom_field_ids",
                    "1,2",
                ]
            )
        )

        assert updated_project == [
            {
                "project_id": "7",
                "name": None,
                "description": None,
                "homepage": "https://example.com",
                "is_public": None,
                "parent_id": None,
                "inherit_members": False,
                "tracker_ids": None,
                "enabled_module_names": ["issue_tracking", "wiki"],
                "issue_custom_field_ids": [1, 2],
                "default_assigned_to_id": None,
                "default_version_id": None,
            }
        ]

    @pytest.mark.parametrize(
        ("option", "value"),
        [
            ("--homepage", "https://example.com"),
            ("--inherit_members", "true"),
            ("--enabled_module_names", "wiki"),
            ("--issue_custom_field_ids", "1"),
            ("--default_assigned_to_id", "3"),
            ("--default_version_id", "5"),
        ],
    )
    def test_single_option_triggers_update(self, updated_project, option, value):
        """新しく足したオプションだけを指定しても「更新なし」で終わらせない"""
        handle_project(parse_project_args(["project", "update", "7", option, value]))

        assert len(updated_project) == 1

    def test_default_fields_are_passed(self, updated_project):
        """--default_assigned_to_id / --default_version_id をそのまま渡す"""
        handle_project(
            parse_project_args(
                [
                    "project",
                    "update",
                    "7",
                    "--default_assigned_to_id",
                    "3",
                    "--default_version_id",
                    "5",
                ]
            )
        )

        assert updated_project[0]["default_assigned_to_id"] == "3"
        assert updated_project[0]["default_version_id"] == "5"

    def test_empty_default_fields_unset_them(self, updated_project):
        """空文字の指定は解除として送る (Redmine は空文字を受けて null にする)"""
        handle_project(
            parse_project_args(
                [
                    "project",
                    "update",
                    "7",
                    "--default_assigned_to_id",
                    "",
                    "--default_version_id",
                    "",
                ]
            )
        )

        assert updated_project[0]["default_assigned_to_id"] == ""
        assert updated_project[0]["default_version_id"] == ""

    def test_no_option_cancels(self, updated_project, capsys):
        """更新するフィールドが1つも無ければ何も送らずに終わる"""
        with pytest.raises(SystemExit):
            handle_project(parse_project_args(["project", "update", "7"]))

        assert updated_project == []
        assert messages.update_canceled in capsys.readouterr().out
