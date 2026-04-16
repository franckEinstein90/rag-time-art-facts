Project Overview

This project is a FastAPI-based backend service designed to act as a unified orchestration layer for interacting with multiple AI models and vectorization services. It provides a consistent interface for querying models, managing conversations, and handling embeddings, while abstracting away provider-specific implementations and constraints.

The system is built around the idea that models are interchangeable components with differing capabilities, costs, and licensing conditions, and that a centralized service should coordinate their use in a controlled, observable, and extensible manner.

Core Responsibilities

The service exposes a set of HTTP endpoints that allow clients to interact with AI models in a flexible and provider-agnostic way. It supports both direct model querying and vectorization workflows, enabling use cases ranging from conversational AI to retrieval-augmented generation.

A key responsibility of the system is to manage conversations independently of the underlying model providers. Even when a provider offers native conversation tracking, the system maintains its own canonical record of interactions, ensuring consistency, portability, and full control over historical context.

The system also maintains an internal state that tracks usage metrics such as token consumption, request frequency, and estimated cost across all models. This allows for monitoring, auditing, and future enforcement of constraints such as quotas or budget limits.

Model Abstraction and Registration

Models are treated as pluggable components that can be dynamically registered with the system. Each model is defined by a configuration that includes its provider, capabilities (e.g., chat, completion, embedding), pricing characteristics, and any associated licensing constraints.

An administrative endpoint allows new models to be added at runtime. This enables the system to evolve without requiring redeployment when integrating new providers or updating existing ones.

When issuing a query, clients may explicitly select a model or provide preferences (such as cost sensitivity, latency, or capability), allowing the system to resolve the most appropriate model dynamically.

API Surface

The service exposes endpoints for:

Submitting queries to language models, with optional conversation context and model selection or preference hints.
Generating vector embeddings for input data using available embedding models.
Registering and configuring new models within the system.
Retrieving and managing stored conversations, including full histories independent of provider implementations.
Accessing usage statistics, including token counts and cost estimates.

All endpoints are designed to be consistent and provider-agnostic, ensuring that clients interact with a stable interface regardless of the underlying model.

State and Persistence

The system maintains its own persistent storage layer for conversations, model configurations, and usage metrics. This ensures that all interactions can be audited, replayed, or reprocessed independently of external providers.

Conversation state is normalized into a common schema, allowing seamless switching between models without losing continuity. Usage data is aggregated per model and per user, forming the basis for monitoring and potential billing or rate-limiting features.

Design Principles

The system is designed with extensibility as a primary concern. New models, providers, and capabilities should be integrable with minimal changes to the core architecture.

It enforces a clear separation between orchestration logic and provider-specific implementations, allowing each model integration to remain isolated and replaceable.

Finally, the system prioritizes observability and control, ensuring that all interactions are measurable, traceable, and governed by a centralized state rather than delegated entirely to external services.
