# carry_over() が自分自身の型 TuiState を返すため、注釈の評価を遅らせる
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from redi import config
from redi.api import PAGE_LIMIT_MAX
from redi.api.time_entry import TimeEntry
from redi.api.wiki import WikiPage
from redi.i18n import messages
from redi.tui.state.issue import IssueTabState

TuiAction = Literal[
    "update",
    "create",
    "comment",
    "edit_comment",
    "delete_comment",
    "create_time_entry",
    "switch_profile",
]
TuiTab = Literal["issues", "wiki", "time_entries"]
WikiDiffColumn = Literal["from", "to"]

# prompt_toolkit の FormattedTextControl に渡す `(style, text)` 断片のリスト。
Renderable = list[tuple[str, str]]

# 一覧/プレビューの外側にある固定行の合計 (タブバー + 罫線 + ステータスバー)。
# Layout の HSplit に固定行を増減したらここも更新すること。
FIXED_ROWS = 3


def compute_page_size(rows: int) -> int:
    """端末の行数から 1 ページの取得件数を求める。

    固定行 (FIXED_ROWS) を除いた行数が一覧に使える行数。最低 1 件は取り、
    Redmine の limit 上限で頭打ちにする (超えた分は返らず Page 表示と
    実データがずれるため)。
    """
    return max(1, min(rows - FIXED_ROWS, PAGE_LIMIT_MAX))


