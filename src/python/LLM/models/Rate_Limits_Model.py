from pydantic import BaseModel, Field


class RateLimits(BaseModel):
    """Provider-enforced rate limits."""

    requests_per_minute: int | None = Field(None, gt=0)
    tokens_per_minute: int | None = Field(None, gt=0)
    tokens_per_day: int | None = Field(None, gt=0)
    concurrent_requests: int | None = Field(None, gt=0)
