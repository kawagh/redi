"""`issue list` / `issue view` の表示整形。

取得は `service.issue_service` に任せ、ここでは print と sys.exit を担当する。
"""

import json
import sys
import webbrowser

from redi.api.exceptions import ProjectNotFoundException, QueryNotFoundException
from redi.api.issue import Issue, IssueNotFoundException
from redi.i18n import messages
from redi.output import eprint
from redi.service import issue_service
from redi.text_format import issue_meta_rows, render_meta_table

# Redmine の関連は片側にだけ記録されるため、相手側から見た関連名に読み替える
INVERSE_RELATION = {
    "precedes": "follows",
    "follows": "precedes",
    "blocks": "blocked",
    "blocked": "blocks",
    "duplicates": "duplicated",
    "duplicated": "duplicates",
    "copied_to": "copied_from",
    "copied_from": "copied_to",
    "relates": "relates",
}


def list_issues(
    project_id: str | None = None,
    fixed_version_id: str | None = None,
    assigned_to: str | None = None,
    status_id: str | None = None,
    tracker_id: str | None = None,
    priority_id: str | None = None,
    query_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    full: bool = False,
) -> None:
    """イシュー一覧を1行ずつ出す。full=True では取得した JSON をそのまま出す。

    Redmine が既定 25 件で打ち切るため、全件出せなかったときは表示範囲と総件数を
    標準エラーに出す。パイプで受け取る側の行を汚さないよう標準出力には混ぜない。

    存在しないプロジェクト・カスタムクエリを指定した場合は案内を出して exit 1。
    """
    try:
        page = issue_service.list_issues_page(
            project_id=project_id,
            fixed_version_id=fixed_version_id,
            assigned_to=assigned_to,
            status_id=status_id,
            tracker_id=tracker_id,
            priority_id=priority_id,
            query_id=query_id,
            limit=limit,
            offset=offset,
        )
    except QueryNotFoundException:
        eprint(messages.query_not_found.format(id=query_id))
        eprint(messages.query_not_found_hint)
        sys.exit(1)
    except ProjectNotFoundException:
        eprint(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    if full:
        print(json.dumps(page, ensure_ascii=False))
        return
    issues = page["issues"]
    for issue in issues:
        print(
            f"{issue['id']} {issue['subject']} "
            f"{issue_service.issue_url(str(issue['id']))}"
        )
    notice = truncation_notice(
        shown=len(issues),
        offset=page.get("offset", 0),
        total_count=page.get("total_count", len(issues)),
    )
    if notice:
        print(notice, file=sys.stderr)


def truncation_notice(shown: int, offset: int, total_count: int) -> str | None:
    """一覧が総件数の一部しか出せていないときに、表示範囲を伝える1行を返す。

    全件出せている場合は None を返し、何も出さない。
    """
    if shown == 0 or shown >= total_count:
        return None
    return messages.issue_list_truncated.format(
        start=offset + 1,
        end=offset + shown,
        total=total_count,
    )


def view_issue(
    issue_id: str, include: str = "", full: bool = False, web: bool = False
) -> None:
    """イシューの詳細を標準出力に出す。存在しない場合は exit 1。"""
    if web:
        url = issue_service.issue_url(issue_id)
        print(url)
        webbrowser.open(url)
        return
    # コメントは既定で表示するため journals も常に取得する
    includes = ["relations", "attachments", "journals"]
    if include:
        for name in include.split(","):
            name = name.strip()
            if name and name not in includes:
                includes.append(name)
    try:
        issue = issue_service.read_issue(issue_id, include=",".join(includes))
    except IssueNotFoundException:
        eprint(messages.issue_not_found.format(id=issue_id))
        sys.exit(1)
    if full:
        print(json.dumps(issue, ensure_ascii=False))
        return
    print("\n".join(format_issue_detail(issue)))


def format_issue_detail(issue: Issue) -> list[str]:
    """イシューの詳細表示を行のリストに整形する。

    件名の下にメタ情報テーブルを出し、`----` で区切って説明・コメントを続ける。
    TUI の右ペイン(プレビュー)と同じ見た目になるよう `text_format` を共有する。
    """
    lines = []
    lines.append(f"#{issue['id']} {issue['subject']}")
    lines.append("")
    lines.extend(render_meta_table(issue_meta_rows(issue)))
    if issue.get("description"):
        lines.append("")
        lines.append("----")
        lines.append(issue["description"])
    relations = issue.get("relations") or []
    if relations:
        lines.append("")
        lines.append(messages.label_relations_header)
        target_id = issue["id"]
        relation_labels = {
            "relates": messages.relation_label_relates,
            "duplicates": messages.relation_label_duplicates,
            "duplicated": messages.relation_label_duplicated,
            "blocks": messages.relation_label_blocks,
            "blocked": messages.relation_label_blocked,
            "precedes": messages.relation_label_precedes,
            "follows": messages.relation_label_follows,
            "copied_to": messages.relation_label_copied_to,
            "copied_from": messages.relation_label_copied_from,
        }
        for r in relations:
            if r["issue_id"] == target_id:
                other = r["issue_to_id"]
                rel_type = r["relation_type"]
            else:
                other = r["issue_id"]
                rel_type = INVERSE_RELATION.get(r["relation_type"], r["relation_type"])
            if isinstance(rel_type, str):
                label = relation_labels.get(rel_type)
            else:
                # unknown rel_type
                label = rel_type
            lines.append(f"  [{label}] {issue_service.issue_url(str(other))}")
    attachments = issue.get("attachments") or []
    if attachments:
        lines.append("")
        lines.append(messages.label_attachments_header)
        for a in attachments:
            lines.append(f"  {a['filename']} {a.get('content_url', '')}")
    children = issue.get("children") or []
    if children:
        lines.append("")
        lines.append(messages.label_children_header)
        for c in children:
            lines.append(f"  #{c['id']} {c.get('subject', '')}")
    watchers = issue.get("watchers") or []
    if watchers:
        lines.append("")
        lines.append(messages.label_watchers_header)
        for w in watchers:
            lines.append(f"  {w.get('name', w.get('id', ''))}")
    allowed_statuses = issue.get("allowed_statuses") or []
    if allowed_statuses:
        lines.append("")
        lines.append(messages.label_allowed_statuses_header)
        for s in allowed_statuses:
            lines.append(f"  {s.get('id')} {s.get('name')}")
    changesets = issue.get("changesets") or []
    if changesets:
        lines.append("")
        lines.append(messages.label_revisions_header)
        for c in changesets:
            lines.append(f"  {c.get('revision', '')} {c.get('comments', '')}".rstrip())
    journals = issue.get("journals") or []
    if journals:
        lines.append("")
        lines.append("----")
        lines.append(messages.label_journals_header)
        for j in journals:
            author = (j.get("user") or {}).get("name", "")
            created = j.get("created_on", "")
            lines.append(f"  [{created}] {author}")
            for d in j.get("details") or []:
                name = d.get("name", "")
                old = d.get("old_value", "")
                new = d.get("new_value", "")
                lines.append(f"    {name}: {old} → {new}")
            notes = j.get("notes") or ""
            for nl in notes.splitlines():
                lines.append(f"    {nl}")
    return lines
