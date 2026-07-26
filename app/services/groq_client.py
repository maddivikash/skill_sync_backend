"""Small shared Groq client: round-robin across keys with rate-limit retry.

Used by the learn/tutor endpoints (the chat agent has its own copy tuned for
tool-calling). Keeping this separate keeps the tutor flow simple and isolated.
"""
import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger("skillsync.groq")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_rr = 0  # round-robin cursor across keys


def _ordered_keys():
    global _rr
    keys = settings.GROQ_API_KEYS
    if not keys:
        return []
    start = _rr % len(keys)
    _rr += 1
    return keys[start:] + keys[:start]


def complete(messages, *, temperature=0.4, max_tokens=900, response_format=None):
    """Call Groq chat-completions and return the assistant's text content.

    Rotates keys, and on rate limits waits and retries a few rounds before
    giving up. Raises RuntimeError if no key is configured or all attempts fail.
    """
    keys = _ordered_keys()
    if not keys:
        raise RuntimeError("no Groq API key configured")

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    resp = None
    for attempt in range(3):
        for key in _ordered_keys():
            resp = httpx.post(GROQ_URL, json=payload, timeout=45,
                              headers={"Authorization": f"Bearer {key}"})
            if resp.is_success:
                data = resp.json()
                return data["choices"][0]["message"]["content"] or ""
            logger.error("groq %s: %s", resp.status_code, resp.text[:300])
        if resp is not None and resp.status_code == 429 and attempt < 2:
            time.sleep(10)
            continue
        break
    raise RuntimeError("Groq call failed")
