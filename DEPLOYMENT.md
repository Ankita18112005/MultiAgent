# 🚀 100% Free Deployment Guide

This guide walks you through deploying the **MultiAgent Research Pipeline** completely free of charge using **Render** or **Hugging Face Spaces**.

---

## 📋 Prerequisites: Get Free API Keys

You need two free API keys (neither requires a credit card):

1. **Google Gemini API Key**:
   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
   - Click **Create API Key**.
   - Copy the key (starts with `AIza...`).

2. **Tavily Search API Key**:
   - Go to [Tavily AI](https://tavily.com).
   - Sign up for the free tier (1,000 free searches/month).
   - Copy your API key from the dashboard (starts with `tvly-...`).

---

## 🌟 Option 1: Deploy to Render (Recommended)

Render offers a generous **Free Web Service** tier that natively supports Python, Gunicorn, and Server-Sent Events (SSE) streaming.

### Step 1: Push Code to GitHub
If your project is not yet on GitHub:
```bash
git init
git add .
git commit -m "Ready for production"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/MultiAgent.git
git push -u origin main
```

### Step 2: Create Web Service on Render
1. Go to [Render.com](https://render.com) and sign in (or create a free account with GitHub).
2. Click **New +** in the top navigation bar and select **Web Service**.
3. Select **Build and deploy from a Git repository**, click **Next**, and choose your `MultiAgent` repository.

### Step 3: Configure the Web Service
Fill in the deployment settings:
- **Name**: `multiagent-research` (or any name you prefer)
- **Region**: Choose the closest region to you (e.g., *Oregon (US West)* or *Frankfurt (EU)*)
- **Branch**: `main`
- **Root Directory**: *(leave blank)*
- **Runtime**: `Python 3`
- **Build Command**:
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  gunicorn --workers=2 --threads=4 --worker-class=gthread --timeout=120 app:app
  ```
- **Instance Type**: Select **Free** (0.5 CPU, 512 MB RAM)

### Step 4: Add Environment Variables
Scroll down to the **Environment Variables** section and click **Add Environment Variable**:

| Key | Value | Description |
| :--- | :--- | :--- |
| `GOOGLE_API_KEY` | `AIza...` | Your Google Gemini API key |
| `TAVILY_API_KEY` | `tvly-...` | Your Tavily Search API key |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Active high-quota model (automatic fallbacks included) |
| `PYTHON_VERSION` | `3.12.0` | Python version for Render |

### Step 5: Deploy
Click **Deploy Web Service**.
- Render will install the dependencies, configure the gthread WSGI server, and launch the service.
- When the build finishes, your app will be live at:
  `https://multiagent-research.onrender.com`

> **Note on Render Free Tier**: Free web services automatically spin down after 15 minutes of inactivity. When a new request arrives, it takes ~30-50 seconds to wake up (cold start).

---

## 🤗 Option 2: Deploy to Hugging Face Spaces (100% Free, 16GB RAM)

Hugging Face Spaces provides **free 2-vCPU / 16GB RAM** Docker containers that stay online without cold-start timeouts.

### Step 1: Create a Space
1. Go to [Hugging Face](https://huggingface.co) and sign in.
2. Click on your profile icon in the top right and select **New Space**.
3. Fill in:
   - **Space name**: `multiagent-research`
   - **License**: `mit` or `apache-2.0`
   - **Select the Space SDK**: Choose **Docker** -> **Blank**.
   - **Space hardware**: `Free CPU (2 vCPU · 16 GB · Free)`
4. Click **Create Space**.

### Step 2: Add Secrets
1. Go to the Space's **Settings** tab.
2. Scroll to **Variables and secrets**.
3. Under **Secrets**, click **New secret** and add:
   - Name: `GOOGLE_API_KEY`, Value: *your Gemini API key*
   - Name: `TAVILY_API_KEY`, Value: *your Tavily API key*
4. Under **Variables**, add:
   - Name: `PORT`, Value: `7860` (Hugging Face standard port)

### Step 3: Push Your Repository
Clone your space or add it as a git remote:
```bash
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/multiagent-research
git push hf main --force
```
Hugging Face will automatically build the `Dockerfile` and run your app. Your public research tool is now live!

---

## 💻 Local Production Run

To run in production mode locally on your machine:

```bash
# Set environment variables
export FLASK_DEBUG=0
export PORT=5000

# Run with standard Python
python app.py
```

Or on Linux / macOS with Gunicorn:
```bash
gunicorn --workers=2 --threads=4 --worker-class=gthread --timeout=120 --bind=0.0.0.0:5000 app:app
```

---

## 🛠 Troubleshooting & Verification

1. **Verify Health Endpoint**:
   Visit `https://YOUR_DOMAIN/api/health` to confirm that keys are recognized and the server is healthy:
   ```json
   {
     "status": "ok",
     "ready": true,
     "active_model": "gemini-3.1-flash-lite",
     "environment": "production"
   }
   ```

2. **Rate Limits & Quota**:
   The application includes an **automatic multi-model fallback chain**:
   If your primary model exhausts its daily free limit, the system seamlessly redirects calls to fallback models (`gemini-3.1-flash-lite-preview`, `gemini-3.5-flash-lite`, etc.) without dropping the user's research session.
