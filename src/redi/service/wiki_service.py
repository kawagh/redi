"""Wiki 操作のサービス層。

Redmine が返すステータスコードの意味を知るのはこの層だけで、CLI / TUI はここが
投げる例外を自分の見せ方に翻訳する。
"""

from redi.api.wiki import delete_wiki_page


class WikiPageNotFoundError(Exception):
    """対象の Wiki ページが存在しない (HTTP 404)。"""

    def __init__(self, page_title: str) -> None:
        super().__init__(page_title)
        self.page_title = page_title


def delete_page(project_id: str, page_title: str) -> None:
    """Wiki ページを削除する。

    Raises:
        WikiPageNotFoundError: 対象ページが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    response = delete_wiki_page(project_id, page_title)
    if response.status_code == 404:
        raise WikiPageNotFoundError(page_title)
    response.raise_for_status()
