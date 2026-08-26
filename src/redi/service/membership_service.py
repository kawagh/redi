"""メンバーシップ操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.membership` が持つ。
"""

from redi.api import membership as membership_api
from redi.api.membership import Membership


def list_memberships(project_id: str) -> list[Membership]:
    """プロジェクトのメンバーシップ一覧を取得する。"""
    return membership_api.fetch_memberships(project_id)


def read_membership(membership_id: str) -> Membership:
    """メンバーシップを取得する。

    Raises:
        MembershipNotFoundException: 対象のメンバーシップが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return membership_api.fetch_membership(membership_id)


def create_membership(
    project_id: str, principal_id: int, role_ids: list[int]
) -> Membership:
    """プロジェクトにメンバーシップを追加する。

    Args:
        principal_id: 追加する user または group の id
                      （どちらを渡すかは呼び出し元が決める）

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return membership_api.create_membership(project_id, principal_id, role_ids)


def update_membership(membership_id: str, role_ids: list[int]) -> None:
    """メンバーシップのロールを更新する。

    Raises:
        MembershipNotFoundException: 対象のメンバーシップが存在しない (HTTP 404)
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    membership_api.update_membership(membership_id, role_ids)


def delete_membership(membership_id: str) -> None:
    """メンバーシップを削除する。

    Raises:
        MembershipNotFoundException: 対象のメンバーシップが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    membership_api.delete_membership(membership_id)
