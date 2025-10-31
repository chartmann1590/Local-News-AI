from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time

from .database import init_db, SessionLocal
from sqlalchemy import func, case
from .models import Article, WeatherReport, AppConfig, AppSettings, TTSSettings, ChatMessage, MobileLog
from .scheduler import start_scheduler, run_harvest_once, restart_scheduler
from . import maintenance
import threading
from .geo import resolve_location, set_location, auto_set_location
from .progress import progress
from . import scheduler as scheduler_mod
from urllib.parse import urlparse, urlunparse
from .tts import TTSClient, DEFAULT_TTS_BASE
from .ai import generate_article_comment
from collections import defaultdict, deque
import uuid
import hashlib

MAX_LOG_UPLOAD_BYTES = int(os.getenv("MAX_LOG_UPLOAD_BYTES", str(5 * 1024 * 1024)))  # 5MB
LOGS_PER_MIN_LIMIT = int(os.getenv("LOGS_RATE_LIMIT_PER_MIN", "10"))

_LOGS_RL_LOCK = threading.Lock()
_LOGS_RL: dict[str, deque] = defaultdict(deque)  # key: ip

def _logs_rate_limited(ip: str) -> bool:
    try:
        now = time.time()
        key = ip or "-"
        with _LOGS_RL_LOCK:
            q = _LOGS_RL[key]
            while q and (now - q[0]) > 60.0:
                q.popleft()
            if len(q) >= LOGS_PER_MIN_LIMIT:
                return True
            q.append(now)
    except Exception:
        return False
    return False

def _ensure_logs_dir() -> str:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "logs"))
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return base

def _save_log_file(fileobj, out_path: str) -> tuple[int, str]:
    sha = hashlib.sha256()
    total = 0
    with open(out_path, 'wb') as f:
        while True:
            chunk = fileobj.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_LOG_UPLOAD_BYTES:
                raise ValueError("file_too_large")
            # allow only text-like content (basic heuristic)
            try:
                _ = chunk.decode('utf-8', errors='ignore')
            except Exception:
                raise ValueError("invalid_content")
            sha.update(chunk)
            f.write(chunk)
    return total, sha.hexdigest()


# ----- Logging setup (container stdout) -----
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        path = request.url.path
        method = request.method
        client = request.client.host if request.client else "-"
        response = None
        try:
            response = await call_next(request)
            return response
        except Exception:
            logger.exception("unhandled_exception", extra={"path": path, "method": method, "client": client})
            raise
        finally:
            dur_ms = int((time.perf_counter() - start) * 1000)
            status = getattr(response, 'status_code', '-')
            logger.info(
                "request",
                extra={
                    "method": method,
                    "path": path,
                    "status": status,
                    "duration_ms": dur_ms,
                    "client": client,
                },
            )


app = FastAPI(title="News-AI")

BASE_DIR = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

