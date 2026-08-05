from typing import TypedDict


class IdName(TypedDict):
    """`id` と `name` のみを持つ Redmine の参照オブジェクト。

    project / tracker / priority / author など、多くのリソースで共通して現れる。
    """

    id: int
    name: str


class Attachment(TypedDict):
    """添付ファイル。

    GET /attachments/{id}.json や include=attachments で返るフィールドを記載。
    """

    id: int
    filename: str
    filesize: int  # bytes
    content_type: str  # ex. text/plain
    description: str
    content_url: str
    author: IdName
    created_on: str
