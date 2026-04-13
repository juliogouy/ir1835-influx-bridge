# IR1835 InfluxDB Bridge — Project Guide

## What This Does

Subscribes to sensor readings published by `modbus_mqtt_gateway` on HiveMQ Cloud
and forwards each reading to InfluxDB Cloud using the line protocol HTTP API.
Data is displayed live on a Grafana Cloud dashboard.

Runs as a Docker container (IOx application) on the same Cisco IR1835 router,
alongside the `modbus_mqtt_gateway` app. No serial device required — purely network.

---

## Full Pipeline

```
XY-MD02 sensor
    │ Modbus RTU / RS485
    ▼
[modbus_mqtt_gateway]  ──MQTT TLS──►  HiveMQ Cloud
                                            │ MQTT subscribe (sensor/+/sensorData)
                                            ▼
                                     [influx_bridge]  ──HTTPS line protocol──►  InfluxDB Cloud
                                                                                      │ Flux queries
                                                                                      ▼
                                                                               Grafana Cloud
                                                                      ciscoiiotjgouy.grafana.net
```

Both IOx apps run self-contained on the IR1835 — no external computer needed once deployed.

---

## Project Files

| File | Purpose |
|------|---------|
| `app.py` | Bridge — subscribes to HiveMQ, writes to InfluxDB via stdlib urllib |
| `config.py` | Runtime settings with real credentials — **not committed to git** |
| `config.example.py` | Template with placeholders — safe to commit, shows all settings |
| `Dockerfile` | ARM64 container image, identical structure to gateway |
| `package.yaml` | IOx manifest — `type: docker`, no `devices` section |
| `activate_payload.json` | IOx activation parameters — network, env vars |
| `requirements.txt` | Only `paho-mqtt==1.6.1` — no influxdb-client needed |
| `grafana-dashboard.json` | Import this into Grafana Cloud to get the dashboard |
| `dist/` | Build artifacts — `influx_bridge.tar` (Docker image, ~45MB) |

---

## Credentials and Environment Variables

Credentials are injected at activation time via `activate_payload.json` — the Docker
image itself contains no secrets and never needs to be rebuilt to change credentials.

### Where credentials live

`activate_payload.json` → `startup.env` block:

```json
"startup": {
  "runtime_options": "--rm",
  "env": {
    "MQTT_BROKER":   "your-cluster.s2.eu.hivemq.cloud",
    "MQTT_PORT":     "8883",
    "MQTT_USER":     "your-username",
    "MQTT_PASS":     "your-password",
    "INFLUX_URL":    "https://your-region.aws.cloud2.influxdata.com",
    "INFLUX_TOKEN":  "your-influxdb-api-token",
    "INFLUX_ORG":    "your-org-name",
    "INFLUX_BUCKET": "sensor_data"
  }
}
```

### How to change credentials (no rebuild needed)

Edit `activate_payload.json`, then stop → deactivate → re-activate → start:

```powershell
cd "C:\jgouy\projects\platforms\IR MODBUS\ir1835-influx-bridge"
ioxclient app stop influx_bridge
ioxclient app deactivate influx_bridge
ioxclient app activate --payload activate_payload.json influx_bridge
ioxclient app start influx_bridge
```

### How config.py reads credentials

`config.py` uses `os.getenv()` with fallback defaults:
```python
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "fallback-value")
```
The env vars from `activate_payload.json` take priority at runtime.
The fallback values in `config.py` are used only outside IOx (e.g. local testing).

---

## Key Settings

### HiveMQ (subscribe)

| Setting | Value |
|---------|-------|
| MQTT_BROKER | `0df3a975794543979e2143bd62e01178.s2.eu.hivemq.cloud` |
| MQTT_PORT | `8883` (TLS) |
| MQTT_USER | `JGouy001` |
| MQTT_CLIENT_ID | `influx-bridge-iox` |
| MQTT_TOPIC | `sensor/+/sensorData` (wildcard — matches any gateway device ID) |

### InfluxDB Cloud

| Setting | Value |
|---------|-------|
| INFLUX_URL | `https://us-east-1-1.aws.cloud2.influxdata.com` |
| INFLUX_ORG | `Cisco_IIoT_Brazil_Edge_Projects` |
| INFLUX_BUCKET | `sensor_data` |
| Measurement | `sensor_reading` |
| Fields | `temperature_c` (°C), `humidity_rh` (%RH) |
| Tags | `sensor`, `gateway` |

### Grafana Cloud

| Setting | Value |
|---------|-------|
| Stack URL | `ciscoiiotjgouy.grafana.net` |
| Dashboard title | Electrical Panel & Control Board Monitoring — Critical Infrastructure |
| Dashboard UID | `ir1835-elec-panel` |
| Datasource | InfluxDB — query language: **Flux** |

---

## Network (Router Configuration)

The bridge needs its own IP on VirtualPortGroup0 — different from the gateway's `.2`:

```
app-hosting appid influx_bridge
 app-vnic gateway0 virtualportgroup 0 guest-interface 0
  guest-ipaddress 192.168.16.3 netmask 255.255.255.0
 app-default-gateway 192.168.16.1 guest-interface 0
 name-server0 8.8.8.8
```

> **Note:** `modbus_mqtt_gateway` uses `192.168.16.2`. Both share VirtualPortGroup0 (`192.168.16.1`).

---

## Build and Deploy

### 1. Build Docker image (dev machine — PowerShell)

```powershell
cd "C:\jgouy\projects\platforms\IR MODBUS\ir1835-influx-bridge"
docker buildx build --platform linux/arm64 -t influx_bridge --load .
docker save influx_bridge -o dist\influx_bridge.tar
```

