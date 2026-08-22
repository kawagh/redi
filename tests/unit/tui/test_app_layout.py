from typing import cast

from prompt_toolkit import Application
from prompt_toolkit.application import create_app_session
from prompt_toolkit.data_structures import Size
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from redi.api.issue import Issue
from redi.tui.app_layout import build_layout, list_pane_width
from redi.tui.conditions import build_conditions
from redi.tui.state import TuiState

SEPARATOR = "│"
ROWS = 24


class _FixedSizeOutput(DummyOutput):
    """端末サイズを固定して返す DummyOutput"""

    def __init__(self, columns: int, rows: int) -> None:
        self._size = Size(rows=rows, columns=columns)

    def get_size(self) -> Size:
        return self._size


def _separator_columns(columns: int, subjects: list[str]) -> set[int]:
    """幅 `columns` の端末に一覧を描画し、区切り線が現れた桁位置を返す"""
    state = TuiState()
    state.issue_tab.issues = cast(
        list[Issue], [{"id": i + 1, "subject": s} for i, s in enumerate(subjects)]
    )
    conditions = build_conditions(state)
    with (
        create_pipe_input() as pipe,
        create_app_session(input=pipe, output=_FixedSizeOutput(columns, ROWS)),
    ):
        app = Application(layout=build_layout(state, conditions), full_screen=True)
        app.renderer.render(app, app.layout)
        screen = app.renderer._last_screen
        assert screen is not None
        lines = [
            "".join(screen.data_buffer[y][x].char for x in range(columns))
            for y in range(ROWS)
        ]
    return {line.index(SEPARATOR) for line in lines if SEPARATOR in line}


class TestListPaneWidth:
    """list_pane_width() は端末幅だけから左ペインの桁数を決める"""

    def test_splits_in_half_excluding_separator(self):
        """区切り線の1桁を除いた幅を左右で半分ずつに分ける"""
        assert list_pane_width(80) == 39

    def test_odd_remainder_goes_to_preview(self):
        """半分に割り切れない1桁は右ペイン(詳細)に渡す"""
        assert list_pane_width(81) == 40

    def test_never_negative_on_narrow_terminal(self):
        """区切り線も置けない幅でも負の桁数を返さない"""
        assert list_pane_width(1) == 0
        assert list_pane_width(0) == 0


class TestPaneBoundary:
    """左右ペインの境界は一覧の内容によらず同じ桁位置に来る"""

    def test_boundary_does_not_move_with_subject_length(self):
        """件名の長さが変わっても区切り線の桁位置は動かない"""
        short = _separator_columns(80, ["a", "b"])
        long = _separator_columns(80, ["x" * 60, "y" * 55])
        assert short == long == {list_pane_width(80)}

    def test_boundary_does_not_move_when_list_is_empty(self):
        """一覧が空でも区切り線の桁位置は変わらない"""
        assert _separator_columns(80, []) == {list_pane_width(80)}
