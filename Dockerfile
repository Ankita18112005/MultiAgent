FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose port
EXPOSE 5000

# Run with gthread worker class to handle concurrent SSE connections
CMD ["sh", "-c", "gunicorn --workers=2 --threads=4 --worker-class=gthread --timeout=120 --bind=0.0.0.0:${PORT:-5000} app:app"]
