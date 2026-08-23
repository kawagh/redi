"""ユーザー詳細の表示整形。

`user view` と `me` で書式と項目を揃えるために共有する。
インデントはここで付け、i18n の文字列にはラベルだけを持たせる。
"""

from __future__ import annotations

from redi.api.user import User
from redi.i18n import messages

INDENT = "  "


def user_summary(user: User) -> str:
    """`id login 氏名` の 1 行表現を作る。取得できなかった項目は詰めて表示する。"""
    name = f"{user.get('firstname', '')} {user.get('lastname', '')}".strip()
    return f"{user['id']} {user.get('login', '')} {name}".rstrip()


def format_user_detail(user: User) -> list[str]:
    """ユーザーの詳細表示を行のリストに整形する。

    含まれない項目は行ごと出さない。`admin` は自分自身か管理者で取得したときだけ
    返るため、キーがあるときに限り yes / no を出す。
    """
    lines = [user_summary(user)]
    if user.get("mail"):
        lines.append(INDENT + messages.label_mail.format(value=user["mail"]))
    if "admin" in user:
        admin = messages.label_yes if user["admin"] else messages.label_no
        lines.append(INDENT + messages.label_admin.format(value=admin))
    if user.get("created_on"):
        lines.append(
            INDENT + messages.label_created_on.format(value=user["created_on"])
        )
    if user.get("last_login_on"):
        lines.append(
            INDENT + messages.label_last_login_on.format(value=user["last_login_on"])
        )
    custom_fields = user.get("custom_fields") or []
    if custom_fields:
        lines.append(INDENT + messages.label_custom_fields_header)
        for cf in custom_fields:
            lines.append(f"{INDENT * 2}{cf.get('name')}: {cf.get('value')}")
    memberships = user.get("memberships") or []
    if memberships:
        lines.append(INDENT + messages.label_membership_header)
        for m in memberships:
            project = m.get("project") or {}
            roles = m.get("roles") or []
            role_str = ", ".join(r.get("name", "") for r in roles)
            lines.append(
                f"{INDENT * 2}{project.get('id', '?')} {project.get('name', '')}"
                f" - {role_str}"
            )
    groups = user.get("groups") or []
    if groups:
        lines.append(INDENT + messages.label_groups_header)
        for g in groups:
            lines.append(f"{INDENT * 2}{g.get('id', '?')} {g.get('name', '')}")
    return lines
