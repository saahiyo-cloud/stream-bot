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


async def fetch_single_chunk(client, message, chunk_index: int, fallback_client=None) -> bytes:
    """
    Fetches a single 1MB chunk from Telegram MTProto with automatic fallback to primary client.
    """
    try:
        async for chunk in client.stream_media(message, offset=chunk_index, limit=1):
            if chunk:
                return chunk
        return b""
    except Exception as e:
        if fallback_client and fallback_client != client:
            logger.debug(f"Worker client failed for chunk {chunk_index}: {e}. Retrying via primary bot...")
            async for chunk in fallback_client.stream_media(message, offset=chunk_index, limit=1):
                if chunk:
                    return chunk
        raise


async def byte_range_chunk_generator(
    client,
    message,
    start_byte: int,
    end_byte: int,
    file_size: int,
    clients=None
) -> AsyncGenerator[bytes, None]:
    """
    Multi-bot parallel chunk streaming generator.
    Distributes consecutive chunks across all available bot workers in parallel,
    multiplying download throughput for both single and multi-threaded transfers.
    """
    if clients and isinstance(clients, list) and len(clients) > 0:
        worker_pool = clients
    elif isinstance(client, list) and len(client) > 0:
        worker_pool = client
    else:
        worker_pool = [client]

    primary_client = worker_pool[0]
    num_workers = len(worker_pool)

    offset_chunk = start_byte // CHUNK_SIZE
    last_chunk = end_byte // CHUNK_SIZE
    total_chunks = (last_chunk - offset_chunk) + 1

    current_byte = offset_chunk * CHUNK_SIZE
    bytes_to_send = (end_byte - start_byte) + 1
    sent_bytes = 0

    # Sliding window prefetch size: keep up to 2 chunks per active worker in-flight
    window_size = min(max(3, num_workers * 2), 6)
    tasks = {}

    try:
        # Pre-seed initial sliding window with concurrent fetch tasks
        for i in range(min(window_size, total_chunks)):
            chunk_idx = offset_chunk + i
            assigned_client = worker_pool[chunk_idx % num_workers]
            tasks[chunk_idx] = asyncio.create_task(
                fetch_single_chunk(assigned_client, message, chunk_idx, fallback_client=primary_client)
            )

        next_chunk = offset_chunk
        while next_chunk <= last_chunk:
            # Await next in-order chunk
            task = tasks.pop(next_chunk, None)
            if task is None:
                assigned_client = worker_pool[next_chunk % num_workers]
                task = asyncio.create_task(
                    fetch_single_chunk(assigned_client, message, next_chunk, fallback_client=primary_client)
                )

            chunk = await task

            # Schedule the next chunk to keep the prefetch pipeline full
            next_to_schedule = next_chunk + window_size
            if next_to_schedule <= last_chunk and next_to_schedule not in tasks:
                assigned_client = worker_pool[next_to_schedule % num_workers]
                tasks[next_to_schedule] = asyncio.create_task(
                    fetch_single_chunk(assigned_client, message, next_to_schedule, fallback_client=primary_client)
                )

            if not chunk:
                next_chunk += 1
                continue

            chunk_len = len(chunk)
            chunk_start = current_byte
            chunk_end = current_byte + chunk_len - 1

            # Determine slice within this chunk
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
        # Cancel all remaining prefetch tasks when stream ends or client aborts
        for t in tasks.values():
            if not t.done():
                t.cancel()
