from typing import TypedDict

from redi.client import client


class IssueTemplate(TypedDict):
    """redmine_issue_templates プラグインで提供されるIssueTemplate
    GET /projects/{project_id}/issue_templates.json のレスポンスに含まれる

    https://www.redmine.org/plugins/redmine_issue_templates
    """

    id: int
    tracker_id: int
    tracker_name: str
    title: str
    issue_title: str
    description: str
    note: str
    enabled: bool
    created_on: str
    updated_on: str


TEMPLATE_KEYS = ("issue_templates", "inherit_templates", "global_issue_templates")


def fetch_issue_templates(
    project_id: str, tracker_id: str | None = None
) -> dict[str, list[IssueTemplate]] | None:
    """テンプレートを種別毎にまとめて返す。

    プラグイン未インストール時は None を返す。
    tracker_id を指定すると、その tracker に紐づくテンプレートのみが返る。
    """
    if tracker_id is not None:
        response = client.get(
            f"/projects/{project_id}/issue_templates/list_templates.json",
            params={"issue_tracker_id": tracker_id},
        )
    else:
        response = client.get(f"/projects/{project_id}/issue_templates.json")
    # プラグイン非インストール時
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def fetch_enabled_issue_templates(
    project_id: str, tracker_id: str | None = None
) -> list[IssueTemplate]:
    """issue create フローで選択肢として並べる有効なテンプレートを取得する。

    プラグイン未インストール時は空リストを返す。
    tracker_id を指定すると、その tracker に紐づくテンプレートのみに絞り込む。
    """
    data = fetch_issue_templates(project_id, tracker_id)
    # プラグイン未インストール時は create を中断せずテンプレートなしとして扱う
    if data is None:
        return []
    templates: list[IssueTemplate] = []
    for key in TEMPLATE_KEYS:
        for template in data.get(key) or []:
            if not template.get("enabled", True):
                continue
            if tracker_id is not None and str(template.get("tracker_id")) != str(
                tracker_id
            ):
                continue
            templates.append(template)
    return templates
