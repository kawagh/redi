"""ニュース操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.news` が持つ。
"""

from __future__ import annotations

from redi import config
from redi.api import news as news_api
from redi.api.news import News


def news_url(news_id: str | int) -> str:
    """ニュースの Web UI 上の URL を組み立てる。"""
    return f"{config.redmine_url}/news/{news_id}"


def list_news(project_id: str | None = None, limit: int | None = None) -> list[News]:
    """ニュース一覧を作成日時の降順で取得する。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return news_api.fetch_news_list(project_id, limit=limit)


def read_news(news_id: str) -> News:
    """ニュースを取得する。

    Raises:
        NewsNotFoundException: 対象ニュースが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return news_api.fetch_news(news_id)


def create_news(
    project_id: str,
    title: str,
    description: str,
    summary: str | None = None,
) -> str:
    """ニュースを作成し、作成したニュースの URL を返す。

    作成 API は 204 を返し body を持たないため、レスポンスからは作成した
    ニュースの id を取れない。一覧は作成日時の降順で返るので、作成直後に
    先頭を引くことで id を得る。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    news_api.create_news(
        project_id=project_id,
        title=title,
        description=description,
        summary=summary,
    )
    news_id = news_api.fetch_news_list(project_id, limit=1)[0]["id"]
    return news_url(news_id)


def update_news(
    news_id: str,
    title: str | None = None,
    description: str | None = None,
    summary: str | None = None,
) -> str:
    """ニュースを更新し、更新したニュースの URL を返す。None を渡した項目は更新しない。

    Raises:
        NewsNotFoundException: 対象ニュースが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    news_api.update_news(
        news_id,
        title=title,
        description=description,
        summary=summary,
    )
    return news_url(news_id)


def delete_news(news_id: str) -> None:
    """ニュースを削除する。

    Raises:
        NewsNotFoundException: 対象ニュースが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    news_api.delete_news(news_id)
