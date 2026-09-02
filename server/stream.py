import math
import logging
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
    file_size: int
) -> AsyncGenerator[bytes, None]:
    """
    Streams file bytes chunk-by-chunk from Telegram MTProto DC,
    slicing the first and last chunks to match exact byte boundaries.
    """
    offset_chunk = start_byte // CHUNK_SIZE
    last_chunk = end_byte // CHUNK_SIZE
    limit_chunks = (last_chunk - offset_chunk) + 1

    current_byte = offset_chunk * CHUNK_SIZE
    bytes_to_send = (end_byte - start_byte) + 1
    sent_bytes = 0

    async def _stream_chunks(active_client, active_msg, current_offset, remaining_limit):
        async for chk in active_client.stream_media(active_msg, offset=current_offset, limit=remaining_limit):
            yield chk

    try:
        async for chunk in client.stream_media(message, offset=offset_chunk, limit=limit_chunks):
            if not chunk:
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

    except Exception as e:
        if "FILE_REFERENCE_EXPIRED" in str(e) or "FileReferenceExpired" in type(e).__name__:
            logger.warning("File reference expired during streaming. Refreshing fresh message context from Telegram...")
            try:
                chat_id = message.chat.id
                fresh_msg = await client.get_messages(chat_id=chat_id, message_ids=message.id)
                if fresh_msg:
                    new_offset = current_byte // CHUNK_SIZE
                    new_limit = max(1, (last_chunk - new_offset) + 1)
                    async for chunk in client.stream_media(fresh_msg, offset=new_offset, limit=new_limit):
                        if not chunk:
                            continue
                        chunk_len = len(chunk)
                        chunk_start = current_byte
                        slice_start = max(0, start_byte - chunk_start)
                        slice_end = min(chunk_len, (end_byte - chunk_start) + 1)
                        part = chunk[slice_start:slice_end]
                        if part:
                            yield part
                            sent_bytes += len(part)
                        current_byte += chunk_len
                        if sent_bytes >= bytes_to_send:
                            break
                    return
            except Exception as refresh_err:
                logger.error(f"Failed to refresh expired message file reference: {refresh_err}")
        logger.error(f"Stream generator exception: {e}")
        raise
