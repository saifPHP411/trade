FROM python:3.12-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY alpaca.py scan.py signals.py rules.md stocks.txt ./
CMD ["python", "-u", "scan.py", "--live", "--today", "--rule", "breakout", "--feed", "sip"]

COPY dashboard.py ./
COPY dashboard_ui ./dashboard_ui
