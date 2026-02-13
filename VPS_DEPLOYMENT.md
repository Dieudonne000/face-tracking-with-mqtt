# VPS Deployment — Dashboard + Broker + WebSocket Relay

This guide walks you through hosting the **MQTT broker**, **WebSocket relay**, and **dashboard** on a VPS so that:

- Your **PC (Vision)** and **ESP8266** connect to the broker on the VPS.
- The **dashboard** is available at a public URL (e.g. `http://YOUR_VPS_IP` or `http://your-domain.com`).
- The dashboard connects to the relay on the same VPS via WebSocket.

---

## What runs where

| Component        | Where it runs | Port  |
|-----------------|---------------|-------|
| MQTT broker     | VPS           | 1883  |
| WebSocket relay | VPS           | 9002  |
| Dashboard (HTTP)| VPS           | 80 or 8080 |
| PC Vision       | Your laptop   | — (connects to VPS:1883) |
| ESP8266         | Your desk     | — (connects to VPS:1883) |

---

## 1. Prerequisites

- **VPS** with a public IP (Linux: Ubuntu 22.04 / Debian 12 or similar).
- **SSH** access to the VPS.
- Your **TEAM_ID** (e.g. `dragonfly`, `team01`) — use the same everywhere.

---

## 2. On the VPS — Initial setup

SSH into your VPS:

```bash
ssh your_user@YOUR_VPS_IP
```

Optional: update system and set a hostname:

```bash
sudo apt update && sudo apt upgrade -y
```

---

## 3. Install and run Mosquitto (MQTT broker)

```bash
sudo apt install -y mosquitto mosquitto-clients
```

Create a config so the broker listens on all interfaces (so your PC and ESP can connect):

```bash
sudo bash -c 'cat > /etc/mosquitto/conf.d/listen.conf << EOF
listener 1883 0.0.0.0
allow_anonymous true
EOF'
```

Restart and enable Mosquitto:

```bash
sudo systemctl restart mosquitto
sudo systemctl enable mosquitto
```

Check that it’s listening:

```bash
ss -tlnp | grep 1883
```

You should see `0.0.0.0:1883`.

---

## 4. Deploy project files on the VPS

You only need the **backend** and **dashboard** on the VPS (no full repo with models/camera).

**Option A — Copy only what’s needed (recommended)**

On your **local machine** (PowerShell or Git Bash):

```powershell
# From your project folder
scp -r backend dashboard your_user@YOUR_VPS_IP:~/
```

So on the VPS you have:

- `~/backend/`  (ws_relay.py, requirements.txt)
- `~/dashboard/` (index.html, etc.)

**Option B — Clone the whole repo on the VPS**

```bash
git clone https://github.com/YOUR_USER/face-with-mqtt.git
cd face-with-mqtt
```

Then use `backend/` and `dashboard/` from there.

---

## 5. Set TEAM_ID on the VPS

Edit the relay config so it uses your team ID:

```bash
nano ~/backend/ws_relay.py
```

Set (near the top):

```python
TEAM_ID = "dragonfly"   # change to your team id, e.g. team01, y3_grp2
```

`MQTT_BROKER` can stay `"127.0.0.1"` because Mosquitto runs on the same VPS.

Save and exit.

---

## 6. Run the WebSocket relay on the VPS

Install Python 3 and pip if needed, then create a venv and install deps:

```bash
cd ~
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

Run the relay (leave this terminal open or use a process manager):

```bash
python backend/ws_relay.py
```

You should see something like:

- `[MQTT] Connected and subscribed to: vision/dragonfly/movement`
- `[WS]   Listening on ws://0.0.0.0:9002`

To run it in the background and survive logout, use **systemd** (see section 9) or **screen**/ **tmux**:

```bash
screen -S relay
source ~/venv/bin/activate
python ~/backend/ws_relay.py
# Detach: Ctrl+A then D
```

---

## 7. Serve the dashboard on the VPS

The dashboard is static (HTML/JS/CSS). When opened in the browser from the VPS URL, it will use `location.hostname:9002` as the WebSocket URL, so it will connect to your relay on the same host.

**Option A — Python HTTP server (quick test)**

