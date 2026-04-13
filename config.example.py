# ── HiveMQ Cloud MQTT (subscribe) ────────────────────────────────────────────
# Copy this file to config.py and replace the placeholders with your credentials.
MQTT_BROKER    = "YOUR_HIVEMQ_CLUSTER_URL.s2.eu.hivemq.cloud"
MQTT_PORT      = 8883                        # TLS
MQTT_USER      = "YOUR_HIVEMQ_USERNAME"
MQTT_PASS      = "YOUR_HIVEMQ_PASSWORD"
MQTT_CLIENT_ID = "influx-bridge-iox"
# Wildcard '+' matches any gateway device-ID segment, e.g. sensor/a1b2c3d4/sensorData
MQTT_TOPIC     = "sensor/+/sensorData"
MQTT_KEEPALIVE = 60

# ── InfluxDB Cloud ────────────────────────────────────────────────────────────
# Create a free account at cloud2.influxdata.com, then fill in the four values below.
# Generate an API token with write access to INFLUX_BUCKET.
INFLUX_URL    = "https://YOUR_REGION.aws.cloud2.influxdata.com"  # e.g. us-east-1-1
INFLUX_TOKEN  = "YOUR_INFLUXDB_API_TOKEN"
INFLUX_ORG    = "YOUR_ORG_NAME"
INFLUX_BUCKET = "sensor_data"
