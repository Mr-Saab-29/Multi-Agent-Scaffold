import json
from dataclasses import dataclass
from importlib import import_module
import random
import time
from typing import Any

from app.core.config import Settings


@dataclass
class LLMResponse:
    text: str


class LLMClient:
    """Gemini-backed client with deterministic fallback."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._backend = "fallback"
        self._fallback_reason: str | None = None
        self._client = None
        self._call_count = 0
        self._estimated_input_tokens = 0
        self._estimated_output_tokens = 0
        self._estimated_cost_usd = 0.0
        self._budget_exceeded = False

        if not settings.gemini_api_key:
            self._fallback_reason = "GEMINI_API_KEY missing"
            return

        genai_module = self._load_genai_module()
        if genai_module is None:
            return

        self._client = genai_module.Client(api_key=settings.gemini_api_key)
        self._backend = "gemini"

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def fallback_reason(self) -> str | None:
        return self._fallback_reason

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def estimated_input_tokens(self) -> int:
        return self._estimated_input_tokens

    @property
    def estimated_output_tokens(self) -> int:
        return self._estimated_output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        return self._estimated_cost_usd

    @property
    def budget_exceeded(self) -> bool:
        return self._budget_exceeded

    def generate_json(self, system_prompt: str, user_prompt: str, model: str | None = None) -> dict:
        if self._over_budget():
            self._switch_to_fallback(reason="Governance budget exceeded")
            self._budget_exceeded = True
        if self._backend == "fallback":
            return self._fallback_json(system_prompt=system_prompt, user_prompt=user_prompt)

        try:
            prompt = (
                f"{system_prompt}\n\n"
                "Return strict JSON only. Do not wrap in markdown fences.\n\n"
                f"User input:\n{user_prompt}"
            )
            response = self._generate_content_with_retry(prompt, model=model)
            raw = (response.text or "").strip()
            self._record_usage(prompt=prompt, output=raw)
            return self._parse_json(raw)
        except Exception as exc:  # noqa: BLE001
            self._switch_to_fallback(reason=f"Gemini request failed: {type(exc).__name__}: {exc}")
            return self._fallback_json(system_prompt=system_prompt, user_prompt=user_prompt)

    def generate_text(self, system_prompt: str, user_prompt: str, model: str | None = None) -> LLMResponse:
        if self._over_budget():
            self._switch_to_fallback(reason="Governance budget exceeded")
            self._budget_exceeded = True
        if self._backend == "fallback":
            return LLMResponse(text=f"{system_prompt}\n\n{user_prompt}")

        try:
            prompt = f"{system_prompt}\n\n{user_prompt}"
            response = self._generate_content_with_retry(prompt, model=model)
            text = (response.text or "").strip()
            self._record_usage(prompt=prompt, output=text)
            return LLMResponse(text=text)
        except Exception as exc:  # noqa: BLE001
            self._switch_to_fallback(reason=f"Gemini request failed: {type(exc).__name__}: {exc}")
            return LLMResponse(text=f"{system_prompt}\n\n{user_prompt}")

    def _fallback_json(self, system_prompt: str, user_prompt: str) -> dict:
        payload = {
            "system_prompt_hint": system_prompt[:80],
            "user_prompt": user_prompt,
        }
        return json.loads(json.dumps(payload))

    def _parse_json(self, raw: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = raw[start : end + 1]
            parsed = json.loads(snippet)
            if isinstance(parsed, dict):
                return parsed

        raise ValueError("LLM did not return valid JSON object")

    def _load_genai_module(self):
        try:
            module = import_module("google.genai")
            return module
        except Exception as exc:  # noqa: BLE001
            self._fallback_reason = f"google-genai import failed: {type(exc).__name__}: {exc}"
            return None

    def _switch_to_fallback(self, reason: str) -> None:
        self._backend = "fallback"
        self._fallback_reason = reason
        self._client = None

    def _generate_content_with_retry(self, prompt: str, model: str | None = None):
        retries = max(0, self._settings.gemini_max_retries)
        base_delay = max(0.0, self._settings.gemini_retry_base_delay_seconds)
        max_delay = max(base_delay, self._settings.gemini_retry_max_delay_seconds)
        target_model = model or self._settings.gemini_model

        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                self._call_count += 1
                return self._client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= retries or not self._is_retryable(exc):
                    raise
                backoff = min(max_delay, base_delay * (2**attempt))
                jitter = random.uniform(0, backoff * 0.2)
                time.sleep(backoff + jitter)

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Gemini request failed without exception details")

    def _is_retryable(self, exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code in {429, 500, 502, 503, 504}:
            return True
        message = str(exc).upper()
        retry_tokens = (
            "503",
            "429",
            "UNAVAILABLE",
            "RESOURCE_EXHAUSTED",
            "TIMEOUT",
            "INTERNAL",
            "RATE LIMIT",
        )
        return any(token in message for token in retry_tokens)

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _record_usage(self, prompt: str, output: str) -> None:
        in_toks = self._estimate_tokens(prompt)
        out_toks = self._estimate_tokens(output)
        self._estimated_input_tokens += in_toks
        self._estimated_output_tokens += out_toks
        in_cost = (in_toks / 1000.0) * self._settings.governance_input_cost_per_1k_tokens_usd
        out_cost = (out_toks / 1000.0) * self._settings.governance_output_cost_per_1k_tokens_usd
        self._estimated_cost_usd += in_cost + out_cost

    def _over_budget(self) -> bool:
        if self._call_count >= self._settings.governance_max_llm_calls:
            return True
        if self._estimated_cost_usd >= self._settings.governance_max_cost_usd:
            return True
        return False
