"""検索 API を CLI / TUI から使いやすい形に整えるサービス。

`/search.json` は `id` / `title` / `description` などしか返さないため、そのままでは
イシュー一覧の描画に必要な status や assigned_to が足りない。ここで検索結果の id を
`/issues.json` で引き直し、通常のイシュー一覧と同じ `IssuesPageResponse` に揃える。
"""

from redi.api.issue import Issue, IssuesPageResponse, fetch_issues_page
from redi.api.search import search

# `/issues.json` は既定で未完了のイシューしか返すため、検索でヒットした終了済みが
# 引き直しで消えてしまう。id を指定して引く以上、ステータスでの絞り込みは不要。
_ALL_STATUSES = "*"


def search_issues_page(
    query: str,
    project_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> IssuesPageResponse:
    """検索クエリに一致するイシューを1ページ分、完全な `Issue` として返す。

    並び順は検索 API が返した順 (更新日時の降順) を保つ。
    `total_count` は検索側の総数で、引き直した件数ではない。
    """
    found = search(
        query=query,
        limit=limit,
        offset=offset,
        project_id=project_id,
        types=["issues"],
    )
    total_count = found.get("total_count", 0)
    issue_ids = [r["id"] for r in found.get("results", []) if r.get("type") == "issue"]
    if not issue_ids:
        return IssuesPageResponse(
            issues=[],
            total_count=total_count,
            offset=offset or 0,
            limit=limit or 0,
        )

    page = fetch_issues_page(
        issue_id=",".join(str(issue_id) for issue_id in issue_ids),
        status_id=_ALL_STATUSES,
        # 既定の 25 件で切られると検索結果の後半が落ちるため、件数を明示する
        limit=len(issue_ids),
    )
    by_id: dict[int, Issue] = {
        issue["id"]: issue for issue in page["issues"] if issue.get("id") is not None
    }
    # 引き直しの結果は id 降順で返るので、検索の並びに戻す。
    # 検索後に削除されるなどして引けなかった id は落とす。
    issues = [by_id[issue_id] for issue_id in issue_ids if issue_id in by_id]
    return IssuesPageResponse(
        issues=issues,
        total_count=total_count,
        offset=offset or 0,
        limit=limit or 0,
    )
