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

    def _pick_default_voice(self) -> Optional[str]:
        """Pick a sensible default voice from the TTS server.

        Preference order:
        - Any voice with locale starting with 'en'
        - Otherwise, the first voice returned by the server
        """
        try:
            voices = self.list_voices() or []
            # Normalize entries to a common shape
            def _vid(v: dict[str, Any]) -> Optional[str]:
                return v.get("key") or v.get("id") or v.get("name")

            # Prefer English voices and more robust engines first
            engine_pref = [
                "larynx",
                "nanotts",
                "piper",
                "coqui-tts",
                "marytts",
                "espeak",
            ]
            for eng in engine_pref:
                for v in voices:
                    if not isinstance(v, dict):
                        continue
                    locale = (v.get("locale") or v.get("lang") or v.get("language") or "").lower()
                    engine = (v.get("engine") or v.get("tts_name") or v.get("type") or "").lower()
                    vid = _vid(v)
                    if vid and engine == eng and (locale.startswith("en") or (isinstance(vid, str) and "en" in vid.lower())):
                        return vid

            # Fallback: first available voice
            for v in voices:
                if isinstance(v, dict):
                    vid = _vid(v)
                    if vid:
                        return vid
            return None
        except Exception:
            return None

    def synthesize_wav(self, text: str, voice: Optional[str] = None, timeout: int = 600) -> bytes | None:
        import logging
        logger = logging.getLogger("app.tts")
        
        # Ensure we always pass a voice. OpenTTS rejects requests without it.
        vv = voice or self._pick_default_voice()

        # Sanitize text to avoid engine crashes on odd glyphs
        def _sanitize(s: str) -> str:
            try:
                import re
                # Remove replacement chars and control chars except basic whitespace
                s = s.replace("\uFFFD", " ")
                s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", s)
                # Collapse excessive whitespace
                s = re.sub(r"\s+", " ", s)
                return s.strip()
            except Exception:
                return s

        safe_text = _sanitize(text)

        params = {"text": safe_text}
        if vv:
            params["voice"] = vv
        params["format"] = "wav"
        
        def _do_request(p: dict) -> bytes:
            url = f"{self.base_url}/api/tts"
            # Decide method per actual request payload length
            use_post_req = len(str(p.get("text", ""))) > 1500
            if use_post_req:
                logger.debug(f"Using POST for TTS (text length: {len(p.get('text') or '')} chars, timeout: {timeout}s)")
                # Prefer JSON body; OpenTTS also accepts form, but JSON is fine
                with requests.post(url, json=p, stream=True, timeout=timeout) as r:
                    r.raise_for_status()
                    buf = io.BytesIO()
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            buf.write(chunk)
                    return buf.getvalue()
            else:
                logger.debug(f"Using GET for TTS (text length: {len(p.get('text') or '')} chars, timeout: {timeout}s)")
                with requests.get(url, params=p, stream=True, timeout=timeout) as r:
                    r.raise_for_status()
                    buf = io.BytesIO()
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            buf.write(chunk)
                    return buf.getvalue()

        # Proactive chunking for very long texts to avoid engine failures
        try:
            CHUNK_THRESHOLD = 300
            if len(safe_text) > CHUNK_THRESHOLD and vv:
                import re
                import wave as pywave
                logger.info(f"app.tts: chunking long text {len(safe_text)} chars")
                # Simple sentence-based splitter
                sentences = re.split(r'(?<=[.!?])\s+', safe_text)
                chunks: list[str] = []
                cur = ""
                for s in sentences:
                    if not s:
                        continue
                    if len(cur) + len(s) + 1 > CHUNK_THRESHOLD:
                        if cur.strip():
                            chunks.append(cur.strip())
                        cur = s
                    else:
                        cur = (cur + " " + s) if cur else s
                if cur.strip():
                    chunks.append(cur.strip())
                if not chunks:
                    chunks = [text]

                writer_buf = io.BytesIO()
                writer: pywave.Wave_write | None = None
                selected_voice = vv

                for idx, ch in enumerate(chunks):
                    p = {"text": ch, "voice": selected_voice, "format": "wav"}
                    try:
                        data = _do_request(p)
                    except Exception as e:
                        # Try voice fallback once for chunking flow
                        try:
                            voices = self.list_voices() or []
                            engine_pref = ["larynx", "nanotts", "piper", "coqui-tts", "marytts", "espeak"]
                            fallback_voice = None
                            for eng in engine_pref:
                                for v in voices:
                                    if not isinstance(v, dict):
                                        continue
                                    vid = v.get("key") or v.get("id") or v.get("name")
                                    if not vid or (vid == selected_voice):
                                        continue
                                    locale = (v.get("locale") or v.get("lang") or v.get("language") or "").lower()
                                    engine = (v.get("engine") or v.get("tts_name") or v.get("type") or "").lower()
                                    if engine == eng and (locale.startswith("en") or (isinstance(vid, str) and "en" in vid.lower())):
                                        fallback_voice = vid
                                        break
                                if fallback_voice:
                                    break
                            if fallback_voice:
                                logger.warning(f"Retrying TTS chunk {idx+1} with fallback voice: {fallback_voice}")
                                selected_voice = fallback_voice
                                p = {"text": ch, "voice": selected_voice, "format": "wav"}
                                data = _do_request(p)
                            else:
                                raise e
                        except Exception:
                            raise e
                    if not data:
                        logger.error(f"TTS chunk {idx+1}/{len(chunks)} returned empty bytes")
                        if writer:
                            try:
                                writer.close()
                            except Exception:
                                pass
                        return None
                    with pywave.open(io.BytesIO(data), 'rb') as rd:
                        params_rd = rd.getparams()
                        frames = rd.readframes(rd.getnframes())
                        if writer is None:
                            writer = pywave.open(writer_buf, 'wb')
                            writer.setparams(params_rd)
                        else:
                            # Basic param consistency check
                            try:
                                if writer.getnchannels() != params_rd.nchannels or writer.getframerate() != params_rd.framerate or writer.getsampwidth() != params_rd.sampwidth:
                                    logger.warning("TTS chunk params differ; audio may be inconsistent")
                            except Exception:
                                pass
                        writer.writeframes(frames)
                if writer:
                    writer.close()
                result = writer_buf.getvalue()
                if not result:
                    logger.warning("TTS chunk merge produced empty result")
                else:
                    logger.debug(f"TTS chunk merge returned {len(result)} bytes")
                return result
        except Exception as e:
            logger.warning(f"app.tts: chunking path failed, falling back to single request: {e}")

        # First attempt with selected/default voice
        try:
            result = _do_request(params)
            if not result:
                logger.warning(f"TTS returned empty response for {len(text)} chars")
            else:
                logger.debug(f"TTS returned {len(result)} bytes")
            return result
        except Exception as e:
            logger.error(f"synthesize_wav failed (voice={params.get('voice')!r}): {e}", exc_info=True)
            # Fallback: try an alternate English voice if available (avoid infinite retries)
            try:
                current_voice = params.get("voice")
                voices = self.list_voices() or []
                # Build engine preference
                engine_pref = ["larynx", "nanotts", "piper", "coqui-tts", "marytts", "espeak"]
                fallback_voice = None
                for eng in engine_pref:
                    for v in voices:
                        if not isinstance(v, dict):
                            continue
                        vid = v.get("key") or v.get("id") or v.get("name")
                        if not vid or (current_voice and vid == current_voice):
                            continue
                        locale = (v.get("locale") or v.get("lang") or v.get("language") or "").lower()
                        engine = (v.get("engine") or v.get("tts_name") or v.get("type") or "").lower()
                        if engine == eng and (locale.startswith("en") or (isinstance(vid, str) and "en" in vid.lower())):
                            fallback_voice = vid
                            break
                    if fallback_voice:
                        break
                if fallback_voice:
                    logger.warning(f"Retrying TTS with fallback voice: {fallback_voice}")
                    p2 = dict(params)
                    p2["voice"] = fallback_voice
                    result = _do_request(p2)
                    if not result:
                        logger.warning("TTS fallback returned empty response")
                    else:
                        logger.debug(f"TTS fallback returned {len(result)} bytes")
                    return result
            except Exception:
                # Ignore fallback errors; will return None below
                pass
            return None
