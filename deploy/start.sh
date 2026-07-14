#!/usr/bin/env bash
# Launch both processes for the single Cloud Run container: the copilot API (internal)
# and the Streamlit cockpit (public, on $PORT). If either dies, take the container down
# so Cloud Run restarts it.
set -euo pipefail

PORT="${PORT:-8080}"

# Copilot API — internal only; the Streamlit chat tab reaches it via COPILOT_API_URL.
/opt/venv-copilot/bin/uvicorn copilot.api:app --host 127.0.0.1 --port 8000 &
COPILOT_PID=$!

# If the copilot exits, don't leave a half-dead container serving a broken chat tab.
trap 'kill "$COPILOT_PID" 2>/dev/null || true' EXIT

# Streamlit in the foreground — this is the process Cloud Run health-checks on $PORT.
exec /opt/venv-app/bin/streamlit run app/main.py \
    --server.port "$PORT" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
