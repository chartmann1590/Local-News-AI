from __future__ import annotations

import io
import os
from typing import Optional, Any

import requests


DEFAULT_TTS_BASE = os.environ.get("TTS_BASE_URL", "http://tts:5500")


class TTSClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or DEFAULT_TTS_BASE).rstrip("/")

    def list_voices(self) -> list[dict[str, Any]] | None:
        try:
            r = requests.get(f"{self.base_url}/api/voices", timeout=10)
            r.raise_for_status()
            data = r.json()
            # OpenTTS variants:
            # 1) {"voices": {name: {...}}}
            # 2) {name: {...}}
            # 3) [ {...}, ... ]
            if isinstance(data, dict):
                def _merge_items(m: dict[str, Any]):
                    out: list[dict[str, Any]] = []
                    for k in list(m.keys()):
                        meta = m.get(k)
                        if isinstance(meta, dict):
                            # Preserve key as canonical identifier and keep friendly name separately
                            entry = {
                                "key": k,
                                "name": meta.get("name") or k,
                                "locale": meta.get("locale") or meta.get("language"),
                                "engine": meta.get("tts_name") or meta.get("engine"),
                                **meta,
                            }
                        else:
                            entry = {"key": k, "name": str(meta), **({} if meta is None else {})}
                        out.append(entry)
                    return out
                if "voices" in data and isinstance(data["voices"], dict):
                    return _merge_items(data["voices"])
                else:
                    return _merge_items(data)
            if isinstance(data, list):
                return data
            return []
        except Exception:
            return None

    def synthesize_wav(self, text: str, voice: Optional[str] = None, timeout: int = 600) -> bytes | None:
        import logging
        logger = logging.getLogger("app.tts")
        
        # Use POST for long text to avoid URL length limits
        # GET is limited to ~2000 chars in URL, POST can handle much more
        use_post = len(text) > 1500
        
        params = {"text": text}
        if voice:
            params["voice"] = voice
        params["format"] = "wav"
        
        try:
            url = f"{self.base_url}/api/tts"
            if use_post:
                # Use POST for long text
                logger.debug(f"Using POST for TTS (text length: {len(text)} chars, timeout: {timeout}s)")
                with requests.post(
                    url, json=params, stream=True, timeout=timeout
                ) as r:
                    r.raise_for_status()
                    buf = io.BytesIO()
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            buf.write(chunk)
                    result = buf.getvalue()
            else:
                # Use GET for short text
                logger.debug(f"Using GET for TTS (text length: {len(text)} chars, timeout: {timeout}s)")
                with requests.get(
                    url, params=params, stream=True, timeout=timeout
                ) as r:
                    r.raise_for_status()
                    buf = io.BytesIO()
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            buf.write(chunk)
                    result = buf.getvalue()
            
            if not result:
                logger.warning(f"TTS returned empty response for {len(text)} chars")
            else:
                logger.debug(f"TTS returned {len(result)} bytes")
            return result
        except Exception as e:
            logger.error(f"synthesize_wav failed: {e}", exc_info=True)
            return None
