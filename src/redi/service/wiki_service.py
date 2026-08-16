"""Wiki 操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.wiki` が持つ。
"""

from redi.api.wiki import delete_wiki_page


def delete_page(project_id: str, page_title: str) -> None:
    """Wiki ページを削除する。

    Raises:
        WikiPageNotFoundException: 対象ページが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    delete_wiki_page(project_id, page_title)
