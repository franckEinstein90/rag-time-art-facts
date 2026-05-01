from pydantic import BaseModel, Field

from .Enum_Types import PricingUnit


class Pricing(BaseModel):
    """Cost structure for API usage."""

    input_cost: float = Field(..., ge=0, description="Cost per pricing unit for input tokens.")
    output_cost: float = Field(..., ge=0, description="Cost per pricing unit for output tokens.")
    unit: PricingUnit = PricingUnit.PER_1M_TOKENS
    currency: str = Field("USD", max_length=3)
    free_tier_tokens: int | None = Field(None, ge=0, description="Free tokens included per billing period.")
