from prompt_toolkit.utils import get_cwidth

from redi.tui import app_render
from redi.tui.conditions import build_conditions
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


class TestRenderStatusSearch:
    """render_status() は確定後も残っている検索クエリをステータスバーに出す"""

    def _status(self, state: TuiState) -> str:
        return "".join(
            text
            for _style, text in app_render.render_status(state, build_conditions(state))
        )

    def test_shows_query_after_search_is_committed(self):
        """検索確定後 (search_mode=False) もクエリと解除方法を表示する"""
        state = TuiState()
        state.search_query = "foo"

        status = self._status(state)

        assert "/foo" in status
        assert "Esc" in status

    def test_hides_query_when_search_is_cleared(self):
        """検索クエリが空なら検索の表示は出さない"""
        state = TuiState()

        assert "Esc" not in self._status(state)

    def test_hides_query_while_not_in_normal_mode(self):
        """通常モードでない間は Esc が検索解除に効かないので案内も出さない"""
        state = TuiState()
        state.search_query = "foo"
        state.issue_tab.comment_select.active = True

        assert "/foo" not in self._status(state)
