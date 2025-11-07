from app.database import SessionLocal
from app.models import Article, RejectedUrl

s = SessionLocal()

# Check article 94
art = s.query(Article).filter_by(id=94).first()
if art:
    print(f'Article 94:')
    print(f'  Title: {art.source_title}')
    print(f'  Published: {art.is_published}')
    print(f'  URL: {art.source_url[:80]}...')
else:
    print('Article 94 not found')

# Check rejected URLs
rejected_count = s.query(RejectedUrl).count()
print(f'\nTotal rejected URLs: {rejected_count}')

# Check if article 94's URL is rejected
if art:
    from app.news_fetcher import normalize_url
    norm_url = normalize_url(art.source_url)
    rejected = s.query(RejectedUrl).filter_by(url=norm_url).first()
    if rejected:
        print(f'  Article 94 URL is in rejected list: {rejected.rejection_reason}')
    else:
        print(f'  Article 94 URL is NOT in rejected list')

s.close()


