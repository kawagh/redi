"""wiki タブの状態。"""

from dataclasses import dataclass, field
from typing import Literal

from redi.api.wiki import WikiPage
from redi.tui.state.choice import ChoiceDialogState

WikiDiffColumn = Literal["from", "to"]


@dataclass
class WikiDeleteDialogState:
    """D で開く wiki 削除確認ダイアログの状態。

    wiki は issue_id にあたる数値 id を持たないため、対象の特定ではなく確認語
    (`DELETE`) の入力で確定させる。
    """

    show: bool = False
    target_title: str = ""
    input_text: str = ""
    # 直前の Enter が削除に至らなかった場合に出す注意メッセージ
    notice: str | None = None


@dataclass
class WikiVersionView:
    """h で選んだ過去版の表示状態。

    最新版の表示は `None` で表し、過去版を開いているときだけこれを持つ。
    対象ページを `title` で持つのは、カーソルが別ページへ移った後に古い版の
    本文を別ページのものとして出さないため。`latest` は選んだ時点の最新版番号。
    描画とステータスバーはこれを使い、ページ一覧を引き直さない。
    """

    title: str
    version: int
    text: str
    latest: int


@dataclass
class WikiDiffView:
    """d で選んだ 2 版の差分を右ペインに出している状態。

    閲覧中の版 (`WikiVersionView`) とは独立に持ち、最新版を見ながらでも差分を出せる。
    向きはダイアログで選んだまま (比較前 → 比較後) で、並べ替えない。
    `diff` は適用時に作った unified diff で、`WikiVersionView.text` と同じく描画は
    これを出すだけにする (空なら差分無し)。
    """

    title: str
    from_version: int
    to_version: int
    diff: str


@dataclass
class WikiDiffDialogState:
    """d で開く、比較前と比較後の版を 2 列で選ぶダイアログの状態。

    フィルタダイアログと同じく列ごとにカーソルを持ち、Tab で列を移る。
    `versions` は最新が先頭で、両列とも同じ並びを出す。列は 2 つしか無いので
    カーソルは列名をキーにした dict で持ち、振り分け関数を置かない。
    """

    show: bool = False
    focus: WikiDiffColumn = "from"
    versions: list[int] = field(default_factory=list)
    cursors: dict[WikiDiffColumn, int] = field(
        default_factory=lambda: {"from": 0, "to": 0}
    )


@dataclass
class WikiTabState:
    loaded: bool = False
    pages: list[WikiPage] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    cursor: int = 0
    texts: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    delete_dialog: WikiDeleteDialogState = field(default_factory=WikiDeleteDialogState)
    # h で開く版選択ダイアログ。描画とキー操作は `tui.choice_dialog` の共通部品を使う。
    version_dialog: ChoiceDialogState = field(default_factory=ChoiceDialogState)
    # 過去版を表示中ならその内容。None は最新版を表示している。
    version_view: WikiVersionView | None = None
    # 過去版の本文キャッシュ。過去版は変わらないので (title, version) で持つ。
    version_texts: dict[tuple[str, int], str] = field(default_factory=dict)
    # d で開く、比較前と比較後の版を選ぶダイアログ。
    diff_dialog: WikiDiffDialogState = field(default_factory=WikiDiffDialogState)
    # 差分を表示中ならその 2 版。None なら本文を表示している。
    diff_view: WikiDiffView | None = None
