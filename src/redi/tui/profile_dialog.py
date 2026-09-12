"""P で開くプロファイル切替 modal を開く/切り替える操作。"""

from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.layout.containers import Float

from redi import config
from redi.config import list_profile_names, profile_has_credentials
from redi.i18n import messages
from redi.tui.choice_dialog import build_choice_dialog
from redi.tui.state import TuiResult, TuiState


def build_profile_dialog(state: TuiState, show: FilterOrBool) -> Float:
    return build_choice_dialog(
        lambda: state.profile_dialog,
        messages.tui_profile_modal_title,
        messages.tui_profile_modal_hint,
        show,
    )


def open_profile_dialog(state: TuiState) -> None:
    """プロファイル切替モーダルを開く。プロファイルが無ければ error modal に流す。"""
    dialog = state.profile_dialog
    profile_names = list_profile_names()
    if not profile_names:
        state.error_dialog = messages.tui_no_profiles
        return
    # プロファイル名がそのまま表示ラベルになる
    dialog.choices = [(name, name) for name in profile_names]
    dialog.cursor = 0
    dialog.active_value = config.current_profile
    if dialog.active_value in profile_names:
        dialog.cursor = profile_names.index(dialog.active_value)
    dialog.show = True


def request_profile_switch(state: TuiState, name: str) -> TuiResult | None:
    """プロファイル切替を要求する。TUI を抜けるべきときだけ `TuiResult` を返す。

    `TuiState` は conditions / keybindings / layout の各クロージャに捕まえられていて
    実行中に差し替えられないため、ここでは抜けるだけにして、適用と作り直しは
    `cli.main` に任せる。
    """
    dialog = state.profile_dialog
    dialog.show = False
    if name == config.current_profile:
        return None
    if not profile_has_credentials(name):
        state.error_dialog = messages.tui_profile_switch_invalid.format(name=name)
        return None
    return TuiResult(action="switch_profile", tab=state.tab, profile_name=name)
