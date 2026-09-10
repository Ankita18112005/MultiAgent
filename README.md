# 🤖 MultiAgent Research Pipeline

An autonomous, multi-agent AI research platform that searches the web, reads and parses multiple top sources concurrently, synthesizes comprehensive research reports, and rigorously critiques them with actionable evaluation scores in real-time.

Built with **LangChain**, **Google Gemini AI**, **Tavily Search**, and **Flask** with **Server-Sent Events (SSE)** streaming.

![Architecture](https://img.shields.io/badge/Architecture-Multi--Agent%20Pipeline-blueviolet)
![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ⚡ Key Features

- **4-Stage Multi-Agent Architecture**:
  1. **Search Agent**: Queries Tavily API for fresh, verified internet sources.
  2. **Reader Agent**: Concurrently scrapes up to 3 article URLs with connection pooling and junk filtering.
  3. **Writer Agent**: Synthesizes a structured, publication-grade research report with citations.
  4. **Critic Agent**: Evaluates the report strictly on quality, completeness, and accuracy, returning a score out of 10 with constructive feedback.
- **Resilient Multi-Model Fallbacks**:
  Automatically cascades across Gemini models (`gemini-3.1-flash-lite`, `gemini-3.1-flash-lite-preview`, `gemini-3.5-flash-lite`, etc.) to prevent 429 quota exhaustion errors on free tiers.
- **Real-Time Streaming UI**:
  Features animated live status indicators, step-by-step progress cards, Markdown rendering, and elapsed timer.
- **Production-Ready**:
  Equipped with Gunicorn WSGI (`gthread` concurrent worker class), security headers, keep-alive heartbeats, and strict input validation.

---

## 🚀 Quick Start (Local)

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/YOUR_USERNAME/MultiAgent.git
cd MultiAgent

python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your free keys:
```env
GOOGLE_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
```

### 4. Run the Web Application
```bash
python app.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

---

## 🌐 100% Free Cloud Deployment

Deploy in 5 minutes with zero cost:

| Platform | Tier | Guide |
| :--- | :--- | :--- |
| **Render** | Free Web Service (512MB RAM, native Python, SSE supported) | [Render Deployment](DEPLOYMENT.md#option-1-deploy-to-render-recommended) |
| **Hugging Face Spaces** | Free Docker Container (16GB RAM, 2 vCPU, no cold timeouts) | [Hugging Face Deployment](DEPLOYMENT.md#option-2-deploy-to-hugging-face-spaces-100-free-16gb-ram) |

For full step-by-step instructions, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

---

## 📁 Repository Structure

```text
├── agents.py           # LLM chains (Writer & Critic) with multi-model fallback resilience
├── app.py              # Flask production server with SSE streaming & security headers
├── tools.py            # Tavily search & concurrent scraping with URL filtering
├── pipeline.py         # Standalone CLI pipeline runner
├── templates/
│   └── index.html      # Modern responsive dark-mode UI with Marked.js rendering
├── requirements.txt    # Lean production dependencies
├── Procfile            # Cloud WSGI runner (Gunicorn + gthread)
├── Dockerfile          # Container specification for HuggingFace / Docker clouds
├── .env.example        # Environment configuration template
├── DEPLOYMENT.md       # Comprehensive 100% free deployment guide
└── README.md           # Project documentation
```

---

## 📄 License
MIT License.
