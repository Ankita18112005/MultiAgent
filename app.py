"""
Flask web server for MultiAgent Research Pipeline.
Wraps the existing pipeline components with SSE streaming for real-time UI updates.
Does NOT modify any core logic — uses the same agents and chains from agents.py.

FIX 1: Dynamically reloads .env + agents on every request (fresh API key).
FIX 2: Automatic retry with backoff for 429 rate-limit errors.
"""

from flask import Flask, render_template, request, Response, jsonify
import json
import sys
import os
import re
import time
import importlib
import traceback

from dotenv import load_dotenv

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tools
import agents

app = Flask(__name__)

# Retry config
MAX_RETRIES = 3


def _reload_agents():
    """
    Dynamically reload .env and the agents/tools modules so the latest API key
    from .env is always used.
    """
    load_dotenv(override=True)
    importlib.reload(tools)
    importlib.reload(agents)
    return agents


def _call_with_retry(fn, description="API call"):
    """
    Call fn() with automatic retry on 429/RESOURCE_EXHAUSTED errors.
    Extracts the retry delay from the error message when available.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            err = str(e)
            is_rate_limit = "429" in err or "RESOURCE_EXHAUSTED" in err
            is_daily_limit = "GenerateRequestsPerDay" in err or "free_tier_requests" in err
            
            if is_daily_limit:
                # Daily limit reached for this key/model, waiting seconds won't help
                raise RuntimeError(
                    "Gemini API daily free-tier limit reached (20 requests/day). "
                    "Please wait for quota reset or update GOOGLE_API_KEY in .env with a billing-enabled key."
                ) from e

            if is_rate_limit and attempt < MAX_RETRIES:
                # Extract retry delay from error message (e.g. "retry in 30.354s")
                delay_match = re.search(r'retry\s+in\s+([\d.]+)', err, re.IGNORECASE)
                wait = float(delay_match.group(1)) if delay_match else 15.0
                wait = min(wait + 2, 60)  # Add 2s buffer, cap at 1 min
                print(f"  [Retry {attempt}/{MAX_RETRIES}] {description} "
                      f"rate-limited, waiting {wait:.0f}s...")
                time.sleep(wait)
            else:
                raise


@app.route("/")
def index():
    """Serve the main UI."""
    return render_template("index.html")


@app.route("/api/research", methods=["POST"])
def research():
    """
    Run the full 4-step research pipeline with Server-Sent Events.
    Includes automatic retry for rate-limit errors and dynamic .env reload.
    """
    data = request.get_json()
    topic = data.get("topic", "").strip()

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    def generate():
        state = {}

        try:
            # ── Reload agents with fresh API key ──────────────
            agents = _reload_agents()

            # ── Step 1: Direct Web Search ──────────────────────────────
            yield _sse({"type": "step_start", "step": 1, "name": "Finding recent sources..."})

            raw_results = _call_with_retry(
                lambda: tools.web_search_direct(query=topic, max_results=3),
                description="Tavily Search API"
            )
            
            # Format results for the writer
            formatted_search = []
            urls_to_scrape = []
            for r in raw_results:
                formatted_search.append(f"Title: {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('content')[:300]}\n")
                if "url" in r:
                    urls_to_scrape.append(r["url"])
                    
            state["search_results"] = "\n---\n".join(formatted_search)

            yield _sse({"type": "step_complete", "step": 1, "content": state["search_results"]})

            # ── Step 2: Concurrent Scraping ──────────────────────────────
            yield _sse({"type": "step_start", "step": 2, "name": "Reading multiple top resources simultaneously..."})

            # Directly scrape up to 3 URLs concurrently (no LLM latency)
            state["scraped_content"] = tools.concurrent_scrape(urls_to_scrape)

            yield _sse({"type": "step_complete", "step": 2, "content": state["scraped_content"]})

            # ── Step 3: Writer Chain ──────────────────────────────
            yield _sse({"type": "step_start", "step": 3, "name": "Writer is drafting the report..."})

            research_combined = (
                f"SEARCH RESULTS :\n {state['search_results']} \n\n"
                f"DETAILED SCRAPED CONTENT :\n {state['scraped_content']}"
            )
            state["report"] = _call_with_retry(
                lambda: agents.writer_chain.invoke({
                    "topic": topic,
                    "research": research_combined
                }),
                description="Writer Chain"
            )

            yield _sse({"type": "step_complete", "step": 3, "content": state["report"]})

            # ── Step 4: Critic Chain ──────────────────────────────
            yield _sse({"type": "step_start", "step": 4, "name": "Critic is reviewing the report..."})

            state["feedback"] = _call_with_retry(
                lambda: agents.critic_chain.invoke({
                    "report": state["report"]
                }),
                description="Critic Chain"
            )

            yield _sse({"type": "step_complete", "step": 4, "content": state["feedback"]})

            # ── Done ──────────────────────────────────────────────
            yield _sse({"type": "complete", "state": state})

        except Exception as e:
            error_msg = str(e)
            traceback.print_exc()
            yield _sse({
                "type": "error",
                "message": f"An error occurred: {error_msg}"
            })

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@app.route("/api/health")
def health():
    """Health check with API key and model preview for debugging."""
    load_dotenv(override=True)
    key = os.getenv("GOOGLE_API_KEY", "NOT SET")
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "TOO SHORT"
    return jsonify({"status": "ok", "api_key_preview": masked, "model": model})


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


if __name__ == "__main__":
    print("\n>> MultiAgent Research Pipeline UI")
    print("   Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000, threaded=True, use_reloader=False)
