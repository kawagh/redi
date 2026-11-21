"""TUI のマウス操作 (ホイール / クリック) の単体テスト。"""

from typing import cast

from prompt_toolkit import Application
from prompt_toolkit.application import create_app_session
from prompt_toolkit.application.current import set_app
from prompt_toolkit.data_structures import Point, Size
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.utils import get_cwidth

from redi import config
from redi.api.issue import Issue
from redi.tui import profile_dialog, project_dialog
from redi.tui.app_layout import build_layout
from redi.tui.conditions import build_conditions
from redi.tui.mouse import PaneControl
from redi.tui.panes import preview_pane
from redi.tui.panes.list_pane import build_list_wheel_handler
from redi.tui.panes.preview_pane import (
    WHEEL_LINES,
    build_preview_click_handler,
    build_preview_wheel_handler,
)
from redi.tui.panes.top_bar import (
    build_profile_click_handler,
    build_project_click_handler,
    build_tab_click_handler,
    render_top_bar,
)
from redi.tui.state import TuiState, TuiTab
from redi.tui.tabs import TABS

PREVIEW = [("", "\n".join(f"line {i}" for i in range(50)))]


def _event(event_type: MouseEventType, position: Point | None = None) -> MouseEvent:
    return MouseEvent(
        position=position if position is not None else Point(0, 0),
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

    def test_click_calls_on_click_with_position(self):
        """MOUSE_UP はクリック位置と共に on_click に流し、MOUSE_DOWN では呼ばない"""
        clicks: list[Point] = []
        control = PaneControl(list, on_click=clicks.append)

        control.mouse_handler(_event(MouseEventType.MOUSE_DOWN, Point(3, 2)))
        control.mouse_handler(_event(MouseEventType.MOUSE_UP, Point(3, 2)))

        assert clicks == [Point(3, 2)]

    def test_without_handler_swallows_wheel(self):
        """on_wheel が無いときもホイールは Window の既定処理へ渡さない"""
        control = PaneControl(list)

        result = control.mouse_handler(_event(MouseEventType.SCROLL_DOWN))

        assert result is None

    def test_create_content_reports_size(self):
        """描画時にペインの (幅, 高さ) を on_size に流す"""
        sizes: list[tuple[int, int]] = []
        control = PaneControl(list, on_size=lambda w, h: sizes.append((w, h)))

        control.create_content(30, 7)

        assert sizes == [(30, 7)]


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

        build_preview_click_handler(state, build_conditions(state))(Point(0, 0))

        assert entered == ["wiki"]

    def test_issue_click_does_nothing(self, monkeypatch):
        """issue タブではクリックしても on_enter (コメント選択モード) に入らない"""
        state, entered = self._state(monkeypatch, "issues")

        build_preview_click_handler(state, build_conditions(state))(Point(0, 0))

        assert entered == []

    def test_ignored_while_dialog_is_open(self, monkeypatch):
        """ダイアログ表示中はクリックしても読み込まない"""
        state, entered = self._state(monkeypatch, "wiki")
        state.show_help = True

        build_preview_click_handler(state, build_conditions(state))(Point(0, 0))

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


class TestProfileLabelClick:
    """タブ行のプロファイル名をクリックすると P と同じくプロファイル切替ダイアログが開く"""

    def _state(self, monkeypatch) -> TuiState:
        monkeypatch.setattr(profile_dialog, "list_profile_names", lambda: ["main"])
        monkeypatch.setattr(config, "current_profile", "main")
        state = TuiState()
        state.flash_message = "x"
        return state

    def test_click_opens_profile_dialog(self, monkeypatch):
        """MOUSE_UP でダイアログが開き、一時的な表示 (flash) は消える"""
        state = self._state(monkeypatch)
        handler = build_profile_click_handler(state, build_conditions(state))

        result = handler(_event(MouseEventType.MOUSE_UP))

        assert result is None
        assert state.profile_dialog.show is True
        assert state.flash_message is None

    def test_mouse_down_is_ignored(self, monkeypatch):
        """MOUSE_DOWN では開かない (押して離したときに開く)"""
        state = self._state(monkeypatch)
        handler = build_profile_click_handler(state, build_conditions(state))

        result = handler(_event(MouseEventType.MOUSE_DOWN))

        assert result is NotImplemented
        assert state.profile_dialog.show is False

    def test_ignored_while_dialog_is_open(self, monkeypatch):
        """ダイアログ表示中はタブ行が見えていてもクリックで開かない"""
        state = self._state(monkeypatch)
        state.show_help = True
        handler = build_profile_click_handler(state, build_conditions(state))

        handler(_event(MouseEventType.MOUSE_UP))

        assert state.profile_dialog.show is False


class TestProjectLabelClick:
    """タブ行のプロジェクト名をクリックすると p と同じくプロジェクト切替ダイアログが開く"""

    def _state(self, monkeypatch) -> TuiState:
        monkeypatch.setattr(
            project_dialog,
            "list_projects",
            lambda all_pages: [{"id": 1, "name": "Alpha", "identifier": "alpha"}],
        )
        state = TuiState()
        state.project_label = "Alpha"
        return state

    def test_click_opens_project_dialog(self, monkeypatch):
        """MOUSE_UP でダイアログが開く"""
        state = self._state(monkeypatch)
        handler = build_project_click_handler(state, build_conditions(state))

        result = handler(_event(MouseEventType.MOUSE_UP))

        assert result is None
        assert state.project_dialog.show is True

    def test_ignored_while_dialog_is_open(self, monkeypatch):
        """ダイアログ表示中はタブ行が見えていてもクリックで開かない"""
        state = self._state(monkeypatch)
        state.show_help = True
        handler = build_project_click_handler(state, build_conditions(state))

        handler(_event(MouseEventType.MOUSE_UP))

        assert state.project_dialog.show is False


def test_wheel_lines_is_between_line_and_half_page():
    """ホイール 1 目盛りは 1 行より多く、半ページより少ない"""
    assert 1 < preview_pane.WHEEL_LINES < 10


class _FixedSizeOutput(DummyOutput):
    def get_size(self) -> Size:
        return Size(rows=24, columns=80)


def _find_on_screen(app: Application, text: str) -> Point:
    """描画結果から `text` が最初に現れる桁・行を返す。

    Float の位置は描画で決まるため。CJK 文字は 2 桁を占めるので、文字列の添字では
    なく画面の桁で返す。
    """
    screen = app.renderer.last_rendered_screen
    assert screen is not None
    size = app.output.get_size()
    for y in range(size.rows):
        cells: list[tuple[int, str]] = []
        x = 0
        while x < size.columns:
            char = screen.data_buffer[y][x]
            cells.append((x, char.char))
            x += max(1, char.width)
        index = "".join(c for _x, c in cells).find(text)
        if index >= 0:
            return Point(cells[index][0], y)
    raise AssertionError(f"{text!r} is not on screen")


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

    def test_render_records_preview_size(self, monkeypatch):
        """描画するとプレビューの実際の幅と高さが state に入る (折り返し計算に使う)"""
        state = TuiState()
        state.page_size = 20
        monkeypatch.setattr(config, "current_profile", None)
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=_FixedSizeOutput()),
        ):
            self._render(monkeypatch, state)

        # 80 桁から区切り 2 桁を引いて等分、24 行から上端バー・区切り線・ステータス行を引く
        assert (state.preview_width, state.preview_height) == (39, 21)

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
        for part in render_top_bar(state):
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

    def test_wheel_over_choice_dialog_moves_dialog_cursor(self, monkeypatch):
        """プロジェクト切替ダイアログの上でホイール下を回すとダイアログのカーソルが下がり、一覧は動かない"""
        state = TuiState()
        state.page_size = 20
        state.project_dialog.show = True
        state.project_dialog.choices = [("1", "Alpha"), ("2", "Beta")]
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=_FixedSizeOutput()),
        ):
            app = self._render(monkeypatch, state)
            row = _find_on_screen(app, "Alpha")
            with set_app(app):
                self._fire(app, row.x, row.y, MouseEventType.SCROLL_DOWN)

        assert state.project_dialog.cursor == 1
        assert state.issue_tab.cursor == 0

    def test_click_on_choice_dialog_row_selects_it(self, monkeypatch):
        """プロジェクト切替ダイアログの行を MOUSE_UP でクリックすると、その行が決定される"""
        state = TuiState()
        state.page_size = 20
        state.project_dialog.show = True
        state.project_dialog.choices = [("1", "Alpha"), ("2", "Beta")]
        applied: list[tuple[str, str]] = []
        monkeypatch.setattr(
            project_dialog,
            "apply_project_switch",
            lambda s, project_id, label: applied.append((project_id, label)),
        )
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=_FixedSizeOutput()),
        ):
            app = self._render(monkeypatch, state)
            row = _find_on_screen(app, "Beta")
            with set_app(app):
                # ラベルの右側の余白でも同じ行として受ける
                self._fire(app, row.x + 10, row.y, MouseEventType.MOUSE_UP)

        assert state.project_dialog.cursor == 1
        assert applied == [("2", "Beta")]

    def test_click_on_profile_label_opens_profile_dialog(self, monkeypatch):
        """タブ行のプロファイル名の桁を MOUSE_UP でクリックするとプロファイル切替ダイアログが開く"""
        monkeypatch.setattr(profile_dialog, "list_profile_names", lambda: ["main"])
        monkeypatch.setattr(config, "current_profile", "main")
        state = TuiState()
        state.page_size = 20
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=_FixedSizeOutput()),
        ):
            app = self._render(monkeypatch, state)
            label = _find_on_screen(app, "profile: main")
            with set_app(app):
                self._fire(app, label.x, label.y, MouseEventType.MOUSE_UP)

        assert state.profile_dialog.show is True

    def test_click_on_project_label_opens_project_dialog(self, monkeypatch):
        """タブ行のプロジェクト名の桁を MOUSE_UP でクリックするとプロジェクト切替ダイアログが開く"""
        monkeypatch.setattr(
            project_dialog,
            "list_projects",
            lambda all_pages: [{"id": 1, "name": "Alpha", "identifier": "alpha"}],
        )
        # 開発者の設定にプロファイルがあると上端バーに [profile: <名前>] が挟まり、
        # 24x80 の描画領域から [project: Alpha] が押し出されるので、プロファイルを出さない
        monkeypatch.setattr(config, "current_profile", None)
        state = TuiState()
        state.page_size = 20
        state.project_label = "Alpha"
        with (
            create_pipe_input() as pipe,
            create_app_session(input=pipe, output=_FixedSizeOutput()),
        ):
            app = self._render(monkeypatch, state)
            label = _find_on_screen(app, "project: Alpha")
            with set_app(app):
                self._fire(app, label.x, label.y, MouseEventType.MOUSE_UP)

        assert state.project_dialog.show is True
