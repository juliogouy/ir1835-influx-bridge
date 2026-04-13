# ============================================================
# Dockerfile - Cisco IOx Application
# HiveMQ MQTT → InfluxDB Cloud Bridge
# Target: Cisco IR1835 (ARM64 / aarch64 architecture)
# No serial device required — purely network.
# ============================================================

# The IR1835 runs on an ARM64 processor.
FROM arm64v8/python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && find / -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
    && pip uninstall -y pip setuptools wheel 2>/dev/null || true

COPY app.py config.py ./

CMD ["sh", "-c", "python3 -u /app/app.py 2>&1; echo '--- APP EXITED ---'; sleep 3600"]
