from __future__ import annotations

import logging
from typing import Dict, List, Tuple
import re
from urllib.parse import urlsplit

from .database import SessionLocal
from .models import Article, AppSettings
from . import scheduler as scheduler_mod

logger = logging.getLogger("app.maintenance")


def _norm_title(text: str | None) -> str | None:
    if not text:
        return None
    s = text.lower().strip()
    # Normalize dashes/quotes and collapse whitespace
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    s = re.sub(r"\s+", " ", s)
    # Drop most punctuation except alnum and spaces
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    s = s.strip()
    return s or None


def _norm_image(url: str | None) -> str | None:
    if not url:
        return None
    try:
        u = urlsplit(url)
        # Use host + path only, strip query/fragments and lower host
        host = (u.netloc or "").lower()
        path = (u.path or "").rstrip("/")
        if not host and not path:
            return None
        return f"{host}{path}"
    except Exception:
        return None


def purge_duplicate_articles() -> dict:
    """Remove duplicate Article rows that share the same (normalized) title.

    We group by a normalized title (prefer `ai_title`, fallback to `source_title`).
    For each group we keep the "most updated" record and delete the rest.

    Keep preference (highest wins):
      1) Non-fallback AI body present
      2) Any AI body present
      3) Newest `ai_generated_at`
      4) Newest `fetched_at`
      5) Newest `published_at`
      6) Longer `raw_content`
      7) Higher id (stable tiebreak)
    """
    session = SessionLocal()
    deleted_ids: List[int] = []
    kept: Dict[str, int] = {}
    try:
        rows: List[Tuple[
            int,
            str | None,  # ai_title
            str | None,  # source_title
            str | None,  # ai_body
            str | None,  # ai_model
            object | None,  # ai_generated_at
            object | None,  # fetched_at
            object | None,  # published_at
            str | None,  # raw_content
            str | None,  # image_url
        ]] = (
            session.query(
                Article.id,
                Article.ai_title,
                Article.source_title,
                Article.ai_body,
                Article.ai_model,
                Article.ai_generated_at,
                Article.fetched_at,
                Article.published_at,
                Article.raw_content,
                Article.image_url,
            ).all()
        )

        # First pass: group by normalized title
        groups: Dict[str, List[Tuple[int, str | None, str | None, object | None, object | None, object | None, str | None, str | None]]] = {}
        for (art_id, ai_title, source_title, ai_body, ai_model, ai_gen, fetched_at, published_at, raw_content, image_url) in rows:
            key = _norm_title(ai_title) or _norm_title(source_title)
            if not key:
                continue
            groups.setdefault(key, []).append(
                (art_id, ai_body, ai_model, ai_gen, fetched_at, published_at, raw_content, image_url)
            )

        def score(item: Tuple[int, str | None, str | None, object | None, object | None, object | None, str | None, str | None]) -> tuple:
            _id, ai_body, ai_model, ai_gen, fetched_at, published_at, raw, _img = item
            has_ai = 1 if (ai_body and ai_body.strip()) else 0
            non_fallback = 1 if (has_ai and not (ai_model or "").startswith("fallback:")) else 0
            def ts(x):
                try:
                    return int(x.timestamp()) if x else 0
                except Exception:
                    return 0
            ai_ts = ts(ai_gen)
            fetched_ts = ts(fetched_at)
            pub_ts = ts(published_at)
            raw_len = len(raw or "")
            # Higher tuple wins
            return (non_fallback, has_ai, ai_ts, fetched_ts, pub_ts, raw_len, _id)

        for key, items in groups.items():
            if len(items) <= 1:
                kept[key] = items[0][0]
                continue
            items_sorted = sorted(items, key=score, reverse=True)
            keep_id = items_sorted[0][0]
            kept[key] = keep_id
            dup_ids = [it[0] for it in items_sorted[1:]]
            if dup_ids:
                (
                    session.query(Article)
                    .filter(Article.id.in_(dup_ids))
                    .delete(synchronize_session=False)
                )
                deleted_ids.extend(dup_ids)

        # Second pass: group remaining rows by normalized image URL to catch lookalikes
        if True:
            remaining_rows: List[Tuple[int, str | None, str | None, str | None, str | None, object | None, object | None, object | None, str | None, str | None]] = (
                session.query(
                    Article.id,
                    Article.ai_title,
                    Article.source_title,
                    Article.ai_body,
                    Article.ai_model,
                    Article.ai_generated_at,
                    Article.fetched_at,
                    Article.published_at,
                    Article.raw_content,
                    Article.image_url,
                ).all()
            )
            img_groups: Dict[str, List[Tuple[int, str | None, str | None, object | None, object | None, object | None, str | None, str | None]]] = {}
            for (art_id, ai_title, source_title, ai_body, ai_model, ai_gen, fetched_at, published_at, raw_content, image_url) in remaining_rows:
                kimg = _norm_image(image_url)
                if not kimg:
                    continue
                # Only consider as a potential duplicate if we also can normalize a title (avoid grouping everything by a stock image)
                ktit = _norm_title(ai_title) or _norm_title(source_title)
                if not ktit:
                    continue
                img_groups.setdefault(kimg, []).append(
                    (art_id, ai_body, ai_model, ai_gen, fetched_at, published_at, raw_content, image_url)
                )
            for key, items in img_groups.items():
                if len(items) <= 1:
                    continue
                items_sorted = sorted(items, key=score, reverse=True)
                keep_id = items_sorted[0][0]
                dup_ids = [it[0] for it in items_sorted[1:]]
                if dup_ids:
                    (
                        session.query(Article)
                        .filter(Article.id.in_(dup_ids))
                        .delete(synchronize_session=False)
                    )
                    deleted_ids.extend(dup_ids)
        session.commit()
        logger.info(
            "maintenance:dedup",
            extra={"deleted": len(deleted_ids), "groups": len(groups)},
        )
        return {"deleted": len(deleted_ids), "kept_groups": len(kept)}
    finally:
        session.close()


def rewrite_missing_articles(limit: int | None = None) -> dict:
    """Queue rewrites for articles missing AI text or using fallback.

    Runs in-process using the same logic as the scheduler: up to 3 retries with
    10-minute timeouts. Optionally limit the number of articles processed.
    """
    session = SessionLocal()
    try:
        q = session.query(Article).filter(
            (Article.ai_body.is_(None)) | (Article.ai_model.like("fallback:%"))
        ).order_by(Article.fetched_at.desc())
        if limit is not None and limit > 0:
            q = q.limit(int(limit))
        to_fix: List[Article] = q.all()

        # Load current AI settings
        aset = session.query(AppSettings).filter_by(id=1).one_or_none()
        base_url = aset.ollama_base_url if aset and aset.ollama_base_url else None
        model = aset.ollama_model if aset and aset.ollama_model else None

        # Report progress totals
        scheduler_mod.progress.phase('rewrite', f'Rewriting missing/fallback articles')
        scheduler_mod.progress.set_rewrite_total(len(to_fix))

        # Use shared implementation (serialized across the app)
        with scheduler_mod.REWRITE_LOCK:
            scheduler_mod._rewrite_and_store(to_fix, base_url=base_url, model=model)
        scheduler_mod.progress.finish()
        return {"rewritten": len(to_fix)}
    finally:
        session.close()
