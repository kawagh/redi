from __future__ import annotations

import json
import sys
from typing import NotRequired, TypedDict, cast

import requests

from redi.api.exceptions import print_http_error_body
from redi.api.types import Attachment, IdName
from redi.client import client
from redi.i18n import messages


class NewsComment(TypedDict):
    """ニュースへのコメント。

    include=comments で返るフィールドを記載。
    Redmine はコメントの投稿日時を API で返さない。
    """

    id: int
    author: IdName
    content: str


class News(TypedDict):
    """redmine News

    GET /news.json / GET /projects/{id}/news.json / GET /news/{id}.json を
    実行して確認できたフィールドを記載。
    """

    id: int
    project: IdName
    author: IdName
    title: str
    description: str
    created_on: str
    # 個別取得では未設定(空)のとき存在しない。一覧では空文字で返る
    summary: NotRequired[str]
    # include 指定時のみ存在
    attachments: NotRequired[list[Attachment]]
    comments: NotRequired[list[NewsComment]]


def list_news(project_id: str | None = None, full: bool = False) -> None:
    if project_id:
        path = f"/projects/{project_id}/news.json"
    else:
        path = "/news.json"
    response = client.get(path)
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    response.raise_for_status()
    news_list = cast("list[News]", response.json()["news"])
    if full:
        print(json.dumps(news_list, ensure_ascii=False))
        return
    for news in news_list:
        parts = [str(news["id"]), news["title"]]
        project = news["project"]["name"]
        if project:
            parts.append(f"[{project}]")
        author = news["author"]["name"]
        if author:
            parts.append(f"by {author}")
        if news["created_on"]:
            parts.append(news["created_on"])
        print(" ".join(parts))


def fetch_news(news_id: str) -> News:
    response = client.get(
        f"/news/{news_id}.json", params={"include": "attachments,comments"}
    )
    if response.status_code == 404:
        print(messages.news_not_found.format(id=news_id))
        sys.exit(1)
    response.raise_for_status()
    return cast("News", response.json()["news"])


def read_news(news_id: str, full: bool = False) -> None:
    news = fetch_news(news_id)
    if full:
        print(json.dumps(news, ensure_ascii=False))
        return
    lines = [f"{news['id']} {news['title']}"]
    project = news["project"]
    lines.append(
        messages.label_project_field.format(id=project["id"], name=project["name"])
    )
    lines.append(messages.label_author.format(value=news["author"]["name"]))
    lines.append(messages.label_created_on.format(value=news["created_on"]))
    summary = news.get("summary")
    if summary:
        lines.append(messages.label_summary_field.format(value=summary))
    if news["description"]:
        lines.append("")
        lines.append(news["description"])
    attachments = news.get("attachments") or []
    if attachments:
        lines.append("")
        lines.append(messages.label_attachments_header)
        for a in attachments:
            lines.append(f"  {a['filename']} {a['content_url']}")
    comments = news.get("comments") or []
    if comments:
        lines.append("")
        lines.append(messages.label_news_comments_header)
        for c in comments:
            lines.append(f"  {c['id']} {c['author']['name']}")
            if c["content"]:
                lines.append(f"    {c['content'].strip()}")
    print("\n".join(lines))


def create_news(
    project_id: str,
    title: str,
    description: str,
    summary: str | None = None,
) -> None:
    data: dict = {"title": title, "description": description}
    if summary is not None:
        data["summary"] = summary
    response = client.post(f"/projects/{project_id}/news.json", json={"news": data})
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.news_create_failed)
        sys.exit(1)
    # 作成 API は 204 を返し本文を持たないため、作成した id は表示できない
    print(messages.news_created.format(title=title))


def update_news(
    news_id: str,
    title: str | None = None,
    description: str | None = None,
    summary: str | None = None,
) -> None:
    data: dict = {}
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if summary is not None:
        data["summary"] = summary
    if len(data) == 0:
        print(messages.update_canceled)
        sys.exit()
    response = client.put(f"/news/{news_id}.json", json={"news": data})
    if response.status_code == 404:
        print(messages.news_not_found.format(id=news_id))
        sys.exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.news_update_failed)
        sys.exit(1)
    print(messages.news_updated.format(id=news_id))


def delete_news(news_id: str) -> None:
    response = client.delete(f"/news/{news_id}.json")
    if response.status_code == 404:
        print(messages.news_not_found.format(id=news_id))
        sys.exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.news_delete_failed)
        sys.exit(1)
    print(messages.news_deleted.format(id=news_id))
