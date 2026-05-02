from collections.abc import Iterator
from typing import Callable

Stream = Iterator[str]
SimpleChat = Callable[[str], str]
StreamingChat = Callable[[str], Stream]