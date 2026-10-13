# The Weekly Brief — Version 1

A responsive, static, GitHub Pages-compatible intelligence dashboard. **All included stories are illustrative educational content, not current news.**

## Run locally

Python 3: `python -m http.server 8000` from this directory, then open http://localhost:8000 . Do not double-click `index.html` because browser restrictions can prevent loading the JSON file.

## Deploy to GitHub Pages

1. Create a GitHub repository and upload the contents of this folder (not the parent folder).
2. In Settings → Pages, choose **Deploy from a branch**, select `main` and `/ (root)`.
3. Open the Pages URL GitHub displays. No API keys are required for the demo.

## What's implemented

- Responsive desktop/mobile layout
- Five topic areas plus all stories and saved stories
- Keyword search, sorting and bookmarks saved in the browser
- Reader modal with plain-English explanations and evidence notes
- Article content loaded from `articles.json`
- Clearly labeled demonstration content

## Architecture for live weekly editions

```
Trusted RSS / PubMed / publisher APIs
                 |
        Scheduled GitHub Action
                 |
    Python ingestion + deduplication
                 |
     LLM summarization (server-side)
                 |
   Fact/source validation and review
                 |
       articles.json (published)
                 |
        Static GitHub Pages UI
```

The `articles.json` file is the contract between the ingestion pipeline and the website. Each article has `id`, `category`, `tag`, `readTime`, `title`, `dek`, `summary` (paragraph array), `why`, `evidence`, `source`, `date`, and optional `featured`.

### Next step (not implemented yet)

Create a scheduled GitHub Actions workflow with a server-side script to retrieve sources and generate summaries. Keep API credentials in GitHub Actions secrets, **never in browser JavaScript or public JSON**. Cite original articles, distinguish peer-reviewed research from preprints, verify dates, preserve trial results and limitations, and never fabricate links. Add human review for medical claims before publication. Do not represent an AI-generated summary as clinical guidance.

## Content editing

To add articles manually, edit `articles.json`, retain valid JSON, use unique IDs, and provide real source URLs for actual news. Bookmark IDs remain stable between editions.
