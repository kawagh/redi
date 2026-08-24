"""Wiki 操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.wiki` が持つ。
"""

from collections import defaultdict
from dataclasses import dataclass

from redi import config
from redi.api.wiki import (
    WikiPage,
    create_wiki_page,
    delete_wiki_page,
    fetch_wiki,
    fetch_wikis,
    update_wiki_page,
)


class ParentPageNotFoundException(Exception):
    """作成時に指定した親ページが存在しないときに送出する例外。"""

    def __init__(self, title: str) -> None:
        super().__init__(title)
        self.title = title


@dataclass(frozen=True)
class WikiCreateResult:
    """`create_page` の結果。

    Redmine の Wiki 作成は更新と同じ PUT なので、既存タイトルを指定すると更新になる。
    呼び出し元が結果を出し分けられるよう `created` で区別する。
    """

    title: str
    created: bool


def page_url(project_id: str, page_title: str, version: int | None = None) -> str:
    """Wiki ページの Web UI 上の URL を組み立てる。"""
    url = f"{config.redmine_url}/projects/{project_id}/wiki/{page_title}"
    if version is not None:
        url = f"{url}/{version}"
    return url


def list_pages(project_id: str) -> list[WikiPage]:
    """Wiki ページ一覧を取得する。"""
    return fetch_wikis(project_id)


def read_page(
    project_id: str,
    page_title: str,
    version: int | None = None,
    full: bool = False,
) -> WikiPage | None:
    """Wiki ページを取得する。存在しない場合は None を返す。

    Args:
        version: 取得する版。None なら最新版
        full: 添付ファイルも含めて取得するか
    """
    return fetch_wiki(project_id, page_title, version=version, full=full)


def create_page(
    project_id: str,
    page_title: str,
    text: str,
    parent_title: str | None = None,
    comments: str = "",
) -> WikiCreateResult:
    """Wiki ページを作成する。

    親ページ指定時はその存在を、作成前に対象タイトルの既存有無を確認する。

    Raises:
        ParentPageNotFoundException: `parent_title` のページが存在しない
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    if parent_title and fetch_wiki(project_id, parent_title) is None:
        raise ParentPageNotFoundException(parent_title)
    exists = fetch_wiki(project_id, page_title) is not None
    create_wiki_page(
        project_id,
        page_title,
        text,
        parent_title=parent_title,
        comments=comments,
    )
    return WikiCreateResult(title=page_title, created=not exists)


def update_page(
    project_id: str,
    page_title: str,
    text: str,
    version: int | None = None,
    comments: str = "",
) -> None:
    """Wiki ページを更新する。

    Raises:
        WikiUpdateConflictException: `version` が Redmine 側の最新版と一致しない (HTTP 409)
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    update_wiki_page(project_id, page_title, text, version=version, comments=comments)


def delete_page(project_id: str, page_title: str) -> None:
    """Wiki ページを削除する。

    Raises:
        WikiPageNotFoundException: 対象ページが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    delete_wiki_page(project_id, page_title)


def build_children_map(pages: list[WikiPage]) -> dict[str | None, list[str]]:
    """親タイトル -> 子タイトル一覧の対応を作る。ルートの親は None。"""
    children_map: dict[str | None, list[str]] = defaultdict(list)
    for page in pages:
        parent_obj = page.get("parent")
        parent = parent_obj["title"] if parent_obj is not None else None
        children_map[parent].append(page["title"])
    for titles in children_map.values():
        titles.sort()
    return children_map


def flatten_wiki_tree(pages: list[WikiPage]) -> list[tuple[WikiPage, str]]:
    """
    Wiki ページをツリー順に並べ、(ページ辞書, ツリー前置子) のペア列として返す。
    前置子は `│   ├── ` のようなツリー装飾で、末尾にタイトル等を連結すれば
    1 行分のツリー表示になる。
    """
    children_map = build_children_map(pages)
    by_title = {p["title"]: p for p in pages}
    result: list[tuple[WikiPage, str]] = []

    def walk(parent: str | None, prefix: str) -> None:
        children = children_map.get(parent, [])
        for i, title in enumerate(children):
            if title not in by_title:
                continue
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            result.append((by_title[title], f"{prefix}{connector}"))
            next_prefix = prefix + ("    " if is_last else "│   ")
            walk(title, next_prefix)

    walk(None, "")
    return result
