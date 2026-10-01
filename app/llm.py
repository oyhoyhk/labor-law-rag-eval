"""Elice ML API (OpenAI-compatible) client with cost accounting and a hard budget."""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# KRW per 1M tokens, Elice public catalog (2026-10-01). Update if the catalog changes.
PRICES = {"openai/gpt-5.6-luna": {"input": 304, "cached_input": 30, "output": 1827}}


def cost_of(model: str, usage: dict) -> float:
    """KRW for one response's usage dict (prompt/completion tokens, cached prompt tokens)."""
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    return Usage(input=usage["prompt_tokens"], cached_input=cached, output=usage["completion_tokens"]).cost_krw(model)


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Usage:
    input: int = 0
    cached_input: int = 0
    output: int = 0
    reasoning: int = 0
    calls: int = 0
    cache_hits: int = 0

    def cost_krw(self, model: str) -> float:
        p = PRICES[model]
        fresh = self.input - self.cached_input
        return (fresh * p["input"] + self.cached_input * p["cached_input"] + self.output * p["output"]) / 1e6


# Fixed sampling for reproducible runs (Luna accepts both; verified 2026-10-02).
SEED, TEMPERATURE = 42, 0


class LLM:
    def __init__(self, model: str | None = None, budget_krw: float = 2000, cache_dir: Path | None = None):
        self.model = model or os.environ["LLM_MODEL"]
        self.client = OpenAI(base_url=os.environ["ELICE_BASE_URL"], api_key=os.environ["ELICE_API_KEY"])
        self.usage = Usage()
        self.budget_krw = budget_krw
        self.cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def spent_krw(self) -> float:
        return self.usage.cost_krw(self.model)

    def chat(self, messages: list[dict], *, max_tokens: int = 1024, reasoning_effort: str = "none",
             json_mode: bool = False, **kwargs) -> tuple[str, dict]:
        """Returns (content, raw_usage). Raises BudgetExceeded before a call once the cap is hit.

        With a cache_dir, identical requests are served from disk at zero cost (usage["cached"] = True).
        """
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        kwargs.setdefault("seed", SEED)
        kwargs.setdefault("temperature", TEMPERATURE)
        request = {"model": self.model, "messages": messages, "max_completion_tokens": max_tokens,
                   "reasoning_effort": reasoning_effort, **kwargs}
        path = None
        if self.cache_dir:
            key = hashlib.sha256(json.dumps(request, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            path = self.cache_dir / f"{key}.json"
            if path.exists():
                hit = json.loads(path.read_text())
                self.usage.cache_hits += 1
                return hit["content"], {**hit["usage"], "cached": True}
        if self.spent_krw >= self.budget_krw:
            raise BudgetExceeded(f"spent {self.spent_krw:.1f} KRW >= budget {self.budget_krw} KRW")
        resp = self.client.chat.completions.create(**request)
        usage = {"model": resp.model, **self._record(resp.usage)}
        content = resp.choices[0].message.content or ""
        if path:
            path.write_text(json.dumps({"content": content, "usage": usage}, ensure_ascii=False))
        return content, usage

    def stream(self, messages: list[dict], *, max_tokens: int = 1024, reasoning_effort: str = "none"):
        """Yields text deltas; the final chunk carries usage only (choices is empty)."""
        if self.spent_krw >= self.budget_krw:
            raise BudgetExceeded(f"spent {self.spent_krw:.1f} KRW >= budget {self.budget_krw} KRW")
        stream = self.client.chat.completions.create(
            model=self.model, messages=messages, max_completion_tokens=max_tokens,
            reasoning_effort=reasoning_effort, stream=True, stream_options={"include_usage": True},
        )
        self.last_stream_meta = {}
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
            if chunk.usage:
                self.last_stream_meta = {"model": chunk.model, **self._record(chunk.usage)}

    def _record(self, u) -> dict:
        self.usage.calls += 1
        self.usage.input += u.prompt_tokens
        self.usage.output += u.completion_tokens
        if u.prompt_tokens_details:
            self.usage.cached_input += u.prompt_tokens_details.cached_tokens or 0
        if u.completion_tokens_details:
            self.usage.reasoning += u.completion_tokens_details.reasoning_tokens or 0
        return u.model_dump()
