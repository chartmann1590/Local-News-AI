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
from .geo import resolve_location, get_local_now
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


def _rewrite_and_store(articles, *, base_url: str | None, model: str | None, fallback_base_url: str | None = None):
    session = SessionLocal()
    try:
        processed = 0
        total = len(articles)
        for i, art in enumerate(articles, start=1):
            # Merge article into current session to ensure it's persistent
            # This handles cases where articles come from different sessions
            art = session.merge(art)
            
            # Rewrite when missing AI, but NOT if it's a fallback or skipped article
            # Fallback articles should be kept permanently, skipped articles can be retried later
            needs_rewrite = (art.raw_content is not None) and (
                (not art.ai_body) and not ((art.ai_model or "").startswith("fallback:"))
            )
            if needs_rewrite:
                # Update progress detail with current item
                try:
                    from urllib.parse import urlparse
                    label = (art.source_title or urlparse(art.source_url or '').netloc or 'article').strip()
                    label = (label[:80] + '…') if len(label) > 80 else label
                    progress.phase('rewrite', f'Rewriting ({i}/{total}): {label}')
                    progress.set_current(art_id=art.id, title=art.source_title, url=art.source_url)
                except Exception:
                    progress.phase('rewrite', f'Rewriting ({i}/{total})')
                    progress.set_current(art_id=art.id, title=None, url=None)
                
                # Check if timeout is exceeded (stuck article) - auto-recover with fallback
                if progress.is_timeout_exceeded():
                    logger.warning(f"Article {art.id} appears stuck (timeout exceeded), applying fallback")
                    art.ai_title = (art.source_title or "").strip()[:500]
                    art.ai_body = (art.raw_content or "").strip()
                    art.ai_model = "fallback:source"
                    art.ai_generated_at = get_local_now()
                    session.add(art)
                    session.commit()
                    processed += 1
                    progress.inc_rewrite(1)
                    progress.clear_timeout()  # Clear timeout tracking
                    progress.clear_flags()
                    continue
                
                # Check if skip was requested (verify it's for this article)
                snapshot = progress.snapshot()
                if snapshot.get('skip_current') and snapshot.get('current_id') == art.id:
                    logger.info(f"Skipping article {art.id} per user request")
                    progress.inc_rewrite(1)
                    progress.clear_flags()  # Clear the flag after using it
                    continue
                
                # Check if fallback was requested (verify it's for this article)
                snapshot = progress.snapshot()
                if snapshot.get('fallback_current') and snapshot.get('current_id') == art.id:
                    logger.info(f"Using fallback for article {art.id} per user request")
                    art.ai_title = (art.source_title or "").strip()[:500]
                    art.ai_body = (art.raw_content or "").strip()
                    art.ai_model = "fallback:source"
                    art.ai_generated_at = get_local_now()
                    session.add(art)
                    session.commit()
                    processed += 1
                    progress.inc_rewrite(1)
                    progress.clear_flags()  # Clear the flag after using it
                    continue
                
                # Retry up to 3 times, 10 minute timeout per attempt (minimum 3 minutes enforced in rewrite_article)
                res = None
                for _attempt in range(3):
                    # Check if timeout is exceeded (stuck article) - auto-recover with fallback
                    if progress.is_timeout_exceeded():
                        logger.warning(f"Article {art.id} appears stuck (timeout exceeded during retry), applying fallback")
                        art.ai_title = (art.source_title or "").strip()[:500]
                        art.ai_body = (art.raw_content or "").strip()
                        art.ai_model = "fallback:source"
                        art.ai_generated_at = get_local_now()
                        session.add(art)
                        session.commit()
                        processed += 1
                        progress.inc_rewrite(1)
                        progress.clear_timeout()  # Clear timeout tracking
                        progress.clear_flags()
                        res = None  # Mark as fallback applied
                        break
                    
                    # Check skip/fallback before each attempt
                    snapshot = progress.snapshot()
                    if snapshot.get('skip_current') and snapshot.get('current_id') == art.id:
                        logger.info(f"Skipping article {art.id} per user request (during retry)")
                        res = None  # Mark as skipped
                        progress.clear_flags()  # Clear flag
                        break
                    if snapshot.get('fallback_current') and snapshot.get('current_id') == art.id:
                        logger.info(f"Using fallback for article {art.id} per user request (during retry)")
                        res = None  # Force fallback
                        progress.clear_flags()  # Clear flag
                        break
                    
                    # Check if article was updated by fallback endpoint (has ai_body now)
                    session.refresh(art)
                    if art.ai_body and art.ai_model and art.ai_model.startswith("fallback:"):
                        logger.info(f"Article {art.id} already has fallback content (updated externally), skipping rewrite")
                        processed += 1
                        progress.inc_rewrite(1)
                        break
                    
                    # Check flags right before starting rewrite
                    snapshot = progress.snapshot()
                    if snapshot.get('skip_current') and snapshot.get('current_id') == art.id:
                        logger.info(f"Skipping article {art.id} per user request (before rewrite)")
                        res = None
                        progress.clear_flags()
                        break
                    if snapshot.get('fallback_current') and snapshot.get('current_id') == art.id:
                        logger.info(f"Using fallback for article {art.id} per user request (before rewrite)")
                        # Apply fallback immediately
                        art.ai_title = (art.source_title or "").strip()[:500]
                        art.ai_body = (art.raw_content or "").strip()
                        art.ai_model = "fallback:source"
                        art.ai_generated_at = get_local_now()
                        session.add(art)
                        session.commit()
                        processed += 1
                        progress.inc_rewrite(1)
                        progress.clear_flags()
                        res = None
                        break
                    
                    # Check during the rewrite attempt
                    # Note: rewrite_article() is blocking, but we check flags immediately after it completes
                    try:
                        res = rewrite_article(art.raw_content, art.source_title, art.location or _location(), base_url=base_url, model=model, fallback_base_url=fallback_base_url, timeout_s=600)  # 600s = 10 min, minimum 3 min enforced
                    except Exception as rewrite_err:
                        # Check if user requested skip/fallback during the rewrite
                        snapshot = progress.snapshot()
                        if snapshot.get('skip_current') and snapshot.get('current_id') == art.id:
                            logger.info(f"Skipping article {art.id} per user request (after rewrite error)")
                            res = None
                            progress.clear_flags()  # Clear flag
                            break
                        if snapshot.get('fallback_current') and snapshot.get('current_id') == art.id:
                            logger.info(f"Using fallback for article {art.id} per user request (after rewrite error)")
                            res = None
                            progress.clear_flags()  # Clear flag
                            break
                        # If it's a real error and no skip/fallback requested, continue to next attempt
                        logger.warning(f"Rewrite attempt {_attempt + 1} failed: {rewrite_err}")
                        res = None
                    
                    # Check flags again after attempt
                    snapshot = progress.snapshot()
                    if snapshot.get('skip_current') and snapshot.get('current_id') == art.id:
                        logger.info(f"Skipping article {art.id} per user request (after attempt)")
                        res = None
                        progress.clear_flags()
                        break
                    if snapshot.get('fallback_current') and snapshot.get('current_id') == art.id:
                        logger.info(f"Using fallback for article {art.id} per user request (after attempt)")
                        # Apply fallback immediately
                        art.ai_title = (art.source_title or "").strip()[:500]
                        art.ai_body = (art.raw_content or "").strip()
                        art.ai_model = "fallback:source"
                        art.ai_generated_at = get_local_now()
                        session.add(art)
                        session.commit()
                        processed += 1
                        progress.inc_rewrite(1)
                        progress.clear_flags()
                        res = None
                        break
                    
                    if res and (res.get("title") or res.get("body")):
                        break
                    
                    # Small delay between retries to allow skip/fallback flags to be processed
                    if _attempt < 2:  # Don't delay after last attempt
                        import time
                        time.sleep(0.5)  # Brief pause to check flags
                if res and (res.get("title") or res.get("body")):
                    art.ai_title = (res.get("title") or art.source_title or "").strip()[:500]
                    art.ai_body = (res.get("body") or "").strip()
                    art.ai_model = (model or os.environ.get("OLLAMA_MODEL", "llama3.2"))
                    art.ai_generated_at = get_local_now()
                else:
                    # Fallback to source content
                    art.ai_title = (art.source_title or "").strip()[:500]
                    art.ai_body = (art.raw_content or "").strip()
                    art.ai_model = "fallback:source"
                    art.ai_generated_at = get_local_now()
                session.add(art)
                session.commit()
                processed += 1
                progress.inc_rewrite(1)
        logger.info("rewrite_completed", extra={"processed": processed})
    finally:
        session.close()


