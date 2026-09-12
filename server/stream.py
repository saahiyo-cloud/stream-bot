import math
import logging
import asyncio
from typing import AsyncGenerator, Tuple, Optional, List

from bot.config import Config

logger = logging.getLogger(__name__)

# Use configurable chunk size from Config, fallback to 1 MiB
CHUNK_SIZE = Config.CHUNK_SIZE or (1024 * 1024)

# Thresholds for activating parallel mode
PARALLEL_THRESHOLD = 10 * 1024 * 1024  # 10 MB — files smaller than this use single-client
LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50 MB — files larger get deeper prefetch buffers


def parse_range_header(range_header: Optional[str], file_size: int) -> Tuple[int, int, bool]:
    """
    Parses HTTP Range header (e.g. 'bytes=0-1024' or 'bytes=1048576-').
    Returns (start, end, is_range_request).
    """
    if not range_header or not range_header.startswith("bytes="):
        return 0, file_size - 1, False

    range_spec = range_header.replace("bytes=", "").strip()
    parts = range_spec.split("-")

    if len(parts) != 2:
        return 0, file_size - 1, False

    start_str, end_str = parts[0].strip(), parts[1].strip()

    if start_str and end_str:
        start = int(start_str)
        end = min(int(end_str), file_size - 1)
    elif start_str:
        start = int(start_str)
        end = file_size - 1
    elif end_str:
        # Suffix range: bytes=-500 (last 500 bytes)
        length = int(end_str)
        start = max(0, file_size - length)
        end = file_size - 1
    else:
        start = 0
        end = file_size - 1

    start = max(0, min(start, file_size - 1))
    end = max(start, min(end, file_size - 1))

    return start, end, True


async def _refresh_message(client, message, chat_id=None, message_id=None):
    """Refresh a message to get a fresh file_reference."""
    try:
        cid = chat_id or getattr(getattr(message, "chat", None), "id", None)
        mid = message_id or getattr(message, "id", None)
        if not cid or not mid:
            return None
        fresh = await asyncio.wait_for(client.get_messages(chat_id=cid, message_ids=mid), timeout=5.0)
        if fresh and not getattr(fresh, "empty", False):
            return fresh
    except Exception as e:
        logger.warning(f"Failed to refresh message via {getattr(client, 'name', 'client')}: {e}")
    return None


# ──────────────────────────────────────────────────────────────────────
#  SINGLE-CLIENT STREAMING  (reliable pipelined prefetch)
# ──────────────────────────────────────────────────────────────────────

async def _single_client_stream(
    client,
    message,
    start_byte: int,
    end_byte: int,
    file_size: int,
    chat_id=None,
    message_id=None,
) -> AsyncGenerator[bytes, None]:
    """
    Pipelined single-client streamer.
    Prefetches up to 4 chunks in RAM and yields sequentially.
    Handles FILE_REFERENCE_EXPIRED automatically by refreshing message.
    """
    offset_chunk = start_byte // CHUNK_SIZE
    last_chunk = end_byte // CHUNK_SIZE
    limit_chunks = (last_chunk - offset_chunk) + 1

    current_byte = offset_chunk * CHUNK_SIZE
    bytes_to_send = (end_byte - start_byte) + 1
    sent_bytes = 0

    queue: asyncio.Queue = asyncio.Queue(maxsize=4)
    stop_producer = asyncio.Event()

    async def _producer():
        prod_chunk_offset = offset_chunk
        try:
            async for chunk in client.stream_media(message, offset=offset_chunk, limit=limit_chunks):
                if stop_producer.is_set():
                    break
                if chunk:
                    await queue.put(chunk)
                    prod_chunk_offset += 1
            await queue.put(None)
        except Exception as e:
            if "FILE_REFERENCE_EXPIRED" in str(e) or "FileReferenceExpired" in type(e).__name__:
                logger.warning("File reference expired during streaming. Refreshing...")
                fresh_msg = await _refresh_message(client, message, chat_id=chat_id, message_id=message_id)
                if fresh_msg and not stop_producer.is_set():
                    rem_offset = prod_chunk_offset
                    rem_limit = max(1, (last_chunk - rem_offset) + 1)
                    try:
                        async for chunk in client.stream_media(fresh_msg, offset=rem_offset, limit=rem_limit):
                            if stop_producer.is_set():
                                break
                            if chunk:
                                await queue.put(chunk)
                                prod_chunk_offset += 1
                        await queue.put(None)
                        return
                    except Exception as refresh_err:
                        await queue.put(refresh_err)
                        return
            await queue.put(e)

    producer_task = asyncio.create_task(_producer())

    try:
        while sent_bytes < bytes_to_send:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item

            chunk_len = len(item)
            chunk_start = current_byte
            chunk_end = current_byte + chunk_len - 1

            slice_start = max(0, start_byte - chunk_start)
            slice_end = min(chunk_len, (end_byte - chunk_start) + 1)

            part = item[slice_start:slice_end]
            if part:
                yield part
                sent_bytes += len(part)

            current_byte += chunk_len
    finally:
        stop_producer.set()
        producer_task.cancel()


