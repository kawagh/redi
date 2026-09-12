"""time_entry タブの状態。"""

from dataclasses import dataclass, field

from redi.api.time_entry import TimeEntry
from redi.i18n import messages


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
