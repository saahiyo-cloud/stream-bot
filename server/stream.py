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


async def _refresh_message(client, message):
    """Refresh a message to get a fresh file_reference."""
    try:
        chat_id = message.chat.id
        fresh = await client.get_messages(chat_id=chat_id, message_ids=message.id)
        if fresh and not getattr(fresh, "empty", False):
            return fresh
    except Exception as e:
        logger.warning(f"Failed to refresh message via {client.name}: {e}")
    return None


# ──────────────────────────────────────────────────────────────────────
#  SINGLE-CLIENT STREAMING  (small files / 1 worker only)
# ──────────────────────────────────────────────────────────────────────

async def _single_client_stream(
    client,
    message,
    start_byte: int,
    end_byte: int,
    file_size: int,
) -> AsyncGenerator[bytes, None]:
    """
    Original pipelined single-client streamer.
    Used for files < 10 MB or when no extra workers are available.
    Prefetches up to 3 chunks (~3 MB) in RAM.
    """
    offset_chunk = start_byte // CHUNK_SIZE
    last_chunk = end_byte // CHUNK_SIZE
    limit_chunks = (last_chunk - offset_chunk) + 1

    current_byte = offset_chunk * CHUNK_SIZE
    bytes_to_send = (end_byte - start_byte) + 1
    sent_bytes = 0

    queue: asyncio.Queue = asyncio.Queue(maxsize=3)
    stop_producer = asyncio.Event()

    async def _producer():
        nonlocal current_byte
        try:
            async for chunk in client.stream_media(message, offset=offset_chunk, limit=limit_chunks):
                if stop_producer.is_set():
                    break
                if chunk:
                    await queue.put(chunk)
            await queue.put(None)
        except Exception as e:
            if "FILE_REFERENCE_EXPIRED" in str(e) or "FileReferenceExpired" in type(e).__name__:
                logger.warning("File reference expired during single-client streaming. Refreshing...")
                fresh_msg = await _refresh_message(client, message)
                if fresh_msg and not stop_producer.is_set():
                    rem_offset = current_byte // CHUNK_SIZE
                    rem_limit = max(1, (last_chunk - rem_offset) + 1)
                    try:
                        async for chunk in client.stream_media(fresh_msg, offset=rem_offset, limit=rem_limit):
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
#  PARALLEL MULTI-CLIENT STREAMING  (large files + multiple workers)
# ──────────────────────────────────────────────────────────────────────

async def _worker_download_segment(
    worker_id: int,
    client,
    message,
    seg_offset: int,
    seg_limit: int,
    global_seq_start: int,
    output_queue: asyncio.Queue,
    stop_event: asyncio.Event,
):
    """
    Downloads a contiguous segment of chunks using one MTProto client session
    and puts (sequence_number, chunk_data) tuples into the shared output queue.
    """
    seq = global_seq_start
    try:
        async for chunk in client.stream_media(message, offset=seg_offset, limit=seg_limit):
            if stop_event.is_set():
                return
            if chunk:
                await output_queue.put((seq, chunk))
                seq += 1

    except Exception as e:
        is_ref_expired = (
            "FILE_REFERENCE_EXPIRED" in str(e)
            or "FileReferenceExpired" in type(e).__name__
        )
        if is_ref_expired:
            logger.warning(f"Worker {worker_id}: file reference expired at chunk seq={seq}. Refreshing...")
            fresh_msg = await _refresh_message(client, message)
            if fresh_msg and not stop_event.is_set():
                # Calculate remaining offset/limit from where we left off
                chunks_done = seq - global_seq_start
                rem_offset = seg_offset + chunks_done
                rem_limit = max(1, seg_limit - chunks_done)
                try:
                    async for chunk in client.stream_media(fresh_msg, offset=rem_offset, limit=rem_limit):
                        if stop_event.is_set():
                            return
                        if chunk:
                            await output_queue.put((seq, chunk))
                            seq += 1
                    return
                except Exception as refresh_err:
                    logger.error(f"Worker {worker_id}: retry after refresh failed: {refresh_err}")
                    await output_queue.put((seq, refresh_err))
                    return
            else:
                logger.error(f"Worker {worker_id}: could not refresh message")
                await output_queue.put((seq, e))
                return

        logger.error(f"Worker {worker_id}: segment download failed: {e}")
        await output_queue.put((seq, e))