# ──────────────────────────────────────────────────────────────────────
#  PARALLEL MULTI-CLIENT STREAMING  (verified multi-worker pool)
# ──────────────────────────────────────────────────────────────────────

async def fetch_single_chunk(
    client,
    message,
    chunk_index: int,
    fallback_client=None,
    fallback_message=None,
    chat_id=None,
    message_id=None,
) -> bytes:
    """
    Fetches a single 1MB chunk from Telegram MTProto using a verified client session.
    Automatically refreshes file references and falls back to primary client if needed.
    """
    try:
        async for chunk in client.stream_media(message, offset=chunk_index, limit=1):
            if chunk:
                return chunk
        return b""
    except Exception as e:
        is_ref_expired = (
            "FILE_REFERENCE_EXPIRED" in str(e)
            or "FileReferenceExpired" in type(e).__name__
        )
        if is_ref_expired:
            logger.warning(f"Worker {getattr(client, 'name', 'worker')}: file reference expired on chunk {chunk_index}. Refreshing...")
            fresh_msg = await _refresh_message(client, message, chat_id=chat_id, message_id=message_id)
            if fresh_msg:
                try:
                    async for chunk in client.stream_media(fresh_msg, offset=chunk_index, limit=1):
                        if chunk:
                            return chunk
                except Exception as retry_err:
                    logger.warning(f"Worker retry on chunk {chunk_index} failed: {retry_err}")

        # Failover rescue: download chunk via primary bot
        if fallback_client and fallback_client != client and fallback_message:
            logger.warning(f"Worker {getattr(client, 'name', 'worker')} failed on chunk {chunk_index} ({e}). Rescuing with primary bot...")
            try:
                async for chunk in fallback_client.stream_media(fallback_message, offset=chunk_index, limit=1):
                    if chunk:
                        return chunk
            except Exception as fb_err:
                logger.error(f"Fallback rescue on chunk {chunk_index} failed: {fb_err}")
                raise fb_err
        raise e


