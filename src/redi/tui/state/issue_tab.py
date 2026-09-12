"""issue タブの状態。"""

from dataclasses import dataclass, field
from typing import Literal

from redi.api.issue import Issue
from redi.i18n import messages

FilterField = Literal["status", "assignee", "tracker", "query"]


@dataclass
class IssueFilter:
    """Issue 一覧のサーバーサイドフィルタ条件。

    Redmine API の `status_id` / `assigned_to_id` / `tracker_id` / `query_id`
    パラメータに渡す値を保持する。`status_id is None` のときは Redmine デフォルト
    挙動 (open のみ) になる。

    Redmine は `query_id` を渡すとカスタムクエリ側の条件を優先し、同時に渡した
    status / assignee / tracker を捨てる。捨てられた条件がステータスラインに
    残ると嘘になるので、`apply` で排他にして片方だけが立つようにする。
    """

    status_id: str | None = None
    status_label: str = messages.tui_filter_status_open_default
    assigned_to_id: str | None = None
    assigned_to_label: str = messages.tui_filter_assignee_none
    tracker_id: str | None = None
    tracker_label: str = messages.tui_filter_unspecified
    query_id: str | None = None
    query_label: str = messages.tui_filter_unspecified

    def apply(self, field: FilterField, value: str | None, label: str) -> None:
        """フィルタダイアログで選ばれた 1 項目を反映する。

        クエリと status / assignee / tracker は Redmine 側で両立しないため、
        有効な値 (None でない) を選んだら反対側をクリアする。「(指定なし)」の
        選択は絞り込みを外す操作なので、反対側には触らない。
        """
        match field:
            case "status":
                self.status_id, self.status_label = value, label
            case "assignee":
                self.assigned_to_id, self.assigned_to_label = value, label
            case "tracker":
                self.tracker_id, self.tracker_label = value, label
            case "query":
                self.query_id, self.query_label = value, label
        if value is None:
            return
        if field == "query":
            self.clear_conditions()
        else:
            self.clear_query()

    def clear_conditions(self) -> None:
        """status / assignee / tracker の絞り込みを既定に戻す。"""
        self.status_id = None
        self.status_label = messages.tui_filter_status_open_default
        self.assigned_to_id = None
        self.assigned_to_label = messages.tui_filter_assignee_none
        self.tracker_id = None
        self.tracker_label = messages.tui_filter_unspecified

    def clear_query(self) -> None:
        """クエリの絞り込みを外す。"""
        self.query_id = None
        self.query_label = messages.tui_filter_unspecified

    def is_active(self) -> bool:
        return (
            self.status_id is not None
            or self.assigned_to_id is not None
            or self.tracker_id is not None
            or self.query_id is not None
        )

    def short_label(self) -> str:
        if self.query_id is not None:
            return f"query={self.query_label}"
        parts = []
        if self.status_id is not None:
            parts.append(f"status={self.status_label}")
        if self.assigned_to_id is not None:
            parts.append(f"assignee={self.assigned_to_label}")
        if self.tracker_id is not None:
            parts.append(f"tracker={self.tracker_label}")
        return " ".join(parts)


@dataclass
class FilterDialogState:
    """f で開くフィルタダイアログの表示・選択肢キャッシュ・カーソル状態。

    実際のフィルタ条件 (`IssueFilter`) とは別にして、ダイアログを閉じれば破棄してよい
    一時的な UI 状態をここにまとめる。
    """

    show: bool = False
    # 現在カーソルがあるセクション (status / assignee / tracker / query)
    focus: FilterField = "status"
    # 各セクションの選択肢: (Redmine API に渡す値, 表示ラベル) の組
    status_choices: list[tuple[str | None, str]] = field(default_factory=list)
    assignee_choices: list[tuple[str | None, str]] = field(default_factory=list)
    tracker_choices: list[tuple[str | None, str]] = field(default_factory=list)
    query_choices: list[tuple[str | None, str]] = field(default_factory=list)
    # 各セクション内のカーソル位置
    status_cursor: int = 0
    assignee_cursor: int = 0
    tracker_cursor: int = 0
    query_cursor: int = 0


@dataclass
class CommentSelectState:
    """issueタブのコメント選択時の状態"""

    active: bool = False
    cursor: int = 0
    editable_indexes: list[int] = field(default_factory=list)


@dataclass
class IssueFind:
    """F で開く検索の条件。Redmine の検索 API に渡すクエリを保持する。

    `/` のバッファ内検索 (`TuiState.search_query`) とは別物で、こちらは API を叩いて
    イシュー一覧そのものを置き換える。
    """

    query: str = ""

    def is_active(self) -> bool:
        return bool(self.query)

    def short_label(self) -> str:
        if not self.query:
            return ""
        return f"find={self.query}"


@dataclass
class IssueFindDialogState:
    """F で開く検索ダイアログの表示と入力状態。"""

    show: bool = False
    input_text: str = ""


@dataclass
class IssueDeleteDialogState:
    """D で開く issue 削除確認ダイアログの状態。"""

    show: bool = False
    target_id: int = 0
    target_subject: str = ""
    input_text: str = ""
    # 直前の Enter が削除に至らなかった場合に出す注意メッセージ
    notice: str | None = None


@dataclass
class IssueTabState:
    offset: int = 0
    cursor: int = 0
    issues: list[Issue] = field(default_factory=list)
    total_count: int = 0
    filter: IssueFilter = field(default_factory=IssueFilter)
    filter_dialog: FilterDialogState = field(default_factory=FilterDialogState)
    find: IssueFind = field(default_factory=IssueFind)
    find_dialog: IssueFindDialogState = field(default_factory=IssueFindDialogState)
    comment_select: CommentSelectState = field(default_factory=CommentSelectState)
    delete_dialog: IssueDeleteDialogState = field(
        default_factory=IssueDeleteDialogState
    )
