from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Dict, Any

import requests

from .database import SessionLocal
from .models import AppConfig


def _env_location_override() -> Optional[str]:
    val = os.environ.get("LOCATION_NAME")
    return val.strip() if val else None


def _ip_api() -> Optional[Dict[str, Any]]:
    try:
        # ip-api.com free endpoint (HTTP only)
        r = requests.get("http://ip-api.com/json", timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "success":
            return data
    except Exception:
        return None
    return None


def _openmeteo_geocode(name: str) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": name, "count": 1, "language": "en", "format": "json"},
            timeout=15,
        )
        r.raise_for_status()
        js = r.json()
        results = js.get("results") or []
        return results[0] if results else None
    except Exception:
        return None


def resolve_location() -> AppConfig:
    """Resolve server location automatically and persist in DB.
    Prefers env override, else IP geolocation, enriched with Open‑Meteo.
    """
    session = SessionLocal()
    try:
        cfg = session.query(AppConfig).filter_by(id=1).one_or_none()
        if cfg:
            return cfg

        cfg = AppConfig(id=1)

        # 1) Env override
        env_loc = _env_location_override()
        if env_loc:
            enriched = _openmeteo_geocode(env_loc)
            if enriched:
                state = enriched.get("admin1") or ""
                loc_name = f"{enriched.get('name')}, {state}".strip().strip(', ')
                cfg.location_name = loc_name
                cfg.latitude = enriched.get("latitude")
                cfg.longitude = enriched.get("longitude")
                cfg.timezone = enriched.get("timezone") or os.environ.get("TZ", "America/New_York")
                cfg.source = "env+openmeteo"
            else:
                cfg.location_name = env_loc
                cfg.timezone = os.environ.get("TZ", "America/New_York")
                cfg.source = "env"

        # 2) IP geolocation fallback
        if not cfg.location_name:
            ip = _ip_api()
            if ip:
                city = ip.get("city") or ""
                region = ip.get("regionName") or ip.get("region") or ""
                tz = ip.get("timezone") or os.environ.get("TZ", "America/New_York")
                loc_name = f"{city}, {region}".strip().strip(', ')
                cfg.location_name = loc_name if loc_name else region or city or "Local"
                cfg.latitude = ip.get("lat")
                cfg.longitude = ip.get("lon")
                cfg.timezone = tz
                cfg.source = "ip-api"

        # 3) If we have a name but no coords, try Open‑Meteo to enrich
        if cfg.location_name and (cfg.latitude is None or cfg.longitude is None):
            enriched = _openmeteo_geocode(cfg.location_name)
            if enriched:
                cfg.latitude = enriched.get("latitude")
                cfg.longitude = enriched.get("longitude")
                cfg.timezone = cfg.timezone or enriched.get("timezone") or os.environ.get("TZ", "America/New_York")
                if cfg.source:
                    cfg.source += "+openmeteo"
                else:
                    cfg.source = "openmeteo"

        # Final fallback
        if not cfg.location_name:
            cfg.location_name = os.environ.get("FALLBACK_LOCATION", "Schenectady, NY")
            cfg.timezone = os.environ.get("TZ", "America/New_York")
            cfg.source = (cfg.source or "") + "+fallback"

        cfg.resolved_at = datetime.utcnow()
        session.merge(cfg)
        session.commit()
        try:
            session.refresh(cfg)
        except Exception:
            pass
        return cfg
    finally:
        session.close()


def location_keywords() -> list[str]:
    """Produce expanded search seeds from resolved location.
    Uses city/state and broader regional aliases to improve coverage.
    """
    cfg = resolve_location()
    base = cfg.location_name or ""
    parts = [p.strip() for p in base.split(",")]
    city = parts[0] if parts else base
    state = parts[1] if len(parts) > 1 else ""

    seeds = [
        base,
        f"{city} {state}".strip(),
        f"{city} County" if city else "",
        f"{state} local news" if state else "",
        f"{city} local news" if city else "",
    ]

    # Broader upstate NY heuristics if state is New York
    s_low = state.lower()
    c_low = city.lower()
    if "new york" in s_low or s_low in ("ny",):
        seeds.extend([
            "Capital Region NY",
            "Albany Schenectady Troy",
            "Upstate New York",
        ])

    return [s for s in seeds if s]


def set_location(name: str) -> AppConfig:
    """Set a manual location override and persist to DB using Open‑Meteo geocoding."""
    session = SessionLocal()
    try:
        cfg = session.query(AppConfig).filter_by(id=1).one_or_none() or AppConfig(id=1)
        enriched = _openmeteo_geocode(name)
        if enriched:
            state = enriched.get("admin1") or ""
            loc_name = f"{enriched.get('name')}, {state}".strip().strip(', ')
            cfg.location_name = loc_name
            cfg.latitude = enriched.get("latitude")
            cfg.longitude = enriched.get("longitude")
            cfg.timezone = enriched.get("timezone") or os.environ.get("TZ", "America/New_York")
            cfg.source = "manual+openmeteo"
        else:
            cfg.location_name = name
            cfg.timezone = os.environ.get("TZ", "America/New_York")
            cfg.source = "manual"
        from datetime import datetime
        cfg.resolved_at = datetime.utcnow()
        session.merge(cfg)
        session.commit()
        try:
            session.refresh(cfg)
        except Exception:
            pass
        return cfg
    finally:
        session.close()


def auto_set_location() -> AppConfig:
    """Force re-detect server location and persist to DB (overwrites existing)."""
    session = SessionLocal()
    try:
        cfg = session.query(AppConfig).filter_by(id=1).one_or_none() or AppConfig(id=1)
        # Prefer env override if present
        env_loc = _env_location_override()
        if env_loc:
            enriched = _openmeteo_geocode(env_loc)
            if enriched:
                state = enriched.get("admin1") or ""
                loc_name = f"{enriched.get('name')}, {state}".strip().strip(', ')
                cfg.location_name = loc_name
                cfg.latitude = enriched.get("latitude")
                cfg.longitude = enriched.get("longitude")
                cfg.timezone = enriched.get("timezone") or os.environ.get("TZ", "America/New_York")
                cfg.source = "env+openmeteo"
            else:
                cfg.location_name = env_loc
                cfg.timezone = os.environ.get("TZ", "America/New_York")
                cfg.source = "env"
        else:
            ip = _ip_api()
            if ip:
                city = ip.get("city") or ""
                region = ip.get("regionName") or ip.get("region") or ""
                tz = ip.get("timezone") or os.environ.get("TZ", "America/New_York")
                loc_name = f"{city}, {region}".strip().strip(', ')
                cfg.location_name = loc_name if loc_name else region or city or "Local"
                cfg.latitude = ip.get("lat")
                cfg.longitude = ip.get("lon")
                cfg.timezone = tz
                cfg.source = "ip-api"
            # Enrich if needed
            if cfg.location_name and (cfg.latitude is None or cfg.longitude is None):
                enriched = _openmeteo_geocode(cfg.location_name)
                if enriched:
                    cfg.latitude = enriched.get("latitude")
                    cfg.longitude = enriched.get("longitude")
                    cfg.timezone = cfg.timezone or enriched.get("timezone") or os.environ.get("TZ", "America/New_York")
                    cfg.source = (cfg.source or "") + "+openmeteo"
        from datetime import datetime
        cfg.resolved_at = datetime.utcnow()
        session.merge(cfg)
        session.commit()
        return cfg
    finally:
        session.close()
