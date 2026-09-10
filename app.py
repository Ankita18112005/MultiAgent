"""
Flask web server for MultiAgent Research Pipeline.
Wraps the existing pipeline components with SSE streaming for real-time UI updates.
Does NOT modify any core logic — uses the same agents and chains from agents.py.
"""

from flask import Flask, render_template, request, Response, jsonify
import json
import sys
import os

# Load .env BEFORE importing agents (which creates the LLM at import time)
from dotenv import load_dotenv
load_dotenv(override=True)

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import build_search_agent, build_reader_agent, writer_chain, critic_chain

app = Flask(__name__)


@app.route("/")
def index():
    """Serve the main UI."""
    return render_template("index.html")


@app.route("/api/research", methods=["POST"])
def research():
    """
    Run the full 4-step research pipeline with Server-Sent Events.
    Mirrors the exact logic of pipeline.py's run_research_pipeline()
    but streams each step's progress to the browser in real time.
    """
    data = request.get_json()
    topic = data.get("topic", "").strip()

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    def generate():
        state = {}

        try:
            # ── Step 1: Search Agent ──────────────────────────────
            yield _sse({"type": "step_start", "step": 1, "name": "Search Agent is finding sources…"})

            search_agent = build_search_agent()
            search_result = search_agent.invoke({
                "messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]
            })
            state["search_results"] = search_result["messages"][-1].content

            yield _sse({"type": "step_complete", "step": 1, "content": state["search_results"]})

            # ── Step 2: Reader Agent ──────────────────────────────
            yield _sse({"type": "step_start", "step": 2, "name": "Reader Agent is scraping top resources…"})

            reader_agent = build_reader_agent()
            reader_result = reader_agent.invoke({
                "messages": [("user",
                    f"Based on the following search results about '{topic}', "
                    f"pick the most relevant URL and scrape it for deeper content.\n\n"
                    f"Search Results:\n{state['search_results'][:800]}"
                )]
            })
            state["scraped_content"] = reader_result["messages"][-1].content

            yield _sse({"type": "step_complete", "step": 2, "content": state["scraped_content"]})

            # ── Step 3: Writer Chain ──────────────────────────────
            yield _sse({"type": "step_start", "step": 3, "name": "Writer is drafting the report…"})

            research_combined = (
                f"SEARCH RESULTS :\n {state['search_results']} \n\n"
                f"DETAILED SCRAPED CONTENT :\n {state['scraped_content']}"
            )
            state["report"] = writer_chain.invoke({
                "topic": topic,
                "research": research_combined
            })

            yield _sse({"type": "step_complete", "step": 3, "content": state["report"]})

            # ── Step 4: Critic Chain ──────────────────────────────
            yield _sse({"type": "step_start", "step": 4, "name": "Critic is reviewing the report…"})

            state["feedback"] = critic_chain.invoke({
                "report": state["report"]
            })

            yield _sse({"type": "step_complete", "step": 4, "content": state["feedback"]})

            # ── Done ──────────────────────────────────────────────
            yield _sse({"type": "complete", "state": state})

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                yield _sse({
                    "type": "error",
                    "message": "⚠️ API quota exhausted. Please wait for the quota to reset or upgrade your plan."
                })
            else:
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
    return jsonify({"status": "ok"})


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


if __name__ == "__main__":
    print("\n>> MultiAgent Research Pipeline UI")
    print("   Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000, threaded=True)
