from datetime import datetime, timezone

from pydantic import BaseModel, Field


class UsageStats(BaseModel):
    """Cumulative usage counters for the model instance."""

    total_requests: int = Field(default=0, ge=0)
    successful_requests: int = Field(default=0, ge=0)
    failed_requests: int = Field(default=0, ge=0)

    total_input_tokens: int = Field(default=0, ge=0)
    total_output_tokens: int = Field(default=0, ge=0)
    total_embedding_tokens: int = Field(default=0, ge=0)

    total_latency_seconds: float = Field(default=0.0, ge=0.0)
    last_request_at: datetime | None = None

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens + self.total_embedding_tokens

    @property
    def average_latency_seconds(self) -> float | None:
        if self.successful_requests == 0:
            return None
        return self.total_latency_seconds / self.successful_requests

    @property
    def success_rate(self) -> float | None:
        if self.total_requests == 0:
            return None
        return self.successful_requests / self.total_requests

    def record_request(
        self,
        *,
        success: bool,
        input_tokens: int = 0,
        output_tokens: int = 0,
        embedding_tokens: int = 0,
        latency_seconds: float = 0.0,
    ) -> None:
        self.total_requests += 1
        self.last_request_at = datetime.now(timezone.utc)
        if success:
            self.successful_requests += 1
            self.total_latency_seconds += latency_seconds
        else:
            self.failed_requests += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_embedding_tokens += embedding_tokens
