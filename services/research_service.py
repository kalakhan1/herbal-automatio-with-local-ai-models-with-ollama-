"""Lightweight research: DuckDuckGo HTML + optional page fetch."""
import logging
import re
import time
from typing import List, Dict
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}

def search_web(query: str, limit: int = 5) -> List[Dict[str, str]]:
    """Search DuckDuckGo HTML (no API key). Returns list of {title, url, snippet}."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for a in soup.select(".result__a")[:limit]:
            title = a.get_text(strip=True)
            href = a.get("href", "")
            # Extract actual URL from DDG redirect
            if href.startswith("/l/?"):
                from urllib.parse import urlparse, parse_qs
                q = parse_qs(urlparse(href).query)
                href = q.get("uddg", [href])[0]
            results.append({"title": title, "url": href})
        # Snippets
        snippets = soup.select(".result__snippet")
        for i, snip in enumerate(snippets[:len(results)]):
            results[i]["snippet"] = snip.get_text(strip=True)
        return results
    except Exception as e:
        log.warning(f"Search failed for '{query}': {e}")
        return []

def fetch_page_text(url: str, max_chars: int = 4000) -> str:
    """Fetch and extract text from a URL."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        # Remove scripts, styles, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "noscript", "iframe", "form"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        return text[:max_chars]
    except Exception as e:
        log.warning(f"Fetch failed {url}: {e}")
        return ""

def research_product(name: str) -> Dict:
    """Research a product. Returns dict with sources and combined text."""
    query = f"{name} herbal uses benefits information"
    results = search_web(query, limit=4)
    sources = []
    combined = []
    for r in results:
        text = fetch_page_text(r["url"], max_chars=2500)
        if len(text) > 300:
            sources.append({"url": r["url"], "title": r.get("title", "")})
            combined.append(text[:1500])
        time.sleep(0.5)

    combined_text = "\n\n".join(combined)[:6000]
    return {
        "query": query,
        "sources": sources,
        "text": combined_text,
        "source_count": len(sources)
    }