async def _parallel_multi_client_stream(
    verified_workers: List[Tuple],
    start_byte: int,
    end_byte: int,
    file_size: int,
    fallback_client=None,
    fallback_message=None,
    chat_id=None,
    message_id=None,
) -> AsyncGenerator[bytes, None]:
    """
    High-throughput interleaved sliding-window parallel streamer.
    Interleaves consecutive chunks across all verified bot workers simultaneously.
    Keeps multiple concurrent chunks in-flight across all workers so all bot sessions
    download concurrently 100% of the time.
    """
    offset_chunk = start_byte // CHUNK_SIZE
    last_chunk = end_byte // CHUNK_SIZE
    total_chunks = (last_chunk - offset_chunk) + 1

    current_byte = offset_chunk * CHUNK_SIZE
    bytes_to_send = (end_byte - start_byte) + 1
    sent_bytes = 0

    num_workers = len(verified_workers)
    # Maintain 3-4 concurrent in-flight chunks per worker to keep all connections saturated
    window_size = min(max(num_workers * 3, 6), 16)

    logger.info(
        f"Interleaved parallel download: {total_chunks} chunks across {num_workers} workers "
        f"(sliding window={window_size} chunks in-flight, file_size={file_size})"
    )

    tasks = {}

    def schedule_chunk(chunk_idx):
        worker_client, worker_msg = verified_workers[chunk_idx % num_workers]
        return asyncio.create_task(
            fetch_single_chunk(
                client=worker_client,
                message=worker_msg,
                chunk_index=chunk_idx,
                fallback_client=fallback_client,
                fallback_message=fallback_message,
                chat_id=chat_id,
                message_id=message_id,
            )
        )

    try:
        # Pre-seed initial sliding window with concurrent tasks across all workers
        for i in range(min(window_size, total_chunks)):
            c_idx = offset_chunk + i
            tasks[c_idx] = schedule_chunk(c_idx)

        next_chunk = offset_chunk
        while next_chunk <= last_chunk:
            task = tasks.pop(next_chunk, None)
            if task is None:
                task = schedule_chunk(next_chunk)

            chunk = await task

            # Schedule the next chunk to keep the worker pipeline full
            next_to_schedule = next_chunk + window_size
            if next_to_schedule <= last_chunk and next_to_schedule not in tasks:
                tasks[next_to_schedule] = schedule_chunk(next_to_schedule)

            if not chunk:
                next_chunk += 1
                continue

            chunk_len = len(chunk)
            chunk_start = current_byte
            chunk_end = current_byte + chunk_len - 1

            slice_start = max(0, start_byte - chunk_start)
            slice_end = min(chunk_len, (end_byte - chunk_start) + 1)

            part = chunk[slice_start:slice_end]
            if part:
                yield part
                sent_bytes += len(part)

            current_byte += chunk_len
            if sent_bytes >= bytes_to_send:
                break

            next_chunk += 1

    finally:
        for t in tasks.values():
            if not t.done():
                t.cancel()


# ──────────────────────────────────────────────────────────────────────
#  PUBLIC API — Unified entry point used by routes.py
# ──────────────────────────────────────────────────────────────────────

async def byte_range_chunk_generator(
    client,
    message,
    start_byte: int,
    end_byte: int,
    file_size: int,
    clients=None,
    chat_id=None,
    message_id=None,
) -> AsyncGenerator[bytes, None]:
    """
    Adaptive chunk streaming generator.

    - Verifies which bot workers have access to the file's storage chat.
    - If multiple bots have verified access & file >= 10 MB, runs parallel multi-client download.
    - If worker bots lack channel access or file < 10 MB, uses single-client pipelined buffer.
    """
    content_length = (end_byte - start_byte) + 1
    cid = chat_id or getattr(getattr(message, "chat", None), "id", None)
    mid = message_id or getattr(message, "id", None)

    # Multi-client candidate check
    active_candidates = clients if clients and len(clients) > 1 else None

    if active_candidates and content_length >= PARALLEL_THRESHOLD and cid and mid:
        # Verify which candidates actually have access to this chat & message
        async def _check_candidate(c):
            if c == client:
                return c, message
            try:
                w_msg = await asyncio.wait_for(c.get_messages(chat_id=cid, message_ids=mid), timeout=3.0)
                if w_msg and not getattr(w_msg, "empty", False):
                    return c, w_msg
            except Exception as e:
                bot_name = getattr(c, "name", "worker")
                logger.warning(
                    f"Worker {bot_name} cannot access storage channel {cid}: {e}. "
                    f"To enable multi-bot speedup, add this bot as an Admin to your storage channel."
                )
            return None

        checked = await asyncio.gather(*[_check_candidate(c) for c in active_candidates], return_exceptions=True)
        verified_workers = [res for res in checked if isinstance(res, tuple) and res[1] is not None]

        if len(verified_workers) > 1:
            logger.info(
                f"Using PARALLEL multi-client stream ({len(verified_workers)} verified workers) "
                f"for {content_length / (1024*1024):.1f} MB transfer"
            )
            async for chunk in _parallel_multi_client_stream(
                verified_workers=verified_workers,
                start_byte=start_byte,
                end_byte=end_byte,
                file_size=file_size,
                fallback_client=client,
                fallback_message=message,
                chat_id=cid,
                message_id=mid,
            ):
                yield chunk
            return

        logger.info("Using single-client pipelined stream (multi-client workers not available or lack channel access).")

    # Single-client fallback
    async for chunk in _single_client_stream(
        client=client,
        message=message,
        start_byte=start_byte,
        end_byte=end_byte,
        file_size=file_size,
        chat_id=cid,
        message_id=mid,
    ):
        yield chunk
