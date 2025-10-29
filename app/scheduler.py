from __future__ import annotations

import os
from datetime import datetime
import threading
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import logging
from typing import List, Dict

from .database import SessionLocal
from .models import Article, WeatherReport, AppSettings
from .news_fetcher import fetch_new_articles
from .ai import rewrite_article, generate_weather_report
from .weather import update_weather
from .geo import resolve_location
from .progress import progress

logger = logging.getLogger("app.scheduler")
REWRITE_LOCK = threading.Lock()

def _get_env_time(name: str, default: str) -> tuple[int, int]:
    val = os.environ.get(name, default)
    hh, mm = val.split(":")
    return int(hh), int(mm)


def _tz_name() -> str:
    # Prefer resolved location timezone
    try:
        cfg = resolve_location()
        if cfg.timezone:
            return cfg.timezone
    except Exception:
        pass
    return os.environ.get("TZ", "America/New_York")


def _location() -> str:
    try:
        cfg = resolve_location()
        if cfg.location_name:
            return cfg.location_name
    except Exception:
        pass
    return os.environ.get("LOCATION_NAME", "Schenectady, NY")


def _min_articles() -> int:
    try:
        return int(os.environ.get("MIN_ARTICLES_PER_RUN", "10"))
    except Exception:
        return 10


def _rewrite_and_store(articles, *, base_url: str | None, model: str | None):
    session = SessionLocal()
    try:
        processed = 0
        total = len(articles)
        for i, art in enumerate(articles, start=1):
            # Rewrite when missing AI or previously fell back to source
            needs_rewrite = (art.raw_content is not None) and (
                (not art.ai_body) or ((art.ai_model or "").startswith("fallback:"))
            )
            if needs_rewrite:
                # Update progress detail with current item
                try:
                    from urllib.parse import urlparse
                    label = (art.source_title or urlparse(art.source_url or '').netloc or 'article').strip()
                    label = (label[:80] + '…') if len(label) > 80 else label
                    progress.phase('rewrite', f'Rewriting ({i}/{total}): {label}')
                except Exception:
                    progress.phase('rewrite', f'Rewriting ({i}/{total})')
                # Retry up to 3 times, 10 minute timeout per attempt
                res = None
                for _attempt in range(3):
                    res = rewrite_article(art.raw_content, art.source_title, art.location or _location(), base_url=base_url, model=model, timeout_s=600)
                    if res and (res.get("title") or res.get("body")):
                        break
                if res and (res.get("title") or res.get("body")):
                    art.ai_title = (res.get("title") or art.source_title or "").strip()[:500]
                    art.ai_body = (res.get("body") or "").strip()
                    art.ai_model = (model or os.environ.get("OLLAMA_MODEL", "llama3.2"))
                    art.ai_generated_at = datetime.utcnow()
                else:
                    # Fallback to source content
                    art.ai_title = (art.source_title or "").strip()[:500]
                    art.ai_body = (art.raw_content or "").strip()
                    art.ai_model = "fallback:source"
                    art.ai_generated_at = datetime.utcnow()
                session.add(art)
                session.commit()
                processed += 1
                progress.inc_rewrite(1)
        logger.info("rewrite_completed", extra={"processed": processed})
    finally:
        session.close()


