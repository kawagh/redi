from typing import Protocol


class MessagesProto(Protocol):
    """全言語が満たすべきメッセージ集合の輪郭。

    新しいメッセージを追加するときはまずここに key を宣言し、
    ja.py / en.py に実装を追加する。実装側に欠けがあれば ty が検出する。
    """

    profile_created: str
    """プロファイル作成成功。{name} を埋め込む。"""
