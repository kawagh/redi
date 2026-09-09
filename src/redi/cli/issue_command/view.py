"""`issue list` / `issue view` の表示整形。

取得は `service.issue_service` に任せ、ここでは print と sys.exit を担当する。
"""

import json
import sys
import webbrowser
from typing import assert_never

from redi.api.exceptions import ProjectNotFoundException, QueryNotFoundException
from redi.api.issue import Issue
from redi.cli.issue_guard import read_issue_or_exit
from redi.cli.shared_options import OutputFormat
from redi.i18n import messages
from redi.output import eprint, print_tsv, tsv_ref
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


def _issue_tsv_row(issue: Issue) -> tuple[object, ...]:
    """イシュー 1 件を tsv の 1 行にする。

    description は複数行・長文なので載せない。custom_fields は可変長なので json に任せる。
    """
    return (
        issue["id"],
        issue["subject"],
        issue_service.issue_url(str(issue["id"])),
        *tsv_ref(issue, "project"),
        tsv_ref(issue, "tracker")[1],
        tsv_ref(issue, "status")[1],
        tsv_ref(issue, "priority")[1],
        tsv_ref(issue, "author")[1],
        *tsv_ref(issue, "assigned_to"),
        tsv_ref(issue, "category")[1],
        tsv_ref(issue, "fixed_version")[1],
        issue.get("start_date"),
        issue.get("due_date"),
        issue.get("done_ratio"),
        issue.get("estimated_hours"),
        issue.get("spent_hours"),
        issue.get("is_private"),
        issue.get("created_on"),
        issue.get("updated_on"),
        issue.get("closed_on"),
    )


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
    fmt: OutputFormat = OutputFormat.PLAIN,
) -> None:
    """イシュー一覧を1行ずつ出す。json では取得した JSON をそのまま出す。

    存在しないプロジェクト・カスタムクエリを指定した場合は案内を出して exit 1。
    """
    try:
        issues = issue_service.list_issues(
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
    match fmt:
        case OutputFormat.JSON:
            print(json.dumps(issues, ensure_ascii=False))
        case OutputFormat.TSV:
            print_tsv(
                (
                    "id",
                    "subject",
                    "url",
                    "project_id",
                    "project_name",
                    "tracker_name",
                    "status_name",
                    "priority_name",
                    "author_name",
                    "assigned_to_id",
                    "assigned_to_name",
                    "category_name",
                    "fixed_version_name",
                    "start_date",
                    "due_date",
                    "done_ratio",
                    "estimated_hours",
                    "spent_hours",
                    "is_private",
                    "created_on",
                    "updated_on",
                    "closed_on",
                ),
                (_issue_tsv_row(i) for i in issues),
            )
        case OutputFormat.PLAIN:
            for issue in issues:
                print(
                    f"{issue['id']} {issue['subject']} "
                    f"{issue_service.issue_url(str(issue['id']))}"
                )
        case _:
            assert_never(fmt)


def view_issue(
    issue_id: str,
    include: list[str] | None = None,
    full: bool = False,
    web: bool = False,
) -> None:
    """イシューの詳細を標準出力に出す。存在しない場合は exit 1。

    include は argparse (`_parse_issue_includes`) で検証済みの値を受け取る。
    """
    if web:
        url = issue_service.issue_url(issue_id)
        print(url)
        webbrowser.open(url)
        return
    # コメントは既定で表示するため journals も常に取得する
    includes = ["relations", "attachments", "journals"]
    for name in include or []:
        if name not in includes:
            includes.append(name)
    issue = read_issue_or_exit(issue_id, include=",".join(includes))
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
            lines.append(f"  {r['id']} [{label}] {issue_service.issue_url(str(other))}")
    attachments = issue.get("attachments") or []
    if attachments:
        lines.append("")
        lines.append(messages.label_attachments_header)
        for a in attachments:
            lines.append(
                f"  {a['id']} {a['filename']} {a.get('content_url', '')}".rstrip()
            )
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
            lines.append(f"  {j['id']} [{created}] {author}")
            for d in j.get("details") or []:
                name = d.get("name", "")
                old = d.get("old_value", "")
                new = d.get("new_value", "")
                lines.append(f"    {name}: {old} → {new}")
            notes = j.get("notes") or ""
            for nl in notes.splitlines():
                lines.append(f"    {nl}")
    return lines
