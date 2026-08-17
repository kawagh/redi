from __future__ import annotations

from typing import NotRequired, TypedDict, cast

from redi.api.exceptions import ProjectNotFoundException
from redi.api.types import Attachment, IdName
from redi.client import client


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


class NewsBody(TypedDict):
    """ニュース作成 (POST) / 更新 (PUT) のリクエストボディ。"""

    title: NotRequired[str]
    description: NotRequired[str]
    summary: NotRequired[str]


class NewsNotFoundException(Exception):
    def __init__(self, news_id: str) -> None:
        super().__init__(news_id)
        self.news_id = news_id


def fetch_news_list(
    project_id: str | None = None, limit: int | None = None
) -> list[News]:
    """ニュースを作成日時の降順で返す。project_id 省略時は全プロジェクトが対象。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    if project_id:
        path = f"/projects/{project_id}/news.json"
    else:
        path = "/news.json"
    params: dict = {}
    if limit is not None:
        params["limit"] = limit
    response = client.get(path, params=params)
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()
    return cast("list[News]", response.json()["news"])


def fetch_news(news_id: str) -> News:
    """ニュースを添付ファイル・コメント込みで取得する。

    Raises:
        NewsNotFoundException: 対象ニュースが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.get(
        f"/news/{news_id}.json", params={"include": "attachments,comments"}
    )
    if response.status_code == 404:
        raise NewsNotFoundException(news_id)
    response.raise_for_status()
    return cast("News", response.json()["news"])


def create_news(
    project_id: str,
    title: str,
    description: str,
    summary: str | None = None,
) -> None:
    """ニュースを作成する。

    作成 API は 204 を返し body を持たないため、作成したニュースの id は
    レスポンスからは取れない。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    body: NewsBody = {"title": title, "description": description}
    if summary is not None:
        body["summary"] = summary
    response = client.post(f"/projects/{project_id}/news.json", json={"news": body})
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()


def update_news(
    news_id: str,
    title: str | None = None,
    description: str | None = None,
    summary: str | None = None,
) -> None:
    """ニュースを更新する。None を渡した項目は更新しない。

    Raises:
        NewsNotFoundException: 対象ニュースが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    body: NewsBody = {}
    if title is not None:
        body["title"] = title
    if description is not None:
        body["description"] = description
    if summary is not None:
        body["summary"] = summary
    response = client.put(f"/news/{news_id}.json", json={"news": body})
    if response.status_code == 404:
        raise NewsNotFoundException(news_id)
    response.raise_for_status()


def delete_news(news_id: str) -> None:
    """ニュースを削除する。

    Raises:
        NewsNotFoundException: 対象ニュースが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.delete(f"/news/{news_id}.json")
    if response.status_code == 404:
        raise NewsNotFoundException(news_id)
    response.raise_for_status()
