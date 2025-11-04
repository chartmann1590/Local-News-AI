from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

import requests
import pytz

from .database import SessionLocal
from .models import AppConfig


def get_local_now() -> datetime:
    """Get current datetime in the location's timezone.
    Always uses AppConfig.timezone, never UTC.
    Falls back to America/New_York if config not available.
    Reads directly from database to avoid circular dependencies.
    """
    try:
        session = SessionLocal()
        try:
            cfg = session.query(AppConfig).filter_by(id=1).one_or_none()
            tz_name = cfg.timezone if cfg and cfg.timezone else os.environ.get("TZ", "America/New_York")
            tz = pytz.timezone(tz_name)
            return datetime.now(tz)
        finally:
            session.close()
    except Exception:
        # Fallback to America/New_York if anything fails
        try:
            tz = pytz.timezone("America/New_York")
            return datetime.now(tz)
        except Exception:
            # Last resort: use system local timezone
            return datetime.now()


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
        # Extract city and state from name if comma-separated
        search_name = name
        target_state = None
        target_state_lower = None
        city_name = None
        
        if "," in name:
            parts = [p.strip() for p in name.split(",")]
            if len(parts) >= 2:
                city_name = parts[0]
                state_part = parts[-1].lower()
                # Map state abbreviations and names
                state_map = {
                    "ny": "New York", "new york": "New York",
                    "ca": "California", "california": "California",
                    "tx": "Texas", "texas": "Texas",
                    "fl": "Florida", "florida": "Florida",
                    "pa": "Pennsylvania", "pennsylvania": "Pennsylvania",
                    "il": "Illinois", "illinois": "Illinois",
                }
                # Normalize state to lowercase for matching
                if state_part in state_map:
                    target_state = state_map[state_part]  # Keep capitalized for display
                    target_state_lower = state_part if state_part in ["ny", "ca", "tx", "fl", "pa", "il"] else state_map[state_part].lower()
                else:
                    target_state = state_part.title()
                    target_state_lower = state_part.lower()
                # Try searching with just city name first, then filter by state
                search_name = city_name
        
        # Search with the city name
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": search_name, "count": 20, "language": "en", "format": "json"},
            timeout=15,
        )
        r.raise_for_status()
        js = r.json()
        results = js.get("results") or []
        if not results:
            return None
        
        # If we have a target state, find the result that matches
        if target_state:
            # Use the lowercase version we computed, or fallback to lowercasing target_state
            if target_state_lower is None:
                target_state_lower = target_state.lower()
            
            # Find matching result by state
            for result in results:
                admin1 = (result.get("admin1") or "").lower()
                country_code = (result.get("country_code") or "").lower()
                
                # Must be US
                if country_code != "us":
                    continue
                
                # Check if state matches (handle variations)
                # For "New York", match "new york" or "ny" in admin1
                state_matches = False
                if target_state_lower == "new york":
                    state_matches = ("new york" in admin1 or admin1 == "ny")
                elif target_state_lower == "ny":
                    state_matches = ("new york" in admin1 or admin1 == "ny")
                # For other states, check if state name is in admin1
                elif target_state_lower in admin1:
                    state_matches = True
                # Check if abbreviation matches
                elif len(target_state_lower) == 2 and admin1 == target_state_lower:
                    state_matches = True
                
                if state_matches:
                    return result
        
        # If no state specified or no match found, prefer US results
        for result in results:
            if result.get("country_code", "").lower() == "us":
                return result
        
        # Return first result as fallback
        return results[0]
    except Exception as e:
        import logging
        import traceback
        error_msg = f"_openmeteo_geocode error for '{name}': {e}\n{traceback.format_exc()}"
        logging.error(error_msg)
        return None


