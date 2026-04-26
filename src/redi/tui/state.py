from dataclasses import dataclass, field
from typing import Literal

TuiAction = Literal["update", "create", "comment", "create_time_entry"]
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
    position: TuiPosition = field(default_factory=TuiPosition)


@dataclass
class IssueFilter:
    """Issue 一覧のサーバーサイドフィルタ条件。

    Redmine API の `status_id` / `assigned_to_id` パラメータに渡す値を保持する。
    `status_id is None` のときは Redmine デフォルト挙動 (open のみ) になる。
    """

    status_id: str | None = None
    status_label: str = "open (デフォルト)"
    assigned_to_id: str | None = None
    assigned_to_label: str = "(指定なし)"

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
class IssueTabState:
    offset: int = 0
    cursor: int = 0
    issues: list[dict] = field(default_factory=list)
    filter: IssueFilter = field(default_factory=IssueFilter)


@dataclass
class WikiTabState:
    loaded: bool = False
    pages: list[dict] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    cursor: int = 0
    texts: dict[str, str] = field(default_factory=dict)
    error: str | None = None


@dataclass
class TimeEntryTabState:
    loaded: bool = False
    entries: list[dict] = field(default_factory=list)
    issue_subjects: dict[int, str] = field(default_factory=dict)
    cursor: int = 0
    error: str | None = None


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
    # f で開く Issue フィルタの floating window を表示中かどうか。
    show_filter: bool = False
    # 1ウインドウ式モーダルで現在カーソルがあるセクション (status か assignee)
    filter_focus: FilterField = "status"
    # 各セクションの選択肢: (Redmine API に渡す値, 表示ラベル) の組
    filter_status_choices: list[tuple[str | None, str]] = field(default_factory=list)
    filter_assignee_choices: list[tuple[str | None, str]] = field(default_factory=list)
    # 各セクション内のカーソル位置
    filter_status_cursor: int = 0
    filter_assignee_cursor: int = 0
