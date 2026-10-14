
import time
import requests
import xml.etree.ElementTree as ET

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

TOPICS = {
    "Hospital Medicine": (
        '(sepsis OR "heart failure" OR pneumonia OR '
        '"acute kidney injury" OR "hospital medicine") '
        'AND (randomized controlled trial[pt] OR '
        'systematic review[pt] OR practice guideline[pt])'
    ),
    "Internal Medicine Research": (
        '("internal medicine" OR cardiology OR diabetes '
        'OR hypertension OR anticoagulation) '
        'AND (randomized controlled trial[pt] OR '
        'meta-analysis[pt] OR systematic review[pt])'
    )
}


def text_of(element):
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def fetch_pubmed(category, query, limit=5):
    search = requests.get(
        BASE + "/esearch.fcgi",
        params={
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": limit * 3,
            "sort": "pub date",
            "datetype": "edat",
            "reldate": 14,
            "tool": "weekly_brief"
        },
        timeout=30
    )
    search.raise_for_status()

    ids = search.json()["esearchresult"]["idlist"]
    if not ids:
        return []

    time.sleep(0.4)

    response = requests.get(
        BASE + "/efetch.fcgi",
        params={
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
            "tool": "weekly_brief"
        },
        timeout=45
    )
    response.raise_for_status()

    root = ET.fromstring(response.content)
    results = []

    for record in root.findall(".//PubmedArticle"):
        citation = record.find("MedlineCitation")
        if citation is None:
            continue

        pmid = text_of(citation.find("PMID"))
        article = citation.find("Article")
        if article is None or not pmid:
            continue

        title = text_of(article.find("ArticleTitle"))
        journal = text_of(article.find("Journal/Title"))

        abstract_parts = []
        for part in article.findall(
            "Abstract/AbstractText"
        ):
            label = part.attrib.get("Label", "")
            content = text_of(part)
            if content:
                abstract_parts.append(
                    f"{label}: {content}"
                    if label else content
                )

        abstract = "\n".join(abstract_parts)

        if not title or not abstract:
            continue

        doi = ""
        for item in record.findall(
            ".//ArticleIdList/ArticleId"
        ):
            if item.attrib.get("IdType") == "doi":
                doi = text_of(item)
                break

        results.append({
            "id": "pubmed-" + pmid,
            "category": category,
            "title": title,
            "journal": journal,
            "pmid": pmid,
            "doi": doi,
            "abstract": abstract[:12000],
            "source": (
                "https://pubmed.ncbi.nlm.nih.gov/"
                + pmid + "/"
            )
        })

        if len(results) >= limit:
            break

    return results


def collect_pubmed_research():
    results = []

    for category, query in TOPICS.items():
        try:
            results.extend(
                fetch_pubmed(category, query)
            )
        except Exception as error:
            print(
                f"PubMed error for {category}: {error}"
            )

    return results


if __name__ == "__main__":
    studies = collect_pubmed_research()

    for study in studies:
        print(
            study["category"],
            study["title"],
            study["source"]
        )

    print(f"Collected {len(studies)} studies")
