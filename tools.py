from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def web_search_direct(query: str, max_results: int = 3) -> list:
    """Search the web for recent and reliable information on a topic. Returns a list of dictionaries with url, title, and content."""
    try:
        results = tavily.search(query=query, max_results=max_results)
        return results.get("results", [])
    except Exception as e:
        print(f"Tavily search failed: {e}")
        return []

def scrape_url_direct(url: str) -> str:
    """Scrape and return clean text content from a given URL for deeper reading."""
    try:
        resp = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        return soup.get_text(separator=" ", strip=True)[:3000]

    except Exception as e:
        return f"Could not scrape URL {url}: {str(e)}"

def concurrent_scrape(urls: list) -> str:
    """Scrapes multiple URLs concurrently and returns combined text."""
    combined_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(scrape_url_direct, url): url for url in urls[:3]}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                combined_results.append(f"--- CONTENT FROM {url} ---\n{data}\n")
            except Exception as exc:
                combined_results.append(f"--- FAILED TO SCRAPE {url} ---\n{exc}\n")
                
    return "\n".join(combined_results)

if __name__ == "__main__":
    results = web_search_direct("Artificial intelligence")
    print(results)
    urls = [r["url"] for r in results]
    scraped = concurrent_scrape(urls)
    print(scraped)
