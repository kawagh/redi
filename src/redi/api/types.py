from typing import TypedDict


class IdName(TypedDict):
    """`id` と `name` のみを持つ Redmine の参照オブジェクト。

    project / tracker / priority / author など、多くのリソースで共通して現れる。
    """

    id: int
    name: str
