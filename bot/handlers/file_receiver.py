import logging
from hydrogram import Client, filters
from hydrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.database.db import db
from bot.config import Config
from bot.utils import human_readable_size, generate_file_hash, extract_media

logger = logging.getLogger(__name__)

CATEGORY_EMOJIS = {
    "video": "🎬 Video",
    "audio": "🎵 Audio / Music",
    "image": "🖼️ Image / Photo",
    "apk": "📱 Android App (APK)",
    "archive": "🗜️ Compressed Archive",
    "pdf": "📄 PDF Document",
    "software": "💻 Software / Executable",
    "document": "📁 Document / File"
}


@Client.on_message(
    (filters.document | filters.video | filters.audio | filters.animation | filters.voice | filters.photo) &
    (filters.private | filters.channel)
)
async def media_file_handler(client: Client, message: Message):
    # Prevent duplicate loops if message arrives from the storage channel itself
    if Config.BIN_CHANNEL != 0 and message.chat and message.chat.id == Config.BIN_CHANNEL:
        return

    media, file_name, file_size, mime_type, file_unique_id, category, is_streamable = extract_media(message)
    if not media:
        return

    # Track user in DB
    user_id = message.from_user.id if message.from_user else (message.sender_chat.id if message.sender_chat else 0)
    if message.from_user:
        await db.add_user(user_id, message.from_user.first_name, message.from_user.username or "")

    # Processing status indicator
    status_msg = await message.reply_text("⚡ **Generating ultra-fast link...**", quote=True)

    try:
        # Check if file has already been stored (deduplication by file_unique_id)
        existing_file = await db.get_file_by_unique_id(file_unique_id)
        if existing_file:
            logger.info(f"Duplicate media detected (unique_id: {file_unique_id}). Reusing hash {existing_file['file_hash']}")
            file_hash = existing_file["file_hash"]
            storage_msg_id = existing_file["message_id"]
        else:
            # Save file reference to BIN_CHANNEL for permanent storage
            storage_msg_id = message.id
            if Config.BIN_CHANNEL != 0:
                try:
                    forwarded_msg = await message.copy(chat_id=Config.BIN_CHANNEL)
                    storage_msg_id = forwarded_msg.id
                except Exception as copy_err:
                    logger.warning(f"Could not forward to BIN_CHANNEL ({Config.BIN_CHANNEL}): {copy_err}. Falling back to direct message ID.")

            # Generate unique vanity file hash
            file_hash = generate_file_hash(storage_msg_id)

            # Store record in database
            await db.add_file(
                file_hash=file_hash,
                message_id=storage_msg_id,
                file_name=file_name,
                file_size=file_size,
                mime_type=mime_type,
                file_unique_id=file_unique_id,
                user_id=user_id
            )

        base_url = Config.get_public_url()
        stream_url = f"{base_url}/watch/{file_hash}"
        download_url = f"{base_url}/{file_hash}"
        formatted_size = human_readable_size(file_size)
        category_label = CATEGORY_EMOJIS.get(category, "📁 File")

        # Check if URL is valid for Telegram InlineKeyboardButton
        has_valid_url = base_url.startswith("http://") or base_url.startswith("https://")
        is_local = "localhost" in base_url or "127.0.0.1" in base_url
        footer_channel = f"\n\n🛠 **Join {Config.UPDATES_CHANNEL} for latest updates!**" if Config.UPDATES_CHANNEL else ""

        if not has_valid_url:
            # Fallback when SERVER_URL is not set yet
            reply_text = (
                "⚠️ **Server Domain Not Configured!**\n\n"
                f"📁 **Name:** `{file_name}`\n"
                f"📦 **Size:** `{formatted_size}`\n\n"
                "Please configure `SERVER_URL` (e.g. `https://your-domain.up.railway.app`) in your environment variables to generate public stream & download links."
            )
            await status_msg.edit_text(reply_text)
            return

        if is_streamable:
            # Streamable Media (Video, Audio, Image)
            reply_text = (
                "✅ **Your Links are Ready!**\n\n"
                f"📁 **Name:**\n"
                f"`{file_name}`\n\n"
                f"📦 **Size:** `{formatted_size}`\n"
                f"🏷 **Type:** `{category_label}`\n\n"
                f"🎬 **Stream:**\n"
                f"{stream_url}\n\n"
                f"📥 **Download:**\n"
                f"{download_url}"
                f"{footer_channel}"
            )

            buttons = []
            if not is_local:
                buttons.append([
                    InlineKeyboardButton("🚀 Download Now", url=download_url),
                    InlineKeyboardButton("🎬 Watch Online", url=stream_url)
                ])
                second_row = []
                if Config.UPDATES_CHANNEL:
                    second_row.append(InlineKeyboardButton("🛠 Updates Channel", url=f"https://t.me/{Config.UPDATES_CHANNEL.lstrip('@')}"))
                second_row.append(InlineKeyboardButton("❌ Close", callback_data="close_data"))
                buttons.append(second_row)
            else:
                first_row = [InlineKeyboardButton("ℹ️ Localhost Link Note", callback_data="local_note")]
                if Config.UPDATES_CHANNEL:
                    first_row.append(InlineKeyboardButton("🛠 Updates Channel", url=f"https://t.me/{Config.UPDATES_CHANNEL.lstrip('@')}"))
                buttons.append(first_row)
                buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_data")])

        else:
            # Non-Streamable Document / APK / Archive
            reply_text = (
                "✅ **Your Download Link is Ready!**\n\n"
                f"📁 **Name:**\n"
                f"`{file_name}`\n\n"
                f"📦 **Size:** `{formatted_size}`\n"
                f"🏷 **Type:** `{category_label}`\n\n"
                f"📥 **Fast Download:**\n"
                f"{download_url}"
                f"{footer_channel}"
            )

            buttons = []
            if not is_local:
                buttons.append([InlineKeyboardButton("🚀 Download File", url=download_url)])
                second_row = []
                if Config.UPDATES_CHANNEL:
                    second_row.append(InlineKeyboardButton("🛠 Updates Channel", url=f"https://t.me/{Config.UPDATES_CHANNEL.lstrip('@')}"))
                second_row.append(InlineKeyboardButton("❌ Close", callback_data="close_data"))
                buttons.append(second_row)
            else:
                first_row = [InlineKeyboardButton("ℹ️ Localhost Link Note", callback_data="local_note")]
                if Config.UPDATES_CHANNEL:
                    first_row.append(InlineKeyboardButton("🛠 Updates Channel", url=f"https://t.me/{Config.UPDATES_CHANNEL.lstrip('@')}"))
                buttons.append(first_row)
                buttons.append([InlineKeyboardButton("❌ Close", callback_data="close_data")])

        await status_msg.edit_text(
            text=reply_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        logger.info(f"Generated link for '{file_name}' ({category}) -> Hash: {file_hash}")

    except Exception as e:
        logger.error(f"Error processing media: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ **Failed to generate stream link.**\n\n`Error: {str(e)}`"
        )
