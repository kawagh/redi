# carry_over() が自分自身の型 TuiState を返すため、注釈の評価を遅らせる
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from redi import config
from redi.api import PAGE_LIMIT_MAX
from redi.tui.state.choice import ChoiceModalState
from redi.tui.state.issue_tab import IssueTabState
from redi.tui.state.time_entry_tab import TimeEntryTabState
from redi.tui.state.wiki_tab import WikiTabState

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
