from redi.cli.interactive import InputCanceledException, prompt, raise_on_cancel
from redi.i18n import messages


def confirm_delete(summary: str) -> None:
    print(summary)
    with raise_on_cancel():
        confirm = prompt(messages.prompt_confirm_delete).strip().lower()
    if confirm != "yes":
        raise InputCanceledException(messages.canceled)


def confirm_overwrite(summary: str) -> None:
    print(summary)
    with raise_on_cancel():
        confirm = prompt(messages.prompt_confirm_overwrite).strip().lower()
    if confirm != "yes":
        raise InputCanceledException(messages.canceled)


def confirm_delete_with_identifier(
    summary: str, expected: str, field_label: str
) -> None:
    print(summary)
    with raise_on_cancel():
        entered = prompt(
            messages.prompt_confirm_delete_with_identifier.format(
                label=field_label, expected=expected
            )
        ).strip()
    if entered != expected:
        raise InputCanceledException(
            messages.canceled_field_mismatch.format(field=field_label)
        )
