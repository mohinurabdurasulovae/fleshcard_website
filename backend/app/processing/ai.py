"""Optional LLM-based flashcard generation.

Disabled unless AI_PROVIDER is set to ``anthropic`` or ``openai`` (any OpenAI-compatible
endpoint, e.g. a local Ollama server) in backend/.env. The rule-based generator is always
available without keys.
"""

from __future__ import annotations

import json
import re

import httpx

from ..config import get_settings
from .flashcards import Card, clean

PROMPT = """You are creating study flashcards from university lecture notes.
Create up to {n} high-quality flashcards from the excerpt below. Use a mix of these types:
definition, concept, explanation, formula, comparison.

Rules:
- Every card must be answerable from the excerpt alone. Do not add outside facts.
- Keep LaTeX maths in $...$ (inline) or $$...$$ (display).
- "quote" must be a short sentence copied VERBATIM from the excerpt that supports the answer.

Return ONLY a JSON array, no prose:
[{{"type": "definition", "question": "...", "answer": "...", "quote": "..."}}]

Section: {title}
Excerpt:
\"\"\"
{text}
\"\"\""""


def _call(prompt: str) -> str:
    s = get_settings()
    if s.ai_provider == "anthropic":
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": s.anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": s.anthropic_model, "max_tokens": 2500, "messages": [{"role": "user", "content": prompt}]},
            timeout=120,
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    if s.ai_provider == "openai":
        headers = {"Authorization": f"Bearer {s.openai_api_key}"} if s.openai_api_key else {}
        r = httpx.post(
            s.openai_base_url.rstrip("/") + "/chat/completions",
            headers=headers,
            json={"model": s.openai_model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    raise RuntimeError("AI generation is not configured (set AI_PROVIDER in backend/.env)")


def model_name() -> str:
    s = get_settings()
    return s.anthropic_model if s.ai_provider == "anthropic" else s.openai_model


def _locate(text: str, quote: str, a: int, b: int) -> tuple[int, int]:
    quote = quote.strip()
    if quote:
        i = text.find(quote, a, b)
        if i >= 0:
            return i, i + len(quote)
        # whitespace-insensitive search
        words = [re.escape(w) for w in quote.split()[:12]]
        if words:
            m = re.compile(r"\s+".join(words)).search(text, a, b)
            if m:
                return m.start(), min(b, m.start() + max(len(quote), m.end() - m.start()))
    return a, min(b, a + 400)


def generate_ai_cards(text: str, sections: list[dict], max_cards: int = 30, max_chunks: int = 6) -> list[Card]:
    # choose the richest sections
    ranked = sorted(range(len(sections)), key=lambda i: -(sections[i]["end"] - sections[i]["start"]))[:max_chunks]
    ranked.sort()
    per = max(3, max_cards // max(len(ranked), 1))
    cards: list[Card] = []
    for si in ranked:
        s = sections[si]
        chunk = text[s["start"]:s["end"]][:7000]
        if len(chunk.split()) < 60:
            continue
        raw = _call(PROMPT.format(n=per, title=s.get("title", ""), text=chunk))
        m = re.search(r"\[.*\]", raw, re.S)
        if not m:
            continue
        try:
            items = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        for it in items:
            ctype = str(it.get("type", "concept")).lower()
            if ctype not in {"definition", "concept", "explanation", "formula", "comparison"}:
                ctype = "concept"
            q, ans = str(it.get("question", "")).strip(), clean(str(it.get("answer", "")))
            if not q or not ans:
                continue
            a, b = _locate(text, str(it.get("quote", "")), s["start"], s["end"])
            cards.append(Card(ctype, q, ans, a, b, si, 0.8))
    return cards[:max_cards]
