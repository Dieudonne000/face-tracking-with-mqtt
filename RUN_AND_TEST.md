# Run and Test — Assignment Compliance

*Distributed Vision-Control System (Face-Locked Servo).* This document summarizes **what is ready**, **how to run** each component, and **how to test** according to the assignment rules.

---

## 1. What’s ready (vs assignment)

| Requirement | Status | Where |
|-------------|--------|--------|
| **PC Vision** — camera, face detect/track, publish movement via MQTT only | ✅ | `pc_vision/` (main, movement_detector, mqtt_publisher, config) |
| **Movement states** — MOVE_LEFT, MOVE_RIGHT, CENTERED, NO_FACE | ✅ | `pc_vision/movement_detector.py` |
| **MQTT payload** — `{ "status", "confidence", "timestamp" }` | ✅ | `pc_vision/mqtt_publisher.py`, `movement_detector.py` |
| **Topic isolation** — `vision/<team_id>/movement` (no generic/wildcard) | ✅ | `pc_vision/config.py`, `backend/ws_relay.py`, `esp8266/config.py` (TEAM_ID = `dragonfly`) |
| **PC must NOT** use WebSocket/HTTP/direct ESP | ✅ | PC uses MQTT only |
| **ESP8266** — subscribe MQTT, drive servo; no HTTP/WebSocket | ✅ | `esp8266/main.py`, `config.py` |
| **Backend** — MQTT subscriber + WebSocket server (port 9002), relay only | ✅ | `backend/ws_relay.py` |
| **Dashboard** — WebSocket only, real-time (no MQTT, no polling) | ✅ | `dashboard/index.html` |
| **Dashboard shows** — last movement status, tracking state, timestamp | ✅ | Movement, Confidence, Last update, Event log |
| **Phase 1** — Open-loop (camera fixed; servo moves with face) | ✅ | As implemented |
| **Optional heartbeat** topic `vision/<team_id>/heartbeat` | ✅ | Topic defined in `pc_vision/config.py` (use if you add heartbeat) |

**Summary:** The codebase matches the assignment architecture. You need to: set up broker, set TEAM_ID everywhere, enroll a face, and (for ESP) WiFi + upload + wiring.

---

## 2. What you must do (your part)

- **Choose a unique `TEAM_ID`** (e.g. `team01`, `y3_grp2`) and set it in:
  - `pc_vision/config.py` → `TEAM_ID`
  - `backend/ws_relay.py` → `TEAM_ID`
  - `esp8266/config.py` → `TEAM_ID`
- **MQTT broker:** Run Mosquitto (e.g. on VPS or local) on port **1883**, listener on `0.0.0.0` if ESP is on another machine.
- **Backend (VPS):** On the machine that runs the broker, install deps and run the relay:
  - `pip install -r backend/requirements.txt`
  - `python backend/ws_relay.py`
- **PC Vision:** Install project deps, download ArcFace model, enroll at least one face (see GUIDE.md Part 1–3). Set `MQTT_BROKER_IP` in `pc_vision/config.py` to the broker IP (VPS or 127.0.0.1).
- **ESP8266:** Flash MicroPython, set WiFi and `MQTT_BROKER` in `esp8266/config.py`, install `umqtt.simple` on device, upload `config.py`, `boot.py`, `main.py`, wire servo to GPIO (see GUIDE.md Part 7).
- **Dashboard URL for submission:** Host `dashboard/` (e.g. static on VPS or any host). If the dashboard is served from the same host as the relay, it will connect to `ws://<host>:9002` automatically; otherwise set the WebSocket URL in `dashboard/index.html` (`WS_URL`).

---

## 3. How to run (order)

**Local (everything on one PC except ESP):**

1. **Broker (local)**  
   Start Mosquitto on 1883 (e.g. `mosquitto -v` or install and start as service).

