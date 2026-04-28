from redi import config

from ._protocol import MessagesProto
from .en import En
from .ja import Ja


def select_messages(lang: str) -> MessagesProto:
    if lang == "ja":
        return Ja()
    return En()


messages: MessagesProto = select_messages(config.language)
