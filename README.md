# Stream Bot ⚡ - Telegram MTProto Streaming & Direct Download Server

24/7 Asynchronous MTProto chunk streaming server with Docker deployment.

## Quick Deploy (Koyeb / Render / Railway)

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `API_ID` | Telegram API ID from my.telegram.org |
| `API_HASH` | Telegram API Hash |
| `BOT_TOKEN` | Bot token from @BotFather |
| `BIN_CHANNEL` | Storage channel ID (e.g. -1001234567890) |
| `SERVER_URL` | Public URL of the deployed service |
| `WORKER_URL` | Cloudflare Worker URL (if using CF proxy) |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `7860` | Server port |
| `OWNER_ID` | `0` | Bot owner Telegram user ID |
| `MULTI_TOKENS` | _(empty)_ | Comma-separated worker bot tokens |
| `UPDATES_CHANNEL` | _(empty)_ | Updates channel username |
| `HASH_PREFIX` | `stream-` | URL hash prefix |

## Docker

```bash
docker build -t stream-bot .
docker run -p 7860:7860 --env-file .env stream-bot
```
