import pytest

from redi.cli import interactive, picker
from redi.i18n import messages


class TestEnsureInteractive:
    """ensure_interactive()は非TTY環境で対話に入る前に終了させる"""

    def test_passes_on_tty(self, tty_stdin):
        """TTYなら何もせず処理を続行する"""
        interactive.ensure_interactive("タイトル: ")

    def test_exits_on_non_tty(self, capsys):
        """非TTYならexit(1)する"""
        with pytest.raises(SystemExit) as exc:
            interactive.ensure_interactive("タイトル: ")
        assert exc.value.code == 1

    def test_shows_requested_input(self, capsys):
        """求めていた入力を末尾のコロンを落として表示する"""
        with pytest.raises(SystemExit):
            interactive.ensure_interactive("タイトル: ")
        err = capsys.readouterr().err
        assert messages.non_interactive_input_required.format(message="タイトル") in err


class TestPrompt:
    """prompt()は非TTYガード付きのprompt_toolkit.prompt"""

    def test_exits_on_non_tty(self):
        """非TTYならEOFErrorを送出せずexit(1)する"""
        with pytest.raises(SystemExit) as exc:
            interactive.prompt("タイトル: ")
        assert exc.value.code == 1


class TestPickerGuard:
    """inline_choice/inline_checkboxも非TTYなら対話に入らない"""

    def test_inline_choice_exits_on_non_tty(self, capsys):
        """inline_choice()は非TTYでexit(1)する"""
        with pytest.raises(SystemExit) as exc:
            picker.inline_choice("更新するニュースを選択", [("1", "1 news")])
        assert exc.value.code == 1
        assert "更新するニュースを選択" in capsys.readouterr().err

    def test_inline_checkbox_exits_on_non_tty(self, capsys):
        """inline_checkbox()は非TTYでexit(1)する"""
        with pytest.raises(SystemExit) as exc:
            picker.inline_checkbox("更新する項目を選択", [("title", "タイトル")])
        assert exc.value.code == 1
        assert "更新する項目を選択" in capsys.readouterr().err
