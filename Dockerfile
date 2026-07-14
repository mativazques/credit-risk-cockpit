# Credit-Risk Cockpit — one Cloud Run image serving the Streamlit cockpit + the copilot.
#
# Streamlit pins protobuf<6 while the copilot's google-genai needs >=6, so they can't
# share a site-packages. We keep the blueprint's "one app on Cloud Run" by baking TWO
# isolated venvs into a single image and running both processes: uvicorn (copilot API) on
# an internal port, Streamlit on Cloud Run's $PORT, talking to it over localhost.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    COPILOT_API_URL=http://127.0.0.1:8000

WORKDIR /app

# Install deps first (own layer) so code changes don't reinstall the world.
COPY app/requirements.txt app/requirements.txt
COPY copilot/requirements.txt copilot/requirements.txt
RUN python -m venv /opt/venv-app \
    && /opt/venv-app/bin/pip install -r app/requirements.txt
RUN python -m venv /opt/venv-copilot \
    && /opt/venv-copilot/bin/pip install -r copilot/requirements.txt

COPY . .

# Cloud Run sends traffic to $PORT (defaults to 8080); Streamlit binds it, the copilot
# stays internal on 8000.
ENV PORT=8080
EXPOSE 8080

CMD ["./deploy/start.sh"]
