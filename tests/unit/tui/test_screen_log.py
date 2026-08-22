import yaml

from redi.tui.screen_log import _append_screen_yaml


def _dump(lines: list[str]) -> dict:
    return {"width": 80, "height": len(lines), "lines": lines}


def test_出力した画面ログがYAMLとして読み戻せる(tmp_path):
    """`--debug-tui` が出力する画面ログは YAML として読み戻せる"""
    path = tmp_path / "screen.yaml"
    lines = [" Issues    Time entries    Wiki", "─" * 10, "", "#1 title"]
    _append_screen_yaml(path, _dump(lines), key="j")
    _append_screen_yaml(path, _dump(lines), key="k")

    entries = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert [e["key"] for e in entries] == ["j", "k"]
    assert entries[0]["screen"] == "\n".join(lines) + "\n"


def test_先頭が空白の行を含む画面をインデントを保って読み戻せる(tmp_path):
    """画面の 1 行目が空白で始まっても各行の先頭の空白は保たれる"""
    path = tmp_path / "screen.yaml"
    lines = ["  indented first line", "no indent", "    deeper"]
    _append_screen_yaml(path, _dump(lines), key="")

    entries = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert entries[0]["screen"] == "\n".join(lines) + "\n"


def test_YAMLの特殊文字をキーにしても読み戻せる(tmp_path):
    """検索中に打った任意の文字がキーとして記録されても壊れない"""
    keys = [
        "#",
        ":",
        "-",
        ">",
        "|",
        "'",
        '"',
        "*",
        "&",
        "!",
        "%",
        "@",
        ",",
        "?",
        "\\",
        "あ",
    ]
    path = tmp_path / "screen.yaml"
    for key in keys:
        _append_screen_yaml(path, _dump([" a", "b"]), key=key)

    entries = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert [e["key"] for e in entries] == keys
