from typing import Union

class Competitor:
    __slots__ = ('chat', 'name', 'data')

    def __init__(self, chat: int, name: str, data: Union[bytes, None]):
        self.chat = chat
        self.name = name
        self.data = data

    def __str__(self):
        return f"{self.name}[{self.chat}]"
