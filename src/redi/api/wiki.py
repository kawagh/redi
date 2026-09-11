# WikiPage が自分より下で定義される WikiPageParent を参照しているため、
# 注釈の評価を遅らせる
from __future__ import annotations

from typing import NotRequired, TypedDict, cast

from redi.api.exceptions import (
    ProjectNotFoundException,
    RedmineValidationException,
    ValidationAction,
)
from redi.api.types import Attachment, IdName
from redi.client import client


class WikiPage(TypedDict):
    """redmine Wiki page

    GET /projects/{id}/wiki/index.json / GET /projects/{id}/wiki/{title}.json を
    実行して確認できたフィールドを記載。
    index では title / version / created_on / updated_on と（あれば）parent のみが
    返り、text / author / comments は個別ページ取得時のみ含まれる。
    """

    title: str
    version: int
    created_on: str
    updated_on: str
    # 親ページを持つ場合のみ存在
    parent: NotRequired[WikiPageParent]
    # 個別ページ取得時のみ存在
    text: NotRequired[str]
    author: NotRequired[IdName]
    comments: NotRequired[str]
    # Redmine 7.0 以降、個別ページ取得時のみ存在
    project: NotRequired[IdName]
    # include=attachments 指定時のみ存在
    attachments: NotRequired[list[Attachment]]


class WikiPageParent(TypedDict):
    """Wiki ページの親ページ参照。`title` のみを持つ。"""

    title: str


class WikiPageBody(TypedDict):
    """Wiki ページ更新 (PUT) のリクエストボディ。作成も同じ PUT で行う。"""

    text: str
    comments: str
    version: NotRequired[int]
    parent_title: NotRequired[str]


class WikiUpdateConflictException(Exception):
    def __init__(self, title: str) -> None:
        super().__init__(title)
        self.title = title


class WikiPageNotFoundException(Exception):
    def __init__(self, title: str) -> None:
        super().__init__(title)
        self.title = title


# redmineで空白文字を含んでwikiのpageを作成するとURLの都合か`_`に置き換えられている
# 既存のwikiのタイトルの先頭文字が大文字になっている
def normalize_title(t: str) -> str:
    normalized = t.strip().replace(" ", "_")
    if normalized and "a" <= normalized[0] <= "z":
        normalized = normalized[0].upper() + normalized[1:]
    return normalized


def fetch_wikis(project_id: str) -> list[WikiPage]:
    """プロジェクトの Wiki ページ一覧を取得する

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.get(f"/projects/{project_id}/wiki/index.json")
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()
    return cast("list[WikiPage]", response.json()["wiki_pages"])


def fetch_wiki(
    project_id: str,
    page_title: str,
    version: int | None = None,
    full: bool = False,
) -> WikiPage | None:
    path = f"/projects/{project_id}/wiki/{page_title}.json"
    if version is not None:
        path = f"/projects/{project_id}/wiki/{page_title}/{version}.json"
    params = {"include": "attachments"} if full else None
    response = client.get(path, params=params)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return cast("WikiPage", response.json()["wiki_page"])


def _put_wiki_page(
    project_id: str,
    page_title: str,
    body: WikiPageBody,
    action: ValidationAction,
) -> None:
    """Wikiページを PUT する

    Raises:
        WikiUpdateConflictException: version がRedmine側の最新バージョンと一致せず、更新が競合した場合（HTTP 409）。
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 409 / 422 以外の HTTP エラーが返った場合
    """
    response = client.put(
        f"/projects/{project_id}/wiki/{page_title}.json",
        json={"wiki_page": body},
    )
    if response.status_code == 409:
        raise WikiUpdateConflictException(page_title)
    if response.status_code == 422:
        raise RedmineValidationException.from_response("wiki", action, response)
    response.raise_for_status()


def create_wiki_page(
    project_id: str,
    page_title: str,
    text: str,
    parent_title: str | None = None,
    comments: str = "",
) -> None:
    """Wikiページを作成する

    Redmine の Wiki 作成は更新と同じ PUT なので、既存のタイトルを渡すと更新になる。
    """
    body: WikiPageBody = {"text": text, "comments": comments}
    if parent_title:
        body["parent_title"] = parent_title
    _put_wiki_page(project_id, page_title, body, "create")


def update_wiki_page(
    project_id: str,
    page_title: str,
    text: str,
    version: int | None = None,
    comments: str = "",
) -> None:
    """Wikiページを更新する

    Args:
        version: 更新対象の期待バージョン。
                 指定するとRedmine 側のバージョンと一致しない場合に409 が返る。
                 Noneの場合はバージョンチェックを行わない
        comments: 更新時のコメント（変更履歴に記録される）
    """
    body: WikiPageBody = {"text": text, "comments": comments}
    if version is not None:
        body["version"] = version
    _put_wiki_page(project_id, page_title, body, "update")


def delete_wiki_page(project_id: str, page_title: str) -> None:
    """Wikiページを削除する

    Raises:
        WikiPageNotFoundException: 対象ページが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.delete(f"/projects/{project_id}/wiki/{page_title}.json")
    if response.status_code == 404:
        raise WikiPageNotFoundException(page_title)
    response.raise_for_status()
