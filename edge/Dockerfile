# Edge gateway: one container per property (ADR-0004). Talks only outward to the control plane.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY edge_gateway ./edge_gateway
RUN useradd --create-home app && mkdir -p /data && chown app /data
USER app
VOLUME ["/data"]
CMD ["python", "-m", "edge_gateway"]
