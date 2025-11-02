from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

import requests


DEFAULT_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


def _post_ollama(path: str, payload: Dict[str, Any], base_url: Optional[str] = None, timeout_s: int = 600) -> Dict[str, Any]:
    url = f"{(base_url or DEFAULT_OLLAMA_BASE_URL)}{path}"
    resp = requests.post(url, json=payload, timeout=timeout_s)
    resp.raise_for_status()
    return resp.json()


# Minimum timeout for article rewrites (3 minutes)
MIN_REWRITE_TIMEOUT_S = 180

def rewrite_article(content: str, source_title: str | None, location: str, *, base_url: Optional[str] = None, model: Optional[str] = None, timeout_s: int = 600) -> Optional[Dict[str, str]]:
    # Ensure timeout is at least 3 minutes
    timeout_s = max(timeout_s, MIN_REWRITE_TIMEOUT_S)
    if not content or len(content.strip()) < 100:
        return None

    text = content.strip()

    system_prompt = (
        "You are a careful local news editor. Rewrite the article below for a local news site. "
        "Preserve all facts, quotes, and numbers. Do not add new information. "
        "Keep a neutral, concise, journalistic tone. Make it about 10-20% shorter but retain substance."
    )
    user_prompt = (
        f"Location: {location}\n"
        f"Original Title: {source_title or 'N/A'}\n\n"
        "Article Content to Rewrite:\n" + text + "\n\n"
        "Output strict JSON with keys: title (string), body (string), author (string)."
    )

    # Use /api/chat for structured prompts with system/user messages
    payload = {
        "model": (model or DEFAULT_OLLAMA_MODEL),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {"temperature": 0.2},
        "format": "json",
    }

    try:
        data = _post_ollama("/api/chat", payload, base_url=base_url, timeout_s=timeout_s)
        # Ollama chat returns {'message': {'content': '...json...'}}
        message = data.get("message", {})
        response_content = message.get("content", "")
        if isinstance(response_content, dict):
            return {
                "title": response_content.get("title", ""),
                "body": response_content.get("body", ""),
                "author": response_content.get("author", ""),
            }
        elif isinstance(response_content, str):
            obj = json.loads(response_content)
            return {
                "title": obj.get("title", ""),
                "body": obj.get("body", ""),
                "author": obj.get("author", ""),
            }
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger("app.ai")
        logger.error(f"rewrite_article failed: {e}", exc_info=True)
        return None
    return None


def generate_weather_report(forecast: Dict[str, Any], location: str, *, base_url: Optional[str] = None, model: Optional[str] = None, wind_speed_unit: Optional[str] = None, timeout_s: int = 600) -> Optional[str]:
    # Keep prompt compact; include key stats only
    try:
        trimmed = json.dumps(forecast)[:8000]
    except Exception:
        trimmed = json.dumps({})

    wind_unit_note = ""
    if wind_speed_unit:
        unit_label = "mph" if wind_speed_unit.lower() == "mph" else "km/h"
        wind_unit_note = f" When mentioning wind speeds, use {unit_label} as the unit."

    system_prompt = (
        "You are a concise meteorologist. Using the provided forecast JSON, write a short, clear local weather report. "
        "Include current conditions and a 5-day outlook. Keep it factual and neutral." + wind_unit_note
    )
    user_prompt = (
        f"Location: {location}\n"
        f"Forecast JSON: {trimmed}\n\n"
        "Write 2-3 short paragraphs."
    )

    # Use /api/chat for structured prompts
    payload = {
        "model": (model or DEFAULT_OLLAMA_MODEL),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }

    try:
        data = _post_ollama("/api/chat", payload, base_url=base_url, timeout_s=timeout_s)
        message = data.get("message", {})
        response = message.get("content", "")
        if isinstance(response, str):
            return response.strip()
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger("app.ai")
        logger.error(f"generate_weather_report failed: {e}", exc_info=True)
        return None
    return None


def ollama_list_models(base_url: Optional[str] = None) -> Optional[list[str]]:
    try:
        url = f"{(base_url or DEFAULT_OLLAMA_BASE_URL)}/api/tags"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = []
        for m in data.get("models", []) or []:
            name = m.get("name")
            if name:
                models.append(name)
        return models
    except Exception:
        return None


def generate_article_comment(
    *,
    article_title: str | None,
    article_body: str,
    user_message: str,
    author_name: str,
    location: str | None = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    history: Optional[list[dict[str, str]]] = None,
    timeout_s: int = 600,
) -> Optional[str]:
    """Generate a short AI reply to a user's comment about an article.
    The AI should respond in the voice of the provided author_name and only use article details.
    """
    if not user_message or not article_body:
        return None
    text = article_body.strip()

    convo = ""
    if history and isinstance(history, list):
        # Include a brief conversation recap
        pairs = []
        for msg in history[-6:]:  # keep it short
            role = (msg.get("role") or "").lower()
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            if role in ("user", "human"):
                pairs.append(f"User: {content}")
            else:
                pairs.append(f"{author_name}: {content}")
        if pairs:
            convo = "\nConversation so far:\n" + "\n".join(pairs)

    system_prompt = (
        "You are an AI news author responding in the comments section. "
        "Answer as '" + author_name + "'. Use only facts from the article text. "
        "If the user asks for info not in the article, say you don't have that detail. "
        "Be concise (2-4 sentences), specific, and non-speculative."
    )
    user_prompt = (
        (f"Location: {location}\n" if location else "") +
        (f"Article Title: {article_title or ''}\n\n" if article_title else "") +
        "Article Text (for context):\n" + text + "\n\n" +
        (convo + "\n\n" if convo else "") +
        "User says: " + user_message.strip()
    )

    # Use /api/chat for structured prompts
    payload = {
        "model": (model or DEFAULT_OLLAMA_MODEL),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        data = _post_ollama("/api/chat", payload, base_url=base_url, timeout_s=timeout_s)
        message = data.get("message", {})
        response = message.get("content", "")
        if isinstance(response, str):
            return response.strip()
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger("app.ai")
        logger.error(f"generate_article_comment failed: {e}", exc_info=True)
        return None
    return None
