"""TUI のプロファイル切替 (P キー) の単体テスト。"""

from redi import config
from redi.i18n import messages
from redi.tui import profile_modal
from redi.tui.state import TuiState

PROFILES = ["main", "sub", "broken"]


class TestOpenProfileModal:
    """open_profile_modal() は選択肢を構築し現在プロファイルへカーソルを合わせる"""

    def test_cursor_on_current_profile(self, monkeypatch):
        """現在のプロファイルの位置にカーソルが乗り active_value が入る"""
        monkeypatch.setattr(profile_modal, "list_profile_names", lambda: PROFILES)
        monkeypatch.setattr(config, "current_profile", "sub")
        state = TuiState()

        profile_modal.open_profile_modal(state)

        assert state.profile_modal.show is True
        assert state.profile_modal.choices == [(n, n) for n in PROFILES]
        assert state.profile_modal.active_value == "sub"
        assert state.profile_modal.cursor == 1

    def test_cursor_top_when_current_profile_is_unknown(self, monkeypatch):
        """config.tomlに無いプロファイル名ならカーソルは先頭に置く"""
        monkeypatch.setattr(profile_modal, "list_profile_names", lambda: PROFILES)
        monkeypatch.setattr(config, "current_profile", None)
        state = TuiState()

        profile_modal.open_profile_modal(state)

        assert state.profile_modal.cursor == 0
        assert state.profile_modal.active_value is None

    def test_no_profiles_goes_to_error_modal(self, monkeypatch):
        """プロファイルが1つも無ければ error modal に流し、モーダルは開かない"""
        monkeypatch.setattr(profile_modal, "list_profile_names", list)
        state = TuiState()

        profile_modal.open_profile_modal(state)

        assert state.profile_modal.show is False
        assert state.error_modal == messages.tui_no_profiles


class TestRequestProfileSwitch:
    """request_profile_switch() は切替が必要なときだけ TuiResult を返す"""

    def test_returns_result_for_other_profile(self, monkeypatch):
        """別プロファイルを選ぶと switch_profile の TuiResult を返す"""
        monkeypatch.setattr(config, "current_profile", "main")
        monkeypatch.setattr(profile_modal, "profile_has_credentials", lambda name: True)
        state = TuiState()
        state.tab = "wiki"
        state.profile_modal.show = True

        result = profile_modal.request_profile_switch(state, "sub")

        assert result is not None
        assert result.action == "switch_profile"
        assert result.profile_name == "sub"
        # 復帰先を揃えるため現在のタブを引き継ぐ
        assert result.tab == "wiki"
        assert state.profile_modal.show is False

    def test_same_profile_does_nothing(self, monkeypatch):
        """現在と同じプロファイルを選んだ場合は再起動せずモーダルを閉じるだけ"""
        monkeypatch.setattr(config, "current_profile", "main")
        state = TuiState()
        state.profile_modal.show = True

        result = profile_modal.request_profile_switch(state, "main")

        assert result is None
        assert state.profile_modal.show is False
        assert state.error_modal is None

    def test_profile_without_credentials_goes_to_error_modal(self, monkeypatch):
        """接続情報が欠けたプロファイルは切り替えずに error modal を出す"""
        monkeypatch.setattr(config, "current_profile", "main")
        monkeypatch.setattr(
            profile_modal, "profile_has_credentials", lambda name: False
        )
        state = TuiState()
        state.profile_modal.show = True

        result = profile_modal.request_profile_switch(state, "broken")

        assert result is None
        assert state.profile_modal.show is False
        assert state.error_modal == messages.tui_profile_switch_invalid.format(
            name="broken"
        )


class TestRenderTabsProfile:
    """render_tabs() は接続中のプロファイルを常に表示する"""

    def test_shows_current_profile(self, monkeypatch):
        """複数インスタンスを行き来するため接続先が分かるようにする"""
        from redi.tui import app_render

        monkeypatch.setattr(config, "current_profile", "sub")
        state = TuiState()

        rendered = "".join(text for _style, text in app_render.render_tabs(state))

        assert "[profile: sub]" in rendered

    def test_no_label_when_profile_is_unset(self, monkeypatch):
        """プロファイル未使用 (環境変数のみ) なら何も出さない"""
        from redi.tui import app_render

        monkeypatch.setattr(config, "current_profile", None)
        state = TuiState()

        rendered = "".join(text for _style, text in app_render.render_tabs(state))

        assert "[profile:" not in rendered
