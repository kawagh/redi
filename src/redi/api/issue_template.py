from __future__ import annotations

import json
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
        exit(1)
    response.raise_for_status()
    return response.json()


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
