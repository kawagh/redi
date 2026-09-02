"""イシュー一覧の列構成。

CLI (`redi issue list`) と TUI の一覧ペインで同じものが見えるよう、列の構成を
ここ 1 箇所で決める。レイアウトは redmine#48 の案に合わせた。

    ● #27 [機能] サブコマンドのタイポに優しい誘導が欲しい (未担当)
    ✓ #4  [機能] 破壊的コマンドに確認プロンプトが無い     (Admin)

- 先頭マーカーで open(●) / closed(✓) を区別する
- URL は 1 行の大半を占めるので既定では出さない
- 件名は端末幅に収まるよう切り詰める(全角込みの表示幅で数える)
"""

from __future__ import annotations

from redi.api.issue import Issue
from redi.i18n import messages
from redi.service.issue_service import issue_url
from redi.text_format import display_width, pad_display, truncate_display

OPEN_MARKER = "●"
CLOSED_MARKER = "✓"

_COLUMN_SEPARATOR = " "
# 端末が狭くても件名が消えてしまわないよう、切り詰めの下限を設ける
_MIN_SUBJECT_WIDTH = 8
_SUBJECT_COLUMN = 3


def _marker(issue: Issue) -> str:
    status = issue.get("status") or {}
    return CLOSED_MARKER if status.get("is_closed") else OPEN_MARKER


def _tracker(issue: Issue) -> str:
    name = (issue.get("tracker") or {}).get("name", "")
    return f"[{name}]" if name else ""


def _assignee(issue: Issue) -> str:
    assigned_to = issue.get("assigned_to") or {}
    return f"({assigned_to.get('name') or messages.issue_list_unassigned})"


def _columns(issue: Issue, show_url: bool) -> list[str]:
    columns = [
        _marker(issue),
        f"#{issue['id']}",
        _tracker(issue),
        issue.get("subject", ""),
        _assignee(issue),
    ]
    if show_url:
        columns.append(issue_url(str(issue["id"])))
    return columns


def _subject_width(widths: list[int], width: int | None) -> int:
    """件名の列幅を返す。`width` に収まらない場合だけ狭める。"""
    subject_width = widths[_SUBJECT_COLUMN]
    if width is None:
        return subject_width
    others = sum(widths) - subject_width
    separators = _COLUMN_SEPARATOR * (len(widths) - 1)
    room = width - others - display_width(separators)
    return max(_MIN_SUBJECT_WIDTH, min(subject_width, room))


def format_issue_list(
    issues: list[Issue], *, width: int | None = None, show_url: bool = False
) -> list[str]:
    """イシュー一覧を 1 件 1 行に整形する。

    `width` を渡すとその表示幅に収まるよう件名を切り詰める。列幅は渡された
    イシューの中で揃える。
    """
    if not issues:
        return []
    rows = [_columns(issue, show_url) for issue in issues]
    widths = [max(display_width(row[i]) for row in rows) for i in range(len(rows[0]))]
    widths[_SUBJECT_COLUMN] = _subject_width(widths, width)
    lines = []
    for row in rows:
        row[_SUBJECT_COLUMN] = truncate_display(
            row[_SUBJECT_COLUMN], widths[_SUBJECT_COLUMN]
        )
        cells = [pad_display(cell, widths[i]) for i, cell in enumerate(row)]
        lines.append(_COLUMN_SEPARATOR.join(cells).rstrip())
    return lines
