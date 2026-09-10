"""
Production Flask Application for MultiAgent Research Pipeline.
Features:
- Real-time Server-Sent Events (SSE) streaming with keep-alive heartbeats
- Production WSGI compatibility (Gunicorn / Waitress / Render / HuggingFace)
- Configurable HOST, PORT, and DEBUG via environment variables
- Security headers on all responses
- Strict input validation and pre-flight API key checks
- Intelligent rate-limit recovery and resilient multi-model fallbacks
"""

import os
import sys
import json
import re
import time
import importlib
import traceback
from flask import Flask, render_template, request, Response, jsonify
from dotenv import load_dotenv

# Ensure project directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

import tools
import agents

app = Flask(__name__)

# Configuration
MAX_RETRIES = 3
DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true")
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")


def _get_active_agents():
    """
    In development mode, reload modules to pick up immediate .env changes.
    In production, use loaded modules for maximum throughput.
    """
    if DEBUG:
        load_dotenv(override=True)
        importlib.reload(tools)
        importlib.reload(agents)
    return agents


def _call_with_retry(fn, description="API call"):
    """
    Call fn() with automatic retry on 429 rate-limit errors.
    Immediately raises descriptive errors if daily free-tier limits are reached.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            err = str(e)
            is_rate_limit = "429" in err or "RESOURCE_EXHAUSTED" in err
            is_daily_limit = "GenerateRequestsPerDay" in err or "free_tier_requests" in err

            if is_daily_limit:
                raise RuntimeError(
                    "Gemini API daily free-tier limit reached (20 requests/day). "
                    "Please wait for daily quota reset or supply a billing-enabled GOOGLE_API_KEY in .env."
                ) from e

            if is_rate_limit and attempt < MAX_RETRIES:
                delay_match = re.search(r'retry\s+in\s+([\d.]+)', err, re.IGNORECASE)
                wait = float(delay_match.group(1)) if delay_match else 10.0
                wait = min(wait + 2, 45)
                print(f"[{description}] Rate-limited (attempt {attempt}/{MAX_RETRIES}). Backing off {wait:.1f}s...")
                time.sleep(wait)
            else:
                raise


def _sse(data: dict) -> str:
    """Format a dict as an SSE data frame."""
    return f"data: {json.dumps(data)}\n\n"


def _ping() -> str:
    """SSE keep-alive comment to prevent reverse-proxy timeouts."""
    return ": keep-alive\n\n"


@app.after_request
def add_security_headers(response):
    """Inject standard security headers."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


@app.route("/")
def index():
    """Serve the single-page research interface."""
    return render_template("index.html")


@app.route("/api/health")
def health():
    """Health check endpoint for cloud monitoring and container probes."""
    load_dotenv(override=True)
    google_key = os.getenv("GOOGLE_API_KEY", "")
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    def _mask(k):
        return k[:6] + "..." + k[-4:] if len(k) > 10 else ("Configured" if k else "Missing")

    is_ready = bool(google_key and tavily_key)
    return jsonify({
        "status": "ok",
        "ready": is_ready,
        "google_api_key": _mask(google_key),
        "tavily_api_key": _mask(tavily_key),
        "active_model": model,
        "environment": "development" if DEBUG else "production"
    })


