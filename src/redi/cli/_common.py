import os
import subprocess
import tempfile

from prompt_toolkit import Application, prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from redi.config import editor


def confirm_delete(summary: str) -> None:
    print(summary)
    try:
        confirm = prompt("削除してもよろしいですか? (yes/No): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("キャンセルしました")
        exit(1)
    if confirm != "yes":
        print("キャンセルしました")
        exit(1)


def confirm_delete_with_identifier(
    summary: str, expected: str, field_label: str
) -> None:
    print(summary)
    try:
        entered = prompt(
            f'削除するには{field_label} "{expected}" を入力してください: '
        ).strip()
    except (KeyboardInterrupt, EOFError):
        print("キャンセルしました")
        exit(1)
    if entered != expected:
        print(f"{field_label}が一致しません。キャンセルしました")
        exit(1)


SUBCOMMAND_ALIASES: dict[str, str] = {
    "v": "view",
    "c": "create",
    "u": "update",
    "co": "comment",
    "d": "delete",
    "l": "list",
}


def resolve_alias(command: str | None) -> str | None:
    if command is None:
        return None
    return SUBCOMMAND_ALIASES.get(command, command)


def inline_checkbox(
    message: str,
    values: list[tuple[str, str]],
    initial_value: str | None = None,
) -> list[str]:
    keys = [v for v, _ in values]
    cursor = keys.index(initial_value) if initial_value in keys else 0
    checked: set[str] = set()

    def render():
        fragments = []
        for i, (value, label) in enumerate(values):
            is_checked = value in checked
            mark = "[x]" if is_checked else "[ ]"
            prefix = "> " if i == cursor else "  "
            mark_style = "ansigreen" if is_checked else ""
            fragments.append(("", prefix))
            fragments.append((mark_style, mark))
            fragments.append(("", f" {label}\n"))
        return fragments

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("c-p")
    @kb.add("k")
    def _up(event):
        nonlocal cursor
        cursor = max(0, cursor - 1)

    @kb.add("down")
    @kb.add("c-n")
    @kb.add("j")
    def _down(event):
        nonlocal cursor
        cursor = min(len(values) - 1, cursor + 1)

    @kb.add(" ")
    def _toggle(event):
        value = values[cursor][0]
        if value in checked:
            checked.remove(value)
        else:
            checked.add(value)

    @kb.add("enter")
    def _accept(event):
        event.app.exit(result=[v for v, _ in values if v in checked])

    @kb.add("c-c")
    def _cancel(event):
        event.app.exit(exception=KeyboardInterrupt())

    layout = Layout(
        HSplit(
            [
                Window(
                    FormattedTextControl(message),
                    dont_extend_height=True,
                    height=1,
                ),
                Window(
                    FormattedTextControl(render, focusable=True, show_cursor=False),
                    dont_extend_height=True,
                ),
            ]
        ),
    )
    app: Application[list[str]] = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=False,
        erase_when_done=True,
    )
    return app.run()


def inline_choice(
    message: str,
    options: list[tuple[str, str]],
    default: str | None = None,
) -> str:
    keys = [v for v, _ in options]
    cursor = keys.index(default) if default in keys else 0

    def render():
        fragments: list[tuple[str, str]] = []
        for i, (_, label) in enumerate(options):
            prefix = "> " if i == cursor else "  "
            fragments.append(("", f"{prefix}{label}\n"))
        return fragments

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("c-p")
    @kb.add("k")
    def _up(event):
        nonlocal cursor
        cursor = max(0, cursor - 1)

    @kb.add("down")
    @kb.add("c-n")
    @kb.add("j")
    def _down(event):
        nonlocal cursor
        cursor = min(len(options) - 1, cursor + 1)

    @kb.add("enter")
    def _accept(event):
        event.app.exit(result=options[cursor][0])

    @kb.add("c-c")
    def _cancel(event):
        event.app.exit(exception=KeyboardInterrupt())

    layout = Layout(
        HSplit(
            [
                Window(
                    FormattedTextControl(message),
                    dont_extend_height=True,
                    height=1,
                ),
                Window(
                    FormattedTextControl(render, focusable=True, show_cursor=False),
                    dont_extend_height=True,
                ),
            ]
        ),
    )
    app: Application[str] = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=False,
        # 描画した選択候補一覧を選択後に消去
        erase_when_done=True,
    )
    return app.run()


def open_editor(initial_text: str = "") -> str:
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", delete=False) as f:
        if initial_text:
            f.write(initial_text)
        tmp_path = f.name
    try:
        if editor == "code":
            # wait to close file
            editor_command = ["code", "--wait"]
        else:
            editor_command = [editor]

        subprocess.run([*editor_command, tmp_path], check=True)
        with open(tmp_path) as f:
            return f.read().strip()
    finally:
        os.unlink(tmp_path)
