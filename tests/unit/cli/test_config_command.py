import argparse

import pytest

from redi.cli import config_command
from redi.i18n import messages


def _update_args() -> argparse.Namespace:
    """`redi config update` を引数なしで実行したときの Namespace"""
    return argparse.Namespace(
        config_command="update",
        full=False,
        profile_name=None,
        project_id=None,
        wiki_project_id=None,
        editor=None,
        language=None,
        api_key=None,
        url=None,
        default_profile=None,
    )


@pytest.fixture
def profiles(monkeypatch):
    """main(default) と sub の2プロファイルが登録された状態にする"""
    monkeypatch.setattr(config_command, "list_profile_names", lambda: ["main", "sub"])
    monkeypatch.setattr(config_command, "get_default_profile", lambda: "main")


@pytest.fixture
def recorded_updates(monkeypatch):
    """update_config() の呼び出しを記録し、実ファイル書き込みを防ぐ"""
    calls: list[tuple[str, str, str | None]] = []
    monkeypatch.setattr(
        config_command,
        "update_config",
        lambda key, value, profile=None: calls.append((key, value, profile)),
    )
    return calls


def _select(action: str, value: str):
    """inline_choice_with_action の差し替え用 fake"""

    def fake(_message, _options, default=None, action_keys=None):
        return action, value

    return fake


class TestSelectDefaultProfile:
    """一覧でEnterを押すとカーソル行をdefault_profileに設定する"""

    def test_sets_default_profile(
        self, monkeypatch, capsys, profiles, recorded_updates
    ):
        """Enter(select)ではset_default_profile()のみ呼ばれ項目更新は走らない"""
        monkeypatch.setattr(
            config_command, "inline_choice_with_action", _select("select", "sub")
        )
        set_calls: list[str] = []
        monkeypatch.setattr(
            config_command,
            "set_default_profile",
            lambda name: (set_calls.append(name), True)[1],
        )

        config_command.handle_config(_update_args())

        assert set_calls == ["sub"]
        assert recorded_updates == []
        assert (
            messages.default_profile_set.format(name="sub") in capsys.readouterr().out
        )

    def test_exits_when_no_profiles(self, monkeypatch, capsys):
        """プロファイルが1つも無ければ案内を出してexit 1する"""
        monkeypatch.setattr(config_command, "list_profile_names", list)

        with pytest.raises(SystemExit) as exc:
            config_command.handle_config(_update_args())

        assert exc.value.code == 1
        assert messages.no_profiles_available in capsys.readouterr().out

    def test_keyboard_interrupt_cancels(self, monkeypatch, capsys, profiles):
        """一覧でCtrl-Cを押すとキャンセルしてexit 1する"""

        def raise_interrupt(_message, _options, default=None, action_keys=None):
            raise KeyboardInterrupt

        monkeypatch.setattr(
            config_command, "inline_choice_with_action", raise_interrupt
        )

        with pytest.raises(SystemExit) as exc:
            config_command.handle_config(_update_args())

        assert exc.value.code == 1
        assert messages.canceled in capsys.readouterr().out

    def test_passes_update_action_key(self, monkeypatch, profiles):
        """一覧のピッカーには u を更新アクションとして渡す"""
        captured: dict[str, object] = {}

        def capture(message, options, default=None, action_keys=None):
            captured["message"] = message
            captured["options"] = options
            captured["default"] = default
            captured["action_keys"] = action_keys
            return "select", "main"

        monkeypatch.setattr(config_command, "inline_choice_with_action", capture)
        monkeypatch.setattr(config_command, "set_default_profile", lambda _name: True)

        config_command.handle_config(_update_args())

        assert captured["message"] == messages.prompt_select_profile
        assert captured["action_keys"] == {"u": "update"}
        assert captured["default"] == "main"
        assert captured["options"] == [("main", "main (default)"), ("sub", "sub")]


