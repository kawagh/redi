from redi import config

from ._protocol import MessagesProto
from .en import En
from .ja import Ja


def _select(lang: str) -> MessagesProto:
    if lang == "ja":
        return Ja()
    return En()


messages: MessagesProto = _select(config.language)
