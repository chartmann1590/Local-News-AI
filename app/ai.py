from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

import requests


DEFAULT_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
# Enable/disable AI fact-checking verification (default: enabled)
ENABLE_FACT_CHECKING = os.environ.get("ENABLE_FACT_CHECKING", "true").lower() in ("true", "1", "yes")


def _post_ollama(path: str, payload: Dict[str, Any], base_url: Optional[str] = None, timeout_s: int = 600) -> Dict[str, Any]:
    """Post to Ollama API with enforced timeout using concurrent.futures."""
    url = f"{(base_url or DEFAULT_OLLAMA_BASE_URL)}{path}"
    
    def _make_request():
        resp = requests.post(url, json=payload, timeout=timeout_s)
        resp.raise_for_status()
        return resp.json()
    
    # Use ThreadPoolExecutor to enforce timeout even if requests hangs
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_make_request)
        try:
            return future.result(timeout=timeout_s)
        except FutureTimeoutError:
            # Cancel the future if possible
            future.cancel()
            raise TimeoutError(f"Request to {url} exceeded timeout of {timeout_s} seconds")
        except Exception as e:
            # Re-raise other exceptions
            raise


# Minimum timeout for article rewrites (3 minutes)
MIN_REWRITE_TIMEOUT_S = 180

def verify_article_facts(original_content: str, rewritten_content: str, *, base_url: Optional[str] = None, model: Optional[str] = None, timeout_s: int = 120) -> Dict[str, Any]:
    """
    Verify that the rewritten article maintains factual accuracy compared to the original.

    Returns a dict with:
    - accurate (bool): Whether the rewrite is factually accurate
    - confidence (float): Confidence score 0-1
    - issues (list): List of factual discrepancies found
    - details (str): Explanation of verification
    """
    import logging
    logger = logging.getLogger("app.ai")

    if not original_content or not rewritten_content:
        return {"accurate": False, "confidence": 0.0, "issues": ["Missing content"], "details": "Cannot verify empty content"}

    system_prompt = (
        "You are a fact-checker verifying that a rewritten news article maintains factual accuracy. "
        "Compare the original and rewritten versions. Check for:\n"
        "- Names of people, organizations, locations (must match exactly)\n"
        "- Dates, times, and numbers (must be identical)\n"
        "- Key events and facts (must not be altered)\n"
        "- Quotes (if present, must be accurate)\n\n"
        "The rewrite can have different wording, structure, or length, but FACTS must remain unchanged."
    )

    user_prompt = (
        "ORIGINAL ARTICLE:\n" + original_content[:3000] + "\n\n"
        "REWRITTEN ARTICLE:\n" + rewritten_content[:3000] + "\n\n"
        "Verify factual accuracy. Output strict JSON:\n"
        "{\n"
        '  "accurate": true/false,\n'
        '  "confidence": 0.0-1.0,\n'
        '  "issues": ["list any factual discrepancies"],\n'
        '  "details": "brief explanation"\n'
        "}"
    )

    payload = {
        "model": (model or DEFAULT_OLLAMA_MODEL),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {"temperature": 0.1},  # Low temperature for factual analysis
        "format": "json",
    }

    try:
        data = _post_ollama("/api/chat", payload, base_url=base_url, timeout_s=timeout_s)
        message = data.get("message", {})
        response_content = message.get("content", "")

        # Parse JSON response
        if isinstance(response_content, dict):
            result = response_content
        elif isinstance(response_content, str):
            content_clean = response_content.strip()
            if content_clean.startswith("```json"):
                content_clean = content_clean[7:]
            elif content_clean.startswith("```"):
                content_clean = content_clean[3:]
            if content_clean.endswith("```"):
                content_clean = content_clean[:-3]
            content_clean = content_clean.strip()

            try:
                result = json.loads(content_clean)
            except json.JSONDecodeError:
                logger.warning("Failed to parse fact-check JSON response")
                return {
                    "accurate": True,  # Default to accepting if verification fails
                    "confidence": 0.5,
                    "issues": [],
                    "details": "Verification service unavailable, proceeding with rewrite"
                }
        else:
            return {
                "accurate": True,
                "confidence": 0.5,
                "issues": [],
                "details": "Verification service returned unexpected format"
            }

        # Ensure required fields exist
        return {
            "accurate": result.get("accurate", True),
            "confidence": float(result.get("confidence", 0.5)),
            "issues": result.get("issues", []),
            "details": result.get("details", "")
        }

    except Exception as e:
        logger.warning(f"Fact verification failed: {e}")
        # If verification fails, default to accepting the rewrite
        return {
            "accurate": True,
            "confidence": 0.5,
            "issues": [],
            "details": f"Verification error: {str(e)}"
        }