def _gen_weather_report(location: str, *, base_url: str | None, model: str | None, temp_unit: str | None, wind_speed_unit: str | None = None):
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
    wr = update_weather(location=location, tz=tz, lat=lat, lon=lon, temp_unit=temp_unit, wind_speed_unit=wind_speed_unit)
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
        text = generate_weather_report(forecast, location, base_url=base_url, model=model, wind_speed_unit=wind_speed_unit, timeout_s=600)
        if text:
            break
    if text:
        session = SessionLocal()
        try:
            wr.ai_report = text
            wr.ai_model = (model or os.environ.get("OLLAMA_MODEL", "llama3.2"))
            wr.ai_generated_at = get_local_now()
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
            wr.ai_generated_at = get_local_now()
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
    # Load AI settings
    session = SessionLocal()
    try:
        aset = session.query(AppSettings).filter_by(id=1).one_or_none()
        # Initialize AppSettings with defaults if it doesn't exist
        if not aset:
            aset = AppSettings(id=1, temp_unit='F', wind_speed_unit='mph')
            session.add(aset)
            session.commit()
        # Always use DB values - never default to None which would cause C/kmh defaults
        # If user hasn't set them yet, use the initialized defaults
        temp_unit = aset.temp_unit if aset.temp_unit else 'F'
        wind_speed_unit = aset.wind_speed_unit if aset.wind_speed_unit else 'mph'
        base_url = (aset.ollama_base_url if aset.ollama_base_url else os.environ.get("OLLAMA_BASE_URL"))
        model = (aset.ollama_model if aset.ollama_model else os.environ.get("OLLAMA_MODEL"))
        fallback_base_url = (aset.ollama_fallback_base_url if aset and aset.ollama_fallback_base_url else None)
        
        # Query for existing articles that need rewriting (missing ai_body or using fallback model)
        # This ensures failed rewrites get retried on every scheduled run
        existing_needing_rewrite = session.query(Article).filter(
            Article.raw_content.isnot(None),
            (Article.ai_body.is_(None) | Article.ai_model.like("fallback:%"))
        ).all()
        
        # Combine new articles with existing articles needing rewrites
        all_articles_to_rewrite = list(new_arts) if new_arts else []
        all_articles_to_rewrite.extend(existing_needing_rewrite)
        
        total_to_rewrite = len(all_articles_to_rewrite)
        logger.info("articles_to_rewrite", extra={"new": len(new_arts) if new_arts else 0, "existing_retry": len(existing_needing_rewrite), "total": total_to_rewrite})
    finally:
        session.close()
    
    # Rewrite via Ollama - includes both new articles and existing articles that need retry
    progress.phase('rewrite', f'Rewriting articles')
    progress.set_rewrite_total(total_to_rewrite)
    # Ensure only a single rewrite runs at a time
    with REWRITE_LOCK:
        _rewrite_and_store(all_articles_to_rewrite, base_url=base_url, model=model, fallback_base_url=fallback_base_url)
    # Enforce deduplication after each run to eliminate lookalikes
    try:
        from .maintenance import purge_duplicate_articles
        purge_duplicate_articles()
    except Exception:
        logger.exception("post_run_dedup_failed")
    # Update weather and generate report
    _gen_weather_report(location, base_url=base_url, model=model, temp_unit=temp_unit, wind_speed_unit=wind_speed_unit)
    
    # Generate broadcast after content updates
    try:
        from .broadcast import generate_and_compile_broadcast
        progress.phase('broadcast', 'Generating news broadcast')
        generate_and_compile_broadcast(
            base_url=base_url,
            model=model,
            location=location,
            force=False
        )
        logger.info("broadcast_generated", extra={"location": location})
    except Exception:
        logger.exception("broadcast_generation_failed")
    
    logger.info("harvest_complete", extra={"location": location, "fetched": len(new_arts) if new_arts else 0})
    progress.finish()


SCHEDULER: Optional[BackgroundScheduler] = None


def start_scheduler() -> BackgroundScheduler:
    global SCHEDULER
    # If scheduler exists and is running, shut it down first
    if SCHEDULER is not None and SCHEDULER.running:
        logger.info("scheduler_restarting", extra={"old_tz": SCHEDULER.timezone if hasattr(SCHEDULER, 'timezone') else None})
        SCHEDULER.shutdown(wait=False)
    
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
        trigger = CronTrigger(hour=hh, minute=mm, timezone=tz)
        sched.add_job(run_harvest_once, trigger=trigger, id=f"harvest_{name}", coalesce=True, max_instances=1)
        logger.info("scheduler_job_added", extra={"job": name, "hour": hh, "minute": mm, "tz": tzname})

    sched.start()
    logger.info("scheduler_started", extra={"tz": tzname})
    SCHEDULER = sched
    return sched


def restart_scheduler() -> BackgroundScheduler:
    """Restart the scheduler with the current timezone from the database."""
    logger.info("scheduler_restart_requested")
    return start_scheduler()


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
