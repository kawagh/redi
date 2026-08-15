from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from redi import config
from redi.api.issue import Issue
from redi.api.time_entry import TimeEntry
from redi.api.wiki import WikiPage
from redi.i18n import messages

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
FilterField = Literal["status", "assignee"]

# prompt_toolkit の FormattedTextControl に渡す `(style, text)` 断片のリスト。
Renderable = list[tuple[str, str]]

# 一覧/プレビューの外側にある固定行の合計 (タブバー + 罫線 + ステータスバー)。
# Layout の HSplit に固定行を増減したらここも更新すること。
FIXED_ROWS = 3


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
class IssueFilter:
    """Issue 一覧のサーバーサイドフィルタ条件。

    Redmine API の `status_id` / `assigned_to_id` パラメータに渡す値を保持する。
    `status_id is None` のときは Redmine デフォルト挙動 (open のみ) になる。
    """

    status_id: str | None = None
    status_label: str = messages.tui_filter_status_open_default
    assigned_to_id: str | None = None
    assigned_to_label: str = messages.tui_filter_assignee_none

    def is_active(self) -> bool:
        return self.status_id is not None or self.assigned_to_id is not None

    def short_label(self) -> str:
        parts = []
        if self.status_id is not None:
            parts.append(f"status={self.status_label}")
        if self.assigned_to_id is not None:
            parts.append(f"assignee={self.assigned_to_label}")
        return " ".join(parts)


@dataclass
class FilterModalState:
    """f で開くフィルタ modal の表示・選択肢キャッシュ・カーソル状態。

    実際のフィルタ条件 (`IssueFilter`) とは別にして、modal を閉じれば破棄してよい
    一時的な UI 状態をここにまとめる。
    """

    show: bool = False
    # 現在カーソルがあるセクション (status か assignee)
    focus: FilterField = "status"
    # 各セクションの選択肢: (Redmine API に渡す値, 表示ラベル) の組
    status_choices: list[tuple[str | None, str]] = field(default_factory=list)
    assignee_choices: list[tuple[str | None, str]] = field(default_factory=list)
    # 各セクション内のカーソル位置
    status_cursor: int = 0
    assignee_cursor: int = 0


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
class CommentSelectState:
    """issueタブのコメント選択時の状態"""

    active: bool = False
    cursor: int = 0
    editable_indexes: list[int] = field(default_factory=list)


@dataclass
class IssueTabState:
    offset: int = 0
    cursor: int = 0
    issues: list[Issue] = field(default_factory=list)
    total_count: int = 0
    filter: IssueFilter = field(default_factory=IssueFilter)
    filter_modal: FilterModalState = field(default_factory=FilterModalState)
    comment_select: CommentSelectState = field(default_factory=CommentSelectState)


@dataclass
class WikiTabState:
    loaded: bool = False
    pages: list[WikiPage] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    cursor: int = 0
    texts: dict[str, str] = field(default_factory=dict)
    error: str | None = None


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
    # D で削除確認中のとき、ステータスバーに出すプロンプト文字列
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

    def effective_project_id(self) -> str | None:
        return self.project_id or config.default_project_id

    def effective_wiki_project_id(self) -> str | None:
        # 明示切替はユーザーの直接操作なので wiki_project_id より優先する。
        return self.project_id or config.wiki_project_id or config.default_project_id

    def carry_over(self, result: TuiResult) -> TuiState:
        """action 実行後の次のTUIループに 絞り込み条件を引き継ぐ"""

        next_state = TuiState(last_result=result)
        next_state.issue_tab.filter = self.issue_tab.filter
        next_state.time_entry_tab.filter = self.time_entry_tab.filter
        next_state.project_id = self.project_id
        next_state.project_label = self.project_label
        return next_state
