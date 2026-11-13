# Edge gateway: one container per property (ADR-0004). Talks only outward to the control plane.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY edge_gateway ./edge_gateway
# No VOLUME here: Railway refuses it. Attach a volume at /data in the service; it is mounted as
# root, so the process runs as root to write its buffer there (it has no open port).
RUN mkdir -p /data
CMD ["python", "-m", "edge_gateway"]
