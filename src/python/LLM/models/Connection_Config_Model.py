from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr


class ConnectionConfig(BaseModel):
    """Everything needed to reach the model's API endpoint."""

    base_url: HttpUrl | None = Field(None, description="Override the provider's default base URL.")
    api_key: SecretStr | None = None
    api_version: str | None = None
    organization_id: str | None = None
    deployment_id: str | None = Field(
        None, description="Azure OpenAI deployment name or similar provider-specific ID."
    )
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=3, ge=0)
    extra_headers: dict[str, str] = Field(default_factory=dict)
    proxy_url: HttpUrl | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
