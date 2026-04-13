"""
============================================================
IOx Application: HiveMQ MQTT → InfluxDB Cloud Bridge
============================================================
Subscribes to sensor readings published by the modbus_mqtt_gateway
on HiveMQ Cloud, and writes each reading to InfluxDB Cloud using
the line protocol HTTP API (stdlib urllib — no extra dependencies).

Runs as a Docker container (IOx application) on the Cisco IR1835,
alongside the modbus_mqtt_gateway app.

No serial device binding required — purely network.
============================================================
"""

import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

import paho.mqtt.client as mqtt

import config

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── InfluxDB write URL (built once at startup) ────────────────────────────────
_INFLUX_WRITE_URL = (
    config.INFLUX_URL.rstrip("/") + "/api/v2/write?"
    + urllib.parse.urlencode({
        "org":       config.INFLUX_ORG,
        "bucket":    config.INFLUX_BUCKET,
        "precision": "s",
    })
)


# ── InfluxDB writer ───────────────────────────────────────────────────────────

def _escape_tag(value: str) -> str:
    """Escape spaces and commas in InfluxDB line protocol tag values."""
    return value.replace(",", "\\,").replace(" ", "\\ ").replace("=", "\\=")


def influx_write(temperature_c: float, humidity_rh: float, sensor: str, gateway: str):
    """Write one data point to InfluxDB using the line protocol REST API."""
    line = (
        f"sensor_reading,"
        f"sensor={_escape_tag(sensor)},"
        f"gateway={_escape_tag(gateway)} "
        f"temperature_c={temperature_c},"
        f"humidity_rh={humidity_rh}"
    )
    req = urllib.request.Request(
        _INFLUX_WRITE_URL,
        data=line.encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Token {config.INFLUX_TOKEN}",
            "Content-Type":  "text/plain; charset=utf-8",
        },
    )
    ctx = ssl.create_default_context()   # verifies cert using system CA bundle
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            if resp.status == 204:
                log.info(f"InfluxDB write OK → {temperature_c}°C  {humidity_rh}%RH")
            else:
                log.warning(f"InfluxDB unexpected status {resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        log.error(f"InfluxDB HTTP error {e.code}: {body}")
    except Exception as e:
        log.error(f"InfluxDB write error: {e}")


# ── MQTT callbacks ────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info(f"MQTT connected to {config.MQTT_BROKER}:{config.MQTT_PORT}")
        client.subscribe(config.MQTT_TOPIC, qos=1)
        log.info(f"Subscribed to {config.MQTT_TOPIC}")
    else:
        log.error(f"MQTT connect failed rc={rc}")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        log.warning(f"MQTT unexpected disconnect rc={rc} — paho will reconnect")


def on_message(client, userdata, msg):
    log.debug(f"Received on {msg.topic}: {msg.payload}")
    try:
        data = json.loads(msg.payload)
        temperature_c = float(data["temperature_c"])
        humidity_rh   = float(data["humidity_rh"])
        sensor        = str(data.get("sensor",  "XY-MD02"))
        gateway       = str(data.get("gateway", "cisco-ir1835"))
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        log.error(f"Bad payload: {e}  raw={msg.payload}")
        return

    influx_write(temperature_c, humidity_rh, sensor, gateway)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=== IR1835 InfluxDB Bridge Starting ===")
    log.info(f"MQTT broker  : {config.MQTT_BROKER}:{config.MQTT_PORT}")
    log.info(f"MQTT topic   : {config.MQTT_TOPIC}")
    log.info(f"InfluxDB URL : {config.INFLUX_URL}")
    log.info(f"Org / Bucket : {config.INFLUX_ORG} / {config.INFLUX_BUCKET}")

    client = mqtt.Client(client_id=config.MQTT_CLIENT_ID)
    client.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
    client.tls_set()
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message
    client.reconnect_delay_set(min_delay=5, max_delay=60)

    while True:
        try:
            client.connect(config.MQTT_BROKER, config.MQTT_PORT,
                           keepalive=config.MQTT_KEEPALIVE)
            client.loop_forever()   # blocks; paho handles reconnects internally
        except Exception as e:
            log.error(f"Connection error: {e} — retrying in 15s")
            time.sleep(15)


if __name__ == "__main__":
    main()
