# IR1835 InfluxDB Bridge — Project Guide

## What This Does

Subscribes to sensor readings published by `modbus_mqtt_gateway` on HiveMQ Cloud
and forwards each reading to InfluxDB Cloud using the line protocol HTTP API.
Displayed live on a Grafana Cloud dashboard.

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

All three IOx apps run self-contained on the IR1835 — no external computer needed during demo.

---

## Project Files

| File | Purpose |
|------|---------|
| `app.py` | Bridge — subscribes to HiveMQ, writes to InfluxDB via stdlib urllib |
| `config.py` | All credentials (HiveMQ + InfluxDB) |
| `config.example.py` | Template with placeholders — safe to commit |
| `requirements.txt` | Only `paho-mqtt==1.6.1` — no influxdb-client needed |
| `Dockerfile` | ARM64 container image, identical structure to gateway |
| `package.yaml` | IOx manifest — no `devices` section |
| `grafana-dashboard.json` | Import this into Grafana Cloud to get the dashboard |

---

## Key Settings (config.py)

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

## Router Configuration

The bridge needs its own IP on VirtualPortGroup0 — different from the gateway's `.2`:

```
app-hosting appid influx_bridge
 app-vnic gateway0 virtualportgroup 0 guest-interface 0
  guest-ipaddress 192.168.16.3 netmask 255.255.255.0
 app-default-gateway 192.168.16.1 guest-interface 0
 name-server0 8.8.8.8
```

> **Note:** `modbus_mqtt_gateway` uses `192.168.16.2`. Both share VirtualPortGroup0.

---

## Build and Deploy

### 1. Build Docker image (dev machine)

```bash
cd "c:/jgouy/projects/platforms/IR MODBUS/ir1835-influx-bridge"
docker buildx build --platform linux/arm64 -t influx_bridge --load .
docker save influx_bridge -o influx_bridge.tar
```

### 2. Start file server (dev machine)

```powershell
# Check if already running:
docker ps --filter name=iox-serve

# Start if not running (single line — PowerShell does not support backslash continuation):
docker run -d --rm -p 8080:80 -v "c:/jgouy/projects/platforms/IR MODBUS/ir1835-influx-bridge:/usr/share/nginx/html:ro" --name iox-serve nginx:alpine
```

### 3. Install on router (SSH into router)

```
copy http://192.168.68.58:8080/influx_bridge.tar flash:/influx_bridge.tar
app-hosting install appid influx_bridge package flash:/influx_bridge.tar
```

### 4. Activate and start

> **No ioxclient needed** — unlike `modbus_mqtt_gateway`, this app has no serial device
> binding so the standard router CLI works fine.

```
app-hosting activate appid influx_bridge
app-hosting start appid influx_bridge
```

### 5. Verify both apps are running

```
show app-hosting list
```

Expected output:
```
App id                                   State
---------------------------------------------------------
influx_bridge                            RUNNING
modbus_mqtt_gateway                      RUNNING
```

---

## Verify It's Working

### Check bridge logs (dev machine)

```bash
ioxclient app logs tail influx_bridge
```

Select log file `1`, show last `20` lines. Healthy output:

```
[INFO] === IR1835 InfluxDB Bridge Starting ===
[INFO] MQTT connected to ...hivemq.cloud:8883
[INFO] Subscribed to sensor/+/sensorData
[INFO] InfluxDB write OK → 33.1°C  41.4%RH
[INFO] InfluxDB write OK → 33.0°C  41.5%RH
```

A new line appears every 60 seconds (matching the gateway publish interval).

### Test InfluxDB connectivity from dev machine (PowerShell)

```powershell
python -c "
import urllib.request, ssl, urllib.parse
url = 'https://us-east-1-1.aws.cloud2.influxdata.com/api/v2/write?' + urllib.parse.urlencode({'org':'Cisco_IIoT_Brazil_Edge_Projects','bucket':'sensor_data','precision':'s'})
req = urllib.request.Request(url, data=b'test_ping x=1', method='POST', headers={'Authorization':'Token LiVKmmKVRKBIWrXEBy8K7jMvThBJa83qUmc9RNp6ffw9ne5WYAwmvsQPclYwBwqi6-SrWcandkBB9xmq3ah1aw==','Content-Type':'text/plain'})
try:
    urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=10)
    print('SUCCESS')
except Exception as e:
    print(f'FAILED: {e}')
"
```

---

## Grafana Dashboard — Import

1. Go to `https://ciscoiiotjgouy.grafana.net`
2. **Dashboards → New → Import → Upload dashboard JSON file**
3. Select `grafana-dashboard.json`
4. Select the InfluxDB datasource when prompted
5. Click **Import**

### Datasource configuration (if reconfiguring)

| Field | Value |
|-------|-------|
| Type | InfluxDB |
| Query Language | **Flux** (not InfluxQL) |
| URL | `https://us-east-1-1.aws.cloud2.influxdata.com` |
| Organization | `Cisco_IIoT_Brazil_Edge_Projects` |
| Token | *(see config.py)* |
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
- Confirm guest IP `192.168.16.3` is configured

### Bridge logs show "InfluxDB HTTP error 401"
- Token has expired or was regenerated — update `INFLUX_TOKEN` in `config.py`, rebuild and redeploy

### Bridge logs show "InfluxDB HTTP error 404"
- Bucket `sensor_data` was deleted — recreate it in InfluxDB Cloud: **Add Data → Buckets → Create Bucket**

### No data in Grafana but bridge logs show writes OK
- Check Grafana datasource: query language must be set to **Flux**, not InfluxQL
- Verify the bucket name matches exactly: `sensor_data` (lowercase)

### ioxclient "access token expired"
- Normal — ioxclient auto-renews and retries. The command succeeds on the retry.

---

## Design Notes

**No `influxdb-client` library** — InfluxDB writes use Python's stdlib `urllib` with
the line protocol HTTP API. This keeps `requirements.txt` identical to the gateway
(`paho-mqtt==1.6.1` only), produces a smaller Docker image, and eliminates a large
dependency chain.

**MQTT wildcard topic** `sensor/+/sensorData` — the gateway generates a dynamic topic
based on its eth0 MAC address hash. The wildcard catches it regardless of the device ID,
and would support multiple gateways simultaneously without any config change.

**Unique MQTT client ID** `influx-bridge-iox` — HiveMQ rejects two clients with the same
ID, so this must differ from the gateway's `ir1835-{hash}`.

**Standard activation** — unlike `modbus_mqtt_gateway` which requires `ioxclient app activate
--payload activate_payload.json`, this app has no serial device binding and can be activated
with the normal `app-hosting activate` router CLI command.
