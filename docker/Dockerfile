FROM python:3.12-slim

LABEL org.opencontainers.image.title="ns3-wifi-performance-analysis"
LABEL org.opencontainers.image.description="Reproducible UDP/TCP analysis pipeline for ns-3 Wi-Fi experiments"
LABEL org.opencontainers.image.authors="Leonel Olimpio Silima"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY docker/requirements-analysis.txt /tmp/requirements-analysis.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install -r /tmp/requirements-analysis.txt

COPY docker/entrypoint.sh /usr/local/bin/wn-entrypoint

RUN chmod 0755 /usr/local/bin/wn-entrypoint

ENTRYPOINT ["/usr/local/bin/wn-entrypoint"]

CMD ["final"]