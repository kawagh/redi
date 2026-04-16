def pytest_itemcollected(item):
    """テストの表示名をdocstringの日本語に差し替える"""
    doc = item.obj.__doc__
    if doc:
        parent_doc = ""
        if item.parent and hasattr(item.parent, "obj") and item.parent.obj.__doc__:
            parent_doc = item.parent.obj.__doc__ + " > "
        item._nodeid = f"{item.path.name}::{parent_doc}{doc}"