async def _parallel_multi_client_stream(
    primary_client,
    message,
    start_byte: int,
    end_byte: int,
    file_size: int,
    clients: List,
) -> AsyncGenerator[bytes, None]:
    """
    High-throughput parallel chunk streamer.
    Splits the requested byte range into segments, assigns each to a different
    MTProto client, downloads concurrently, and reassembles in order.
    """
    offset_chunk = start_byte // CHUNK_SIZE
    last_chunk = end_byte // CHUNK_SIZE
    total_chunks = (last_chunk - offset_chunk) + 1

    current_byte = offset_chunk * CHUNK_SIZE
    bytes_to_send = (end_byte - start_byte) + 1
    sent_bytes = 0

    num_workers = len(clients)

    # Determine prefetch depth based on file size
    if file_size >= LARGE_FILE_THRESHOLD:
        prefetch_depth = 8
    else:
        prefetch_depth = 4

    # Output queue: (sequence_number, chunk_bytes) — large enough for all workers
    output_queue: asyncio.Queue = asyncio.Queue(maxsize=prefetch_depth * num_workers)
    stop_event = asyncio.Event()

    # Split chunks evenly across workers
    base_per_worker = total_chunks // num_workers
    remainder = total_chunks % num_workers

    worker_tasks = []
    current_offset = offset_chunk
    global_seq = 0

    for i, client in enumerate(clients):
        seg_limit = base_per_worker + (1 if i < remainder else 0)
        if seg_limit <= 0:
            break

        task = asyncio.create_task(
            _worker_download_segment(
                worker_id=i,
                client=client,
                message=message,
                seg_offset=current_offset,
                seg_limit=seg_limit,
                global_seq_start=global_seq,
                output_queue=output_queue,
                stop_event=stop_event,
            )
        )
        worker_tasks.append(task)

        current_offset += seg_limit
        global_seq += seg_limit

    logger.info(
        f"Parallel download: {total_chunks} chunks across {len(worker_tasks)} workers "
        f"(prefetch={prefetch_depth}, file_size={file_size})"
    )

    # ── Ordered reassembly consumer ──
    # We need to yield chunks in order even though workers finish at different rates.
    # Buffer out-of-order chunks and yield sequentially.
    next_expected_seq = 0
    buffered: dict = {}  # seq -> chunk_data
    total_expected = total_chunks

    try:
        while sent_bytes < bytes_to_send and next_expected_seq < total_expected:
            # Check if next chunk is already buffered
            if next_expected_seq in buffered:
                item = buffered.pop(next_expected_seq)
            else:
                # Wait for any chunk from the queue
                try:
                    seq, item = await asyncio.wait_for(output_queue.get(), timeout=120)
                except asyncio.TimeoutError:
                    logger.error("Parallel download timed out waiting for chunk")
                    break

                if isinstance(item, Exception):
                    raise item

                # If this isn't the one we need next, buffer it
                if seq != next_expected_seq:
                    buffered[seq] = item
                    continue

            # Process the chunk in order
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
            next_expected_seq += 1

    finally:
        stop_event.set()
        for task in worker_tasks:
            task.cancel()
        # Drain remaining items to prevent stuck coroutines
        while not output_queue.empty():
            try:
                output_queue.get_nowait()
            except asyncio.QueueEmpty:
                break


# ──────────────────────────────────────────────────────────────────────
#  PUBLIC API — Unified entry point used by routes.py
# ──────────────────────────────────────────────────────────────────────

async def byte_range_chunk_generator(
    client,
    message,
    start_byte: int,
    end_byte: int,
    file_size: int,
    clients=None
) -> AsyncGenerator[bytes, None]:
    """
    Adaptive chunk streaming generator.

    - For small files (< 10 MB) or when only 1 client is available:
      Uses the efficient single-client pipelined streamer.

    - For large files with multiple clients available:
      Splits the byte range across all clients for parallel downloading,
      reassembles chunks in order, and yields them to the HTTP response.
    """
    content_length = (end_byte - start_byte) + 1

    # Decide: parallel or single-client
    active_clients = clients if clients and len(clients) > 1 else None

    if active_clients and content_length >= PARALLEL_THRESHOLD:
        logger.info(
            f"Using PARALLEL multi-client stream ({len(active_clients)} clients) "
            f"for {content_length / (1024*1024):.1f} MB transfer"
        )
        async for chunk in _parallel_multi_client_stream(
            primary_client=client,
            message=message,
            start_byte=start_byte,
            end_byte=end_byte,
            file_size=file_size,
            clients=active_clients,
        ):
            yield chunk
    else:
        async for chunk in _single_client_stream(
            client=client,
            message=message,
            start_byte=start_byte,
            end_byte=end_byte,
            file_size=file_size,
        ):
            yield chunk
