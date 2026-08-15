"""プロジェクト切替 / プロファイル切替が共有する選択肢 modal の単体テスト。"""

from redi.tui.choice_modal import render_choice_list
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
