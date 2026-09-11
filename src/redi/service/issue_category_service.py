"""イシューカテゴリ操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は
`api.issue_category` が持つ。
"""

from redi.api import issue_category as issue_category_api
from redi.api.issue_category import IssueCategory


def list_issue_categories(project_id: str) -> list[IssueCategory]:
    """プロジェクトのイシューカテゴリ一覧を取得する。"""
    return issue_category_api.fetch_issue_categories(project_id)


def read_issue_category(category_id: str) -> IssueCategory:
    """イシューカテゴリを取得する。

    Raises:
        IssueCategoryNotFoundException: 対象カテゴリが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return issue_category_api.fetch_issue_category(category_id)


def create_issue_category(
    project_id: str,
    name: str,
    assigned_to_id: int | None = None,
) -> IssueCategory:
    """イシューカテゴリを作成し、作成されたカテゴリを返す。

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return issue_category_api.create_issue_category(
        project_id=project_id,
        name=name,
        assigned_to_id=assigned_to_id,
    )


def update_issue_category(
    category_id: str,
    name: str | None = None,
    assigned_to_id: int | None = None,
) -> None:
    """イシューカテゴリを更新する。

    Raises:
        IssueCategoryNotFoundException: 対象カテゴリが存在しない (HTTP 404)
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    issue_category_api.update_issue_category(
        category_id=category_id,
        name=name,
        assigned_to_id=assigned_to_id,
    )


def delete_issue_category(
    category_id: str,
    reassign_to_id: int | None = None,
) -> None:
    """イシューカテゴリを削除する。

    Args:
        reassign_to_id: 削除するカテゴリに紐づくイシューの付け替え先カテゴリID

    Raises:
        IssueCategoryNotFoundException: 対象カテゴリが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    issue_category_api.delete_issue_category(
        category_id,
        reassign_to_id=reassign_to_id,
    )
