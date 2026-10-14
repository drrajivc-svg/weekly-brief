import os
import json
import re
import hashlib
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
from anthropic import Anthropic
from pubmed_research import collect_pubmed_research

OUTPUT = 'articles.json'
API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not API_KEY:
    raise RuntimeError('ANTHROPIC_API_KEY is not configured')
client = Anthropic(api_key=API_KEY)

SOURCES = {
    'AI & Technology': [
        'artificial intelligence OpenAI Anthropic Google',
        'robotics technology breakthroughs',
    ],
    'Gaming': [
        'gaming industry game development',
        'Unreal Engine Godot AI gaming',
    ],
    'Politics & World': [
        'US politics public policy',
        'world politics international affairs',
    ],
}
LIMITS = {
    'Hospital Medicine': 5,
    'Internal Medicine Research': 5,
    'AI & Technology': 5,
    'Gaming': 3,
    'Politics & World': 5,
}


def collect_news(category, queries):
    candidates = []
    seen = set()
    for query in queries:
        url = (
            'https://news.google.com/rss/search?q='
            + quote(query + ' when:7d')
            + '&hl=en-US&gl=US&ceid=US:en'
        )
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            title = re.sub(r'<[^>]+>', '', entry.get('title', ''))
            link = entry.get('link', '')
            if not title or not link:
                continue
            key = title.lower().strip()
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                'title': title,
                'source': link,
                'published': entry.get('published', ''),
                'description': re.sub(r'<[^>]+>', ' ', entry.get('summary', ''))[:1000],
                'category': category,
                'kind': 'news',
            })
    return candidates


def make_pubmed_candidate(study):
    return {
        'title': study['title'],
        'source': study['source'],
        'published': 'Indexed in PubMed within the past 14 days; publication date not verified',
        'description': study['abstract'],
        'category': study['category'],
        'kind': 'pubmed',
        'journal': study.get('journal', ''),
        'pmid': study.get('pmid', ''),
        'doi': study.get('doi', ''),
    }


def summarize(article):
    if article['kind'] == 'pubmed':
        prompt = f'''Create a careful, accessible clinical research briefing using ONLY the PubMed record below.
Title: {article['title']}
Journal: {article.get('journal', '')}
PMID: {article.get('pmid', '')}
DOI: {article.get('doi', '')}
PubMed URL: {article['source']}
Abstract:\n{article['description']}

Return one valid JSON object with these exact keys:
"dek": one sentence summarizing the study
"summary": array of 2-3 short paragraphs covering design and population, reported results, and interpretation
"why": clinical relevance and how it might inform discussion, not a practice-changing directive
"evidence": design, sample size if reported, major limitations and uncertainty
"tag": short uppercase research topic label

Rules: Distinguish outcomes and conclusions from hypotheses. Include numerical effects only when stated in the abstract. Never invent patient counts, effect sizes, p-values, confidence intervals, trial registration, or publication dates. Explain whether findings are observational or randomized if specified. Do not claim to have read the full paper. If information is missing, say so. Do not issue individualized treatment advice.'''
    else:
        prompt = f'''Create a factual, accessible news briefing.
Headline: {article['title']}
Published: {article['published']}
Source link: {article['source']}
Feed description: {article['description']}
Category: {article['category']}

Return one valid JSON object with these exact keys:
"dek": one-sentence description
"summary": array of 2-3 short paragraphs
"why": why this matters
"evidence": evidence quality and limitations
"tag": short uppercase topic label

Rules: Use simple, clear English. Never invent statistics, findings, or quotations. Do not claim to have read the full article. Distinguish reported claims from verified evidence. State when details cannot be verified. For politics, use neutral, balanced language. Avoid unsupported clinical recommendations.'''

    response = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1500,
        system='You are a careful medical research and news briefing editor. Return only valid JSON.',
        messages=[{'role': 'user', 'content': prompt}],
    )
    raw = ''.join(block.text for block in response.content if getattr(block, 'type', '') == 'text').strip()
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1]
        raw = raw.rsplit('```', 1)[0].strip()
    return json.loads(raw)


def publish_candidate(candidate, count):
    brief = summarize(candidate)
    paragraphs = brief.get('summary', [])
    if not isinstance(paragraphs, list) or not paragraphs:
        raise ValueError('Missing summary paragraphs')
    paragraphs = [p.strip() for p in paragraphs if isinstance(p, str) and p.strip()]
    if not paragraphs:
        raise ValueError('Empty summary paragraphs')
    article_id = hashlib.sha256(candidate['source'].encode()).hexdigest()[:16]
    is_pubmed = candidate['kind'] == 'pubmed'
    return {
        'id': article_id,
        'category': candidate['category'],
        'tag': brief.get('tag', 'RESEARCH' if is_pubmed else 'NEWS'),
        'readTime': 3,
        'title': candidate['title'],
        'dek': brief.get('dek', ''),
        'summary': paragraphs,
        'why': brief.get('why', ''),
        'evidence': brief.get('evidence', ''),
        'source': candidate['source'],
        'date': 'Recently indexed in PubMed' if is_pubmed else candidate['published'][:25],
        'featured': count == 0,
        **({'journal': candidate['journal'], 'pmid': candidate['pmid'], 'doi': candidate['doi']} if is_pubmed else {}),
    }


def main():
    articles = []
    used_titles = set()
    grouped = {category: [] for category in LIMITS}
    for study in collect_pubmed_research():
        if study['category'] in grouped:
            grouped[study['category']].append(make_pubmed_candidate(study))
    for category, queries in SOURCES.items():
        grouped[category] = collect_news(category, queries)

    for category, candidates in grouped.items():
        count = 0
        for candidate in candidates:
            if count >= LIMITS[category]:
                break
            title_key = candidate['title'].lower().strip()
            if title_key in used_titles:
                continue
            try:
                articles.append(publish_candidate(candidate, count))
                used_titles.add(title_key)
                count += 1
            except Exception as error:
                print(f'Skipping {category} article: {str(error)[:200]}')
        print(f'{category}: {count} articles')

    if not articles:
        raise RuntimeError('No articles generated. Existing edition preserved.')
    # Keep previous medical articles if PubMed is temporarily unavailable.
    missing_medical = [c for c in ('Hospital Medicine', 'Internal Medicine Research') if not any(a['category'] == c for a in articles)]
    if missing_medical and os.path.exists(OUTPUT):
        try:
            with open(OUTPUT, encoding='utf-8') as file:
                previous = json.load(file)
            for old in previous.get('articles', []):
                if old.get('category') in missing_medical and old.get('id') not in {a['id'] for a in articles}:
                    articles.append(old)
            print('Retained prior articles for:', ', '.join(missing_medical))
        except (OSError, ValueError, TypeError) as error:
            print('Unable to retain previous medical articles:', error)

    data = {
        'edition': 'Weekly Intelligence Brief',
        'updated': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'articles': articles,
    }
    with open(OUTPUT, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    print(f'Published {len(articles)} articles')


if __name__ == '__main__':
    main()
