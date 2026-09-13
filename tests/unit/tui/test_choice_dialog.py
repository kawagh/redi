"""プロジェクト切替 / プロファイル切替が共有する選択肢ダイアログの単体テスト。"""

from prompt_toolkit.data_structures import Point
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from redi.tui.choice_dialog import (
    build_choice_click_handler,
    build_choice_wheel_handler,
    register_choice_keys,
    render_choice_list,
)
from redi.tui.mouse import ClickHandler
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

    def _setup(
        self, labels: list[str], selected: list[tuple[str, str]] | None = None
    ) -> tuple[KeyBindings, ChoiceDialogState]:
        dialog = _dialog(labels)
        kb = KeyBindings()
        on_select = selected.append if selected is not None else lambda *_args: None
        register_choice_keys(
            kb, lambda: dialog, True, "P", lambda v, l: on_select((v, l))
        )
        return kb, dialog

    def test_enter_selects_cursor_row(self):
        """Enter でカーソル行の (値, ラベル) を決定処理に渡す"""
        selected: list[tuple[str, str]] = []
        kb, dialog = self._setup(["a", "b", "c"], selected)
        dialog.cursor = 1

        _handler(kb, (Keys.Enter,))(None)

        assert selected == [("1", "b")]

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


def _dialog(labels: list[str]) -> ChoiceDialogState:
    return ChoiceDialogState(
        show=True, choices=[(str(i), label) for i, label in enumerate(labels)]
    )


class TestChoiceDialogWheel:
    """選択肢ダイアログ上のホイールは j / k と同じく 1 行ずつカーソルを動かす"""

    def test_scroll_down_moves_cursor_down(self):
        """ホイール下でカーソルが 1 行下がる"""
        dialog = _dialog(["a", "b", "c"])
        on_wheel = build_choice_wheel_handler(lambda: dialog)

        on_wheel(1)

        assert dialog.cursor == 1

    def test_scroll_stops_at_both_ends(self):
        """先頭より上、末尾より下へは行かない"""
        dialog = _dialog(["a", "b"])
        on_wheel = build_choice_wheel_handler(lambda: dialog)

        on_wheel(-1)
        assert dialog.cursor == 0
        on_wheel(1)
        on_wheel(1)
        assert dialog.cursor == 1

    def test_keeps_cursor_at_zero_without_choices(self):
        """候補が無いときのホイールはカーソルを負にしない"""
        dialog = _dialog([])
        on_wheel = build_choice_wheel_handler(lambda: dialog)

        on_wheel(1)
        on_wheel(-1)

        assert dialog.cursor == 0


class TestChoiceDialogClick:
    """選択肢の行をクリックすると、その行にカーソルを合わせて Enter と同じく決定する"""

    def _setup(
        self, labels: list[str]
    ) -> tuple[ChoiceDialogState, list[tuple[str, str]], ClickHandler]:
        dialog = _dialog(labels)
        selected: list[tuple[str, str]] = []
        on_click = build_choice_click_handler(
            lambda: dialog, lambda v, l: selected.append((v, l))
        )
        return dialog, selected, on_click

    def test_click_selects_clicked_row(self):
        """クリックした行 (クリック位置の y) が決定される"""
        dialog, selected, on_click = self._setup(["a", "b", "c"])

        on_click(Point(x=5, y=2))

        assert dialog.cursor == 2
        assert selected == [("2", "c")]

    def test_click_below_choices_does_nothing(self):
        """選択肢の無い行 (末尾の空行) をクリックしても決定しない"""
        dialog, selected, on_click = self._setup(["a", "b"])

        on_click(Point(x=0, y=2))

        assert dialog.cursor == 0
        assert selected == []
