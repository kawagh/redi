from dataclasses import dataclass, field
from typing import Literal

TuiAction = Literal["update", "create", "comment", "create_time_entry"]
TuiTab = Literal["issues", "wiki", "time_entries"]

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
class IssueTabState:
    offset: int = 0
    cursor: int = 0
    issues: list[dict] = field(default_factory=list)


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