def rewrite_article(content: str, source_title: str | None, location: str, *, base_url: Optional[str] = None, model: Optional[str] = None, fallback_base_url: Optional[str] = None, timeout_s: int = 600, verify_facts: Optional[bool] = None) -> Optional[Dict[str, str]]:
    # Use environment variable default if verify_facts not explicitly set
    if verify_facts is None:
        verify_facts = ENABLE_FACT_CHECKING

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

    import logging
    logger = logging.getLogger("app.ai")
    from .progress import progress

    # Try primary server first
    try:
        progress.set_timeout(timeout_s)
        data = _post_ollama("/api/chat", payload, base_url=base_url, timeout_s=timeout_s)
        progress.clear_timeout()
        # Ollama chat returns {'message': {'content': '...json...'}}
        message = data.get("message", {})
        response_content = message.get("content", "")
        rewrite_result = None

        if isinstance(response_content, dict):
            rewrite_result = {
                "title": response_content.get("title", ""),
                "body": response_content.get("body", ""),
                "author": response_content.get("author", ""),
            }
        elif isinstance(response_content, str):
            # Clean up the response - sometimes Ollama includes markdown code blocks
            content_clean = response_content.strip()
            # Remove markdown code block markers if present
            if content_clean.startswith("```json"):
                content_clean = content_clean[7:]  # Remove ```json
            elif content_clean.startswith("```"):
                content_clean = content_clean[3:]  # Remove ```
            if content_clean.endswith("```"):
                content_clean = content_clean[:-3]  # Remove closing ```
            content_clean = content_clean.strip()

            try:
                obj = json.loads(content_clean)
                rewrite_result = {
                    "title": obj.get("title", ""),
                    "body": obj.get("body", ""),
                    "author": obj.get("author", ""),
                }
            except json.JSONDecodeError as json_err:
                # Try to extract JSON from the response if it's embedded in text
                import re
                json_match = re.search(r'\{[^{}]*"title"[^{}]*\}', content_clean, re.DOTALL)
                if json_match:
                    try:
                        obj = json.loads(json_match.group(0))
                        rewrite_result = {
                            "title": obj.get("title", ""),
                            "body": obj.get("body", ""),
                            "author": obj.get("author", ""),
                        }
                    except json.JSONDecodeError:
                        pass
                if not rewrite_result:
                    logger.warning(f"JSON parse error: {json_err}")
                    logger.debug(f"Response content (first 1000 chars): {content_clean[:1000]}")
                    raise  # Re-raise to trigger fallback

        # Perform fact-checking verification if enabled and rewrite was successful
        if rewrite_result and verify_facts:
            logger.info("Verifying factual accuracy of rewrite...")
            verification = verify_article_facts(
                text,
                rewrite_result.get("body", ""),
                base_url=base_url,
                model=model,
                timeout_s=120
            )

            logger.info(f"Fact-check: accurate={verification['accurate']}, confidence={verification['confidence']:.2f}")

            # If verification fails with high confidence, reject the rewrite
            if not verification["accurate"] and verification["confidence"] > 0.7:
                logger.warning(f"Fact-check FAILED: {verification['details']}")
                if verification["issues"]:
                    logger.warning(f"Issues found: {', '.join(verification['issues'])}")

                # Add verification metadata to result
                rewrite_result["verification"] = verification
                rewrite_result["fact_check_failed"] = True

                # Return None to indicate the rewrite should be rejected
                return None
            elif not verification["accurate"]:
                # Low confidence failure - log warning but accept
                logger.warning(f"Fact-check uncertain: {verification['details']}")
                rewrite_result["verification"] = verification
            else:
                # Passed verification
                logger.info(f"✓ Fact-check passed: {verification['details']}")
                rewrite_result["verification"] = verification

        return rewrite_result
    except Exception as e:
        progress.clear_timeout()
        logger.warning(f"rewrite_article failed on primary server: {e}")
        
        # Try fallback server if available
        if fallback_base_url:
            try:
                logger.info(f"Attempting rewrite with fallback server: {fallback_base_url}")
                progress.set_timeout(timeout_s)
                data = _post_ollama("/api/chat", payload, base_url=fallback_base_url, timeout_s=timeout_s)
                progress.clear_timeout()
                message = data.get("message", {})
                response_content = message.get("content", "")
                fallback_result = None

                if isinstance(response_content, dict):
                    fallback_result = {
                        "title": response_content.get("title", ""),
                        "body": response_content.get("body", ""),
                        "author": response_content.get("author", ""),
                    }
                elif isinstance(response_content, str):
                    # Clean up the response - sometimes Ollama includes markdown code blocks
                    content_clean = response_content.strip()
                    # Remove markdown code block markers if present
                    if content_clean.startswith("```json"):
                        content_clean = content_clean[7:]  # Remove ```json
                    elif content_clean.startswith("```"):
                        content_clean = content_clean[3:]  # Remove ```
                    if content_clean.endswith("```"):
                        content_clean = content_clean[:-3]  # Remove closing ```
                    content_clean = content_clean.strip()

                    try:
                        obj = json.loads(content_clean)
                        fallback_result = {
                            "title": obj.get("title", ""),
                            "body": obj.get("body", ""),
                            "author": obj.get("author", ""),
                        }
                    except json.JSONDecodeError as json_err:
                        # Try to extract JSON from the response if it's embedded in text
                        import re
                        json_match = re.search(r'\{[^{}]*"title"[^{}]*\}', content_clean, re.DOTALL)
                        if json_match:
                            try:
                                obj = json.loads(json_match.group(0))
                                fallback_result = {
                                    "title": obj.get("title", ""),
                                    "body": obj.get("body", ""),
                                    "author": obj.get("author", ""),
                                }
                            except json.JSONDecodeError:
                                pass
                        if not fallback_result:
                            logger.warning(f"Fallback server JSON parse error: {json_err}")
                            raise  # Re-raise to continue error handling

                # Perform fact-checking on fallback result if enabled
                if fallback_result and verify_facts:
                    logger.info("Verifying factual accuracy of fallback rewrite...")
                    verification = verify_article_facts(
                        text,
                        fallback_result.get("body", ""),
                        base_url=fallback_base_url,
                        model=model,
                        timeout_s=120
                    )

                    logger.info(f"Fallback fact-check: accurate={verification['accurate']}, confidence={verification['confidence']:.2f}")

                    if not verification["accurate"] and verification["confidence"] > 0.7:
                        logger.warning(f"Fallback fact-check FAILED: {verification['details']}")
                        if verification["issues"]:
                            logger.warning(f"Issues found: {', '.join(verification['issues'])}")
                        return None
                    else:
                        fallback_result["verification"] = verification

                return fallback_result
            except Exception as e2:
                progress.clear_timeout()
                logger.error(f"rewrite_article failed on fallback server: {e2}", exc_info=True)
        
        # Log the error for debugging
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
