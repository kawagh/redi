from __future__ import annotations

import json
import sys
from typing import TypedDict

from redi.client import client
from redi.i18n import messages


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


_KEYS = ("issue_templates", "inherit_templates", "global_issue_templates")


def fetch_issue_templates(project_id: str) -> dict[str, list[IssueTemplate]]:
    response = client.get(f"/projects/{project_id}/issue_templates.json")
    # プラグイン非インストール時
    if response.status_code == 404:
        print(messages.issue_template_not_available)
        sys.exit(1)
    response.raise_for_status()
    return response.json()


def fetch_enabled_issue_templates(
    project_id: str, tracker_id: str | None = None
) -> list[IssueTemplate]:
    """issue create フローで選択肢として並べる有効なテンプレートを取得する。

    プラグイン未インストール時は exit せず空リストを返す。
    tracker_id を指定すると、その tracker に紐づくテンプレートのみに絞り込む。
    """
    response = client.get(f"/projects/{project_id}/issue_templates.json")
    # プラグイン非インストール時は create を中断せずテンプレートなしとして扱う
    if response.status_code == 404:
        return []
    response.raise_for_status()
    data = response.json()
    templates: list[IssueTemplate] = []
    for key in _KEYS:
        for template in data.get(key) or []:
            if not template.get("enabled", True):
                continue
            if tracker_id is not None and str(template.get("tracker_id")) != str(
                tracker_id
            ):
                continue
            templates.append(template)
    return templates


def list_issue_templates(project_id: str, full: bool = False) -> None:
    templates = fetch_issue_templates(project_id)
    if full:
        print(json.dumps(templates, ensure_ascii=False))
        return
    for key in _KEYS:
        section = templates.get(key) or []
        if not section:
            continue
        print(f"# {key}")
        for template in section:
            print(f"{template['id']} {template['title']}")
