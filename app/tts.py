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

    def synthesize_wav(self, text: str, voice: Optional[str] = None) -> bytes | None:
        params = {"text": text}
        if voice:
            params["voice"] = voice
        # Prefer wav for broad browser support
        params["format"] = "wav"
        try:
            with requests.get(
                f"{self.base_url}/api/tts", params=params, stream=True, timeout=60
            ) as r:
                r.raise_for_status()
                buf = io.BytesIO()
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        buf.write(chunk)
                return buf.getvalue()
        except Exception:
            return None
