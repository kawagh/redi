"""書き込み系 API が 422 を RedmineValidationException に変換することを確かめる。

変換が無い間は `raise_for_status()` の例外と Redmine の生 JSON
(`{"errors":[...]}`) がそのまま端末に出ていた (github#442)。
"""

import json

import pytest
import requests

from redi.api import group as group_module
from redi.api import issue_relation as issue_relation_module
from redi.api import news as news_module
from redi.api import time_entry as time_entry_module
from redi.api.exceptions import RedmineValidationException
from redi.api.time_entry import TimeEntryNotFoundException


def _response(status_code: int, errors: list[str]) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps({"errors": errors}).encode()
    return response


CASES = [
    (
        "group_create",
        group_module,
        "post",
        lambda: group_module.create_group(""),
        "group",
        "create",
    ),
    (
        "group_update",
        group_module,
        "put",
        lambda: group_module.update_group("1", name=""),
        "group",
        "update",
    ),
    (
        "news_create",
        news_module,
        "post",
        lambda: news_module.create_news("redi_df", "", "x"),
        "news",
        "create",
    ),
    (
        "news_update",
        news_module,
        "put",
        lambda: news_module.update_news("1", title=""),
        "news",
        "update",
    ),
    (
        "relation_create",
        issue_relation_module,
        "post",
        lambda: issue_relation_module.create_relation("1", "2", "nosuchtype"),
        "issue_relation",
        "create",
    ),
]


class TestValidationErrorIsConverted:
    """422 は生の JSON ではなく RedmineValidationException で返す"""

    @pytest.mark.parametrize(
        ("module", "method", "call", "resource", "action"),
        [c[1:] for c in CASES],
        ids=[c[0] for c in CASES],
    )
    def test_raises_validation_exception(
        self, module, method, call, resource, action, monkeypatch
    ):
        """リソース名と操作、Redmine が返したメッセージを持って送出する"""
        monkeypatch.setattr(
            module.client,
            method,
            lambda *a, **kw: _response(422, ["Name cannot be blank"]),
        )

        with pytest.raises(RedmineValidationException) as e:
            call()

        assert e.value.resource == resource
        assert e.value.action == action
        assert e.value.errors == ["Name cannot be blank"]


class TestTimeEntryUpdateNotFound:
    """time_entry の更新も 404 を例外にする

    fetch / delete は 404 を変換していたのに更新の経路だけ漏れており、
    生の 404 URL が出ていた (github#443)。
    """

    def test_raises_not_found_on_404(self, monkeypatch):
        """view と同じ「作業時間が見つかりません」に落とせる形で返す"""
        monkeypatch.setattr(
            time_entry_module.client, "put", lambda *a, **kw: _response(404, [])
        )

        with pytest.raises(TimeEntryNotFoundException) as e:
            time_entry_module.update_time_entry("999999", hours=1)

        assert e.value.time_entry_id == "999999"
