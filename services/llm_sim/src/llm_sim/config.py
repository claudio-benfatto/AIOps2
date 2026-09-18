from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the llm-sim service.

    The only field that feeds a random number generator is `seed`
    (CLAUDE.md invariant 5: llm-sim is deterministic under a seed). Every
    other field is a deterministic cost-model or admission-control knob.
    """

    model_config = SettingsConfigDict(env_prefix="LLM_SIM_", extra="ignore")

    seed: int = 1337

    kv_cache_budget_tokens: int = 32768
    prefill_tokens_per_second: float = 8000.0
    decode_tokens_per_second_total: float = 400.0

    # Output token count when a request omits `max_tokens`: drawn from
    # Random(seed).randint(default_min_output_tokens, default_max_output_tokens).
    default_min_output_tokens: int = 16
    default_max_output_tokens: int = 128

    host: str = "0.0.0.0"
    port: int = 8000
