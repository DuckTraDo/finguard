from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "on"}


def _coerce_value(raw_value: Any, current_value: Any) -> Any:
    if isinstance(current_value, bool):
        return _parse_bool(raw_value)
    if isinstance(current_value, int) and not isinstance(current_value, bool):
        return int(raw_value)
    if isinstance(current_value, float):
        return float(raw_value)
    return str(raw_value)


@dataclass
class FinGuardConfig:
    # Feature flags
    enable_guard: bool = True
    enable_verify: bool = True
    enable_skills: bool = True
    strict_financial_scope: bool = False
    augment_queries: bool = True
    enable_llm_classifier_refiner: bool = False

    # Thresholds
    hallucination_risk_threshold: float = 0.3
    injection_detection_threshold: float = 0.8
    classifier_refiner_confidence_floor: float = 0.8

    # Endpoints
    base_model_url: str = "http://localhost:18080"
    large_ctx_model_url: str = "http://localhost:18081"

    # SEC EDGAR
    edgar_user_agent: str = ""
    edgar_rate_limit: int = 8

    # API keys
    claude_api_key: str = ""
    codex_api_key: str = ""

    # Messaging
    compliance_disclaimer: str = (
        "Educational information only. This is not financial, investment, legal, or tax advice."
    )

    @classmethod
    def load(cls) -> "FinGuardConfig":
        config = cls()
        payload: dict[str, Any] = {}

        candidate_paths: list[Path] = []
        env_path = os.environ.get("FINGUARD_CONFIG_PATH")
        if env_path:
            candidate_paths.append(Path(env_path))

        repo_root = Path(__file__).resolve().parent.parent
        candidate_paths.extend(
            [
                Path.cwd() / ".finguard.toml",
                repo_root / ".finguard.toml",
            ]
        )

        for path in candidate_paths:
            if not path.exists():
                continue
            try:
                parsed = tomllib.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue

            if not isinstance(parsed, dict):
                continue
            scoped = parsed.get("finguard", parsed)
            if isinstance(scoped, dict):
                payload.update(scoped)

        for field_def in fields(config):
            if field_def.name in payload:
                current = getattr(config, field_def.name)
                try:
                    coerced = _coerce_value(payload[field_def.name], current)
                except (TypeError, ValueError):
                    continue
                setattr(config, field_def.name, coerced)

        for field_def in fields(config):
            env_name = f"FINGUARD_{field_def.name.upper()}"
            raw_value = os.environ.get(env_name)
            if raw_value is None:
                continue
            current = getattr(config, field_def.name)
            try:
                coerced = _coerce_value(raw_value, current)
            except (TypeError, ValueError):
                continue
            setattr(config, field_def.name, coerced)

        if not config.claude_api_key:
            config.claude_api_key = os.environ.get("CLAUDE_API_KEY", "")
        if not config.codex_api_key:
            config.codex_api_key = os.environ.get("CODEX_API_KEY", "")

        return config