def realign_page(offset: int, cursor: int, page_size: int) -> tuple[int, int]:
    """カーソル行を保ったまま offset を新しい page_size のページ境界へ揃える。

    `(offset, cursor)` を返す。offset が page_size の倍数になるので、
    ステータスバーの Page 表示 (offset // page_size) が実データとずれない。
    """
    absolute = offset + cursor
    new_offset = (absolute // page_size) * page_size
    return new_offset, absolute - new_offset


@dataclass
class TuiPosition:
    offset: int = 0
    cursor: int = 0


@dataclass
class TuiResult:
    action: TuiAction
    tab: TuiTab
    issue_id: str | None = None
    wiki_title: str | None = None
    parent_wiki_title: str | None = None
    time_entry_id: str | None = None
    journal_id: str | None = None
    journal_notes: str = ""
    # action == "switch_profile" のときの切替先プロファイル名。
    profile_name: str | None = None
    position: TuiPosition = field(default_factory=TuiPosition)


@dataclass
class ChoiceModalState:
    """一覧から1つ選ぶ modal (p のプロジェクト切替 / P のプロファイル切替) の状態。

    描画とキーバインドは `tui.choice_modal` が共通で持つ。
    """

    show: bool = False
    # 選択肢: (値, 表示ラベル) の組
    choices: list[tuple[str, str]] = field(default_factory=list)
    cursor: int = 0
    # 現在有効な選択肢の値。`*` 表示とカーソル初期位置に使う。プロジェクトは
    # config に identifier も設定できるため、開くときに id へ解決してから入れる。
    active_value: str | None = None


@dataclass
class WikiDeleteModalState:
    """D で開く wiki 削除確認 modal の状態。

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
    向きは modal で選んだまま (比較前 → 比較後) で、並べ替えない。
    `diff` は適用時に作った unified diff で、`WikiVersionView.text` と同じく描画は
    これを出すだけにする (空なら差分無し)。
    """

    title: str
    from_version: int
    to_version: int
    diff: str


@dataclass
class WikiDiffModalState:
    """d で開く、比較前と比較後の版を 2 列で選ぶ modal の状態。

    フィルタ modal と同じく列ごとにカーソルを持ち、Tab で列を移る。
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
    delete_modal: WikiDeleteModalState = field(default_factory=WikiDeleteModalState)
    # h で開く版選択 modal。描画とキー操作は `tui.choice_modal` の共通部品を使う。
    version_modal: ChoiceModalState = field(default_factory=ChoiceModalState)
    # 過去版を表示中ならその内容。None は最新版を表示している。
    version_view: WikiVersionView | None = None
    # 過去版の本文キャッシュ。過去版は変わらないので (title, version) で持つ。
    version_texts: dict[tuple[str, int], str] = field(default_factory=dict)
    # d で開く、比較前と比較後の版を選ぶ modal。
    diff_modal: WikiDiffModalState = field(default_factory=WikiDiffModalState)
    # 差分を表示中ならその 2 版。None なら本文を表示している。
    diff_view: WikiDiffView | None = None


@dataclass
class TimeEntryFilter:
    """time_entry 一覧のサーバーサイドフィルタ条件。

    Redmine API の `user_id` パラメータに渡す値を保持する。`me` は自分。
    デフォルトは「自分」(`me`)。
    """

    user_id: str | None = "me"
    user_label: str = messages.tui_filter_assignee_me

    def is_active(self) -> bool:
        return self.user_id is not None

    def short_label(self) -> str:
        if self.user_id is None:
            return ""
        return f"user={self.user_label}"


@dataclass
class TimeEntryFilterModalState:
    """time_entry タブの filter modal の表示・選択肢キャッシュ・カーソル状態。"""

    show: bool = False
    user_choices: list[tuple[str | None, str]] = field(default_factory=list)
    user_cursor: int = 0


@dataclass
class TimeEntryTabState:
    loaded: bool = False
    offset: int = 0
    entries: list[TimeEntry] = field(default_factory=list)
    total_count: int = 0
    issue_subjects: dict[int, str] = field(default_factory=dict)
    cursor: int = 0
    error: str | None = None
    filter: TimeEntryFilter = field(default_factory=TimeEntryFilter)
    filter_modal: TimeEntryFilterModalState = field(
        default_factory=TimeEntryFilterModalState
    )


@dataclass
class TuiState:
    last_result: TuiResult | None = None
    page_size: int = 0
    tab: TuiTab = "issues"
    issue_tab: IssueTabState = field(default_factory=IssueTabState)
    wiki_tab: WikiTabState = field(default_factory=WikiTabState)
    time_entry_tab: TimeEntryTabState = field(default_factory=TimeEntryTabState)
    # <N>G で issue にジャンプする際に入力中の数字列を保持する。
    number_buffer: str = ""
    # / で検索中かどうか、および現在のクエリ (確定後も保持して n/N とハイライトに使う)。
    search_mode: bool = False
    search_query: str = ""
    # time_entries タブで D 押下時の削除確認プロンプト (status bar に y/N で出す)。
    # issue タブはステータスバーではなく Float モーダル (issue_tab.delete_modal) で確認する。
    confirm_delete_prompt: str | None = None
    # 直前のアクション結果をステータスバーに出す一時メッセージ。次のキー入力で消える。
    flash_message: str | None = None
    # ? でヘルプの floating window を表示しているかどうか。
    show_help: bool = False
    # 右ペイン (preview) のスクロール位置 (先頭からの行数)。
    # カーソル移動・タブ切り替え時に 0 に戻す。
    preview_scroll: int = 0
    # API エラー等を Float で出すための本文
    error_modal: str | None = None
    # 起動時に `/my/account.json` から取得した自分のユーザー id。
    # フィルタモーダルの選択肢で「自分」と実ユーザーの重複表示を避けるために使う。
    me_id: str | None = None
    # p で切り替えたセッション内のプロジェクト。None は未切替 (config の既定に従う)。
    project_id: str | None = None
    project_label: str = ""
    project_modal: ChoiceModalState = field(default_factory=ChoiceModalState)
    profile_modal: ChoiceModalState = field(default_factory=ChoiceModalState)

    def apply_terminal_rows(self, rows: int) -> bool:
        """端末の行数から page_size を更新する。値が変わったときだけ True を返す。"""
        new_size = compute_page_size(rows)
        if new_size == self.page_size:
            return False
        self.page_size = new_size
        return True

    def effective_project_id(self) -> str | None:
        return self.project_id or config.default_project_id

    def effective_wiki_project_id(self) -> str | None:
        # 明示切替はユーザーの直接操作なので wiki_project_id より優先する。
        return self.project_id or config.wiki_project_id or config.default_project_id

    def carry_over(self, result: TuiResult) -> TuiState:
        """action 実行後の次のTUIループに 絞り込み条件を引き継ぐ"""

        next_state = TuiState(last_result=result)
        next_state.issue_tab.filter = self.issue_tab.filter
        next_state.issue_tab.find = self.issue_tab.find
        next_state.time_entry_tab.filter = self.time_entry_tab.filter
        next_state.project_id = self.project_id
        next_state.project_label = self.project_label
        return next_state
