"""接続先を明示して疎通確認する。

`redi.client` のシングルトンは起動時のプロファイルに束縛されているため、
任意の接続先を確かめたい `init` / `config check` はこちらを使う。
"""

from typing import NamedTuple

import requests

from redi.i18n import MessagesProto


class ConnectionResult(NamedTuple):
    """疎通確認の結果。失敗した理由は `error` に表示用の文言で入る。"""

    ok: bool
    user: dict | None
    error: str | None


def verify_connection(
    url: str, api_key: str, messages: MessagesProto
) -> ConnectionResult:
    """`/my/account.json` を叩いて接続と認証を確かめる。

    表示のしかたは呼び出し側で異なるため、ここでは print せず結果を返すだけにする。
    """
    error: str
    try:
        response = requests.get(
            f"{url.rstrip('/')}/my/account.json",
            headers={"X-Redmine-API-Key": api_key},
            timeout=10,
        )
        response.raise_for_status()
        return ConnectionResult(ok=True, user=response.json().get("user"), error=None)
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
