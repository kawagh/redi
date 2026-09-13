"""TUI のマウスホイールによるプレビュースクロールの単体テスト。"""

from typing import cast

from prompt_toolkit import Application
from prompt_toolkit.application import create_app_session
from prompt_toolkit.application.current import set_app
from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.output import DummyOutput

from redi.api.issue import Issue
from redi.tui import mouse
from redi.tui.app_layout import build_layout
from redi.tui.conditions import build_conditions
from redi.tui.mouse import WHEEL_LINES, WheelControl, build_preview_wheel_handler
from redi.tui.state import TuiState
from redi.tui.tabs import TABS

PREVIEW = [("", "\n".join(f"line {i}" for i in range(50)))]


def _event(event_type: MouseEventType) -> MouseEvent:
    return MouseEvent(
        position=Point(0, 0),
        event_type=event_type,
        button=MouseButton.NONE,
        modifiers=frozenset(),
    )


def _state(monkeypatch) -> TuiState:
    state = TuiState()
    state.page_size = 20
    monkeypatch.setattr(TABS["issues"], "render_preview", lambda s: PREVIEW)
    return state


class TestWheelControl:
    """WheelControl はホイールだけを on_wheel に流す"""

    def test_scroll_down_is_positive(self):
        """ホイール下は +1 として渡す"""
        received: list[int] = []
        control = WheelControl(list, on_wheel=received.append)

        control.mouse_handler(_event(MouseEventType.SCROLL_DOWN))

        assert received == [1]

    def test_scroll_up_is_negative(self):
        """ホイール上は -1 として渡す"""
        received: list[int] = []
        control = WheelControl(list, on_wheel=received.append)

        control.mouse_handler(_event(MouseEventType.SCROLL_UP))

        assert received == [-1]

    def test_click_is_not_handled(self):
        """クリックは on_wheel に渡さず、未処理 (NotImplemented) として返す"""
        received: list[int] = []
        control = WheelControl(list, on_wheel=received.append)

        result = control.mouse_handler(_event(MouseEventType.MOUSE_UP))

        assert result is NotImplemented
        assert received == []

    def test_without_handler_swallows_wheel(self):
        """on_wheel が無いときもホイールは Window の既定処理へ渡さない"""
        control = WheelControl(list)

        result = control.mouse_handler(_event(MouseEventType.SCROLL_DOWN))

        assert result is None


class TestPreviewWheel:
    """プレビュー上のホイールは Ctrl+E / Ctrl+Y と同じ向きにスクロールする"""

    def test_scroll_down_moves_preview(self, monkeypatch):
        """ホイール下でプレビューが WHEEL_LINES 行進む"""
        state = _state(monkeypatch)
        on_wheel = build_preview_wheel_handler(state, build_conditions(state))

        on_wheel(1)

        assert state.preview_scroll == WHEEL_LINES

    def test_scroll_up_moves_back_and_stops_at_top(self, monkeypatch):
        """ホイール上で戻り、先頭より上へは行かない"""
        state = _state(monkeypatch)
        state.preview_scroll = 1
        on_wheel = build_preview_wheel_handler(state, build_conditions(state))

        on_wheel(-1)

        assert state.preview_scroll == 0

    def test_works_in_comment_select_mode(self, monkeypatch):
        """コメント選択モードでもプレビューをスクロールできる"""
        state = _state(monkeypatch)
        state.issue_tab.comment_select.active = True
        on_wheel = build_preview_wheel_handler(state, build_conditions(state))

        on_wheel(1)

        assert state.preview_scroll == WHEEL_LINES

    def test_ignored_while_dialog_is_open(self, monkeypatch):
        """ダイアログ表示中はダイアログの外を回しても動かない"""
        state = _state(monkeypatch)
        state.show_help = True
        on_wheel = build_preview_wheel_handler(state, build_conditions(state))

        on_wheel(1)

        assert state.preview_scroll == 0


def test_wheel_lines_is_between_line_and_half_page():
    """ホイール 1 目盛りは 1 行より多く、半ページより少ない"""
    assert 1 < mouse.WHEEL_LINES < 10


class _FixedSizeOutput(DummyOutput):
    def get_size(self) -> Size:
        return Size(rows=24, columns=80)


class TestLayoutWiring:
    """描画したレイアウト上でホイールを回すと、プレビューの上でだけスクロールする"""

    @staticmethod
    def _fire(app: Application, x: int, y: int, event_type: MouseEventType) -> None:
        handler = app.renderer.mouse_handlers.mouse_handlers[y][x]
        handler(MouseEvent(Point(x, y), event_type, MouseButton.NONE, frozenset()))

    def _render(self, monkeypatch, state: TuiState) -> Application:
        state.issue_tab.issues = cast(list[Issue], [{"id": 1, "subject": "a"}])
        monkeypatch.setattr(TABS["issues"], "render_preview", lambda s: PREVIEW)
        app = Application(
            layout=build_layout(state, build_conditions(state)),
            full_screen=True,
            mouse_support=True,
        )
        app.renderer.render(app, app.layout)
        # Window のマウスハンドラは「現在のモーダル領域」の判定に親子関係を使う。
        # 実アプリでは _redraw が更新するので、ここでも同じ状態にする。
        app.layout.update_parents_relations()
        return app

    def test_wheel_over_preview_scrolls(self, monkeypatch):
        """右ペイン (プレビュー) の上でホイール下を回すとプレビューが進む"""
        state = TuiState()
        state.page_size = 20
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=_FixedSizeOutput()),
        ):
            app = self._render(monkeypatch, state)
            with set_app(app):
                self._fire(app, 60, 5, MouseEventType.SCROLL_DOWN)

        assert state.preview_scroll == WHEEL_LINES

    def test_wheel_over_list_does_nothing(self, monkeypatch):
        """左ペイン (一覧) の上でホイールを回してもプレビューは動かない"""
        state = TuiState()
        state.page_size = 20
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=_FixedSizeOutput()),
        ):
            app = self._render(monkeypatch, state)
            with set_app(app):
                self._fire(app, 10, 5, MouseEventType.SCROLL_DOWN)

        assert state.preview_scroll == 0