def _gen_weather_report(location: str, *, base_url: str | None, model: str | None, temp_unit: str | None):
    tz = _tz_name()
    # Refresh forecast record based on resolved coordinates when available
    lat = None
    lon = None
    try:
        cfg = resolve_location()
        lat = cfg.latitude
        lon = cfg.longitude
    except Exception:
        pass
    progress.phase('weather_fetch', 'Updating weather forecast')
    wr = update_weather(location=location, tz=tz, lat=lat, lon=lon, temp_unit=temp_unit)
    if not wr:
        logger.warning("weather_update_failed", extra={"location": location})
        return
    # Generate readable report from latest forecast
    try:
        import json
        forecast = json.loads(wr.forecast_json or "{}")
    except Exception:
        forecast = {}
    progress.phase('weather_generate', 'Generating weather report')
    # Retry up to 3 times, 10 minute timeout per attempt
    text = None
    for _attempt in range(3):
        text = generate_weather_report(forecast, location, base_url=base_url, model=model, timeout_s=600)
        if text:
            break
    if text:
        session = SessionLocal()
        try:
            wr.ai_report = text
            wr.ai_model = (model or os.environ.get("OLLAMA_MODEL", "llama3.2"))
            wr.ai_generated_at = datetime.utcnow()
            session.merge(wr)
            session.commit()
            logger.info("weather_report_generated", extra={"location": location})
        finally:
            session.close()
    else:
        logger.warning("weather_report_generation_failed", extra={"location": location})
        session = SessionLocal()
        try:
            wr.ai_report = "Weather report unavailable — showing raw forecast data."
            wr.ai_model = "fallback:forecast"
            wr.ai_generated_at = datetime.utcnow()
            session.merge(wr)
            session.commit()
        finally:
            session.close()


def run_harvest_once():
    location = _location()
    count = _min_articles()
    logger.info("harvest_start", extra={"location": location, "min_articles": count})
    progress.start()
    progress.phase('fetch', 'Fetching news sources')
    # Fetch new raw articles
    new_arts = fetch_new_articles(min_count=count, location=location)
    # Rewrite via Ollama
    progress.phase('rewrite', f'Rewriting articles')
    progress.set_rewrite_total(len(new_arts) if new_arts else 0)
    # Load AI settings
    session = SessionLocal()
    try:
        aset = session.query(AppSettings).filter_by(id=1).one_or_none()
        base_url = (aset.ollama_base_url if aset and aset.ollama_base_url else os.environ.get("OLLAMA_BASE_URL"))
        model = (aset.ollama_model if aset and aset.ollama_model else os.environ.get("OLLAMA_MODEL"))
        temp_unit = (aset.temp_unit if aset and aset.temp_unit else None)
    finally:
        session.close()
    # Ensure only a single rewrite runs at a time
    with REWRITE_LOCK:
        _rewrite_and_store(new_arts, base_url=base_url, model=model)
    # Enforce deduplication after each run to eliminate lookalikes
    try:
        from .maintenance import purge_duplicate_articles
        purge_duplicate_articles()
    except Exception:
        logger.exception("post_run_dedup_failed")
    # Update weather and generate report
    _gen_weather_report(location, base_url=base_url, model=model, temp_unit=temp_unit)
    logger.info("harvest_complete", extra={"location": location, "fetched": len(new_arts) if new_arts else 0})
    progress.finish()


SCHEDULER: Optional[BackgroundScheduler] = None


def start_scheduler() -> BackgroundScheduler:
    tzname = _tz_name()
    tz = pytz.timezone(tzname)
    sched = BackgroundScheduler(timezone=tz)

    h1, m1 = _get_env_time("SCHEDULE_MORNING", "07:30")
    h2, m2 = _get_env_time("SCHEDULE_NOON", "12:00")
    h3, m3 = _get_env_time("SCHEDULE_EVENING", "19:30")

    for hh, mm, name in [
        (h1, m1, "morning"),
        (h2, m2, "noon"),
        (h3, m3, "evening"),
    ]:
        trigger = CronTrigger(hour=hh, minute=mm)
        sched.add_job(run_harvest_once, trigger=trigger, id=f"harvest_{name}", coalesce=True, max_instances=1)
        logger.info("scheduler_job_added", extra={"job": name, "hour": hh, "minute": mm, "tz": tzname})

    sched.start()
    logger.info("scheduler_started", extra={"tz": tzname})
    global SCHEDULER
    SCHEDULER = sched
    return sched


def next_runs() -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    try:
        if SCHEDULER is None:
            return out
        jobs = SCHEDULER.get_jobs()
        for j in jobs:
            if j.next_run_time is not None:
                out.append({"id": j.id, "next_run": j.next_run_time.isoformat()})
        out.sort(key=lambda x: x["next_run"])
    except Exception:
        pass
    return out
