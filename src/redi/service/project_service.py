"""プロジェクト操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.project` が持つ。
"""

from __future__ import annotations

import re

from redi import config
from redi.api import project as project_api
from redi.api.exceptions import ProjectNotFoundException
from redi.api.project import Project

# Redmine のプロジェクト識別子の最大長
IDENTIFIER_MAX_LENGTH = 100


def suggest_identifier(name: str) -> str:
    """プロジェクト名から識別子の候補を作る。候補を作れない場合は空文字を返す。

    Redmine の識別子に使えるのは英小文字・数字・ハイフン・アンダースコアだけで、
    数字のみの識別子は拒否される。日本語名のように候補を作れない場合は空文字を返し、
    呼び出し側で入力を促す。
    """
    candidate = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    candidate = candidate[:IDENTIFIER_MAX_LENGTH].strip("-")
    if not candidate or candidate.isdigit():
        return ""
    return candidate


def project_url(project_id: str) -> str:
    """プロジェクトの Web UI 上の URL を組み立てる。"""
    return f"{config.redmine_url}/projects/{project_id}"


def list_projects() -> list[Project]:
    """アクセスできるプロジェクトを全件取得する。"""
    return project_api.fetch_projects()


def sort_projects_by_id_desc(projects: list[Project]) -> list[Project]:
    """プロジェクトを id の降順 (新しいものが先) に並べ替える。"""
    return sorted(projects, key=lambda p: p["id"], reverse=True)


def resolve_project_id(value: str) -> str:
    """identifier や名前で指定されたプロジェクトを数値 id に解決する。

    数値であれば API を呼ばずそのまま返す。

    Raises:
        ProjectNotFoundException: 一致するプロジェクトが無い
        requests.exceptions.HTTPError: 一覧取得で HTTP エラー
    """
    if str(value).isdigit():
        return str(value)
    for project in project_api.fetch_projects():
        if project.get("identifier") == value or project.get("name") == value:
            return str(project["id"])
    raise ProjectNotFoundException(value)


def read_project(project_id: str, include: str = "") -> Project:
    """プロジェクトを取得する。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない (HTTP 404)
        ProjectPermissionDeniedException: アーカイブ済みか参照権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return project_api.fetch_project(project_id, include=include)


def create_project(
    name: str,
    identifier: str,
    description: str | None = None,
    homepage: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    inherit_members: bool | None = None,
    tracker_ids: list[int] | None = None,
    enabled_module_names: list[str] | None = None,
    issue_custom_field_ids: list[int] | None = None,
) -> Project:
    """プロジェクトを作成し、作成されたプロジェクトを返す。

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return project_api.create_project(
        name=name,
        identifier=identifier,
        description=description,
        homepage=homepage,
        is_public=is_public,
        parent_id=parent_id,
        inherit_members=inherit_members,
        tracker_ids=tracker_ids,
        enabled_module_names=enabled_module_names,
        issue_custom_field_ids=issue_custom_field_ids,
    )


def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    homepage: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    inherit_members: bool | None = None,
    tracker_ids: list[int] | None = None,
    enabled_module_names: list[str] | None = None,
    issue_custom_field_ids: list[int] | None = None,
) -> None:
    """プロジェクトを更新する。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない (HTTP 404)
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    project_api.update_project(
        project_id,
        name=name,
        description=description,
        homepage=homepage,
        is_public=is_public,
        parent_id=parent_id,
        inherit_members=inherit_members,
        tracker_ids=tracker_ids,
        enabled_module_names=enabled_module_names,
        issue_custom_field_ids=issue_custom_field_ids,
    )


def archive_project(project_id: str) -> None:
    """プロジェクトをアーカイブする。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    project_api.archive_project(project_id)


def unarchive_project(project_id: str) -> None:
    """プロジェクトのアーカイブを解除する。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    project_api.unarchive_project(project_id)


def delete_project(project_id: str) -> None:
    """プロジェクトを削除する。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    project_api.delete_project(project_id)