def resolve_location() -> AppConfig:
    """Resolve server location automatically and persist in DB.
    Prefers env override, else IP geolocation, enriched with Open‑Meteo.
    NEVER overwrites existing location_name if one is already set in the database.
    This ensures user-set locations are NEVER changed on rebuild/restart.
    """
    session = SessionLocal()
    try:
        cfg = session.query(AppConfig).filter_by(id=1).one_or_none()
        # CRITICAL: If location_name exists and is not empty, NEVER overwrite it
        # This prevents IP geolocation or ENV vars from changing user-set locations
        if cfg and cfg.location_name and cfg.location_name.strip():
            # Existing location found - preserve it completely, never overwrite
            # Only update resolved_at timestamp if it's missing
            if not cfg.resolved_at:
                cfg.resolved_at = get_local_now()
                session.merge(cfg)
                session.commit()
            return cfg
        # Only auto-resolve if no config exists OR config exists but has no location_name
        if not cfg:
            cfg = AppConfig(id=1)

        # 1) Env override - ONLY if location_name is not already set
        # CRITICAL: Do NOT let ENV vars override existing user-set locations
        env_loc = None
        if not cfg.location_name or not cfg.location_name.strip():
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

        cfg.resolved_at = get_local_now()
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
    """Set a manual location override and persist to DB using Open‑Meteo geocoding.
    Validates coordinates to ensure they match the location name before saving.
    """
    session = SessionLocal()
    try:
        cfg = session.query(AppConfig).filter_by(id=1).one_or_none() or AppConfig(id=1)
        enriched = _openmeteo_geocode(name)
        if enriched:
            state = enriched.get("admin1") or ""
            loc_name = f"{enriched.get('name')}, {state}".strip().strip(', ')
            lat = enriched.get("latitude")
            lon = enriched.get("longitude")
            
            # Validate coordinates by checking all results if the first seems wrong
            name_lower = name.lower()
            # If name contains state info, verify the result matches
            if any(state_term in name_lower for state_term in ["new york", "ny", "california", "ca", "texas", "tx", "florida", "fl"]):
                result_admin1 = (enriched.get("admin1") or "").lower()
                result_country = (enriched.get("country_code") or "").lower()
                
                # Check if the state matches
                state_matches = False
                if "new york" in name_lower or "ny" in name_lower:
                    state_matches = "new york" in result_admin1 or result_admin1 == "ny"
                elif "california" in name_lower or "ca" in name_lower:
                    state_matches = "california" in result_admin1
                elif "texas" in name_lower or "tx" in name_lower:
                    state_matches = "texas" in result_admin1
                elif "florida" in name_lower or "fl" in name_lower:
                    state_matches = "florida" in result_admin1
                
                # If state doesn't match, search again with more specific query
                if not state_matches and result_country == "us":
                    # Try searching with state abbreviation or full state name
                    if "ny" in name_lower or "new york" in name_lower:
                        better_result = _openmeteo_geocode(f"{name.split(',')[0].strip()}, NY, USA")
                    else:
                        better_result = _openmeteo_geocode(f"{name}, USA")
                    
                    if better_result:
                        better_admin1 = (better_result.get("admin1") or "").lower()
                        if (("new york" in name_lower or "ny" in name_lower) and ("new york" in better_admin1 or better_admin1 == "ny")) or \
                           (("california" in name_lower or "ca" in name_lower) and "california" in better_admin1) or \
                           (("texas" in name_lower or "tx" in name_lower) and "texas" in better_admin1) or \
                           (("florida" in name_lower or "fl" in name_lower) and "florida" in better_admin1):
                            enriched = better_result
                            state = enriched.get("admin1") or ""
                            loc_name = f"{enriched.get('name')}, {state}".strip().strip(', ')
                            lat = enriched.get("latitude")
                            lon = enriched.get("longitude")
            
            cfg.location_name = loc_name
            cfg.latitude = lat
            cfg.longitude = lon
            cfg.timezone = enriched.get("timezone") or os.environ.get("TZ", "America/New_York")
            cfg.source = "manual+openmeteo"
        else:
            cfg.location_name = name
            cfg.timezone = os.environ.get("TZ", "America/New_York")
            cfg.source = "manual"
        cfg.resolved_at = get_local_now()
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
        cfg.resolved_at = get_local_now()
        session.merge(cfg)
        session.commit()
        return cfg
    finally:
        session.close()
