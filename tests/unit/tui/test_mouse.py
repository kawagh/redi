"""TUI のマウスホイールによるプレビュースクロールの単体テスト。"""

from typing import cast

from prompt_toolkit import Application
from prompt_toolkit.application import create_app_session
from prompt_toolkit.application.current import set_app
from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.utils import get_cwidth

from redi.api.issue import Issue
from redi.tui import mouse
from redi.tui.app_layout import build_layout
from redi.tui.app_render import render_tabs
from redi.tui.conditions import build_conditions
from redi.tui.mouse import (
    WHEEL_LINES,
    PaneControl,
    build_list_wheel_handler,
    build_preview_click_handler,
    build_preview_wheel_handler,
    build_tab_click_handler,
)
from redi.tui.state import TuiState, TuiTab
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


class TestPaneControl:
    """PaneControl はホイールを on_wheel に流し、他のマウスイベントは無視する"""

    def test_scroll_down_is_positive(self):
        """ホイール下は +1 として渡す"""
        received: list[int] = []
        control = PaneControl(list, on_wheel=received.append)

        control.mouse_handler(_event(MouseEventType.SCROLL_DOWN))

        assert received == [1]

    def test_scroll_up_is_negative(self):
        """ホイール上は -1 として渡す"""
        received: list[int] = []
        control = PaneControl(list, on_wheel=received.append)

        control.mouse_handler(_event(MouseEventType.SCROLL_UP))

        assert received == [-1]

    def test_click_without_handler_is_not_handled(self):
        """on_click が無ければクリックは on_wheel に渡さず、未処理 (NotImplemented) として返す"""
        received: list[int] = []
        control = PaneControl(list, on_wheel=received.append)

        result = control.mouse_handler(_event(MouseEventType.MOUSE_UP))

        assert result is NotImplemented
        assert received == []

    def test_click_calls_on_click(self):
        """MOUSE_UP は on_click に流し、MOUSE_DOWN では呼ばない"""
        clicks: list[str] = []
        control = PaneControl(list, on_click=lambda: clicks.append("x"))

        control.mouse_handler(_event(MouseEventType.MOUSE_DOWN))
        control.mouse_handler(_event(MouseEventType.MOUSE_UP))

        assert clicks == ["x"]

    def test_without_handler_swallows_wheel(self):
        """on_wheel が無いときもホイールは Window の既定処理へ渡さない"""
        control = PaneControl(list)

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


class TestListWheel:
    """一覧上のホイールは j / k と同じカーソル移動になる"""

    def _state(self) -> TuiState:
        state = TuiState()
        state.page_size = 20
        state.issue_tab.issues = cast(
            list[Issue], [{"id": i, "subject": f"s{i}"} for i in range(1, 4)]
        )
        return state

    def test_scroll_down_moves_cursor_down(self):
        """ホイール下でカーソルが 1 行下がる"""
        state = self._state()
        on_wheel = build_list_wheel_handler(state, build_conditions(state))

        on_wheel(1)

        assert state.issue_tab.cursor == 1

    def test_scroll_up_stops_at_top(self):
        """ホイール上でカーソルが 1 行上がり、先頭より上へは行かない"""
        state = self._state()
        state.issue_tab.cursor = 1
        on_wheel = build_list_wheel_handler(state, build_conditions(state))

        on_wheel(-1)
        on_wheel(-1)

        assert state.issue_tab.cursor == 0

    def test_resets_preview_scroll(self, monkeypatch):
        """カーソルが動いたらプレビューのスクロール位置を先頭へ戻す (j / k と同じ)"""
        state = self._state()
        state.preview_scroll = 5
        on_wheel = build_list_wheel_handler(state, build_conditions(state))

        on_wheel(1)

        assert state.preview_scroll == 0

    def test_ignored_in_comment_select_mode(self):
        """コメント選択モードでは一覧のカーソルを動かさない"""
        state = self._state()
        state.issue_tab.comment_select.active = True
        on_wheel = build_list_wheel_handler(state, build_conditions(state))

        on_wheel(1)

        assert state.issue_tab.cursor == 0


class TestPreviewClick:
    """wiki タブでプレビューをクリックすると Enter と同じく本文を読み込む"""

    def _state(self, monkeypatch, tab: TuiTab) -> tuple[TuiState, list[str]]:
        state = TuiState()
        state.tab = tab
        entered: list[str] = []
        for key, view in TABS.items():
            monkeypatch.setattr(
                view, "on_enter", lambda s, key=key: entered.append(key)
            )
        return state, entered

    def test_wiki_click_loads_text(self, monkeypatch):
        """wiki タブではクリックで on_enter (本文の読み込み) を呼ぶ"""
        state, entered = self._state(monkeypatch, "wiki")

        build_preview_click_handler(state, build_conditions(state))()

        assert entered == ["wiki"]

    def test_issue_click_does_nothing(self, monkeypatch):
        """issue タブではクリックしても on_enter (コメント選択モード) に入らない"""
        state, entered = self._state(monkeypatch, "issues")

        build_preview_click_handler(state, build_conditions(state))()

        assert entered == []

    def test_ignored_while_dialog_is_open(self, monkeypatch):
        """ダイアログ表示中はクリックしても読み込まない"""
        state, entered = self._state(monkeypatch, "wiki")
        state.show_help = True

        build_preview_click_handler(state, build_conditions(state))()

        assert entered == []


