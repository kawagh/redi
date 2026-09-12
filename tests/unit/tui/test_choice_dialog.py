"""プロジェクト切替 / プロファイル切替が共有する選択肢ダイアログの単体テスト。"""

from prompt_toolkit.key_binding import KeyBindings

from redi.tui.choice_dialog import register_choice_keys, render_choice_list
from redi.tui.state import ChoiceDialogState


class TestRenderChoiceList:
    """render_choice_list() はカーソル行に > を、active な行に * を付ける"""

    def test_marks_cursor_and_active_rows(self):
        dialog = ChoiceDialogState(
            choices=[("2", "Beta"), ("1", "Alpha")], cursor=0, active_value="1"
        )

        rendered = "".join(text for _style, text in render_choice_list(dialog))

        assert " >   Beta" in rendered
        assert "   * Alpha" in rendered

    def test_no_mark_without_active(self):
        dialog = ChoiceDialogState(choices=[("1", "Alpha")])

        rendered = "".join(text for _style, text in render_choice_list(dialog))

        assert "*" not in rendered


def _handler(kb: KeyBindings, keys: tuple):
    """実際に呼ばれるハンドラを返す。

    prompt_toolkit は有効な binding のうち最後のものを呼ぶ。
    """
    active = [b for b in kb.get_bindings_for_keys(keys) if b.filter()]
    if not active:
        raise AssertionError(f"no active binding for {keys}")
    return active[-1].handler


class TestChoiceDialogKeys:
    """選択肢ダイアログは先頭 / 末尾へ一手で飛べる"""

    def _setup(self, labels: list[str]) -> tuple[KeyBindings, ChoiceDialogState]:
        dialog = ChoiceDialogState(
            show=True, choices=[(str(i), label) for i, label in enumerate(labels)]
        )
        kb = KeyBindings()
        register_choice_keys(kb, lambda: dialog, True, "P", lambda *_args: None)
        return kb, dialog

    def test_gg_moves_to_top(self):
        """gg で先頭へ飛ぶ(候補数ぶんの k 連打を避ける)"""
        kb, dialog = self._setup(["a", "b", "c"])
        dialog.cursor = 2

        _handler(kb, ("g", "g"))(None)

        assert dialog.cursor == 0

    def test_shift_g_moves_to_bottom(self):
        """G で末尾へ飛ぶ"""
        kb, dialog = self._setup(["a", "b", "c"])

        _handler(kb, ("G",))(None)

        assert dialog.cursor == 2

    def test_shift_g_keeps_cursor_at_zero_without_choices(self):
        """候補が無いときの G はカーソルを負にしない"""
        kb, dialog = self._setup([])

        _handler(kb, ("G",))(None)

        assert dialog.cursor == 0
