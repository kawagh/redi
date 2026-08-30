import sys

from redi.cli.interactive import exit_on_cancel, prompt
from redi.i18n import messages
from redi.output import eprint


def confirm_delete(summary: str) -> None:
    print(summary)
    with exit_on_cancel():
        confirm = prompt(messages.prompt_confirm_delete).strip().lower()
    if confirm != "yes":
        eprint(messages.canceled)
        sys.exit(1)


def confirm_overwrite(summary: str) -> None:
    print(summary)
    with exit_on_cancel():
        confirm = prompt(messages.prompt_confirm_overwrite).strip().lower()
    if confirm != "yes":
        eprint(messages.canceled)
        sys.exit(1)


def confirm_delete_with_identifier(
    summary: str, expected: str, field_label: str
) -> None:
    print(summary)
    with exit_on_cancel():
        entered = prompt(
            messages.prompt_confirm_delete_with_identifier.format(
                label=field_label, expected=expected
            )
        ).strip()
    if entered != expected:
        eprint(messages.canceled_field_mismatch.format(field=field_label))
        sys.exit(1)
