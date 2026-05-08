from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys


def digit_only_key_bindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add(Keys.Any)
    def _(event) -> None:
        if event.data.isdigit():
            event.current_buffer.insert_text(event.data)

    return kb


def digit_and_period_key_bindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add(Keys.Any)
    def _(event) -> None:
        if event.data.isdigit() or event.data == ".":
            event.current_buffer.insert_text(event.data)

    return kb
