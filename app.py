import os
import asyncio
import logging
import urllib.parse
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr
from jinja2 import Environment, FileSystemLoader

# Set up event loop before importing hydrogram
try:
    _loop = asyncio.get_event_loop()
except RuntimeError:
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

from bot.config import Config
from bot.client import bot
from bot.database.db import db
from bot.utils import human_readable_size
from server.stream import parse_range_header, byte_range_chunk_generator

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s - %(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("HF-Stream-Bot")

# Template engine
templates_dir = Path(__file__).parent / "server" / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)), enable_async=True)

# 1. Initialize FastAPI Application
app = FastAPI(title="Telegram Stream Bot ⚡")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    logger.info("Initializing SQLite database...")
    await db.init_db()
    logger.info("Starting Telegram MTProto Stream Bot client...")
    try:
        await bot.start()
        logger.info(f"⚡ Stream Bot successfully online as @{bot.me.username if bot.me else 'unknown'}!")
    except Exception as e:
        logger.error(f"Error starting Telegram client: {e}", exc_info=True)


@app.get("/status")
async def status_endpoint():
    stats = await db.get_stats()
    return JSONResponse({
        "status": "healthy",
        "bot": f"@{bot.me.username if bot.me else 'unknown'}",
        "total_files": stats["total_files"],
        "total_users": stats["total_users"],
        "total_size_bytes": stats["total_size"],
        "total_size_formatted": human_readable_size(stats["total_size"]),
        "workers_online": len(bot.worker_clients) + 1
    })


@app.get("/watch/{file_hash}")
async def watch_player_endpoint(file_hash: str):
    file_info = await db.get_file_by_hash(file_hash)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found or expired.")

    await db.increment_views(file_hash)
    public_base = Config.get_public_url()
    raw_stream_url = f"{public_base}/{file_hash}?stream=1"
    download_url = f"{public_base}/{file_hash}"

    template = jinja_env.get_template("player.html")
    rendered_html = await template.render_async(
        file_name=file_info["file_name"] or "Media File",
        formatted_size=human_readable_size(file_info["file_size"]),
        mime_type=file_info["mime_type"] or "video/mp4",
        raw_stream_url=raw_stream_url,
        download_url=download_url,
        updates_channel=Config.UPDATES_CHANNEL
    )
    return HTMLResponse(content=rendered_html)


@app.get("/{file_hash}")
async def stream_download_endpoint(file_hash: str, request: Request):
    if file_hash in ["favicon.ico", "status", "watch", "gradio_api", "ui"]:
        raise HTTPException(status_code=404)

    file_info = await db.get_file_by_hash(file_hash)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found.")

    file_size = file_info["file_size"]
    file_name = file_info["file_name"] or f"file_{file_hash}"
    mime_type = file_info["mime_type"] or "application/octet-stream"
    message_id = file_info["message_id"]

    range_header = request.headers.get("Range")
    start_byte, end_byte, is_range = parse_range_header(range_header, file_size)

    chat_id = Config.BIN_CHANNEL if Config.BIN_CHANNEL != 0 else file_info["user_id"]
    try:
        msg = await bot.get_messages(chat_id=chat_id, message_ids=message_id)
    except Exception as e:
        logger.error(f"Failed to fetch Telegram message {message_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch media from Telegram storage.")

    if not msg:
        raise HTTPException(status_code=404, detail="Media message not found in Telegram storage.")

    stream_client = bot.get_stream_client()
    content_length = (end_byte - start_byte) + 1
    safe_filename = urllib.parse.quote(file_name)

    is_stream_request = request.query_params.get("stream") == "1" or is_range or "video" in mime_type or "audio" in mime_type
    disposition = "inline" if is_stream_request else "attachment"

    headers = {
        "Content-Type": mime_type,
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": f'{disposition}; filename="{file_name}"; filename*=UTF-8\'\'{safe_filename}',
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Range, Content-Type",
        "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges",
        "Cache-Control": "public, max-age=86400"
    }

    status_code = 200
    if is_range:
        headers["Content-Range"] = f"bytes {start_byte}-{end_byte}/{file_size}"
        status_code = 206

    if start_byte == 0:
        await db.increment_downloads(file_hash)

    return StreamingResponse(
        byte_range_chunk_generator(
            client=stream_client,
            message=msg,
            start_byte=start_byte,
            end_byte=end_byte,
            file_size=file_size
        ),
        status_code=status_code,
        headers=headers
    )


# 2. Gradio Dashboard
with gr.Blocks(title="Telegram Stream Bot ⚡", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# ⚡ Telegram File Stream & Direct Download Bot")
    gr.Markdown("### 24/7 High-Speed MTProto Chunk Streaming Server")
    with gr.Row():
        gr.Markdown(
            "🟢 **Status:** `Online & Ready`\n\n"
            "🤖 **Bot Username:** [@mastream_bot](https://t.me/mastream_bot)\n\n"
            "🌐 **Edge CDN Domain:** `https://dl.shakir-ansarii075.workers.dev`\n\n"
            "🚀 **Engine:** Hydrogram MTProto + FastAPI Streaming"
        )
    gr.Markdown("---")
    gr.Markdown("📤 **How to use:** Send any media (Video, Audio, Photo, APK, Document) to **[@mastream_bot](https://t.me/mastream_bot)** on Telegram to generate live streaming & direct download links!")

# Mount Gradio onto FastAPI root
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
