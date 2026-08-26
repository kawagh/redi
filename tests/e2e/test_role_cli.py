import json

import pytest

from redi.service.role_service import CATEGORY_OTHER, group_permissions
from tests.e2e.utils import run_redi


@pytest.mark.e2e
class TestRoleView:
    """`redi role view` はロールの権限をカテゴリ単位で表示する"""

    def test_no_permission_falls_into_other_category(self):
        """対象 Redmine のロールが持つ権限がカテゴリ表に載っている

        カテゴリ表は redi 側に静的に持っているため Redmine のバージョン差で
        腐るが、表から漏れた権限は落とさず「その他」に出す作りなのでエラーには
        ならない。単体テストの固定リストだけでは対応バージョンを増やしたときに
        気付けないので、実際の Redmine が返す権限で確かめる。
        """
        uncategorized = {}
        for role in json.loads(run_redi("role", "list", "--full").stdout):
            detail = json.loads(
                run_redi("role", "view", str(role["id"]), "--full").stdout
            )
            grouped = dict(group_permissions(detail.get("permissions") or []))
            if CATEGORY_OTHER in grouped:
                uncategorized[role["name"]] = grouped[CATEGORY_OTHER]

        assert not uncategorized, uncategorized
