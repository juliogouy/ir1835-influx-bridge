import os

# ── HiveMQ Cloud MQTT (subscribe) ────────────────────────────────────────────
# Copy this file to config.py and replace the placeholders with your credentials.
# Credentials are read from environment variables injected via activate_payload.json
# (startup.env block). Fallback values are used when running outside IOx (e.g. testing).
# Copy this file to config.py and set your fallback values, or leave placeholders.
MQTT_BROKER    = os.getenv("MQTT_BROKER",    "YOUR_HIVEMQ_CLUSTER_URL.s2.eu.hivemq.cloud")
MQTT_PORT      = int(os.getenv("MQTT_PORT",  "8883"))
MQTT_USER      = os.getenv("MQTT_USER",      "YOUR_HIVEMQ_USERNAME")
MQTT_PASS      = os.getenv("MQTT_PASS",      "YOUR_HIVEMQ_PASSWORD")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "influx-bridge-iox")
# Wildcard '+' matches any gateway device-ID segment, e.g. sensor/a1b2c3d4/sensorData
MQTT_TOPIC     = os.getenv("MQTT_TOPIC",     "sensor/+/sensorData")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))

# ── InfluxDB Cloud ────────────────────────────────────────────────────────────
# Create a free account at cloud2.influxdata.com, then fill in the four values below.
# Generate an API token with write access to INFLUX_BUCKET.
INFLUX_URL    = os.getenv("INFLUX_URL",    "https://YOUR_REGION.aws.cloud2.influxdata.com")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN",  "YOUR_INFLUXDB_API_TOKEN")
INFLUX_ORG    = os.getenv("INFLUX_ORG",    "YOUR_ORG_NAME")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "sensor_data")
