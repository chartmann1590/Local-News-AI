from __future__ import annotations

import os
import re
from datetime import datetime
from typing import List, Tuple, Optional, Dict

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from readability import Document

from .database import SessionLocal
from .models import Article
from .geo import location_keywords
from .progress import progress
import logging

logger = logging.getLogger("app.fetcher")


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _headers() -> Dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}


def normalize_url(url: str) -> str:
    try:
        from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
        u = urlsplit(url)
        scheme = (u.scheme or 'http').lower()
        netloc = (u.netloc or '').lower()
        path = u.path or ''
        # Strip common AMP suffixes
        if path.endswith('/amp') or path.endswith('/amp/'):
            path = path[: -4]
        if path.endswith('.amp'):
            path = path[: -4]
        # Remove fragments
        frag = ''
        # Drop tracking params
        drop = { 'utm_source','utm_medium','utm_campaign','utm_term','utm_content','gclid','fbclid','mc_cid','mc_eid','msclkid','igshid','ref','ref_src','utm_id','tid','c','mkt' }
        kept = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=False) if k.lower() not in drop]
        query = urlencode(kept, doseq=True)
        return urlunsplit((scheme, netloc, path, query, frag))
    except Exception:
        return url


def build_google_news_feeds(location: str) -> List[str]:
    from urllib.parse import quote_plus

    # Generate seeds from resolved location automatically
    seeds = location_keywords()
    feeds = []
    suffixes = ["", " local news", " breaking", " news"]
    for q in seeds[:6]:
        q_enc = quote_plus(q)
        for s in suffixes:
            q2 = quote_plus((q + s).strip())
            feeds.append(
                f"https://news.google.com/rss/search?q={q2}&hl=en-US&gl=US&ceid=US:en"
            )
        # Google News geo-local headlines
        feeds.append(
            f"https://news.google.com/rss/headlines/section/geo/{q_enc}?hl=en-US&gl=US&ceid=US:en"
        )
    # Dedupe while preserving order, then limit
    seen = set()
    uniq = []
    for f in feeds:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq[:10]


def build_bing_news_feeds(location: str) -> List[str]:
    from urllib.parse import quote_plus
    seeds = location_keywords()
    feeds: List[str] = []
    for q in seeds[:6]:
        q2 = quote_plus(f"{q} local news")
        feeds.append(f"https://www.bing.com/news/search?q={q2}&format=rss")
    # Dedupe and limit
    seen = set()
    uniq = []
    for f in feeds:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq[:6]


def extra_feed_urls() -> List[str]:
    val = os.environ.get("FEED_EXTRA_URLS", "").strip()
    if not val:
        return []
    return [x.strip() for x in val.split(",") if x.strip()]


def parse_published(value) -> Optional[datetime]:
    try:
        return dateparser.parse(value)
    except Exception:
        return None


def _extract_final_url_from_entry(entry) -> str:
    # Try to prefer publisher link over Google redirect when available
    for key in ("feedburner_origlink",):
        if key in entry:
            return entry[key]
    link = entry.get("link")
    if link and "news.google.com" not in link:
        # Handle Bing News aggregator links by extracting publisher url param
        try:
            if "bing.com/news/apiclick.aspx" in link and "url=" in link:
                from urllib.parse import urlparse, parse_qs
                q = parse_qs(urlparse(link).query)
                t = (q.get('url') or [None])[0]
                if t:
                    return normalize_url(t)
        except Exception:
            pass
        return normalize_url(link)
    # Follow redirects for Google links to reach publisher
    if link:
        try:
            # If Google redirect, try extract target from url param first
            if "news.google.com" in link and "url=" in link:
                from urllib.parse import urlparse, parse_qs
                q = parse_qs(urlparse(link).query)
                t = (q.get('url') or [None])[0]
                if t:
                    return normalize_url(t)
            resp = requests.get(link, headers=_headers(), timeout=15, allow_redirects=True)
            if resp.url:
                return normalize_url(resp.url)
        except Exception:
            return normalize_url(link)
    return normalize_url(link or "")


