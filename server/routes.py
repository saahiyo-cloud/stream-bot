import logging
import urllib.parse
from pathlib import Path
from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from bot.config import Config
from bot.database.db import db
from bot.client import bot
from bot.utils import human_readable_size
from server.stream import parse_range_header, byte_range_chunk_generator

logger = logging.getLogger(__name__)

# Template directory setup
templates_dir = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)), enable_async=True)


async def home_route(request: web.Request) -> web.Response:
    return web.json_response({
        "bot": "Telegram File Stream Bot ⚡",
        "status": "online",
        "version": "1.0.0",
        "engine": "Hydrogram MTProto + Async aiohttp",
        "docs": "Send any media file to the Telegram bot to generate a stream link."
    })


async def status_route(request: web.Request) -> web.Response:
    stats = await db.get_stats()
    return web.json_response({
        "status": "healthy",
        "total_files": stats["total_files"],
        "total_users": stats["total_users"],
        "total_size_bytes": stats["total_size"],
        "total_size_formatted": human_readable_size(stats["total_size"]),
        "workers_online": len(bot.worker_clients) + 1
    })


async def watch_player_route(request: web.Request) -> web.Response:
    file_hash = request.match_info.get("file_hash", "").strip()
    if not file_hash:
        raise web.HTTPBadRequest(text="Missing file hash parameter")

    file_info = await db.get_file_by_hash(file_hash)
    if not file_info:
        raise web.HTTPNotFound(text="File not found or expired.")

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

    return web.Response(text=rendered_html, content_type="text/html")


async def stream_download_route(request: web.Request) -> web.StreamResponse:
    file_hash = request.match_info.get("file_hash", "").strip()
    if not file_hash:
        raise web.HTTPBadRequest(text="Missing file hash")

    file_info = await db.get_file_by_hash(file_hash)
    if not file_info:
        raise web.HTTPNotFound(text="Requested file was not found.")

    file_size = file_info["file_size"]
    file_name = file_info["file_name"] or f"file_{file_hash}"
    mime_type = file_info["mime_type"] or "application/octet-stream"
    message_id = file_info["message_id"]

    # Check range header
    range_header = request.headers.get("Range")
    start_byte, end_byte, is_range = parse_range_header(range_header, file_size)

    # Fetch Telegram message from storage channel / chat
    chat_id = Config.BIN_CHANNEL if Config.BIN_CHANNEL != 0 else file_info["user_id"]
    try:
        msg = await bot.get_messages(chat_id=chat_id, message_ids=message_id)
    except Exception as e:
        logger.error(f"Failed to fetch Telegram message {message_id}: {e}")
        raise web.HTTPInternalServerError(text="Failed to fetch media from Telegram storage.")

    if not msg:
        raise web.HTTPNotFound(text="Media message not found in Telegram storage.")

    # Get worker client from pool for load balancing
    stream_client = bot.get_stream_client()

    content_length = (end_byte - start_byte) + 1
    safe_filename = urllib.parse.quote(file_name)

    is_stream_request = request.query.get("stream") == "1" or is_range or "video" in mime_type or "audio" in mime_type
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

    if is_range:
        headers["Content-Range"] = f"bytes {start_byte}-{end_byte}/{file_size}"
        status_code = 206
    else:
        status_code = 200

    response = web.StreamResponse(status=status_code, headers=headers)
    await response.prepare(request)

    # Track download/stream in background
    if start_byte == 0:
        await db.increment_downloads(file_hash)

    try:
        async for chunk in byte_range_chunk_generator(
            client=stream_client,
            message=msg,
            start_byte=start_byte,
            end_byte=end_byte,
            file_size=file_size
        ):
            await response.write(chunk)

        await response.write_eof()
    except (ConnectionResetError, web.HTTPException):
        # Client aborted playback or disconnected
        pass
    except Exception as e:
        logger.error(f"Error while streaming response: {e}")

    return response


def setup_routes(app: web.Application):
    app.router.add_get("/", home_route)
    app.router.add_get("/status", status_route)
    app.router.add_get("/watch/{file_hash}", watch_player_route)
    app.router.add_get("/{file_hash}", stream_download_route)

