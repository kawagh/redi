"""wiki タブの d で開く、比較前と比較後の版を選ぶダイアログと、選んだ 2 版の差分を表示する操作。

フィルタダイアログと同じ 2 列構成で、左が比較前・右が比較後。開いたときは比較前に表示中の版、
比較後に最新版を置くので、Enter だけで「表示中の版から最新版までの差分」になる。
Redmine の REST API には差分を返すエンドポイントが無いので、本文は
`wiki_tab.load_version_text` で取り、差分は `service.wiki_service.diff_texts` で手元で作る。
"""

from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    HSplit,
    ScrollOffsets,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame

from redi.i18n import messages
from redi.service import wiki_service
from redi.tui.state import Renderable, TuiState
from redi.tui.state.wiki_tab import WikiDiffColumn, WikiDiffDialogState, WikiDiffView
from redi.tui.wiki.version_dialog import latest_version, version_label
from redi.tui.wiki.wiki_tab import (
    current_page,
    load_version_text,
    viewing_diff,
    viewing_version,
)

COLUMNS: tuple[WikiDiffColumn, ...] = ("from", "to")


def move_cursor(dialog: WikiDiffDialogState, step: int) -> None:
    """focus のある列のカーソルを step だけ動かす。端で止まる。"""
    last = max(0, len(dialog.versions) - 1)
    dialog.cursors[dialog.focus] = min(
        last, max(0, dialog.cursors[dialog.focus] + step)
    )


def move_cursor_to_end(dialog: WikiDiffDialogState, top: bool) -> None:
    """focus のある列のカーソルを先頭か末尾へ飛ばす。"""
    dialog.cursors[dialog.focus] = 0 if top else max(0, len(dialog.versions) - 1)


def shift_focus(current: WikiDiffColumn, step: int) -> WikiDiffColumn:
    """focus を step だけ動かす。端では反対側へ巡回する。"""
    idx = COLUMNS.index(current)
    return COLUMNS[(idx + step) % len(COLUMNS)]


def render_diff_column(state: TuiState, column: WikiDiffColumn) -> Renderable:
    """比較前 / 比較後の 1 列を描画する。

    フィルタダイアログと同じく、カーソル行を出すのは focus のある列だけ。
    `*` は適用中の差分の版で、focus の無い列でも残る。
    """
    dialog = state.wiki_tab.diff_dialog
    focused = dialog.focus == column
    title = (
        messages.tui_wiki_diff_from if column == "from" else messages.tui_wiki_diff_to
    )
    header_style = "bold fg:ansicyan" if focused else "bold"
    parts: Renderable = [(header_style, f"[{title}]\n")]
    latest = dialog.versions[0] if dialog.versions else 0
    active = _active_version(state, column)
    cursor = dialog.cursors[column]
    for i, version in enumerate(dialog.versions):
        is_cursor = focused and i == cursor
        is_active = version == active
        cursor_mark = ">" if is_cursor else " "
        active_mark = "*" if is_active else " "
        line_style = "reverse" if is_cursor else ("bold" if is_active else "")
        parts.append(
            (
                line_style,
                f" {cursor_mark} {active_mark} {version_label(version, latest)}\n",
            )
        )
    return parts


def _active_version(state: TuiState, column: WikiDiffColumn) -> int | None:
    diff = viewing_diff(state)
    if diff is None:
        return None
    return diff.from_version if column == "from" else diff.to_version


def diff_column_cursor_y(dialog: WikiDiffDialogState, column: WikiDiffColumn) -> int:
    """描画結果におけるカーソル行 (0 始まり)。0 行目は列ヘッダ。"""
    return 1 + dialog.cursors[column]


def _diff_column_window(state: TuiState, column: WikiDiffColumn) -> Window:
    return Window(
        FormattedTextControl(
            lambda: render_diff_column(state, column),
            show_cursor=False,
            get_cursor_position=lambda: Point(
                0, diff_column_cursor_y(state.wiki_tab.diff_dialog, column)
            ),
        ),
        wrap_lines=False,
        scroll_offsets=ScrollOffsets(top=1, bottom=1),
    )


def build_diff_dialog(state: TuiState, show: FilterOrBool) -> Float:
    """比較前 / 比較後の 2 列を並べたダイアログの Float。構成はフィルタダイアログに合わせる。"""
    return Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        HSplit(
                            [
                                VSplit(
                                    [
                                        _diff_column_window(state, "from"),
                                        Window(width=1, char=" "),
                                        Window(width=1, char="│"),
                                        Window(width=1, char=" "),
                                        _diff_column_window(state, "to"),
                                    ]
                                ),
                                Window(
                                    FormattedTextControl(
                                        messages.tui_wiki_diff_dialog_hint,
                                        show_cursor=False,
                                    ),
                                    height=1,
                                ),
                            ]
                        ),
                        title=messages.tui_wiki_diff_dialog_title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=show,
        ),
    )


def shown_version(state: TuiState) -> int | None:
    """右ペインに出している版。過去版を開いていればその版、そうでなければ最新版。"""
    view = viewing_version(state)
    if view is not None:
        return view.version
    return latest_version(current_page(state))


def open_diff_dialog(state: TuiState) -> bool:
    """比較する版を選ぶダイアログを開く。版が 1 つしか無ければ flash で知らせて開かない。

    比較前は表示中の版、比較後は最新版に置く。最新版を表示中は比較前を 1 つ前の版にし、
    Enter だけで直前の編集の差分になるようにする。差分を出していればその 2 版に合わせる。
    """
    latest = latest_version(current_page(state))
    shown = shown_version(state)
    if latest is None or shown is None:
        return False
    if latest < 2:
        state.flash_message = messages.tui_wiki_diff_no_other_versions
        return False
    dialog = state.wiki_tab.diff_dialog
    dialog.versions = list(range(latest, 0, -1))
    diff = viewing_diff(state)
    if diff is not None:
        from_version, to_version = diff.from_version, diff.to_version
    else:
        from_version = shown if shown != latest else latest - 1
        to_version = latest
    dialog.cursors = {
        "from": dialog.versions.index(from_version),
        "to": dialog.versions.index(to_version),
    }
    dialog.focus = "from"
    dialog.show = True
    return True


def apply_diff(state: TuiState) -> bool:
    """両列のカーソルにある版の差分を右ペインに出す。

    フィルタダイアログと同じく適用してもダイアログは閉じず、組を変えて押し直せる。閉じるのは
    Esc / d。本文はここで取り (キャッシュにも載る)、取得に失敗したら表示は変えない
    (flash は取得側が出す)。同じ版どうしは弾かず、差分無しとして出す。
    """
    dialog = state.wiki_tab.diff_dialog
    page = current_page(state)
    latest = latest_version(page)
    if page is None or latest is None or not dialog.versions:
        return False
    from_version = dialog.versions[dialog.cursors["from"]]
    to_version = dialog.versions[dialog.cursors["to"]]
    title = page["title"]
    old = load_version_text(state, title, from_version, latest)
    if old is None:
        return False
    new = load_version_text(state, title, to_version, latest)
    if new is None:
        return False
    state.wiki_tab.diff_view = WikiDiffView(
        title=title,
        from_version=from_version,
        to_version=to_version,
        diff=wiki_service.diff_texts(old, new, from_version, to_version),
    )
    return True


def clear_diff(state: TuiState) -> None:
    """差分表示をやめて本文に戻す。ダイアログはフィルタの c と同じく開いたまま。"""
    state.wiki_tab.diff_view = None
