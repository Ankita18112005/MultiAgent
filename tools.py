"""
Optimized search and web scraping tools for MultiAgent Research Pipeline.
Features:
- Reused requests.Session with connection pooling and custom User-Agent
- URL filtering to skip video links (YouTube), PDFs, and social media redirects
- Lazy Tavily client initialization with graceful API key validation
- Concurrently scrapes up to 3 articles with timeout safety
"""

import os
import re
import concurrent.futures
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

# Reused session with connection pooling for fast scraping
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
})

# Extensions and domains to skip during scraping
_SKIPPED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".mp4", ".mp3", ".avi", ".mov", ".zip", ".tar", ".gz"
}
_SKIPPED_DOMAINS = {
    "youtube.com", "youtu.be", "twitter.com", "x.com",
    "instagram.com", "facebook.com", "tiktok.com"
}


def _get_tavily_client() -> TavilyClient:
    """Lazily initialize Tavily client with API key validation."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY is not set. Please add your Tavily API key to .env "
            "or set the environment variable. Get a free key at https://tavily.com"
        )
    return TavilyClient(api_key=api_key)


def is_scrapable_url(url: str) -> bool:
    """Filter out video sites, binary files, and social media redirects."""
    if not url or not url.startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if any(d in domain for d in _SKIPPED_DOMAINS):
            return False
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in _SKIPPED_EXTENSIONS):
            return False
        return True
    except Exception:
        return False


def web_search_direct(query: str, max_results: int = 3) -> list:
    """
    Search the web using Tavily API.
    Returns list of dicts with 'url', 'title', and 'content'.
    """
    client = _get_tavily_client()
    try:
        results = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic"
        )
        return results.get("results", [])
    except Exception as e:
        print(f"[tools.py] Tavily search error: {e}")
        raise


def scrape_url_direct(url: str, timeout: int = 8) -> str:
    """
    Scrape and return clean, readable text content from a given URL.
    Removes boilerplate, navbars, scripts, and footers.
    """
    if not is_scrapable_url(url):
        return f"Skipped scraping {url} (unsupported format or domain)."

    try:
        resp = _SESSION.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()

        # Verify content is HTML
        content_type = resp.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            return f"Skipped {url}: Content-Type is {content_type}."

        soup = BeautifulSoup(resp.text, "html.parser")

        # Decompose non-content tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]):
            tag.decompose()

        # Prioritize main article or body
        main_content = soup.find("article") or soup.find("main") or soup.body
        if not main_content:
            return f"No readable content found in {url}."

        text = main_content.get_text(separator=" ", strip=True)
        # Collapse repeated whitespace
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned[:3000]

    except requests.exceptions.Timeout:
        return f"Timeout ({timeout}s) while attempting to scrape {url}."
    except Exception as e:
        return f"Could not scrape {url}: {str(e)}"


def concurrent_scrape(urls: list, max_workers: int = 3) -> str:
    """
    Concurrently scrape valid URLs and return combined structured text.
    """
    valid_urls = [u for u in urls if is_scrapable_url(u)][:max_workers]
    if not valid_urls:
        return "No valid scrapeable URLs found in search results."

    combined_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(scrape_url_direct, u): u for u in valid_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                combined_results.append(f"--- SOURCE: {url} ---\n{data}\n")
            except Exception as exc:
                combined_results.append(f"--- FAILED TO SCRAPE: {url} ---\n{exc}\n")

    return "\n".join(combined_results)


if __name__ == "__main__":
    test_q = "Artificial Intelligence breakthroughs 2026"
    print(f"Testing search for: {test_q}")
    res = web_search_direct(test_q, max_results=2)
    print(f"Got {len(res)} results.")
    urls = [r["url"] for r in res]
    print(f"Scraping URLs: {urls}")
    scraped = concurrent_scrape(urls)
    print(f"Scraped length: {len(scraped)} characters.")