static_dir = os.path.join(BASE_DIR, "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    # Serve Vite build assets at /assets for production bundle
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

app.add_middleware(RequestLoggingMiddleware)


def _normalize_ollama_base(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        u = urlparse(url)
        scheme = u.scheme or "http"
        netloc = u.netloc or u.path  # handle bare host:port
        path = ""
        if not netloc:
            return None
        host = netloc
        if host.startswith("localhost") or host.startswith("127.0.0.1"):
            host = host.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
        norm = urlunparse((scheme, host, path, "", "", ""))
        return norm.rstrip("/")
    except Exception:
        return url


def _normalize_tts_base(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        u = urlparse(url)
        scheme = u.scheme or "http"
        netloc = u.netloc or u.path
        if not netloc:
            return None
        host = netloc
        if host.startswith("localhost") or host.startswith("127.0.0.1"):
            host = host.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
        norm = urlunparse((scheme, host, "", "", "", ""))
        return norm.rstrip("/")
    except Exception:
        return url

# ----- Simple in-memory rate limit for article chat -----
_CHAT_RL_LOCK = threading.Lock()
_CHAT_RL: dict[str, deque] = defaultdict(deque)  # key: f"{ip}:{article_id}"
_CHAT_RL_MAX = int(os.getenv("CHAT_RATE_LIMIT_PER_MIN", "10"))

def _rate_limited(ip: str, article_id: int) -> bool:
    try:
        now = time.time()
        key = f"{ip}:{article_id}"
        with _CHAT_RL_LOCK:
            q = _CHAT_RL[key]
            # drop entries older than 60s
            while q and (now - q[0]) > 60.0:
                q.popleft()
            if len(q) >= _CHAT_RL_MAX:
                return True
            q.append(now)
    except Exception:
        return False
    return False

@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("startup:init_db_done")
    # Resolve and persist location before scheduler uses it
    try:
        resolve_location()
        logger.info("startup:location_resolved")
    except Exception:
        logger.exception("startup:location_resolution_failed")
    start_scheduler()
    logger.info("startup:scheduler_started")
    # Kick off a first run on boot without blocking startup
    def _background_first_run():
        try:
            run_harvest_once()
            logger.info("startup:first_run_completed")
        except Exception:
            logger.exception("startup:first_run_failed")

    threading.Thread(target=_background_first_run, daemon=True).start()


@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}


@app.get("/api/status")
def api_status():
    snap = progress.snapshot()
    snap["next_runs"] = scheduler_mod.next_runs()
    return snap


@app.post("/api/run-now")
def run_now():
    try:
        logger.info("api:run_now:start")
        run_harvest_once()
        logger.info("api:run_now:ok")
        return {"status": "ok"}
    except Exception as e:
        logger.exception("api:run_now:error")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


def _latest_weather(session: SessionLocal) -> Optional[WeatherReport]:
    return (
        session.query(WeatherReport)
        .order_by(WeatherReport.fetched_at.desc())
        .limit(1)
        .one_or_none()
    )


def _latest_articles(session: SessionLocal, limit: int = 30, offset: int = 0) -> List[Article]:
    # Primary sort: published_at DESC when available. Items missing published_at come after,
    # and are sorted by fetched_at DESC.
    return (
        session.query(Article)
        .order_by(
            case((Article.published_at.is_(None), 1), else_=0),
            Article.published_at.desc(),
            Article.fetched_at.desc(),
        )
        .offset(int(offset))
        .limit(int(limit))
        .all()
    )


def _funny_author_for(article: Article) -> str:
    try:
        import hashlib
        seed = (article.source_url or article.source_title or str(article.id) or "seed").encode("utf-8", errors="ignore")
        h = int(hashlib.sha256(seed).hexdigest(), 16)
        firsts = [
            "Waffles", "Pickles", "Biscuit", "Snickers", "Pumpkin", "Noodle", "Sprinkles", "Muffin", "Peaches", "Tofu",
        ]
        lasts = [
            "McGiggles", "Von Quill", "Fizzlebottom", "O'Snark", "Bumblebee", "Flapjack", "Wobbleton", "Sparkplug", "Featherstone", "Noodlekins",
        ]
        titles = ["Correspondent", "Staff Writer", "Senior Scribe", "Field Reporter", "News Enthusiast"]
        return f"{firsts[h % len(firsts)]} {lasts[(h // 7) % len(lasts)]}, {titles[(h // 13) % len(titles)]}"
    except Exception:
        return "Sammy Scribbles, Staff Writer"


@app.get("/", response_class=HTMLResponse)
def index():
    # Serve built React app if available; fallback to server-rendered page
    static_index = os.path.join(static_dir, "index.html")
    if os.path.exists(static_index):
        logger.info("serve:index_static")
        return FileResponse(static_index)
    # Fallback
    logger.warning("serve:index_fallback_html")
    session = SessionLocal()
    try:
        weather = _latest_weather(session)
        weather_json = {}
        if weather and weather.forecast_json:
            try:
                weather_json = json.loads(weather.forecast_json)
            except Exception:
                weather_json = {}
        articles = _latest_articles(session)
        location = os.environ.get("LOCATION_NAME", "Local")
        # Minimal inline fallback HTML (avoid Tailwind)
        html = """
        <html><head><title>Local News</title></head><body>
        <h1>Local News</h1>
        <p>Location: {loc}</p>
        <h2>Weather</h2>
        <pre style='white-space:pre-wrap'>{wr}</pre>
        <h2>Articles</h2>
        <ul>
        {arts}
        </ul>
        </body></html>
        """
        arts_li = "".join(
            f"<li><a href='{a.source_url}' target='_blank'>{a.ai_title or a.source_title}</a></li>"
            for a in articles
        )
        wr_text = (weather.ai_report if weather and weather.ai_report else "Weather pending…")
        return HTMLResponse(html.format(loc=location, wr=wr_text, arts=arts_li))
    finally:
        session.close()


# (moved spa_fallback to the end of file to avoid shadowing API routes)


@app.get("/api/articles")
def api_articles(page: int = 1, limit: int = 10):
    session = SessionLocal()
    try:
        # Clamp params
        page = max(1, int(page or 1))
        limit = max(1, min(100, int(limit or 10)))
        total = session.query(Article).count()
        pages = max(1, (total + limit - 1) // limit)
        if page > pages:
            page = pages
        offset = (page - 1) * limit
        arts = _latest_articles(session, limit=limit, offset=offset)
        items = []
        for a in arts:
            # Compute numeric sort timestamp in UTC milliseconds
            base_dt = a.published_at or a.fetched_at
            if base_dt is not None and base_dt.tzinfo is None:
                base_dt = base_dt.replace(tzinfo=timezone.utc)
            sort_ts = int(base_dt.timestamp() * 1000) if base_dt else None
            items.append({
                "id": a.id,
                "title": a.ai_title or a.source_title,
                "source": a.source_name,
                "source_url": a.source_url,
                "image_url": a.image_url,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "fetched_at": a.fetched_at.isoformat(),
                "sort_ts": sort_ts,
                "ai_model": a.ai_model,
                "ai_body": a.ai_body,
                "byline": _funny_author_for(a) if (a.ai_body and not (a.ai_model or "").startswith("fallback:")) else None,
                "rewrite_note": ("Showing original text (AI unavailable)" if (a.ai_model or "").startswith("fallback:") else None),
            })
        logger.info("api:articles", extra={"count": len(items), "page": page, "limit": limit, "total": total})
        return {"items": items, "page": page, "limit": limit, "total": total, "pages": pages}
    finally:
        session.close()


@app.get("/api/articles/{article_id}/chat")
def api_article_chat_get(article_id: int):
    session = SessionLocal()
    try:
        a = session.query(Article).filter_by(id=article_id).one_or_none()
        if not a:
            return JSONResponse(status_code=404, content={"error": "article not found"})
        author_name = _funny_author_for(a) if (a.ai_body and not (a.ai_model or "").startswith("fallback:")) else "Local Desk"
        msgs = (
            session.query(ChatMessage)
            .filter_by(article_id=article_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        items = [
            {"role": m.role, "content": m.content, "created_at": (m.created_at.isoformat() if m.created_at else None)}
            for m in msgs
        ]
        return {"author": author_name, "messages": items}
    finally:
        session.close()


@app.delete("/api/articles/{article_id}/chat")
def api_article_chat_clear(article_id: int):
    session = SessionLocal()
    try:
        session.query(ChatMessage).filter_by(article_id=article_id).delete()
        session.commit()
        return {"status": "cleared"}
    finally:
        session.close()


@app.post("/api/articles/{article_id}/chat")
def api_article_chat(article_id: int, payload: dict, request: Request):
    if not payload or not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "invalid payload"})
    message = (payload.get("message") or "").strip()
    if not message:
        return JSONResponse(status_code=400, content={"error": "message required"})
    # Basic size guard
    if len(message) > 2000:
        message = message[:2000]
    history = payload.get("history") if isinstance(payload.get("history"), list) else None

    session = SessionLocal()
    try:
        a = session.query(Article).filter_by(id=article_id).one_or_none()
        if not a or not a.ai_body:
            return JSONResponse(status_code=404, content={"error": "article not found or empty"})
        # Build author name similar to list API
        author_name = _funny_author_for(a) if (a.ai_body and not (a.ai_model or "").startswith("fallback:")) else "Local Desk"
        # Load AI settings
        aset = session.query(AppSettings).filter_by(id=1).one_or_none()
        base_url = aset.ollama_base_url if aset and aset.ollama_base_url else os.environ.get("OLLAMA_BASE_URL")
        model = aset.ollama_model if aset and aset.ollama_model else os.environ.get("OLLAMA_MODEL")
        cfg = session.query(AppConfig).filter_by(id=1).one_or_none()
        location = cfg.location_name if cfg else os.environ.get("LOCATION_NAME", "Local")
        # Persist user's message
        um = ChatMessage(article_id=article_id, role="user", content=message)
        session.add(um)
        session.commit()
    finally:
        session.close()

    # Rate limit per IP + article
    ip = request.client.host if request.client else "-"
    if _rate_limited(ip, article_id):
        return JSONResponse(status_code=429, content={"error": "rate_limited"})

    # Include recent persisted history (plus provided) capped to 6 turns
    session = SessionLocal()
    try:
        msgs = (
            session.query(ChatMessage)
            .filter_by(article_id=article_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        persisted = [{"role": m.role, "content": m.content} for m in msgs[-6:]]
    finally:
        session.close()
    merged_history = []
    if persisted:
        merged_history.extend(persisted)
    if history:
        # Append only the last few client-side messages
        merged_history.extend(history[-6:])

    reply = generate_article_comment(
        article_title=a.ai_title or a.source_title,
        article_body=a.ai_body,
        user_message=message,
        author_name=author_name,
        location=location,
        base_url=base_url,
        model=model,
        history=merged_history,
        timeout_s=600,
    )
    if not reply:
        return JSONResponse(status_code=502, content={"error": "ai_unavailable"})
    # Persist AI reply
    session = SessionLocal()
    try:
        am = ChatMessage(article_id=article_id, role="ai", content=reply)
        session.add(am)
        session.commit()
    finally:
        session.close()
    return {"author": author_name, "reply": reply}


# ----- Logs endpoints -----

@app.post("/api/logs/upload")
async def api_logs_upload(
    request: Request,
    deviceId: str = Form("") ,
    platform: str = Form("android"),
    appVersion: str = Form(""),
    buildNumber: str = Form(""),
    notes: str | None = Form(None),
    log: UploadFile = File(...),
):
    ip = request.client.host if request.client else "-"
    if _logs_rate_limited(ip):
        return JSONResponse(status_code=429, content={"error": "rate_limited"})
    # Guard filename and content type
    fname = (log.filename or "app.log").lower()
    if any(fname.endswith(ext) for ext in [".exe", ".bin", ".zip", ".apk"]):
        return JSONResponse(status_code=400, content={"error": "invalid_file_type"})
    # Storage path
    base = _ensure_logs_dir()
    today = datetime.utcnow()
    day_dir = os.path.join(base, f"{today.year:04d}", f"{today.month:02d}", f"{today.day:02d}")
    os.makedirs(day_dir, exist_ok=True)
    log_id = str(uuid.uuid4())
    out_path = os.path.join(day_dir, f"{log_id}.log")
    try:
        size, digest = _save_log_file(log.file, out_path)
    except ValueError as ve:
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass
        if str(ve) == "file_too_large":
            return JSONResponse(status_code=413, content={"error": "file_too_large"})
        return JSONResponse(status_code=400, content={"error": "invalid_content"})
    except Exception as e:
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass
        logger.exception("logs_upload_failed")
        return JSONResponse(status_code=500, content={"error": "upload_failed"})

    # Persist metadata
    rel_path = os.path.relpath(out_path, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    session = SessionLocal()
    try:
        ml = MobileLog(
            id=log_id,
            device_id=(deviceId or ""),
            platform=(platform or "android")[:16],
            app_version=(appVersion or "")[:64],
            build_number=(buildNumber or "")[:32],
            uploaded_at=datetime.utcnow(),
            file_path=rel_path.replace("\\", "/"),
            file_size_bytes=int(size),
            sha256=digest,
            notes=(notes or None),
        )
        session.add(ml)
        session.commit()
    finally:
        session.close()

    return {"id": log_id, "uploadedAt": today.isoformat()}


@app.get("/api/logs")
def api_logs_list(q: str | None = None, platform: str | None = None, deviceId: str | None = None, after: str | None = None, before: str | None = None, page: int = 1, pageSize: int = 20):
    session = SessionLocal()
    try:
        page = max(1, int(page or 1))
        pageSize = max(1, min(100, int(pageSize or 20)))
        qry = session.query(MobileLog)
        if platform:
            qry = qry.filter(MobileLog.platform == platform)
        if deviceId:
            qry = qry.filter(MobileLog.device_id == deviceId)
        if after:
            try:
                dt = datetime.fromisoformat(after)
                qry = qry.filter(MobileLog.uploaded_at >= dt)
            except Exception:
                pass
        if before:
            try:
                dt = datetime.fromisoformat(before)
                qry = qry.filter(MobileLog.uploaded_at <= dt)
            except Exception:
                pass
        # Simple q across id/app_version/notes
        if q:
            like = f"%{q}%"
            qry = qry.filter((MobileLog.id.like(like)) | (MobileLog.app_version.like(like)) | (MobileLog.notes.like(like)))
        total = qry.count()
        items = (
            qry.order_by(MobileLog.uploaded_at.desc())
            .offset((page - 1) * pageSize)
            .limit(pageSize)
            .all()
        )
        out = []
        for m in items:
            out.append({
                "id": m.id,
                "device_id": m.device_id,
                "platform": m.platform,
                "app_version": m.app_version,
                "build_number": m.build_number,
                "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
                "file_size_bytes": m.file_size_bytes,
            })
        return {"items": out, "page": page, "pageSize": pageSize, "total": total}
    finally:
        session.close()


@app.get("/api/logs/{log_id}")
def api_logs_detail(log_id: str):
    session = SessionLocal()
    try:
        m = session.query(MobileLog).filter_by(id=log_id).one_or_none()
        if not m:
            return JSONResponse(status_code=404, content={"error": "not_found"})
        # Build preview
        abs_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        abs_path = os.path.join(abs_root, m.file_path)
        preview = ""
        try:
            with open(abs_path, 'rb') as f:
                preview = f.read(256 * 1024).decode('utf-8', errors='replace')
        except Exception:
            preview = ""
        return {
            "id": m.id,
            "device_id": m.device_id,
            "platform": m.platform,
            "app_version": m.app_version,
            "build_number": m.build_number,
            "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
            "file_size_bytes": m.file_size_bytes,
            "sha256": m.sha256,
            "notes": m.notes,
            "preview": preview,
        }
    finally:
        session.close()


@app.get("/api/logs/{log_id}/download")
def api_logs_download(log_id: str):
    session = SessionLocal()
    try:
        m = session.query(MobileLog).filter_by(id=log_id).one_or_none()
        if not m:
            return JSONResponse(status_code=404, content={"error": "not_found"})
        abs_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        abs_path = os.path.join(abs_root, m.file_path)
        if not os.path.exists(abs_path):
            return JSONResponse(status_code=404, content={"error": "file_missing"})
        return FileResponse(abs_path, media_type='text/plain', filename=f"{log_id}.log")
    finally:
        session.close()


@app.delete("/api/logs/{log_id}")
def api_logs_delete(log_id: str):
    session = SessionLocal()
    try:
        m = session.query(MobileLog).filter_by(id=log_id).one_or_none()
        if not m:
            return JSONResponse(status_code=404, content={"error": "not_found"})
        abs_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        abs_path = os.path.join(abs_root, m.file_path)
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception:
            logger.exception("logs_delete_file_failed")
        session.delete(m)
        session.commit()
        return {"status": "deleted"}
    finally:
        session.close()


@app.get("/api/weather")
def api_weather():
    session = SessionLocal()
    try:
        wr = _latest_weather(session)
        cfg = session.query(AppConfig).filter_by(id=1).one_or_none()
        forecast = {}
        if wr and wr.forecast_json:
            try:
                forecast = json.loads(wr.forecast_json)
            except Exception:
                forecast = {}
        result = {
            "location": (cfg.location_name if cfg else os.environ.get("LOCATION_NAME", "Local")),
            "timezone": (cfg.timezone if cfg else os.environ.get("TZ", "America/New_York")),
            "latitude": (cfg.latitude if cfg else None),
            "longitude": (cfg.longitude if cfg else None),
            "report": (wr.ai_report if wr else None),
            "forecast": forecast,
            "updated_at": (wr.fetched_at.isoformat() if wr and wr.fetched_at else None),
        }
        if wr and (wr.ai_model or "").startswith("fallback:"):
            result["report_note"] = "AI report unavailable — showing raw forecast data."
        elif not (wr and wr.ai_report):
            result["report_note"] = "AI report pending…"
        logger.info("api:weather", extra={"has_report": bool(result["report"])})
        return result
    finally:
        session.close()


@app.get("/api/config")
def api_config():
    session = SessionLocal()
    try:
        cfg = session.query(AppConfig).filter_by(id=1).one_or_none()
        tz_name = cfg.timezone if cfg and cfg.timezone else os.environ.get("TZ", "America/New_York")
        # Get current time in location's timezone
        try:
            import pytz
            tz = pytz.timezone(tz_name)
            local_time = datetime.now(tz)
            current_datetime = local_time.isoformat()
            current_date = local_time.strftime("%Y-%m-%d")
            current_time = local_time.strftime("%H:%M:%S")
        except Exception:
            # Fallback to UTC if timezone fails
            local_time = datetime.now(timezone.utc)
            current_datetime = local_time.isoformat()
            current_date = local_time.strftime("%Y-%m-%d")
            current_time = local_time.strftime("%H:%M:%S")
        data = {
            "location": (cfg.location_name if cfg else None),
            "timezone": tz_name,
            "min_articles": int(os.environ.get("MIN_ARTICLES_PER_RUN", "10")),
            "current_datetime": current_datetime,
            "current_date": current_date,
            "current_time": current_time,
        }
        logger.info("api:config", extra={"location": data["location"], "timezone": data["timezone"], "min_articles": data["min_articles"]})
        return data
    finally:
        session.close()


@app.post("/api/location-disabled")
async def api_set_location(payload: dict):
    name = (payload or {}).get("location") or (payload or {}).get("name")
    if not name or not isinstance(name, str) or len(name.strip()) < 2:
        return JSONResponse(status_code=400, content={"error": "location string required"})
    cfg = set_location(name.strip())
    # Note: scheduler timezone won’t change until restart; runs will pick new location immediately.
    return {
        "location": cfg.location_name,
        "timezone": cfg.timezone,
        "latitude": cfg.latitude,
        "longitude": cfg.longitude,
        "source": cfg.source,
    }


@app.post("/api/location")
async def api_set_location_new(payload: dict):
    name = (payload or {}).get("location") or (payload or {}).get("name")
    if not name or not isinstance(name, str) or len(name.strip()) < 2:
        return JSONResponse(status_code=400, content={"error": "location string required"})
    cfg = set_location(name.strip())
    # Restart scheduler to use new timezone
    try:
        restart_scheduler()
    except Exception:
        logger.exception("scheduler_restart_failed_after_location_change")
    def _bg_refresh():
        try:
            session = SessionLocal()
            try:
                aset = session.query(AppSettings).filter_by(id=1).one_or_none()
                base_url = aset.ollama_base_url if aset and aset.ollama_base_url else None
                model = aset.ollama_model if aset and aset.ollama_model else None
                temp_unit = aset.temp_unit if aset and aset.temp_unit else None
            finally:
                session.close()
            scheduler_mod.progress.phase('weather_fetch', 'Updating due to location change')
            scheduler_mod._gen_weather_report(cfg.location_name, base_url=base_url, model=model, temp_unit=temp_unit)
        except Exception:
            logger.exception("location_change_refresh_failed")
    threading.Thread(target=_bg_refresh, daemon=True).start()
    return {
        "location": cfg.location_name,
        "timezone": cfg.timezone,
        "latitude": cfg.latitude,
        "longitude": cfg.longitude,
        "source": cfg.source,
    }

@app.post("/api/location/auto")
def api_auto_location():
    cfg = auto_set_location()
    # Restart scheduler to use new timezone
    try:
        restart_scheduler()
    except Exception:
        logger.exception("scheduler_restart_failed_after_auto_location")
    def _bg_refresh():
        try:
            session = SessionLocal()
            try:
                aset = session.query(AppSettings).filter_by(id=1).one_or_none()
                base_url = aset.ollama_base_url if aset and aset.ollama_base_url else None
                model = aset.ollama_model if aset and aset.ollama_model else None
                temp_unit = aset.temp_unit if aset and aset.temp_unit else None
            finally:
                session.close()
            scheduler_mod.progress.phase('weather_fetch', 'Updating due to auto location')
            scheduler_mod._gen_weather_report(cfg.location_name, base_url=base_url, model=model, temp_unit=temp_unit)
        except Exception:
            logger.exception("auto_location_refresh_failed")
    threading.Thread(target=_bg_refresh, daemon=True).start()
    return {"ok": True}

@app.get("/api/settings")
def api_get_settings():
    session = SessionLocal()
    try:
        s = session.query(AppSettings).filter_by(id=1).one_or_none()
        return {
            "ollama_base_url": s.ollama_base_url if s else None,
            "ollama_model": s.ollama_model if s else None,
            "temp_unit": s.temp_unit if s else "F",
        }
    finally:
        session.close()

@app.post("/api/settings")
def api_set_settings(payload: dict):
    session = SessionLocal()
    try:
        s = session.query(AppSettings).filter_by(id=1).one_or_none()
        if not s:
            s = AppSettings(id=1)
        changed_unit = False
        if payload is None:
            payload = {}
        if "ollama_base_url" in payload:
            s.ollama_base_url = _normalize_ollama_base((payload.get("ollama_base_url") or None))
        if "ollama_model" in payload:
            s.ollama_model = (payload.get("ollama_model") or None)
        if "temp_unit" in payload:
            new_unit = (payload.get("temp_unit") or "").upper()[:1] or None
            changed_unit = (new_unit != s.temp_unit)
            s.temp_unit = new_unit
        s.updated_at = datetime.utcnow()
        session.merge(s)
        session.commit()
    finally:
        session.close()
    if changed_unit:
        def _bg_refresh_unit():
            try:
                cfg_session = SessionLocal()
                try:
                    cfg = cfg_session.query(AppConfig).filter_by(id=1).one_or_none()
                    aset = cfg_session.query(AppSettings).filter_by(id=1).one_or_none()
                    base_url = aset.ollama_base_url if aset and aset.ollama_base_url else None
                    model = aset.ollama_model if aset and aset.ollama_model else None
                    temp_unit = aset.temp_unit if aset and aset.temp_unit else None
                finally:
                    cfg_session.close()
                loc = cfg.location_name if cfg else os.environ.get("LOCATION_NAME", "Local")
                scheduler_mod.progress.phase('weather_fetch', 'Updating due to unit change')
                scheduler_mod._gen_weather_report(loc, base_url=base_url, model=model, temp_unit=temp_unit)
            except Exception:
                logger.exception("unit_change_refresh_failed")
        threading.Thread(target=_bg_refresh_unit, daemon=True).start()
    return {"status": "ok"}

@app.post("/api/weather/refresh")
def api_refresh_weather():
    cfg = resolve_location()
    def _bg():
        try:
            session = SessionLocal()
            try:
                aset = session.query(AppSettings).filter_by(id=1).one_or_none()
                base_url = aset.ollama_base_url if aset and aset.ollama_base_url else None
                model = aset.ollama_model if aset and aset.ollama_model else None
                temp_unit = aset.temp_unit if aset and aset.temp_unit else None
            finally:
                session.close()
            scheduler_mod.progress.phase('weather_fetch', 'Manual refresh')
            scheduler_mod._gen_weather_report(cfg.location_name, base_url=base_url, model=model, temp_unit=temp_unit)
        except Exception:
            logger.exception("weather_manual_refresh_failed")
    threading.Thread(target=_bg, daemon=True).start()
    return {"status": "queued"}

@app.post("/api/ollama/test")
def api_ollama_test(payload: dict):
    base_url = _normalize_ollama_base((payload or {}).get("base_url") or None)
    try:
        from .ai import ollama_list_models
        models = ollama_list_models(base_url=base_url)
        if models is None:
            return JSONResponse(status_code=502, content={"ok": False, "error": "cannot reach ollama"})
        return {"ok": True, "models": models}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

@app.get("/api/ollama/models")
def api_ollama_models(base_url: Optional[str] = None):
    try:
        from .ai import ollama_list_models
        models = ollama_list_models(base_url=_normalize_ollama_base(base_url))
        if models is None:
            return JSONResponse(status_code=502, content={"error": "cannot reach ollama"})
        return {"models": models}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ----- TTS endpoints -----

@app.get("/api/tts/settings")
def api_tts_get_settings():
    session = SessionLocal()
    try:
        s = session.query(TTSSettings).filter_by(id=1).one_or_none()
        return {
            "enabled": bool(s.enabled) if s else False,
            "base_url": s.base_url if s and s.base_url else DEFAULT_TTS_BASE,
            "voice": s.voice if s else None,
            "speed": s.speed if s and s.speed else 1.0,
        }
    finally:
        session.close()


@app.post("/api/tts/settings")
def api_tts_set_settings(payload: dict):
    session = SessionLocal()
    try:
        s = session.query(TTSSettings).filter_by(id=1).one_or_none()
        if not s:
            s = TTSSettings(id=1)
        if payload is None:
            payload = {}
        if "enabled" in payload:
            s.enabled = bool(payload.get("enabled"))
        if "base_url" in payload:
            s.base_url = _normalize_tts_base((payload.get("base_url") or None))
        if "voice" in payload:
            s.voice = (payload.get("voice") or None)
        if "speed" in payload:
            try:
                val = float(payload.get("speed"))
                s.speed = max(0.5, min(2.0, val))
            except Exception:
                pass
        session.merge(s)
        session.commit()
        return {"status": "ok"}
    finally:
        session.close()


@app.get("/api/tts/voices")
def api_tts_voices(base_url: Optional[str] = None):
    # Prefer explicit base_url arg; fall back to settings; then env default
    session = SessionLocal()
    try:
        s = session.query(TTSSettings).filter_by(id=1).one_or_none()
        b = _normalize_tts_base(base_url) or (s.base_url if s and s.base_url else DEFAULT_TTS_BASE)
    finally:
        session.close()
    client = TTSClient(base_url=b)
    voices = client.list_voices()
    if voices is None:
        return JSONResponse(status_code=502, content={"error": "cannot reach tts server"})
    out = []
    for v in voices:
        if not isinstance(v, dict):
            continue
        # Prefer canonical key for API usage and friendly label for UI
        key = v.get("key") or v.get("id") or v.get("name")
        label = v.get("name") or key
        if key:
            out.append({
                "name": key,
                "label": label,
                "locale": v.get("locale") or v.get("lang") or None,
                "engine": v.get("engine") or v.get("tts_name") or v.get("type") or None,
            })
    return {"voices": out}


@app.get("/api/tts/article/{article_id}")
def api_tts_article(article_id: int, voice: Optional[str] = None):
    # Load TTS settings
    session = SessionLocal()
    try:
        tset = session.query(TTSSettings).filter_by(id=1).one_or_none()
        if not tset or not tset.enabled:
            return JSONResponse(status_code=400, content={"error": "tts not enabled"})
        a = session.query(Article).filter_by(id=article_id).one_or_none()
        if not a or not a.ai_body:
            return JSONResponse(status_code=404, content={"error": "article not found or empty"})
        txt = a.ai_body
        vv = voice or (tset.voice or None)
        base = tset.base_url or DEFAULT_TTS_BASE
    finally:
        session.close()
    client = TTSClient(base_url=base)
    wav = client.synthesize_wav(txt, voice=vv)
    if wav is None:
        return JSONResponse(status_code=502, content={"error": "tts synthesis failed"})
    return Response(content=wav, media_type="audio/wav")


@app.get("/api/tts/weather")
def api_tts_weather(voice: Optional[str] = None):
    session = SessionLocal()
    try:
        tset = session.query(TTSSettings).filter_by(id=1).one_or_none()
        if not tset or not tset.enabled:
            return JSONResponse(status_code=400, content={"error": "tts not enabled"})
        w = (
            session.query(WeatherReport)
            .order_by(WeatherReport.fetched_at.desc())
            .limit(1)
            .one_or_none()
        )
        if not w or not w.ai_report:
            return JSONResponse(status_code=404, content={"error": "weather report not found or empty"})
        txt = w.ai_report
        vv = voice or (tset.voice or None)
        base = tset.base_url or DEFAULT_TTS_BASE
    finally:
        session.close()
    client = TTSClient(base_url=base)
    wav = client.synthesize_wav(txt, voice=vv)
    if wav is None:
        return JSONResponse(status_code=502, content={"error": "tts synthesis failed"})
    return Response(content=wav, media_type="audio/wav")


@app.post("/api/tts/preview")
def api_tts_preview(payload: dict):
    if not payload or not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "invalid payload"})
    text = (payload.get("text") or "").strip()
    if not text:
        return JSONResponse(status_code=400, content={"error": "text required"})
    voice = (payload.get("voice") or None)
    base_url = _normalize_tts_base((payload.get("base_url") or None))
    session = SessionLocal()
    try:
        tset = session.query(TTSSettings).filter_by(id=1).one_or_none()
        if not (tset and tset.enabled):
            return JSONResponse(status_code=400, content={"error": "tts not enabled"})
        base = base_url or (tset.base_url or DEFAULT_TTS_BASE)
        vv = voice or (tset.voice or None)
    finally:
        session.close()
    client = TTSClient(base_url=base)
    wav = client.synthesize_wav(text, voice=vv)
    if wav is None:
        return JSONResponse(status_code=502, content={"error": "tts synthesis failed"})
    return Response(content=wav, media_type="audio/wav")


# ----- Maintenance endpoints -----

@app.post("/api/maintenance/dedup")
def api_maintenance_dedup():
    try:
        res = maintenance.purge_duplicate_articles()
        return {"status": "ok", **res}
    except Exception as e:
        logger.exception("maintenance_dedup_failed")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


@app.post("/api/maintenance/rewrite-missing")
def api_maintenance_rewrite_missing(limit: int | None = None):
    # Run in a background thread to avoid blocking HTTP
    def _bg():
        try:
            maintenance.rewrite_missing_articles(limit=limit)
        except Exception:
            logger.exception("maintenance_rewrite_missing_failed")
    threading.Thread(target=_bg, daemon=True).start()
    return {"status": "queued"}

# SPA fallback for client-side routes (avoids 404/blank on refresh)
@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
def spa_fallback(full_path: str):
    # Do not shadow API routes
    if full_path.startswith("api/") or full_path == "health":
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    static_index = os.path.join(static_dir, "index.html")
    if os.path.exists(static_index):
        logger.info("serve:spa_fallback", extra={"path": full_path})
        return FileResponse(static_index)
    return HTMLResponse("<html><body><h1>App not built</h1></body></html>", status_code=200)
