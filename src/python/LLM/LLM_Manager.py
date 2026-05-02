"""
LLM abstraction layer using Pydantic.
Covers capabilities, tokenization, connection, usage tracking, and lifecycle.
"""

from __future__ import annotations

from uuid import UUID

from .models import (
    LLMModel,
    ModelCapability,
    ServiceProvider,
)


# ---------------------------------------------------------------------------
# LLM Manager
# ---------------------------------------------------------------------------


class LLMManager:
    """
    Registry for LLMModel instances.

    Supports add, remove, lookup by id or model_id, and various filters.
    All mutations return `self` for optional chaining.
    """

    def __init__(self) -> None:
        self._models: dict[UUID, LLMModel] = {}
        self._manager_model_id: UUID | None = None

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, model: LLMModel, *, overwrite: bool = False) -> "LLMManager":
        """Register a model. Raises if the UUID already exists and overwrite=False."""
        if model.id in self._models and not overwrite:
            raise ValueError(
                f"Model with id={model.id} already registered. "
                "Pass overwrite=True to replace it."
            )
        self._models[model.id] = model
        return self

    def remove(self, model_id: UUID) -> "LLMManager":
        """Remove a model by its internal UUID. Raises KeyError if not found."""
        if model_id not in self._models:
            raise KeyError(f"No model with id={model_id}.")
        del self._models[model_id]
        if self._manager_model_id == model_id:
            self._manager_model_id = None
        return self

    def update(self, model: LLMModel) -> "LLMManager":
        """Replace an existing model. Raises if the model is not registered."""
        if model.id not in self._models:
            raise KeyError(f"Model id={model.id} is not registered. Use add() first.")
        model.touch()
        self._models[model.id] = model
        return self

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, model_id: UUID) -> LLMModel:
        """Fetch by internal UUID."""
        try:
            return self._models[model_id]
        except KeyError:
            raise KeyError(f"No model with id={model_id}.")

    def get_by_model_id(self, model_id: str) -> list[LLMModel]:
        """Return all models matching a provider model_id string (may be multiple versions)."""
        return [m for m in self._models.values() if m.model_id == model_id]

    def find_one(self, model_id: str) -> LLMModel | None:
        """Return the first match for a model_id string, or None."""
        matches = self.get_by_model_id(model_id)
        return matches[0] if matches else None

    # ------------------------------------------------------------------
    # Manager model
    # ------------------------------------------------------------------

    @property
    def manager_model_id(self) -> UUID | None:
        """Internal UUID of the currently designated manager model, if any."""
        return self._manager_model_id

    @property
    def manager_model(self) -> LLMModel | None:
        """Return the designated manager model, or None when not set."""
        if self._manager_model_id is None:
            return None
        return self._models.get(self._manager_model_id)

    def set_manager(self, model_id: UUID) -> "LLMManager":
        """Designate a registered model (by internal UUID) as the manager model."""
        if model_id not in self._models:
            raise KeyError(f"No model with id={model_id}.")
        self._manager_model_id = model_id
        return self

    def set_manager_by_model_id(self, model_id: str) -> "LLMManager":
        """Designate the first registered model matching model_id as manager."""
        model = self.find_one(model_id)
        if model is None:
            raise KeyError(f"No model with model_id={model_id}.")
        self._manager_model_id = model.id
        return self

    def clear_manager(self) -> "LLMManager":
        """Remove manager model designation."""
        self._manager_model_id = None
        return self

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    @property
    def all(self) -> list[LLMModel]:
        return list(self._models.values())

    @property
    def active(self) -> list[LLMModel]:
        return [m for m in self._models.values() if m.is_active]

    def by_provider(self, provider: ServiceProvider) -> list[LLMModel]:
        return [m for m in self._models.values() if m.provider == ServiceProvider(provider)]

    def with_capability(self, capability: ModelCapability) -> list[LLMModel]:
        return [m for m in self._models.values() if m.supports(capability)]

    def expiring_within(self, days: int) -> list[LLMModel]:
        """Return models expiring within `days` days (including already-expired)."""
        return [
            m for m in self._models.values()
            if m.days_until_expiry is not None and m.days_until_expiry <= days
        ]

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def deactivate_expired(self) -> list[LLMModel]:
        """Deactivate all expired models and return the affected list."""
        affected = [m for m in self._models.values() if m.is_expired]
        for m in affected:
            m.deactivate()
        return affected

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._models)

    def __contains__(self, model_id: UUID) -> bool:
        return model_id in self._models

    def __repr__(self) -> str:
        return (
            f"<LLMManager models={len(self._models)}"
            f" manager_model_id={self._manager_model_id}>"
        )