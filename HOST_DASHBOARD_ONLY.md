# Host Only the Dashboard on a VPS

Serve just the `dashboard/` folder (e.g. `index.html`) on your VPS so the dashboard is available at a URL.

---

## 1. Upload the dashboard to the VPS

From your **PC** (PowerShell, in the project folder):

```powershell
scp -r dashboard your_user@YOUR_VPS_IP:~/
```

Example: `scp -r dashboard ubuntu@157.173.101.159:~/`

This creates `~/dashboard/` on the VPS with `index.html` inside.

---

## 2. Serve it on the VPS

**Option A — Python (quick)**

SSH into the VPS, then:

```bash
cd ~
python3 -m http.server 8080 --directory dashboard
```

- Dashboard URL: **http://YOUR_VPS_IP:8080**
- To run in background:  
  `nohup python3 -m http.server 8080 --directory ~/dashboard &`  
  Or use `screen`/`tmux` so it keeps running after you disconnect.

**Option B — Nginx (port 80, recommended for “production”)**

```bash
sudo apt update
sudo apt install -y nginx
```

Create a config (replace `YOUR_USER` with your VPS username):

```bash
sudo nano /etc/nginx/sites-available/dashboard
```

Paste (adjust path if your user is different):

```nginx
server {
    listen 80 default_server;
    root /home/YOUR_USER/dashboard;
    index index.html;
    server_name _;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Enable and reload:

```bash
sudo ln -sf /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

- Dashboard URL: **http://YOUR_VPS_IP** (port 80)

---

## 3. Open the firewall (if needed)

```bash
# For Python server on 8080:
sudo ufw allow 8080/tcp

# For Nginx on 80:
sudo ufw allow 80/tcp

sudo ufw enable
sudo ufw status
```

---

## 4. Important: WebSocket relay

The dashboard **connects to the WebSocket relay** to show live data. In `index.html` it uses:

- **Same host as the page:** `ws://<current host>:9002`

So:

- If you **only** host the dashboard on the VPS and do **not** run the relay on the VPS, the page will try `ws://VPS_IP:9002` and get “Connecting…” forever (no live updates).
- To have a **working live dashboard** at `http://YOUR_VPS_IP`, you should also run the **WebSocket relay** on the same VPS (and usually the MQTT broker there too). See [VPS_DEPLOYMENT.md](../VPS_DEPLOYMENT.md) for that.

If the relay runs somewhere else (e.g. your PC), edit `dashboard/index.html` and set `WS_URL` to that address, e.g.:

```javascript
const WS_URL = "ws://YOUR_PC_PUBLIC_IP:9002";
```

(Only works if your PC is reachable from the internet on port 9002.)

---

## Summary

| Step | Command / action |
|------|-------------------|
| Upload | `scp -r dashboard your_user@YOUR_VPS_IP:~/` |
| Serve (quick) | `python3 -m http.server 8080 --directory ~/dashboard` |
| Serve (Nginx) | Configure nginx `root` to `~/dashboard`, reload nginx |
| URL | `http://YOUR_VPS_IP:8080` or `http://YOUR_VPS_IP` |
| Live data | Run the WebSocket relay on the VPS (port 9002) so the dashboard can connect |
