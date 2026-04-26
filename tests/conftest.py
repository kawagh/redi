def pytest_itemcollected(item):
    """テストの表示名をdocstringの日本語に差し替える"""
    doc = item.obj.__doc__
    if not doc:
        return
    # 祖先 class の docstring を内側→外側の順で集める (Module は除外)
    parent_docs = []
    parent = item.parent
    while parent is not None and hasattr(parent, "obj"):
        parent_obj = parent.obj
        if not isinstance(parent_obj, type):
            break
        if parent_obj.__doc__:
            parent_docs.append(parent_obj.__doc__)
        parent = parent.parent
    parent_docs.reverse()
    parent_prefix = " > ".join(parent_docs) + " > " if parent_docs else ""
    # parametrize されたテストにのみ callspec が存在し、id にパラメータ値が入る
    suffix = ""
    callspec = getattr(item, "callspec", None)
    if callspec is not None:
        suffix = f" [{callspec.id}]"
    item._nodeid = f"{item.path.name}::{parent_prefix}{doc}{suffix}"
