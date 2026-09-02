# Stream Bot ⚡ — High-Speed Telegram MTProto Streaming Engine

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Engine](https://img.shields.io/badge/Engine-Hydrogram%20MTProto-06b6d4?logo=telegram&logoColor=white)](https://github.com/hydrogram/hydrogram)
[![Server](https://img.shields.io/badge/Web%20Server-aiohttp%20Async-8b5cf6)](https://docs.aiohttp.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?logo=docker&logoColor=white)](https://docker.com)
[![Deploy](https://img.shields.io/badge/Deploy-Railway%20%2F%20Koyeb%20%2F%20Render-10b981)](https://railway.app)
[![License](https://img.shields.io/badge/License-MIT-gray)](LICENSE)

**An ultra-fast, zero-disk Telegram media streaming and direct download server with an Awwwards-tier web player.**

[Live Demo](https://streambot.up.railway.app) • [Features](#-key-features) • [Performance Stats](#-live-performance-stats) • [Environment Variables](#-environment-variables) • [Deployment](#-deployment)

</div>

---

## ⚡ Key Features

- **Zero-Disk RAM Streaming**: Bytes are piped asynchronously from Telegram's MTProto data centers straight to the HTTP client socket without storing files on server disk.
- **Pipelined Chunk Prefetcher**: Background prefetch queue (`asyncio.Queue`) downloads upcoming chunks concurrently in RAM, eliminating turnaround latency between chunks.
- **Multi-Bot Worker Pool (`MULTI_TOKENS`)**: Round-robin load balancing distributes stream requests across multiple secondary bot accounts to bypass Telegram's single-token bandwidth limits.
- **HTTP 206 Partial Content**: Full support for video seeking, scrubbing, and multi-connection download managers (IDM, 1DM, ADM, aria2).
- **Awwwards-Tier Cinema Web Player**:
  - **Ethereal Glass Design**: Deep OLED black (`#050508`) canvas with radial ambient mesh orbs.
  - **Double-Bezel (Doppelrand) Architecture**: Precision concentric enclosures with machined hairline highlights.
  - **Asymmetrical Bento Grid**: Modern modular layout organizing metadata, payload specs, and direct action bars.
  - **Button-in-Button CTA**: Fully rounded interactive pills with kinetic diagonal trailing icon tension.
- **Smart Playback Resume**: Video player automatically tracks watch position in `localStorage` and restores timestamps on return with haptic toast feedback.
- **1-Tap Telegram Quick-Share**: Integrated `t.me/share/url` deep links allow users to share files into chats with one tap.
- **Volume-Independent Ephemeral Architecture**: Vanity hash schema (`stream-{12_entropy}{message_id}`) recovers files on-the-fly from `BIN_CHANNEL` if the database resets during redeployment.
- **Media Upload Deduplication**: SHA-indexed `file_unique_id` cache reuses existing stream links when duplicate files are forwarded.

---

## 📊 Live Performance Stats

Benchmarked on production Railway instances with 3 active Telegram bot workers:

| Metric | Measured Value | Real-World Impact |
| :--- | :---: | :--- |
| **Time to First Byte (TTFB)** | **`459.5 ms`** | Instant video start; zero initial buffering |
| **Sustained Single-Stream Speed** | **`25.5 Mbps` (~3.2 MB/s)** | Over 12× faster than required for 1080p/4K streaming |
| **Parallel IDM Speed** | **`15 – 30+ MB/s`** | Saturates multi-connection range downloads |
| **Server RAM Footprint** | **`< 120 MB`** | High efficiency with zero memory leaks |
| **Storage Usage** | **`0 MB` (Disk-Free)** | Pure RAM-piped byte transmission |
| **Network Node** | **Singapore (`asia-southeast1`)** | Direct proximity to Telegram DC5 Asia & DC2 Europe |

---

## 🛠 Tech Stack

- **Core MTProto**: [Hydrogram](https://github.com/hydrogram/hydrogram) (Layer 181) with compiled [TgCrypto](https://github.com/pyrogram/tgcrypto) AES-256-CTR encryption
- **Asynchronous Web Framework**: [aiohttp](https://docs.aiohttp.org/) 3.9+
- **Database**: SQLite3 with WAL (Write-Ahead Logging) mode & unique indexing
- **Frontend Engine**: Jinja2 + Vanilla CSS (No bloated frameworks) + [Plyr 3.7.8](https://plyr.io/)
- **Containerization**: Docker multi-stage Alpine build

---

## 📋 Environment Variables

### Required Settings

| Variable | Type | Description |
| :--- | :---: | :--- |
| `API_ID` | Integer | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | String | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | String | Primary bot token from [@BotFather](https://t.me/BotFather) |
| `BIN_CHANNEL` | Integer | Private channel ID for permanent file storage (e.g. `-1001234567890`) |
| `SERVER_URL` | String | Public base URL of your deployed server (e.g. `https://streambot.up.railway.app`) |

### Optional Performance Settings

| Variable | Default | Description |
| :--- | :---: | :--- |
| `MULTI_TOKENS` | _(empty)_ | Comma-separated secondary worker bot tokens for multi-worker bandwidth scaling |
| `SESSION_STRING` | _(empty)_ | String session for primary bot to avoid login FloodWaits on ephemeral redeploys |
| `PORT` | `7860` | Web server listening port (automatically set by Railway / Render) |
| `OWNER_ID` | `0` | Telegram user ID of the bot administrator |
| `UPDATES_CHANNEL` | _(empty)_ | Telegram updates channel username (e.g. `@MyChannel`) |
| `HASH_PREFIX` | `stream-` | Prefix used for generated stream vanity URLs |

---

## 🚀 Deployment

### Option 1: Deploy on Railway (Recommended)

1. Fork or push this repository to GitHub.
2. In [Railway Dashboard](https://railway.app), click **New Project** ➔ **Deploy from GitHub repo**.
3. In **Service Settings**:
   - Set **Region** to **Asia (Singapore - `asia-southeast1`)** or **Europe (Amsterdam)** for low Telegram DC latency.
4. Add the required **Variables** (`API_ID`, `API_HASH`, `BOT_TOKEN`, `BIN_CHANNEL`, `SERVER_URL`).
5. Ensure your bot tokens are added as **Administrators** in your Telegram `BIN_CHANNEL`.

### Option 2: Run with Docker Compose

```yaml
version: "3.8"

services:
  stream-bot:
    build: .
    restart: always
    ports:
      - "7860:7860"
    env_file:
      - .env
```

```bash
docker compose up -d --build
```

### Option 3: Local Setup

```bash
# 1. Clone repository
git clone https://github.com/saahiyo-cloud/stream-bot.git
cd stream-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Start the application
python app.py
```

---

## 🌐 API & URL Structure

| Route | Method | Description |
| :--- | :---: | :--- |
| `/` | `GET` | Agency landing page (HTML) or server telemetry (JSON for API clients) |
| `/watch/{file_hash}` | `GET` | Responsive Cinema Web Player with metadata stats and direct actions |
| `/{file_hash}` | `GET, HEAD` | Direct media stream with HTTP 206 byte-range seeking |
| `/{file_hash}?download=1` | `GET, HEAD` | Forced file download (`Content-Disposition: attachment`) |
| `/status` | `GET` | Real-time JSON health check, active worker pool count, and database stats |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
