from redi import config

from ._protocol import MessagesProto
from .en import En
from .ja import Ja


def _select(lang: str) -> MessagesProto:
    if lang == "en":
        return En()
    return Ja()


messages: MessagesProto = _select(config.language)
