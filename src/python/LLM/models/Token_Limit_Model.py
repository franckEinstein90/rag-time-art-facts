from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class TokenLimits(BaseModel):
    """Token budget and window sizes for the model."""

    context_window: int = Field(..., gt=0, description="Max tokens in a single context (prompt + completion).")
    max_output_tokens: int | None = Field(None, gt=0, description="Hard cap on generated tokens per request.")
    max_input_tokens: int | None = Field(None, gt=0, description="Hard cap on prompt tokens per request.")
    embedding_dimensions: int | None = Field(None, gt=0, description="Output vector size (embedding models only).")

    @model_validator(mode="after")
    def output_fits_in_context(self) -> "TokenLimits":
        if self.max_output_tokens and self.max_output_tokens > self.context_window:
            raise ValueError("max_output_tokens cannot exceed context_window.")
        return self
