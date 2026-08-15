from prompt_toolkit.utils import get_cwidth

from redi.tui import app_render
from redi.tui.state import TuiState
from redi.tui.tabs import TABS


def _rendered_lines(parts) -> list[str]:
    return "".join(text for _style, text in parts).split("\n")


class TestRenderHelp:
    """render_help() は各タブのヘルプ本文と末尾のバージョンを組み立てる"""

    def test_shows_version_at_last_line(self):
        """最終行に redi のバージョンを表示する"""
        lines = _rendered_lines(app_render.render_help(TuiState()))
        assert lines[-1].strip() == app_render.help_version_label()

    def test_version_line_is_right_aligned(self):
        """バージョン行は本文の最大幅に右寄せする (右下に表示)"""
        for tab in TABS:
            state = TuiState()
            state.tab = tab
            lines = _rendered_lines(app_render.render_help(state))
            body_width = max(get_cwidth(line) for line in lines[:-1])
            assert get_cwidth(lines[-1]) == body_width
            assert lines[-1].endswith(app_render.help_version_label())

    def test_blank_line_before_version(self):
        """バージョン行の直前は空行にして本文と分ける"""
        lines = _rendered_lines(app_render.render_help(TuiState()))
        assert lines[-2] == ""