2. **Backend relay**  
   From repo root:
   ```bash
   pip install -r backend/requirements.txt
   python backend/ws_relay.py
   ```
   Leave running. You should see: `Listening on ws://0.0.0.0:9002`.

3. **Dashboard**  
   Open `dashboard/index.html` in a browser (file or via a static server). It should show “Connected” and connect to `ws://127.0.0.1:9002` when opened as file.

4. **PC Vision**  
   In another terminal, from repo root:
   ```bash
   python -m pc_vision.main
   ```
   Select an enrolled face when prompted. Camera window opens; movement is published to MQTT and relayed to the dashboard.

5. **ESP8266**  
   Power the board (or reset). Ensure `MQTT_BROKER` in `esp8266/config.py` is your PC’s LAN IP so it reaches the same broker. The ESP subscribes and drives the servo.

**VPS (broker + relay on VPS):**

- On VPS: install Mosquitto (port 1883), then run `python backend/ws_relay.py` (after `pip install -r backend/requirements.txt`).
- On PC: set `pc_vision/config.py` → `MQTT_BROKER_IP` = VPS IP; run `python -m pc_vision.main`.
- ESP: set `esp8266/config.py` → `MQTT_BROKER` = VPS IP.
- Host `dashboard/` on the VPS (or same host as relay) and use that URL for submission; dashboard will use `ws://<that-host>:9002`.

---

## 4. How to test (assignment-style)

### 4.1 MQTT only (no vision, no ESP)

- **Subscribe** (replace `dragonfly` with your `TEAM_ID` if different):
  ```bash
  mosquitto_sub -h 127.0.0.1 -t "vision/dragonfly/movement" -v
  ```
- **Publish** (other terminal):
  ```bash
  mosquitto_pub -h 127.0.0.1 -t "vision/dragonfly/movement" -m '{"status":"MOVE_LEFT","confidence":0.87,"timestamp":1730000000}'
  ```
- Subscriber should print the message. Use broker host/IP instead of `127.0.0.1` if testing from another machine.

### 4.2 WebSocket relay (MQTT → dashboard)

1. Start broker and then `python backend/ws_relay.py`.
2. Open `dashboard/index.html`.
3. In another terminal: `mosquitto_pub -h 127.0.0.1 -t "vision/dragonfly/movement" -m '{"status":"CENTERED","confidence":0.9,"timestamp":1730000000}'`
4. Dashboard should update immediately (Movement, Confidence, Last update, log). No polling.

### 4.3 Full stack (vision → MQTT → relay → dashboard + ESP)

1. Broker + relay running; dashboard open; ESP powered and connected to same broker.
2. Run `python -m pc_vision.main`, select enrolled face.
3. Move face left/right/center; leave frame (NO_FACE). Check:
   - Dashboard updates in real time (status, confidence, timestamp).
   - ESP servo moves left/right/center and holds on NO_FACE.
   - No wildcard topics; only `vision/<your_team_id>/movement` is used.

### 4.4 Topic isolation (shared broker)

- Use a unique `TEAM_ID` in all three configs.
- Do **not** subscribe to `vision/#` or `#`.
- Do **not** use topics like `vision/movement`, `movement`, or `servo`.

---

## 5. Quick reference — MQTT topics

| Topic | Publisher | Subscribers | Payload |
|-------|-----------|-------------|---------|
| `vision/<team_id>/movement` | PC Vision | Backend relay, ESP8266 | `{"status":"MOVE_LEFT\|MOVE_RIGHT\|CENTERED\|NO_FACE","confidence":0.87,"timestamp":1730000000}` |
| `vision/<team_id>/heartbeat` | Optional (any node) | Optional | `{"node":"pc","status":"ONLINE","timestamp":1730000000}` |

---

## 6. Golden rule

**Vision computes. Devices speak MQTT. Browsers speak WebSocket. The backend relays in real time.**

All run and test steps above respect this. For full environment setup (venv, ArcFace model, enrollment, Mosquitto, ESP flashing), see **GUIDE.md**.
