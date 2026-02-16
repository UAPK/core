#!/bin/bash
set -e

cd /home/dsanker/uapk-gateway/backend

# Activate virtual environment
source ../venv/bin/activate

# Start the service with production config
# The app will read .env.production automatically through python-dotenv
ENV_FILE=../.env.production uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
