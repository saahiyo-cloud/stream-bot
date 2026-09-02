import math
import os
import mimetypes
import secrets
import string
from bot.config import Config

# Initialize mimetypes
mimetypes.init()


def human_readable_size(size_bytes: int) -> str:
    """Format bytes into human readable format like 85.63 MB"""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def generate_file_hash(message_id: int) -> str:
    """
    Generate unique vanity hash like 'stream-8acv0ltdpmu893130'
    incorporating random entropy and the message ID.
    """
    prefix = Config.HASH_PREFIX

    entropy = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(12))
    return f"{prefix}{entropy}{message_id}"


VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".wmv", ".flv", ".ts", ".m4v", ".3gp", ".vob", ".mpg", ".mpeg"}
AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".wav", ".aac", ".opus", ".ogg", ".wma", ".mka"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg", ".ico", ".tiff"}
APK_EXTS = {".apk", ".xapk", ".apks", ".aab"}
ARCHIVE_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".tgz"}
DOCUMENT_EXTS = {".pdf", ".epub", ".mobi", ".docx", ".doc", ".xlsx", ".pptx", ".txt", ".csv", ".json"}
SOFTWARE_EXTS = {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm"}


def classify_media_type(file_name: str, raw_mime: str, raw_type: str):
    """
    Intelligently determines file category, accurate MIME type, and whether
    the file is streamable (video/audio/image) or a downloadable document/app.
    """
    ext = os.path.splitext(file_name)[1].lower() if file_name else ""
    mime_type = raw_mime

    # 1. Video Detection (even if sent uncompressed as Document)
    if raw_type == "video" or raw_type == "animation" or ext in VIDEO_EXTS or (mime_type and mime_type.startswith("video/")):
        guessed_mime = mimetypes.guess_type(file_name)[0] or "video/mp4"
        return "video", guessed_mime, True

    # 2. Audio Detection
    if raw_type == "audio" or raw_type == "voice" or ext in AUDIO_EXTS or (mime_type and mime_type.startswith("audio/")):
        guessed_mime = mimetypes.guess_type(file_name)[0] or "audio/mpeg"
        return "audio", guessed_mime, True

    # 3. Image Detection
    if raw_type == "photo" or ext in IMAGE_EXTS or (mime_type and mime_type.startswith("image/")):
        guessed_mime = mimetypes.guess_type(file_name)[0] or "image/jpeg"
        return "image", guessed_mime, True

    # 4. Android App (APK)
    if ext in APK_EXTS or (mime_type and "android.package-archive" in mime_type):
        return "apk", "application/vnd.android.package-archive", False

    # 5. Compressed Archives
    if ext in ARCHIVE_EXTS or (mime_type and any(x in mime_type for x in ["zip", "rar", "tar", "7z"])):
        guessed_mime = mimetypes.guess_type(file_name)[0] or "application/zip"
        return "archive", guessed_mime, False

    # 6. PDF / Documents
    if ext == ".pdf" or (mime_type and "pdf" in mime_type):
        return "pdf", "application/pdf", False

    if ext in DOCUMENT_EXTS:
        guessed_mime = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        return "document", guessed_mime, False

    # 7. Executable / Software
    if ext in SOFTWARE_EXTS:
        return "software", "application/octet-stream", False

    # Default fallback
    guessed_mime = mimetypes.guess_type(file_name)[0] or mime_type or "application/octet-stream"
    return "document", guessed_mime, False


def extract_media(message):
    """
    Extract media object, accurate filename, size, and category classification.
    """
    media = None
    media_type = "file"

    if message.document:
        media = message.document
        media_type = "document"
    elif message.video:
        media = message.video
        media_type = "video"
    elif message.audio:
        media = message.audio
        media_type = "audio"
    elif message.animation:
        media = message.animation
        media_type = "animation"
    elif message.voice:
        media = message.voice
        media_type = "voice"
    elif message.photo:
        media = message.photo
        media_type = "photo"

    if not media:
        return None, None, None, None, None, None, False

    file_name = getattr(media, "file_name", None)
    if not file_name:
        if media_type == "photo":
            file_name = f"photo_{message.id}.jpg"
        elif media_type == "video":
            file_name = f"video_{message.id}.mp4"
        elif media_type == "audio":
            file_name = f"audio_{message.id}.mp3"
        elif media_type == "animation":
            file_name = f"animation_{message.id}.mp4"
        elif media_type == "voice":
            file_name = f"voice_{message.id}.ogg"
        else:
            file_name = f"file_{message.id}"

    file_size = getattr(media, "file_size", 0)
    raw_mime = getattr(media, "mime_type", None)
    file_unique_id = getattr(media, "file_unique_id", str(message.id))

    category, mime_type, is_streamable = classify_media_type(file_name, raw_mime, media_type)

    return media, file_name, file_size, mime_type, file_unique_id, category, is_streamable
