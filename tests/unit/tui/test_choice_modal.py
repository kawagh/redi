"""プロジェクト切替 / プロファイル切替が共有する選択肢 modal の単体テスト。"""

from prompt_toolkit.key_binding import KeyBindings

from redi.tui.choice_modal import register_choice_keys, render_choice_list
from redi.tui.state import ChoiceModalState


class TestRenderChoiceList:
    """render_choice_list() はカーソル行に > を、active な行に * を付ける"""

    def test_marks_cursor_and_active_rows(self):
        modal = ChoiceModalState(
            choices=[("2", "Beta"), ("1", "Alpha")], cursor=0, active_value="1"
        )

        rendered = "".join(text for _style, text in render_choice_list(modal))

        assert " >   Beta" in rendered
        assert "   * Alpha" in rendered

    def test_no_mark_without_active(self):
        modal = ChoiceModalState(choices=[("1", "Alpha")])

        rendered = "".join(text for _style, text in render_choice_list(modal))

        assert "*" not in rendered


def _handler(kb: KeyBindings, keys: tuple):
    """実際に呼ばれるハンドラを返す。

    prompt_toolkit は有効な binding のうち最後のものを呼ぶ。
    """
    active = [b for b in kb.get_bindings_for_keys(keys) if b.filter()]
    if not active:
        raise AssertionError(f"no active binding for {keys}")
    return active[-1].handler


class TestChoiceModalKeys:
    """選択肢 modal は先頭 / 末尾へ一手で飛べる"""

    def _setup(self, labels: list[str]) -> tuple[KeyBindings, ChoiceModalState]:
        modal = ChoiceModalState(
            show=True, choices=[(str(i), label) for i, label in enumerate(labels)]
        )
        kb = KeyBindings()
        register_choice_keys(kb, lambda: modal, True, "P", lambda *_args: None)
        return kb, modal

    def test_gg_moves_to_top(self):
        """gg で先頭へ飛ぶ(候補数ぶんの k 連打を避ける)"""
        kb, modal = self._setup(["a", "b", "c"])
        modal.cursor = 2

        _handler(kb, ("g", "g"))(None)

        assert modal.cursor == 0

    def test_shift_g_moves_to_bottom(self):
        """G で末尾へ飛ぶ"""
        kb, modal = self._setup(["a", "b", "c"])

        _handler(kb, ("G",))(None)

        assert modal.cursor == 2

    def test_shift_g_keeps_cursor_at_zero_without_choices(self):
        """候補が無いときの G はカーソルを負にしない"""
        kb, modal = self._setup([])

        _handler(kb, ("G",))(None)

        assert modal.cursor == 0
