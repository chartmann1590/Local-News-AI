#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import Article, AppSettings
from app.ai import analyze_article_quality
import os

s = SessionLocal()
a94 = s.query(Article).filter_by(id=94).first()
aset = s.query(AppSettings).filter_by(id=1).one_or_none()

print(f"Article 94: {a94.source_title}")
print(f"Content length: {len(a94.raw_content or '')} chars")
print(f"First 500 chars: {(a94.raw_content or '')[:500]}")
print()

base_url = (aset.ollama_base_url if aset and aset.ollama_base_url else os.environ.get("OLLAMA_BASE_URL")) if aset else os.environ.get("OLLAMA_BASE_URL")
model = (aset.ollama_model if aset and aset.ollama_model else os.environ.get("OLLAMA_MODEL")) if aset else os.environ.get("OLLAMA_MODEL")

print(f"Testing quality analysis...")
print(f"Ollama URL: {base_url}")
print(f"Model: {model}")
print()

try:
    result = analyze_article_quality(
        content=a94.raw_content,
        title=a94.source_title,
        url=a94.source_url,
        location=a94.location,
        base_url=base_url,
        model=model,
        timeout_s=600
    )
    
    print(f"Quality Analysis Result:")
    print(f"  Score: {result.get('score')}")
    print(f"  Is Garbage: {result.get('is_garbage')}")
    print(f"  Reasons: {result.get('reasons')}")
    print(f"  Details: {result.get('details')}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

s.close()


