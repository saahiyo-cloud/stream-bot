# Stream Bot ⚡ - High-Speed Telegram File to Stream & Download Bot

A high-performance Telegram File-to-Stream and Direct Download Link generator bot built with **Hydrogram MTProto** and an asynchronous **aiohttp** streaming engine, with optional **Cloudflare Worker** edge acceleration.

---

## ✨ Features

- ⚡ **Zero-Disk I/O RAM Streaming**: Directly streams Telegram media chunks in real-time from Telegram Data Centers without saving to disk.
- 🎬 **HTTP 206 Partial Content (Range Support)**: Full video scrub & seek support for browsers, VLC, MX Player, and iOS Safari.
- 🚀 **Multi-Client Acceleration**: Distribute chunk streaming requests across a pool of secondary bot tokens to bypass Telegram rate limits (FloodWait) and multiply throughput.
- 🌐 **Cloudflare Worker Edge Reverse Proxy**: Optional `dl.<yourname>.workers.dev` proxy providing free SSL, CDN caching, and origin IP masking.
- 📺 **Built-in Web Video Player**: Responsive dark-mode HTML5 web player with Plyr.js, speed controls, PiP, and direct download buttons.
- 📦 **Supports All Media**: Handles Videos, Audios, Documents, Voice notes, GIFs, and Photos up to 2GB (or 4GB for Premium).

---

## 📁 Project Structure

```
stream_bot ⚡/
├── bot/
│   ├── config.py                 # Bot settings & environment variable parser
│   ├── client.py                 # Multi-client MTProto manager
│   ├── utils.py                  # File size formatter & hash generator
│   ├── database/
│   │   └── db.py                 # SQLite database for files and statistics
│   └── handlers/
│       ├── start.py              # /start, /help, /about, /stats commands
│       └── file_receiver.py      # Listens for media & generates stream links
├── server/
│   ├── app.py                    # aiohttp web server runner
│   ├── routes.py                 # /watch/{id}, /{id}, /status endpoints
│   ├── stream.py                 # Byte-range chunk streamer & MTProto bridge
│   └── templates/
│       └── player.html           # Dark-mode HTML5 video player (Plyr.js)
├── cloudflare/
│   ├── worker.js                 # Cloudflare Worker reverse proxy script
│   └── wrangler.toml             # Cloudflare deployment config
├── main.py                       # Unified entrypoint (runs bot + web server)
├── .env.example                  # Environment variables template
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container definition
├── docker-compose.yml            # Docker compose file
└── README.md                     # Documentation
```

---

## 🚀 Quick Setup & Installation

### 1. Prerequisites & Credentials
You will need:
1. **Telegram API ID & API Hash**: Obtain from [my.telegram.org](https://my.telegram.org).
2. **Telegram Bot Token**: Create a new bot with [@BotFather](https://t.me/BotFather).
3. **Storage / Bin Channel**: Create a private Telegram channel, add your bot as an **Administrator**, and get the channel ID (e.g., `-1001234567890`).

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Edit `.env` with your values:
```env
API_ID=12345678
API_HASH=your_api_hash_here
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
BIN_CHANNEL=-1001234567890
PORT=8080
SERVER_URL=http://localhost:8080
UPDATES_CHANNEL=

```

### 3. Run Locally
```powershell
# Install dependencies
pip install -r requirements.txt

# Start the bot and stream server
python main.py
```

### 4. Run with Docker
```powershell
docker-compose up --build -d
```

---

## 🌐 Deploying Cloudflare Worker Edge Proxy (Optional)

To achieve the URL structure shown in the reference (e.g. `https://dl.yourname.workers.dev/watch/...`):

1. Log in to your [Cloudflare Dashboard](https://dash.cloudflare.com/) and go to **Workers & Pages**.
2. Click **Create Application** -> **Create Worker**.
3. Replace the worker code with the contents of [`cloudflare/worker.js`](file:///c:/Users/Shakir/OneDrive/Desktop/New%20folder/stream_bot%20%E2%9A%A1/cloudflare/worker.js).
4. Set the `BACKEND_ORIGIN` variable in the worker to your backend server URL (e.g., `https://your-bot-server.com`).
5. In your `.env`, set `WORKER_URL=https://dl.yourname.workers.dev`.
6. Restart the bot!

---

## ⚡ Multi-Client Bandwidth Acceleration

To scale for high concurrent traffic:
1. Create 2–5 additional bot tokens via [@BotFather](https://t.me/BotFather).
2. Add them as administrators to your `BIN_CHANNEL`.
3. Put the comma-separated tokens in `.env`:
   ```env
   MULTI_TOKENS=123456:Token1,654321:Token2,987654:Token3
   ```
4. The bot will automatically load-balance chunk requests across all worker bots in round-robin!
