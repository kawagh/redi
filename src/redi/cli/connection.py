"""接続確認の共通処理。

`init` / `config create` / `config check` は、まだ config に反映されていない
URL / API キーに対して疎通を確かめる。表示のしかたは呼び出し側で異なるため、
ここでは表示せず結果を返す。
"""

from typing import NamedTuple

import requests

from redi.api.me import MyAccount, fetch_my_account
from redi.client import RedmineClient
from redi.i18n import MessagesProto

# 接続確認は入力されたばかりの URL に対して行うため、応答が返らないときに
# 待たされ続けないよう timeout を置く
VERIFY_TIMEOUT_SECONDS = 10


class ConnectionResult(NamedTuple):
    """疎通確認の結果。失敗した理由は `error` に表示用の文言で入る。"""

    ok: bool
    user: MyAccount | None
    error: str | None


def verify_connection(
    api_client: RedmineClient, messages: MessagesProto
) -> ConnectionResult:
    """`/my/account.json` を叩いて接続と認証を確かめる。"""
    error: str
    try:
        user = fetch_my_account(api_client, timeout=VERIFY_TIMEOUT_SECONDS)
        return ConnectionResult(ok=True, user=user, error=None)
    except requests.exceptions.HTTPError as e:
        if e.response is not None:
            error = messages.connection_failed_http.format(
                status=e.response.status_code, reason=e.response.reason
            )
        else:
            error = messages.connection_failed_other.format(error=e)
    except requests.exceptions.RequestException as e:
        error = messages.connection_failed_other.format(error=e)
    return ConnectionResult(ok=False, user=None, error=error)