Only needed when `app.py`, `config.py`, `Dockerfile`, or `requirements.txt` change.

### 2. Start file server (dev machine — PowerShell)

Serves the entire `IR MODBUS` parent folder so both apps share one server:

```powershell
docker rm -f iox-serve
docker run -d --rm -p 8080:80 `
  -v "C:/jgouy/projects/platforms/IR MODBUS:/usr/share/nginx/html:ro" `
  --name iox-serve nginx:alpine
```

Check it's running: `docker ps --filter name=iox-serve`

### 3. Remove old app from router (SSH into router)

```
app-hosting stop appid influx_bridge
app-hosting deactivate appid influx_bridge
app-hosting uninstall appid influx_bridge
```

### 4. Transfer and install

```
copy http://192.168.68.54:8080/ir1835-influx-bridge/dist/influx_bridge.tar flash:/influx_bridge.tar
app-hosting install appid influx_bridge package flash:/influx_bridge.tar
```

Wait for: `app-hosting: influx_bridge installed successfully. Current state is DEPLOYED`

### 5. Activate (dev machine — use ioxclient with payload)

```powershell
cd "C:\jgouy\projects\platforms\IR MODBUS\ir1835-influx-bridge"
ioxclient app activate --payload activate_payload.json influx_bridge
```

> **Note:** Even though this app has no serial device, using `ioxclient app activate --payload`
> ensures `startup.env` credentials are injected correctly. The router CLI
> `app-hosting activate` does not process the env vars.

### 6. Start

```powershell
ioxclient app start influx_bridge
```

### 7. Verify both apps are running (router CLI)

```
show app-hosting list
```

Expected:
```
App id                                   State
---------------------------------------------------------
influx_bridge                            RUNNING
modbus_mqtt_gateway                      RUNNING
```

---

## Verify It's Working

### Get log filename (dev machine)

```powershell
ioxclient app logs info influx_bridge
```

### Tail logs

```powershell
ioxclient app logs tail influx_bridge <filename-from-above> 50
```

Healthy output:
```
[INFO] === IR1835 InfluxDB Bridge Starting ===
[INFO] MQTT broker  : ...hivemq.cloud:8883
[INFO] InfluxDB URL : https://us-east-1-1.aws.cloud2.influxdata.com
[INFO] MQTT connected to ...hivemq.cloud:8883
[INFO] Subscribed to sensor/+/sensorData
[INFO] InfluxDB write OK → 31.9°C  41.0%RH
[INFO] InfluxDB write OK → 31.9°C  40.8%RH
```

A new `InfluxDB write OK` line appears every 60 seconds.

---

## Grafana Dashboard — Import

1. Go to `https://ciscoiiotjgouy.grafana.net`
2. **Dashboards → New → Import → Upload dashboard JSON file**
3. Select `grafana-dashboard.json`
4. Select the InfluxDB datasource when prompted
5. Click **Import**

### Datasource configuration

| Field | Value |
|-------|-------|
| Type | InfluxDB |
| Query Language | **Flux** (not InfluxQL) |
| URL | `https://us-east-1-1.aws.cloud2.influxdata.com` |
| Organization | `Cisco_IIoT_Brazil_Edge_Projects` |
| Token | *(see activate_payload.json)* |
| Default Bucket | `sensor_data` |

### Share dashboard publicly (for demo)

1. Open the dashboard
2. Click the **Share** icon (top toolbar)
3. Select **Public dashboard** tab
4. Toggle **Enable public access** → On
5. Copy and share the URL — no login required

---

## Troubleshooting

### Bridge logs show "MQTT connect failed"
- Verify internet connectivity from router: `ping 8.8.8.8`
- Check VirtualPortGroup0 is up: `show interfaces VirtualPortGroup0`
- Confirm guest IP `192.168.16.3` is configured in router

### Bridge logs show "InfluxDB HTTP error 401"
- Token has expired or was regenerated
- Update `INFLUX_TOKEN` in `activate_payload.json` startup.env
- Stop → deactivate → re-activate → start (no rebuild needed)

### Bridge logs show "InfluxDB HTTP error 404"
- Bucket `sensor_data` was deleted — recreate it in InfluxDB Cloud:
  **Load Data → Buckets → Create Bucket**

### No data in Grafana but bridge logs show writes OK
- Check datasource: query language must be **Flux**, not InfluxQL
- Verify bucket name matches exactly: `sensor_data` (case-sensitive)

### Env vars not applied (app still using old credentials)
- Must use `ioxclient app activate --payload activate_payload.json influx_bridge`
- The router CLI `app-hosting activate` does not inject startup.env variables

### ioxclient "access token expired"
- Normal — ioxclient auto-renews and retries. The command succeeds on the retry.

---

## Design Notes

**No `influxdb-client` library** — writes use Python's stdlib `urllib` with the
InfluxDB line protocol HTTP API. Keeps `requirements.txt` minimal (`paho-mqtt` only),
produces a smaller Docker image, and eliminates a large dependency chain.

**MQTT wildcard topic** `sensor/+/sensorData` — the gateway generates a dynamic topic
based on its eth0 MAC address hash. The wildcard catches it regardless of device ID,
and supports multiple gateways simultaneously without config changes.

**Unique MQTT client ID** `influx-bridge-iox` — HiveMQ rejects two clients with the
same ID, so this must differ from the gateway's `ir1835-{hash}`.

---

## Git Repository

- **Remote:** https://github.com/juliogouy/ir1835-influx-bridge
- **Main branch:** `master` — stable, deployed version
- **`config.py` is excluded from git** (contains real credentials)
- **`dist/*.tar` is excluded from git** (large binary build artifacts)

To merge a tested feature branch:
```powershell
git checkout master
git merge feature/env-vars
git push
```
