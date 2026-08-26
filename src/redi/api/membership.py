from typing import NotRequired, TypedDict, cast

from redi.api.exceptions import (
    ProjectNotFoundException,
    RedmineValidationException,
)
from redi.api.types import IdName
from redi.client import client


class ProjectUser(TypedDict):
    """`memberships[].user` の要素。"""

    id: int
    name: str


class Role(TypedDict):
    """`memberships[].roles` の要素。"""

    id: int
    name: str
    # グループ経由で付与されたロールにのみ存在
    inherited: NotRequired[bool]


class Membership(TypedDict):
    """`memberships[]` の要素。

    `user` と `group` はどちらか一方のみ存在する。
    `project` は GET /memberships/{id}.json のときのみ返る。
    """

    id: int
    roles: list[Role]
    user: NotRequired[ProjectUser]
    group: NotRequired[IdName]
    project: NotRequired[IdName]


class MembershipsResponse(TypedDict):
    """GET /projects/{id}/memberships.json のレスポンス。"""

    memberships: list[Membership]
    total_count: NotRequired[int]
    offset: NotRequired[int]
    limit: NotRequired[int]


class MembershipNotFoundException(Exception):
    """対象のメンバーシップが存在しないときに送出する例外。"""

    def __init__(self, membership_id: str) -> None:
        super().__init__(membership_id)
        self.membership_id = membership_id


def fetch_memberships(project_id: str) -> list[Membership]:
    """プロジェクトのメンバーシップ一覧を取得する。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.get(f"/projects/{project_id}/memberships.json")
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()
    data = cast("MembershipsResponse", response.json())
    return data["memberships"]


def fetch_project_users(project_id: str) -> list[ProjectUser]:
    """プロジェクトのメンバー（user）を返す。"""
    users: list[ProjectUser] = []
    for membership in fetch_memberships(project_id):
        user = membership.get("user")
        if user is not None:
            users.append(user)
    return users


def fetch_membership(membership_id: str) -> Membership:
    """メンバーシップを取得する。

    Raises:
        MembershipNotFoundException: 対象のメンバーシップが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.get(f"/memberships/{membership_id}.json")
    if response.status_code == 404:
        raise MembershipNotFoundException(membership_id)
    response.raise_for_status()
    return cast("Membership", response.json()["membership"])


def create_membership(
    project_id: str, principal_id: int, role_ids: list[int]
) -> Membership:
    """プロジェクトにメンバーシップを追加する。

    Args:
        principal_id: 追加する user または group の id
                      （Redmine はどちらも `user_id` で受け取る）

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 422 以外の HTTP エラーが返った場合
    """
    response = client.post(
        f"/projects/{project_id}/memberships.json",
        json={"membership": {"user_id": principal_id, "role_ids": role_ids}},
    )
    if response.status_code == 422:
        raise RedmineValidationException.from_response("membership", "create", response)
    response.raise_for_status()
    return cast("Membership", response.json()["membership"])


def update_membership(membership_id: str, role_ids: list[int]) -> None:
    """メンバーシップのロールを更新する。

    Raises:
        MembershipNotFoundException: 対象のメンバーシップが存在しない場合（HTTP 404）
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 404 / 422 以外の HTTP エラーが返った場合
    """
    response = client.put(
        f"/memberships/{membership_id}.json",
        json={"membership": {"role_ids": role_ids}},
    )
    if response.status_code == 404:
        raise MembershipNotFoundException(membership_id)
    if response.status_code == 422:
        raise RedmineValidationException.from_response("membership", "update", response)
    response.raise_for_status()


def delete_membership(membership_id: str) -> None:
    """メンバーシップを削除する。

    Raises:
        MembershipNotFoundException: 対象のメンバーシップが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.delete(f"/memberships/{membership_id}.json")
    if response.status_code == 404:
        raise MembershipNotFoundException(membership_id)
    response.raise_for_status()
