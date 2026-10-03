"""Model catalogue. Prices are USD per 1k tokens. Mock prices are *hypothetical* values that mimic a
cheap vs premium hosted model so cost tracking and routing can be exercised for free."""
from __future__ import annotations

import os
from dataclasses import dataclass

from .providers import MockProvider, OllamaProvider, Provider


@dataclass(frozen=True)
class ModelConfig:
    name: str
    provider: str
    tier: str  # "small" | "large"
    price_in: float
    price_out: float


MODELS: dict[str, ModelConfig] = {
    "mock-small": ModelConfig("mock-small", "mock", "small", 0.0002, 0.0006),
    "mock-large": ModelConfig("mock-large", "mock", "large", 0.003, 0.015),
}
if os.getenv("PROMPTOPS_ENABLE_OLLAMA") == "1":
    MODELS[os.getenv("OLLAMA_MODEL", "llama3.2:3b")] = ModelConfig(
        os.getenv("OLLAMA_MODEL", "llama3.2:3b"), "ollama", "small", 0.0, 0.0)


def default_providers() -> dict[str, Provider]:
    return {"mock": MockProvider(), "ollama": OllamaProvider()}
