#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import Article

s = SessionLocal()
articles = s.query(Article).filter_by(is_published=True).order_by(Article.fetched_at.desc()).limit(3).all()

print("Most recent 3 published articles:\n")
for a in articles:
    print(f"Article {a.id}:")
    print(f"  Title: {a.source_title}")
    print(f"  URL: {a.source_url[:80]}...")
    print(f"  Fetched: {a.fetched_at}")
    print(f"  Content length: {len(a.raw_content or '')} chars")
    print(f"  First 500 chars of content:")
    print(f"  {(a.raw_content or '')[:500]}")
    print()

s.close()


