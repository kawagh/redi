import os
import subprocess
import tempfile

import questionary
import questionary.prompts.common

from redi.config import editor

questionary.prompts.common.INDICATOR_SELECTED = "[x]"  # ty: ignore[invalid-assignment]  # pyright: ignore[reportPrivateImportUsage]
questionary.prompts.common.INDICATOR_UNSELECTED = "[ ]"  # ty: ignore[invalid-assignment]  # pyright: ignore[reportPrivateImportUsage]


SUBCOMMAND_ALIASES: dict[str, str] = {
    "v": "view",
    "c": "create",
    "u": "update",
    "co": "comment",
}


def resolve_alias(command: str | None) -> str | None:
    if command is None:
        return None
    return SUBCOMMAND_ALIASES.get(command, command)


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
