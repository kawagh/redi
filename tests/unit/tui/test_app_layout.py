from typing import cast

from prompt_toolkit import Application
from prompt_toolkit.application import create_app_session
from prompt_toolkit.data_structures import Size
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from redi.api.issue import Issue
from redi.tui.app_layout import build_layout
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
        # 全角文字は 2 セルを占め、2 セル目の char は空文字列になる。そのまま
        # 連結すると文字列上の位置が桁位置とずれるので、空文字列は空白で埋める。
        lines = [
            "".join(screen.data_buffer[y][x].char or " " for x in range(columns))
            for y in range(ROWS)
        ]
    return {line.index(SEPARATOR) for line in lines if SEPARATOR in line}


class TestPaneBoundary:
    """左右ペインの境界は一覧の内容によらず同じ桁位置に来る"""

    def test_boundary_does_not_move_with_subject_length(self):
        """件名の長さが変わっても区切り線は端末幅の半分の桁位置に来る"""
        assert _separator_columns(80, ["a", "b"]) == {40}
        assert _separator_columns(80, ["x" * 60, "y" * 55]) == {40}

    def test_boundary_does_not_move_when_list_is_empty(self):
        """一覧が空でも区切り線の桁位置は変わらない"""
        assert _separator_columns(80, []) == {40}
