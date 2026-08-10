from prompt_toolkit import Application
from prompt_toolkit.data_structures import Point
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, ScrollOffsets, Window
from prompt_toolkit.layout.controls import FormattedTextControl


def inline_checkbox(
    message: str,
    values: list[tuple[str, str]],
    initial_value: str | None = None,
    initial_checked: list[str] | None = None,
) -> list[str]:
    keys = [v for v, _ in values]
    cursor = (
        keys.index(initial_value)
        if initial_value is not None and initial_value in keys
        else 0
    )
    checked: set[str] = {v for v in (initial_checked or []) if v in keys}

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

    @kb.add("g", "g")
    def _top(event):
        nonlocal cursor
        cursor = 0

    @kb.add("G")
    def _bottom(event):
        nonlocal cursor
        cursor = len(values) - 1

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
                    FormattedTextControl(
                        render,
                        focusable=True,
                        show_cursor=False,
                        get_cursor_position=lambda: Point(0, cursor),
                    ),
                    dont_extend_height=True,
                    scroll_offsets=ScrollOffsets(top=1, bottom=1),
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


def inline_choice_with_action(
    message: str,
    options: list[tuple[str, str]],
    default: str | None = None,
    action_keys: dict[str, str] | None = None,
) -> tuple[str, str]:
    """カーソル行の値と、確定に使われたアクション名を返す。

    Enter は "select" を返す。action_keys に {キー: アクション名} を渡すと
    そのキー押下でカーソル行の値と対応するアクション名を返す。
    """
    keys = [v for v, _ in options]
    cursor = keys.index(default) if default is not None and default in keys else 0

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

    @kb.add("g", "g")
    def _top(event):
        nonlocal cursor
        cursor = 0

    @kb.add("G")
    def _bottom(event):
        nonlocal cursor
        cursor = len(options) - 1

    @kb.add("enter")
    def _accept(event):
        event.app.exit(result=("select", options[cursor][0]))

    for key, action in (action_keys or {}).items():
        # action はループ変数なのでデフォルト引数で束縛する
        @kb.add(key)
        def _action(event, action=action):
            event.app.exit(result=(action, options[cursor][0]))

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
                    FormattedTextControl(
                        render,
                        focusable=True,
                        show_cursor=False,
                        get_cursor_position=lambda: Point(0, cursor),
                    ),
                    dont_extend_height=True,
                    scroll_offsets=ScrollOffsets(top=1, bottom=1),
                ),
            ]
        ),
    )
    app: Application[tuple[str, str]] = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=False,
        # 描画した選択候補一覧を選択後に消去
        erase_when_done=True,
    )
    return app.run()


def inline_choice(
    message: str,
    options: list[tuple[str, str]],
    default: str | None = None,
) -> str:
    return inline_choice_with_action(message, options, default)[1]
