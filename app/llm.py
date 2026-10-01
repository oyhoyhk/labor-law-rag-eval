"""Elice ML API (OpenAI-compatible) client with cost accounting and a hard budget."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# KRW per 1M tokens, Elice public catalog (2026-10-01). Update if the catalog changes.
PRICES = {"openai/gpt-5.6-luna": {"input": 304, "cached_input": 30, "output": 1827}}


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class Usage:
    input: int = 0
    cached_input: int = 0
    output: int = 0
    reasoning: int = 0
    calls: int = 0

    def cost_krw(self, model: str) -> float:
        p = PRICES[model]
        fresh = self.input - self.cached_input
        return (fresh * p["input"] + self.cached_input * p["cached_input"] + self.output * p["output"]) / 1e6


class LLM:
    def __init__(self, model: str | None = None, budget_krw: float = 2000):
        self.model = model or os.environ["LLM_MODEL"]
        self.client = OpenAI(base_url=os.environ["ELICE_BASE_URL"], api_key=os.environ["ELICE_API_KEY"])
        self.usage = Usage()
        self.budget_krw = budget_krw

    @property
    def spent_krw(self) -> float:
        return self.usage.cost_krw(self.model)

    def chat(self, messages: list[dict], *, max_tokens: int = 1024, reasoning_effort: str = "none",
             json_mode: bool = False, **kwargs) -> tuple[str, dict]:
        """Returns (content, raw_usage). Raises BudgetExceeded before a call once the cap is hit."""
        if self.spent_krw >= self.budget_krw:
            raise BudgetExceeded(f"spent {self.spent_krw:.1f} KRW >= budget {self.budget_krw} KRW")
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, max_completion_tokens=max_tokens,
            reasoning_effort=reasoning_effort, **kwargs,
        )
        u = resp.usage
        self.usage.calls += 1
        self.usage.input += u.prompt_tokens
        self.usage.output += u.completion_tokens
        if u.prompt_tokens_details:
            self.usage.cached_input += u.prompt_tokens_details.cached_tokens or 0
        if u.completion_tokens_details:
            self.usage.reasoning += u.completion_tokens_details.reasoning_tokens or 0
        return resp.choices[0].message.content or "", {"model": resp.model, **u.model_dump()}