class TestTabClick:
    """タブ行のラベルをクリックすると Tab キーと同じくそのタブに切り替わる"""

    def _state(self, monkeypatch) -> TuiState:
        state = TuiState()
        state.page_size = 20
        # on_activate は API を呼ぶので差し替える
        for tab in TABS.values():
            monkeypatch.setattr(tab, "on_activate", lambda s: None)
        return state

    def test_click_switches_tab(self, monkeypatch):
        """wiki のラベルを MOUSE_UP でクリックすると wiki タブになる"""
        state = self._state(monkeypatch)
        state.preview_scroll = 5
        handler = build_tab_click_handler(state, build_conditions(state))("wiki")

        result = handler(_event(MouseEventType.MOUSE_UP))

        assert result is None
        assert state.tab == "wiki"
        assert state.preview_scroll == 0

    def test_mouse_down_is_ignored(self, monkeypatch):
        """MOUSE_DOWN では切り替えない (押して離したときに切り替える)"""
        state = self._state(monkeypatch)
        handler = build_tab_click_handler(state, build_conditions(state))("wiki")

        result = handler(_event(MouseEventType.MOUSE_DOWN))

        assert result is NotImplemented
        assert state.tab == "issues"

    def test_ignored_while_dialog_is_open(self, monkeypatch):
        """ダイアログ表示中はタブ行が見えていてもクリックで切り替えない"""
        state = self._state(monkeypatch)
        state.show_help = True
        handler = build_tab_click_handler(state, build_conditions(state))("wiki")

        handler(_event(MouseEventType.MOUSE_UP))

        assert state.tab == "issues"

    def test_current_tab_is_not_reloaded(self, monkeypatch):
        """今のタブをクリックしても on_activate (再読込) は呼ばない"""
        state = self._state(monkeypatch)
        called: list[str] = []
        monkeypatch.setattr(TABS["issues"], "on_activate", lambda s: called.append("x"))
        handler = build_tab_click_handler(state, build_conditions(state))("issues")

        handler(_event(MouseEventType.MOUSE_UP))

        assert called == []


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
        state.issue_tab.issues = cast(
            list[Issue], [{"id": 1, "subject": "a"}, {"id": 2, "subject": "b"}]
        )
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

    def test_wheel_over_list_moves_cursor(self, monkeypatch):
        """左ペイン (一覧) の上でホイール下を回すとカーソルが下がり、プレビューは動かない"""
        state = TuiState()
        state.page_size = 20
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=_FixedSizeOutput()),
        ):
            app = self._render(monkeypatch, state)
            with set_app(app):
                self._fire(app, 10, 5, MouseEventType.SCROLL_DOWN)

        assert state.issue_tab.cursor == 1
        assert state.preview_scroll == 0

    def test_click_on_tab_label_switches_tab(self, monkeypatch):
        """タブ行の wiki ラベルの桁を MOUSE_UP でクリックすると wiki タブになる"""
        state = TuiState()
        state.page_size = 20
        for tab in TABS.values():
            monkeypatch.setattr(tab, "on_activate", lambda s: None)
        # ラベルの位置は描画結果から測る (言語によりラベルの幅が変わる)
        x = 0
        for part in render_tabs(state):
            if part[1] == f" {TABS['wiki'].label} ":
                break
            x += get_cwidth(part[1])
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=_FixedSizeOutput()),
        ):
            app = self._render(monkeypatch, state)
            with set_app(app):
                self._fire(app, x + 1, 0, MouseEventType.MOUSE_UP)

        assert state.tab == "wiki"

    def test_click_on_preview_loads_wiki_text(self, monkeypatch):
        """wiki タブで右ペインの余白を MOUSE_UP でクリックすると本文の読み込みが呼ばれる"""
        state = TuiState()
        state.page_size = 20
        state.tab = "wiki"
        entered: list[str] = []
        monkeypatch.setattr(TABS["wiki"], "on_enter", lambda s: entered.append("wiki"))
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=_FixedSizeOutput()),
        ):
            app = self._render(monkeypatch, state)
            with set_app(app):
                self._fire(app, 60, 15, MouseEventType.MOUSE_UP)

        assert entered == ["wiki"]
