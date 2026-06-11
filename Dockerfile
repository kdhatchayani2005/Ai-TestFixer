FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Render sets $PORT; Streamlit must bind to 0.0.0.0 so Render's proxy can reach it
ENV PORT=8501

EXPOSE $PORT

# Use shell form so $PORT is expanded at runtime
CMD streamlit run dashboard/app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false \
    --server.headless=true
