from collections.abc import Iterator
from typing import Callable, TypedDict

Stream = Iterator[str]
SimpleChat = Callable[[str], str]
SimpleStreamingChat = Callable[[str], Stream]

class _ChatRequestRequired(TypedDict):
	message: str

class ChatRequest(_ChatRequestRequired, total=False):
	system_prompt: str

class ChatResponse(TypedDict):
	response: str
	duration: float

Chat = Callable[[ChatRequest], ChatResponse]