@app.route("/api/research", methods=["POST"])
def research():
    """
    Execute the 4-step research pipeline with real-time SSE streaming.
    Step 1: Tavily Web Search
    Step 2: Concurrent Multi-Source Web Scraping
    Step 3: Writer Agent (Detailed Research Report)
    Step 4: Critic Agent (Structured Review & Scoring)
    """
    data = request.get_json(silent=True) or {}
    topic = str(data.get("topic", "")).strip()

    # Input validation
    if not topic:
        return jsonify({"error": "Topic is required"}), 400
    if len(topic) < 3:
        return jsonify({"error": "Topic must be at least 3 characters long"}), 400
    if len(topic) > 300:
        return jsonify({"error": "Topic exceeds maximum length of 300 characters"}), 400

    def generate():
        state = {}

        try:
            # ── Pre-flight API Key Validation ─────────────────────────────
            if not os.getenv("GOOGLE_API_KEY"):
                yield _sse({
                    "type": "error",
                    "message": "Missing GOOGLE_API_KEY. Please configure your Gemini API key."
                })
                return

            if not os.getenv("TAVILY_API_KEY"):
                yield _sse({
                    "type": "error",
                    "message": "Missing TAVILY_API_KEY. Please configure your Tavily API key at https://tavily.com."
                })
                return

            active_agents = _get_active_agents()

            # ── Step 1: Web Search ────────────────────────────────────────
            yield _sse({"type": "step_start", "step": 1, "name": "Finding recent reliable sources..."})
            yield _ping()

            raw_results = _call_with_retry(
                lambda: tools.web_search_direct(query=topic, max_results=3),
                description="Tavily Search API"
            )

            if not raw_results:
                yield _sse({
                    "type": "error",
                    "message": f"No search results found for topic: '{topic}'. Try a different search query."
                })
                return

            formatted_search = []
            urls_to_scrape = []
            for r in raw_results:
                title = r.get("title", "Untitled")
                url = r.get("url", "")
                snippet = (r.get("content") or "")[:300]
                formatted_search.append(f"Title: {title}\nURL: {url}\nSnippet: {snippet}\n")
                if url:
                    urls_to_scrape.append(url)

            state["search_results"] = "\n---\n".join(formatted_search)
            yield _sse({"type": "step_complete", "step": 1, "content": state["search_results"]})

            # ── Step 2: Concurrent Web Scraping ───────────────────────────
            yield _sse({"type": "step_start", "step": 2, "name": "Reading multiple top resources simultaneously..."})
            yield _ping()

            state["scraped_content"] = tools.concurrent_scrape(urls_to_scrape)
            yield _sse({"type": "step_complete", "step": 2, "content": state["scraped_content"]})

            # ── Step 3: Writer Chain ──────────────────────────────────────
            yield _sse({"type": "step_start", "step": 3, "name": "Writer is synthesizing report..."})
            yield _ping()

            research_combined = (
                f"SEARCH RESULTS:\n{state['search_results']}\n\n"
                f"DETAILED SCRAPED CONTENT:\n{state['scraped_content']}"
            )

            state["report"] = _call_with_retry(
                lambda: active_agents.writer_chain.invoke({
                    "topic": topic,
                    "research": research_combined
                }),
                description="Writer Agent"
            )
            yield _sse({"type": "step_complete", "step": 3, "content": state["report"]})

            # ── Step 4: Critic Chain ──────────────────────────────────────
            yield _sse({"type": "step_start", "step": 4, "name": "Critic is reviewing the report..."})
            yield _ping()

            state["feedback"] = _call_with_retry(
                lambda: active_agents.critic_chain.invoke({
                    "report": state["report"]
                }),
                description="Critic Agent"
            )
            yield _sse({"type": "step_complete", "step": 4, "content": state["feedback"]})

            # ── Pipeline Finished ─────────────────────────────────────────
            yield _sse({"type": "complete", "state": state})

        except Exception as e:
            traceback.print_exc()
            error_msg = str(e)
            # Remove any raw internal stack noise for clean user UI
            if "google.genai.errors.ClientError:" in error_msg:
                error_msg = error_msg.split("google.genai.errors.ClientError:")[-1].strip()
            yield _sse({
                "type": "error",
                "message": f"An error occurred: {error_msg}"
            })

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


if __name__ == "__main__":
    print(f"\n>> MultiAgent Research Pipeline UI running on http://{HOST}:{PORT}")
    print("   Press CTRL+C to stop\n")
    app.run(host=HOST, port=PORT, debug=DEBUG, threaded=True)
