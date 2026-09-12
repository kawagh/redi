from wcwidth import wcswidth

from redi.api.issue import Issue
from redi.i18n import messages


def pad_display(text: str, width: int) -> str:
    padding = max(0, width - wcswidth(text))
    return text + " " * padding


def highlight_segments(
    text: str,
    query: str,
    base_style: str = "",
    hit_style: str = "reverse",
) -> list[tuple[str, str]]:
    """
    `text` の中で `query` (case-insensitive) にマッチする部分を
    `hit_style` で、それ以外を `base_style` で返す `(style, chunk)` のリスト。
    `query` が空なら全体を `base_style` で返す。
    """
    if not query:
        return [(base_style, text)]
    lower_text = text.lower()
    lower_query = query.lower()
    segments: list[tuple[str, str]] = []
    i = 0
    query_len = len(query)
    while i < len(text):
        idx = lower_text.find(lower_query, i)
        if idx == -1:
            segments.append((base_style, text[i:]))
            break
        if idx > i:
            segments.append((base_style, text[i:idx]))
        end = idx + query_len
        segments.append((hit_style, text[idx:end]))
        i = end
    return segments


def render_meta_table(meta: list[tuple[str, str]]) -> list[str]:
    """
    `[ラベル] 値` 形式のメタ情報テーブルを整形する。ラベル列はメタの中で
    最大表示幅に揃える。値が空文字列のときは `-` を表示する。
    """
    if not meta:
        return []
    label_width = max(wcswidth(label) for label, _ in meta)
    return [
        f"[{pad_display(label, label_width)}] {value if value else '-'}"
        for label, value in meta
    ]


def issue_meta_rows(issue: Issue) -> list[tuple[str, str]]:
    """イシューのメタ情報を `(ラベル, 値)` の並びにする。

    CLI の `issue view` と TUI のプレビューで同じ表を出すために共有する。
    """

    def named(field: str) -> str:
        value = issue.get(field)
        if isinstance(value, dict):
            return value.get("name", "")
        return ""

    # Redmine は親がある場合のみ `"parent": {"id": N}` を返し、subject は含まない
    parent = issue.get("parent")
    parent_value = f"#{parent['id']}" if parent else ""

    return [
        (messages.meta_status, named("status")),
        (messages.meta_priority, named("priority")),
        (messages.meta_tracker, named("tracker")),
        (messages.meta_parent, parent_value),
        (messages.meta_assignee, named("assigned_to")),
        (messages.meta_author, named("author")),
        (messages.meta_start_date, issue.get("start_date") or ""),
        (messages.meta_due_date, issue.get("due_date") or ""),
        (
            messages.meta_progress,
            f"{issue['done_ratio']}%" if issue.get("done_ratio") is not None else "",
        ),
        (
            messages.meta_estimated_hours,
            f"{issue['estimated_hours']} h"
            if issue.get("estimated_hours") is not None
            else "",
        ),
        (
            messages.meta_spent_hours,
            f"{issue['spent_hours']} h" if issue.get("spent_hours") is not None else "",
        ),
        (messages.meta_created, issue.get("created_on") or ""),
        (messages.meta_updated, issue.get("updated_on") or ""),
    ]
