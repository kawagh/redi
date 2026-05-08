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
