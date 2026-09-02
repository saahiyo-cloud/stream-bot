import logging
import urllib.parse
from pathlib import Path
from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from bot.config import Config
from bot.database.db import db
from bot.client import bot
from bot.utils import human_readable_size, extract_media
from server.stream import parse_range_header, byte_range_chunk_generator

logger = logging.getLogger(__name__)

# Template directory setup
templates_dir = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(templates_dir)), enable_async=True)


async def get_or_recover_file(file_hash: str):
    """
    Retrieve file from database. If missing (e.g. ephemeral container redeployment),
    automatically reconstruct and recover record from BIN_CHANNEL using the encoded message_id.
    """
    file_info = await db.get_file_by_hash(file_hash)
    if file_info:
        return file_info

    # Attempt automatic recovery from Telegram storage channel
    prefix = Config.HASH_PREFIX
    if file_hash.startswith(prefix):
        payload = file_hash[len(prefix):]
        # First 12 characters are entropy, remainder is the message_id
        if len(payload) > 12:
            msg_id_str = payload[12:]
            if msg_id_str.isdigit():
                message_id = int(msg_id_str)
                chat_id = Config.BIN_CHANNEL
                if chat_id != 0:
                    try:
                        client = bot.get_stream_client()
                        try:
                            msg = await client.get_messages(chat_id=chat_id, message_ids=message_id)
                        except Exception:
                            msg = await bot.get_messages(chat_id=chat_id, message_ids=message_id)

                        if msg and not getattr(msg, "empty", False):
                            media, file_name, file_size, mime_type, file_unique_id, category, is_streamable = extract_media(msg)
                            if media and file_size:
                                await db.add_file(
                                    file_hash=file_hash,
                                    message_id=message_id,
                                    file_name=file_name,
                                    file_size=file_size,
                                    mime_type=mime_type,
                                    file_unique_id=file_unique_id,
                                    user_id=0
                                )
                                logger.info(f"Auto-recovered file metadata for {file_hash} (msg_id: {message_id}) from Telegram storage")
                                return await db.get_file_by_hash(file_hash)
                    except Exception as e:
                        logger.warning(f"Could not auto-recover {file_hash} from storage channel: {e}")
    return None


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

    file_info = await get_or_recover_file(file_hash)
    if not file_info:
        raise web.HTTPNotFound(text="File not found or expired.")

    await db.increment_views(file_hash)

    public_base = Config.get_public_url()
    raw_stream_url = f"{public_base}/{file_hash}?stream=1"
    download_url = f"{public_base}/{file_hash}"
    import datetime
    created_ts = file_info.get("created_at") or 0
    uploaded_date = datetime.datetime.fromtimestamp(created_ts, tz=datetime.timezone.utc).strftime("%b %d, %Y • %H:%M UTC") if created_ts else "Recent"

    template = jinja_env.get_template("player.html")
    rendered_html = await template.render_async(
        file_name=file_info["file_name"] or "Media File",
        formatted_size=human_readable_size(file_info["file_size"]),
        mime_type=file_info["mime_type"] or "video/mp4",
        raw_stream_url=raw_stream_url,
        download_url=download_url,
        updates_channel=Config.UPDATES_CHANNEL,
        views_count=file_info.get("views_count", 1),
        downloads_count=file_info.get("downloads_count", 0),
        uploaded_date=uploaded_date,
        file_hash=file_hash
    )

    return web.Response(text=rendered_html, content_type="text/html")


async def stream_download_route(request: web.Request) -> web.StreamResponse:
    file_hash = request.match_info.get("file_hash", "").strip()
    if not file_hash:
        raise web.HTTPBadRequest(text="Missing file hash")

    file_info = await get_or_recover_file(file_hash)
    if not file_info:
        raise web.HTTPNotFound(text="Requested file was not found.")

    file_size = file_info["file_size"]
    file_name = file_info["file_name"] or f"file_{file_hash}"
    mime_type = file_info["mime_type"] or "application/octet-stream"
    message_id = file_info["message_id"]

    # Check range header
    range_header = request.headers.get("Range")
    start_byte, end_byte, is_range = parse_range_header(range_header, file_size)

    # Get worker client from pool for load balancing
    stream_client = bot.get_stream_client()

    # Fetch Telegram message directly using the stream_client that will read the bytes
    chat_id = Config.BIN_CHANNEL if Config.BIN_CHANNEL != 0 else file_info["user_id"]
    try:
        msg = await stream_client.get_messages(chat_id=chat_id, message_ids=message_id)
    except Exception as e:
        logger.warning(f"Worker client failed to fetch message {message_id}: {e}. Retrying with primary bot...")
        try:
            msg = await bot.get_messages(chat_id=chat_id, message_ids=message_id)
            stream_client = bot
        except Exception as e2:
            logger.error(f"Failed to fetch Telegram message {message_id}: {e2}")
            raise web.HTTPInternalServerError(text="Failed to fetch media from Telegram storage.")

    if not msg:
        raise web.HTTPNotFound(text="Media message not found in Telegram storage.")

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