class TestUpdateProfileFields:
    """一覧でuを押すとカーソル行のプロファイルの項目を更新する"""

    def test_updates_checked_items(
        self, monkeypatch, capsys, profiles, recorded_updates
    ):
        """チェックした項目だけが選択したプロファイルに対して更新される"""
        monkeypatch.setattr(
            config_command, "inline_choice_with_action", _select("update", "sub")
        )
        monkeypatch.setattr(
            config_command, "read_profile_values", lambda _profile: {"editor": "vim"}
        )
        monkeypatch.setattr(
            config_command,
            "inline_checkbox",
            lambda _message, _values: ["editor", "project_id"],
        )
        monkeypatch.setattr(
            config_command,
            "prompt",
            lambda _message, default="", validator=None, is_password=False: {
                messages.prompt_editor: "nvim",
                messages.prompt_default_project_id: "42",
            }[_message],
        )

        config_command.handle_config(_update_args())

        assert recorded_updates == [
            ("default_project_id", "42", "sub"),
            ("editor", "nvim", "sub"),
        ]
        out = capsys.readouterr().out
        assert messages.field_editor in out
        assert "nvim" in out

    def test_prefills_current_values(self, monkeypatch, profiles, recorded_updates):
        """入力プロンプトの初期値には現在の設定値が入る"""
        monkeypatch.setattr(
            config_command, "inline_choice_with_action", _select("update", "main")
        )
        monkeypatch.setattr(
            config_command,
            "read_profile_values",
            lambda _profile: {"redmine_url": "https://old.example.com"},
        )
        monkeypatch.setattr(
            config_command, "inline_checkbox", lambda _message, _values: ["url"]
        )
        captured: dict[str, str] = {}

        def capture(message, default="", validator=None, is_password=False):
            captured[message] = default
            return "https://new.example.com"

        monkeypatch.setattr(config_command, "prompt", capture)

        config_command.handle_config(_update_args())

        assert captured[messages.prompt_redmine_url] == "https://old.example.com"
        assert recorded_updates == [("redmine_url", "https://new.example.com", "main")]

    def test_selects_language_from_supported(
        self, monkeypatch, profiles, recorded_updates
    ):
        """languageはSUPPORTED_LANGUAGESからの選択で更新する"""
        monkeypatch.setattr(
            config_command, "inline_choice_with_action", _select("update", "main")
        )
        monkeypatch.setattr(
            config_command, "read_profile_values", lambda _profile: {"language": "en"}
        )
        monkeypatch.setattr(
            config_command, "inline_checkbox", lambda _message, _values: ["language"]
        )
        captured: dict[str, object] = {}

        def capture_choice(message, options, default=None):
            captured["options"] = options
            captured["default"] = default
            return "ja"

        monkeypatch.setattr(config_command, "inline_choice", capture_choice)

        config_command.handle_config(_update_args())

        assert captured["options"] == [("en", "en"), ("ja", "ja")]
        assert captured["default"] == "en"
        assert recorded_updates == [("language", "ja", "main")]

    def test_no_items_selected_cancels(
        self, monkeypatch, capsys, profiles, recorded_updates
    ):
        """何もチェックせずEnterした場合は何も更新しない"""
        monkeypatch.setattr(
            config_command, "inline_choice_with_action", _select("update", "main")
        )
        monkeypatch.setattr(config_command, "read_profile_values", lambda _profile: {})
        monkeypatch.setattr(
            config_command, "inline_checkbox", lambda _message, _values: []
        )

        config_command.handle_config(_update_args())

        assert recorded_updates == []
        assert messages.canceled_no_items_selected in capsys.readouterr().out

    def test_keyboard_interrupt_on_checkbox_cancels(
        self, monkeypatch, capsys, profiles, recorded_updates
    ):
        """項目選択中のCtrl-Cは何も更新せずキャンセルする"""
        monkeypatch.setattr(
            config_command, "inline_choice_with_action", _select("update", "main")
        )
        monkeypatch.setattr(config_command, "read_profile_values", lambda _profile: {})

        def raise_interrupt(_message, _values):
            raise KeyboardInterrupt

        monkeypatch.setattr(config_command, "inline_checkbox", raise_interrupt)

        config_command.handle_config(_update_args())

        assert recorded_updates == []
        assert messages.canceled in capsys.readouterr().out

    def test_keyboard_interrupt_on_prompt_cancels(
        self, monkeypatch, capsys, profiles, recorded_updates
    ):
        """値入力中のCtrl-Cは何も更新せずキャンセルする"""
        monkeypatch.setattr(
            config_command, "inline_choice_with_action", _select("update", "main")
        )
        monkeypatch.setattr(config_command, "read_profile_values", lambda _profile: {})
        monkeypatch.setattr(
            config_command, "inline_checkbox", lambda _message, _values: ["editor"]
        )

        def raise_interrupt(_message, default="", validator=None, is_password=False):
            raise KeyboardInterrupt

        monkeypatch.setattr(config_command, "prompt", raise_interrupt)

        config_command.handle_config(_update_args())

        assert recorded_updates == []
        assert messages.canceled in capsys.readouterr().out