```bash
cd ~
source venv/bin/activate
python -m http.server 8080 --directory dashboard
```

Dashboard URL: `http://YOUR_VPS_IP:8080`

To run in background with screen:

```bash
screen -S dashboard
source ~/venv/bin/activate
python -m http.server 8080 --directory ~/dashboard
# Ctrl+A, D to detach
```

**Option B — Nginx (production, port 80)**

Install nginx:

```bash
sudo apt install -y nginx
```

Create a site config:

```bash
sudo nano /etc/nginx/sites-available/face-dashboard
```

Paste (replace `YOUR_VPS_IP` or use `_` for default server):

```nginx
server {
    listen 80;
    server_name YOUR_VPS_IP;
    root /home/YOUR_USER/dashboard;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/face-dashboard /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Dashboard URL: `http://YOUR_VPS_IP` (port 80).

---

## 8. Open firewall ports on the VPS

Allow MQTT, WebSocket, and HTTP so your PC, ESP, and browser can reach the VPS:

```bash
sudo ufw allow 1883/tcp   # MQTT
sudo ufw allow 9002/tcp  # WebSocket relay
sudo ufw allow 80/tcp    # HTTP (dashboard, if using nginx)
# or for Python server:
sudo ufw allow 8080/tcp
sudo ufw enable
sudo ufw status
```

---

## 9. (Optional) Run relay as a systemd service

So the relay starts on boot and restarts on failure:

```bash
sudo nano /etc/systemd/system/face-ws-relay.service
```

Paste (replace `YOUR_USER` and path if different):

```ini
[Unit]
Description=Face MQTT-WebSocket Relay
After=network.target mosquitto.service

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER
Environment="PATH=/home/YOUR_USER/venv/bin"
ExecStart=/home/YOUR_USER/venv/bin/python /home/YOUR_USER/backend/ws_relay.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable face-ws-relay
sudo systemctl start face-ws-relay
sudo systemctl status face-ws-relay
```

---

## 10. Configure your PC and ESP to use the VPS

**On your PC (in the project):**

Edit `pc_vision/config.py`:

```python
MQTT_BROKER_IP = "YOUR_VPS_IP"   # e.g. "157.173.101.159"
TEAM_ID = "dragonfly"            # same as on VPS
```

**On the ESP8266:**

Edit `esp8266/config.py` (before uploading):

```python
MQTT_BROKER = "YOUR_VPS_IP"
TEAM_ID    = "dragonfly"
```

---

## 11. Submission URL

The **live dashboard URL** to submit is:

- If using **Python server**: `http://YOUR_VPS_IP:8080`
- If using **Nginx**: `http://YOUR_VPS_IP` or `http://your-domain.com` if you pointed a domain to the VPS.

Anyone opening that URL will see the dashboard; it will connect to the WebSocket on the same host (port 9002).

---

## 12. Quick checklist

| Step | Done |
|------|------|
| Mosquitto installed, listening on 0.0.0.0:1883 | ☐ |
| backend/ and dashboard/ on VPS | ☐ |
| TEAM_ID set in backend/ws_relay.py | ☐ |
| Relay running (python backend/ws_relay.py or systemd) | ☐ |
| Dashboard served (http.server or nginx) | ☐ |
| Firewall: 1883, 9002, 80 or 8080 open | ☐ |
| pc_vision/config.py: MQTT_BROKER_IP = VPS IP | ☐ |
| esp8266/config.py: MQTT_BROKER = VPS IP | ☐ |

---

## Troubleshooting

| Problem | Check |
|--------|--------|
| Dashboard shows "Connecting…" forever | Relay running? Port 9002 open? Same TEAM_ID in relay and vision? |
| PC Vision can’t connect to MQTT | VPS firewall allows 1883? MQTT_BROKER_IP correct? Mosquitto running? |
| ESP can’t connect | WiFi OK? MQTT_BROKER = VPS IP? Port 1883 open on VPS? |
| "Connection refused" on 9002 | Run `python backend/ws_relay.py` and leave it running; check ufw. |

For full architecture and run order, see [RUN_AND_TEST.md](RUN_AND_TEST.md) and [GUIDE.md](GUIDE.md).
