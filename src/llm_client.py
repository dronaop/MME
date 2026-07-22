import json
import httpx
import os
import re
import sys
import time
from dataclasses import dataclass
from src.debug import log


@dataclass
class CallResult:
    text: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    model: str


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _call_groq(system_prompt, user_prompt):
    

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

    body = {
        "model": model,
        "max_tokens": 500,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],

        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.perf_counter()
    resp = httpx.post(GROQ_URL, json=body, headers=headers, timeout=60.0)
    latency = time.perf_counter() - start

    if resp.status_code != 200:
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text}")

    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return CallResult(
        text=text,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        latency_s=latency,
        model=model,
    )

PROVIDERS = {"groq": _call_groq}


def call_llm(system_prompt, user_prompt):
    provider = os.environ.get("LLM_PROVIDER", "groq")
    fn = PROVIDERS.get(provider)
    if fn is None:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
    log("LLM request", {"provider": provider, "system_chars": len(system_prompt), "user_chars": len(user_prompt)})
    result = fn(system_prompt, user_prompt)
    log("LLM response metadata", {
        "model": result.model,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "latency_s": round(result.latency_s, 2),
    })
    return result