def _extract_image_url(html: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        for prop in ("og:image", "twitter:image", "image"):
            tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                return tag["content"].strip()
    except Exception:
        pass
    return None


def fetch_article_content(url: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        resp = requests.get(url, headers=_headers(), timeout=20)
        if resp.status_code != 200:
            return None, None
        html = resp.text
        doc = Document(html)
        content_html = doc.summary(html_partial=True)
        text = BeautifulSoup(content_html, "html.parser").get_text("\n")
        # Basic cleanup
        text = re.sub(r"\n{2,}", "\n\n", text).strip()
        img = _extract_image_url(html)
        # Fallback: try <article> tag if too short
        if not text or len(text) < 200:
            try:
                soup = BeautifulSoup(html, "html.parser")
                art = soup.find("article")
                if art:
                    tx = art.get_text("\n").strip()
                    tx = re.sub(r"\n{2,}", "\n\n", tx).strip()
                    if len(tx) > len(text):
                        text = tx
            except Exception:
                pass
        return text, img
    except Exception:
        return None, None


def gather_candidates(location: str) -> List[Dict]:
    # Prefer Bing (less likely to 503) before Google
    feeds = build_bing_news_feeds(location) + build_google_news_feeds(location) + extra_feed_urls()
    items: List[Dict] = []
    logger.info("feeds_start", extra={"count": len(feeds)})
    max_feeds = 12
    for i, feed_url in enumerate(feeds):
        if i >= max_feeds:
            break
        try:
            r = requests.get(feed_url, headers={"User-Agent": USER_AGENT}, timeout=6)
            if r.status_code != 200:
                logger.warning("feed_http_status", extra={"url": feed_url, "status": r.status_code})
                continue
            parsed = feedparser.parse(r.content)
            try:
                logger.info("feed_ok", extra={"url": feed_url, "entries": len(parsed.entries)})
            except Exception:
                pass
        except Exception as e:
            logger.warning("feed_error", extra={"url": feed_url, "error": str(e)})
            continue
        for e in parsed.entries:
            url = normalize_url(_extract_final_url_from_entry(e))
            if not url:
                continue
            title = e.get("title")
            source_name = None
            if "source" in e and hasattr(e.source, "title"):
                source_name = e.source.title
            published = parse_published(e.get("published") or e.get("updated"))
            items.append(
                {
                    "url": url,
                    "title": title,
                    "source_name": source_name,
                    "published": published,
                }
            )
    # Deduplicate by URL (normalized)
    uniq: Dict[str, Dict] = {}
    for it in items:
        key = normalize_url(it["url"])
        if key not in uniq:
            it["url"] = key
            uniq[key] = it
    out = list(uniq.values())
    if len(out) > 60:
        out = out[:60]
    logger.info("feeds_parsed", extra={"candidates": len(out)})
    return out


def fetch_new_articles(min_count: int, location: str) -> List[Article]:
    session = SessionLocal()
    created: List[Article] = []
    try:
        progress.phase('fetch', 'Gathering RSS candidates')
        candidates = gather_candidates(location)
        progress.phase('fetch', f'Found {len(candidates)} candidates')
        # Filter out URLs we already have (consider normalized forms)
        existing_raw = [u for (u,) in session.query(Article.source_url).all()]
        existing_norm = { normalize_url(u) for u in existing_raw }
        existing_all = set(existing_raw) | existing_norm
        new_items = [c for c in candidates if normalize_url(c["url"]) not in existing_all]
        logger.info("new_items", extra={"count": len(new_items)})

        for idx, item in enumerate(new_items, start=1):
            if len(created) >= min_count:
                break
            progress.phase('fetch', f'Fetching content {idx}/{len(new_items)}')
            content, image_url = fetch_article_content(item["url"])
            if not content or len(content) < 120:
                continue
            art = Article(
                source_url=item["url"],
                source_title=item.get("title"),
                source_name=item.get("source_name"),
                published_at=item.get("published"),
                location=location,
                raw_content=content,
                image_url=image_url,
            )
            session.add(art)
            session.commit()
            session.refresh(art)
            created.append(art)
        logger.info("created_articles", extra={"count": len(created)})
        return created
    finally:
        session.close()
