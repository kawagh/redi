from prompt_toolkit import prompt

from redi.i18n import messages


def confirm_delete(summary: str) -> None:
    print(summary)
    try:
        confirm = prompt(messages.prompt_confirm_delete).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)
    if confirm != "yes":
        print(messages.canceled)
        exit(1)


def confirm_overwrite(summary: str) -> None:
    print(summary)
    try:
        confirm = prompt(messages.prompt_confirm_overwrite).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)
    if confirm != "yes":
        print(messages.canceled)
        exit(1)


def confirm_delete_with_identifier(
    summary: str, expected: str, field_label: str
) -> None:
    print(summary)
    try:
        entered = prompt(
            messages.prompt_confirm_delete_with_identifier.format(
                label=field_label, expected=expected
            )
        ).strip()
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)
    if entered != expected:
        print(messages.canceled_field_mismatch.format(field=field_label))
        exit(1)
