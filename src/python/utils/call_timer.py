from __future__ import annotations

from functools import wraps
from time import perf_counter

from ..LLM.types import Chat, ChatRequest, ChatResponse


def timed_chat(chat_fn: Chat) -> Chat:
	"""Decorator that measures chat execution time and returns ChatResponse.

	The wrapped function can return either:
	- ChatResponse: the response field is preserved, duration is overwritten
	  with measured wall-clock duration.
	- str: adapted to ChatResponse with measured duration.
	"""

	@wraps(chat_fn)
	def _wrapper(request: ChatRequest) -> ChatResponse:
		started_at = perf_counter()
		result = chat_fn(request)
		elapsed = perf_counter() - started_at

		if isinstance(result, dict):
			response = result.get("response")
			if isinstance(response, str):
				return {"response": response, "duration": elapsed}
			raise TypeError("ChatResponse must contain a string 'response' field.")

		if isinstance(result, str):
			return {"response": result, "duration": elapsed}

		raise TypeError("Timed chat function must return str or ChatResponse.")

	return _wrapper

