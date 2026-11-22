# Spaza Sales Analyser API
# Build:  docker build -t spaza-api .
# Run:    docker run -p 8000:8000 spaza-api
# Then open http://localhost:8000 (chatbot) or http://localhost:8000/docs (API docs).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

# Install dependencies first, so Docker can reuse this layer when only the code changes.
COPY requirements.txt requirements-ai.txt ./
RUN pip install -r requirements.txt -r requirements-ai.txt

COPY spaza_analyser/ spaza_analyser/
COPY sql/ sql/
COPY data/sales_2025.csv data/sales_2025.csv

# Don't run as root inside the container.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

CMD ["uvicorn", "spaza_analyser.api:app", "--host", "0.0.0.0", "--port", "8000"]
