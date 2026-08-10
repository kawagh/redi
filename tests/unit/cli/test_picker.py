import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from redi.cli.picker import inline_choice, inline_choice_with_action

OPTIONS = [("main", "main (default)"), ("sub", "sub")]


def _run(keys: str, **kwargs):
    """pipe input にキー列を流して inline_choice_with_action を実行する"""
    with create_pipe_input() as pipe:
        pipe.send_text(keys)
        with create_app_session(input=pipe, output=DummyOutput()):
            return inline_choice_with_action(
                "message", OPTIONS, action_keys={"u": "update"}, **kwargs
            )


class TestInlineChoiceWithAction:
    """inline_choice_with_action()は(アクション名, カーソル行の値)を返す"""

    def test_enter_returns_select(self):
        """Enterはアクション名"select"を返す"""
        assert _run("\r") == ("select", "main")

    def test_action_key_returns_action_name(self):
        """action_keysに指定したキーは対応するアクション名を返す"""
        assert _run("u") == ("update", "main")

    def test_action_key_uses_cursor_row(self):
        """アクションキーはカーソル移動後の行の値を返す"""
        assert _run("ju") == ("update", "sub")

    def test_starts_at_default(self):
        """defaultに指定した値の行からカーソルが始まる"""
        assert _run("u", default="sub") == ("update", "sub")

    def test_ctrl_c_raises_keyboard_interrupt(self):
        """Ctrl-CはKeyboardInterruptを送出する"""
        with pytest.raises(KeyboardInterrupt):
            _run("\x03")


class TestInlineChoice:
    """inline_choice()は従来どおり選択した値のみを返す"""

    def test_returns_value_only(self):
        """Enterで確定した値を文字列で返す"""
        with create_pipe_input() as pipe:
            pipe.send_text("j\r")
            with create_app_session(input=pipe, output=DummyOutput()):
                assert inline_choice("message", OPTIONS) == "sub"
