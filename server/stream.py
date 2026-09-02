import math
import logging
import asyncio
from typing import AsyncGenerator, Tuple, Optional

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024  # 1 MiB


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


async def byte_range_chunk_generator(
    client,
    message,
    start_byte: int,
    end_byte: int,
    file_size: int,
    clients=None
) -> AsyncGenerator[bytes, None]:
    """
    High-throughput pipelined chunk streaming generator.
    Maintains a continuous MTProto media stream from Telegram DC while prefetching
    up to 3 chunks (~3MB) in RAM to maximize single-stream throughput with zero timeouts.
    """
    offset_chunk = start_byte // CHUNK_SIZE
    last_chunk = end_byte // CHUNK_SIZE
    limit_chunks = (last_chunk - offset_chunk) + 1

    current_byte = offset_chunk * CHUNK_SIZE
    bytes_to_send = (end_byte - start_byte) + 1
    sent_bytes = 0

    # Pipeline buffer: prefetch up to 3 chunks in RAM
    queue = asyncio.Queue(maxsize=3)
    stop_producer = asyncio.Event()

    active_client = client if not isinstance(client, list) else client[0]

    async def _producer():
        try:
            async for chunk in active_client.stream_media(message, offset=offset_chunk, limit=limit_chunks):
                if stop_producer.is_set():
                    break
                if chunk:
                    await queue.put(chunk)
            await queue.put(None)  # Sentinel: end of stream
        except Exception as e:
            if "FILE_REFERENCE_EXPIRED" in str(e) or "FileReferenceExpired" in type(e).__name__:
                logger.warning("File reference expired during streaming. Refreshing fresh context...")
                try:
                    chat_id = message.chat.id
                    fresh_msg = await active_client.get_messages(chat_id=chat_id, message_ids=message.id)
                    if fresh_msg and not stop_producer.is_set():
                        rem_offset = current_byte // CHUNK_SIZE
                        rem_limit = max(1, (last_chunk - rem_offset) + 1)
                        async for chunk in active_client.stream_media(fresh_msg, offset=rem_offset, limit=rem_limit):
                            if stop_producer.is_set():
                                break
                            if chunk:
                                await queue.put(chunk)
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

            # Determine slice within this chunk
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
