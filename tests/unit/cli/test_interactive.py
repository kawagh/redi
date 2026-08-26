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


class TestCanceledAsExit:
    """canceled_as_exit()はキャンセルを標準エラーに通知してexit(1)する"""

    @pytest.mark.parametrize("error", [KeyboardInterrupt, EOFError])
    def test_exits_on_cancel(self, error, capsys):
        """Ctrl-C/Ctrl-Dのどちらもexit(1)する"""
        with pytest.raises(SystemExit) as exc, interactive.canceled_as_exit():
            raise error
        assert exc.value.code == 1
        assert messages.canceled in capsys.readouterr().err

    def test_passes_through_without_cancel(self):
        """キャンセルされなければ何もしない"""
        with interactive.canceled_as_exit():
            pass

    def test_uses_given_notice(self, capsys):
        """notice を渡すと設定の言語ではなくそちらで通知する"""
        with pytest.raises(SystemExit), interactive.canceled_as_exit("中止しました"):
            raise KeyboardInterrupt
        assert "中止しました" in capsys.readouterr().err


class TestCanceledAsFlag:
    """canceled_as_flag()はキャンセルを標準出力に通知して呼び出し元へ戻す"""

    @pytest.mark.parametrize("error", [KeyboardInterrupt, EOFError])
    def test_raises_flag_on_cancel(self, error, capsys):
        """キャンセルを握りつぶしてフラグを立てる"""
        with interactive.canceled_as_flag() as canceled:
            raise error
        assert canceled
        assert messages.canceled in capsys.readouterr().out

    def test_flag_is_falsy_without_cancel(self, capsys):
        """キャンセルされなければフラグは立たず通知もしない"""
        with interactive.canceled_as_flag() as canceled:
            pass
        assert not canceled
        assert capsys.readouterr().out == ""
