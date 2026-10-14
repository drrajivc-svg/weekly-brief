
import os
import json
import re
import hashlib
from datetime import datetime, timezone
from urllib.parse import quote
import feedparser
from anthropic import Anthropic

OUTPUT = "articles.json"
API_KEY = os.environ.get("ANTHROPIC_API_KEY")

if not API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY is not configured")

client = Anthropic(api_key=API_KEY)

SOURCES = {
    "Hospital Medicine": [
        "hospital medicine sepsis heart failure inpatient",
        "hospitalist clinical guidelines pneumonia AKI"
    ],
    "Internal Medicine Research": [
        "site:nejm.org internal medicine clinical trial",
        "site:jamanetwork.com randomized clinical trial",
        "site:nature.com/articles medicine cardiology"
    ],
    "AI & Technology": [
        "artificial intelligence OpenAI Anthropic Google",
        "robotics technology breakthroughs"
    ],
    "Gaming": [
        "gaming industry game development",
        "Unreal Engine Godot AI gaming"
    ],
    "Politics & World": [
        "US politics public policy",
        "world politics international affairs"
    ]
}

LIMITS = {
    "Hospital Medicine": 5,
    "Internal Medicine Research": 5,
    "AI & Technology": 5,
    "Gaming": 3,
    "Politics & World": 5
}

def collect_news(category, queries):
    candidates = []
    seen = set()

    for query in queries:
        url = (
            "https://news.google.com/rss/search?q="
            + quote(query + " when:7d")
            + "&hl=en-US&gl=US&ceid=US:en"
        )
        feed = feedparser.parse(url)

        for entry in feed.entries[:15]:
            title = re.sub(r"<[^>]+>", "", entry.title)
            link = entry.get("link", "")

            if not title or not link:
                continue

            key = title.lower().strip()

            if key in seen:
                continue

            seen.add(key)

            candidates.append({
                "title": title,
                "source": link,
                "published": entry.get("published", ""),
                "description": re.sub(
                    r"<[^>]+>", " ",
                    entry.get("summary", "")
                )[:1000],
                "category": category
            })

    return candidates


def summarize(article):
    prompt = f"""
Create a factual, accessible news briefing.

Headline: {article['title']}
Published: {article['published']}
Source link: {article['source']}
Feed description: {article['description']}
Category: {article['category']}

Return a JSON object containing:
dek: one-sentence description
summary: array of 2-3 short paragraphs
why: why this matters
evidence: evidence quality and limitations
tag: short uppercase topic label

Rules:
- Use simple, clear English.
- Never invent statistics, findings, or quotations.
- Do not claim to have read the full article.
- Distinguish reported claims from verified evidence.
- For medical studies, explain study design and
  results only when provided in the source material.
- State when details cannot be verified.
- For politics, use neutral, balanced language.
- Avoid unsupported clinical recommendations.
"""

   
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        temperature=0.2,
        system=(
            "You are a careful medical research and "
            "news briefing editor. Return only valid JSON."
        ),
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0].strip()

    return json.loads(raw)



def main():
    articles = []
    used_titles = set()

    for category, queries in SOURCES.items():
        candidates = collect_news(category, queries)
        count = 0

        for candidate in candidates:
            if count >= LIMITS[category]:
                break

            title_key = candidate["title"].lower()

            if title_key in used_titles:
                continue

            try:
                brief = summarize(candidate)

                paragraphs = brief.get("summary", [])
                if not isinstance(paragraphs, list) or not paragraphs:
                    continue

                article_id = hashlib.sha256(
                    candidate["source"].encode()
                ).hexdigest()[:16]

                articles.append({
                    "id": article_id,
                    "category": category,
                    "tag": brief.get("tag", "NEWS"),
                    "readTime": 3,
                    "title": candidate["title"],
                    "dek": brief.get("dek", ""),
                    "summary": paragraphs,
                    "why": brief.get("why", ""),
                    "evidence": brief.get(
                        "evidence", "Based on news feed metadata."
                    ),
                    "source": candidate["source"],
                    "date": candidate["published"][:25],
                    "featured": count == 0
                })

                used_titles.add(title_key)
                count += 1

            except Exception as error:
                print("Skipping article:", str(error)[:200])

    if not articles:
        raise RuntimeError(
            "No articles generated. Existing edition preserved."
        )

    data = {
        "edition": "Weekly Intelligence Brief",
        "updated": datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d"),
        "articles": articles
    }

    with open(OUTPUT, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    print(f"Published {len(articles)} articles")


if __name__ == "__main__":
    main()
