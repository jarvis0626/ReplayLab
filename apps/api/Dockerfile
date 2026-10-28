FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data AI_PROVIDER=mock
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 replaylab \
    && useradd --uid 10001 --gid replaylab --create-home replaylab \
    && mkdir -p /data /app/apps/api \
    && chown -R replaylab:replaylab /data /app

WORKDIR /app/apps/api
COPY apps/api/requirements.lock ./requirements.lock
RUN python -m pip install --no-cache-dir -r requirements.lock
COPY --chown=replaylab:replaylab apps/api/ /app/apps/api/
COPY --chown=replaylab:replaylab demo/fixtures/evaluation.json /app/demo/fixtures/evaluation.json
COPY --chown=replaylab:replaylab demo/evaluation/digital/ /app/demo/evaluation/digital/

USER replaylab
EXPOSE 8010
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/api/health', timeout=3).read()" || exit 1
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", "--workers", "1"]
