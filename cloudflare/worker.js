var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// src/bot/media.ts
var VIDEO_EXTS = /* @__PURE__ */ new Set([".mp4", ".mkv", ".webm", ".avi", ".mov", ".wmv", ".flv", ".ts", ".m4v", ".3gp", ".mpg", ".mpeg"]);
var AUDIO_EXTS = /* @__PURE__ */ new Set([".mp3", ".m4a", ".flac", ".wav", ".aac", ".opus", ".ogg", ".wma", ".mka"]);
var IMAGE_EXTS = /* @__PURE__ */ new Set([".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg", ".ico"]);
var APK_EXTS = /* @__PURE__ */ new Set([".apk", ".xapk", ".apks", ".aab"]);
var ARCHIVE_EXTS = /* @__PURE__ */ new Set([".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".tgz"]);
var DOCUMENT_EXTS = /* @__PURE__ */ new Set([".pdf", ".epub", ".mobi", ".docx", ".doc", ".xlsx", ".pptx", ".txt", ".csv", ".json"]);
var SOFTWARE_EXTS = /* @__PURE__ */ new Set([".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm"]);
function getExtension(filename) {
  const match = filename.match(/\.[0-9a-z]+$/i);
  return match ? match[0].toLowerCase() : "";
}
__name(getExtension, "getExtension");
function classifyMedia(fileName, rawMime, rawType) {
  const ext = getExtension(fileName);
  if (rawType === "video" || rawType === "animation" || VIDEO_EXTS.has(ext) || rawMime && rawMime.startsWith("video/")) {
    return {
      category: "video",
      mimeType: rawMime && rawMime.startsWith("video/") ? rawMime : "video/mp4",
      isStreamable: true
    };
  }
  if (rawType === "audio" || rawType === "voice" || AUDIO_EXTS.has(ext) || rawMime && rawMime.startsWith("audio/")) {
    return {
      category: "audio",
      mimeType: rawMime && rawMime.startsWith("audio/") ? rawMime : "audio/mpeg",
      isStreamable: true
    };
  }
  if (rawType === "photo" || IMAGE_EXTS.has(ext) || rawMime && rawMime.startsWith("image/")) {
    return {
      category: "image",
      mimeType: rawMime && rawMime.startsWith("image/") ? rawMime : "image/jpeg",
      isStreamable: true
    };
  }
  if (APK_EXTS.has(ext) || rawMime && rawMime.includes("android.package-archive")) {
    return {
      category: "apk",
      mimeType: "application/vnd.android.package-archive",
      isStreamable: false
    };
  }
  if (ARCHIVE_EXTS.has(ext) || rawMime && (rawMime.includes("zip") || rawMime.includes("rar") || rawMime.includes("tar"))) {
    return {
      category: "archive",
      mimeType: rawMime || "application/zip",
      isStreamable: false
    };
  }
  if (ext === ".pdf" || rawMime && rawMime.includes("pdf")) {
    return {
      category: "pdf",
      mimeType: "application/pdf",
      isStreamable: false
    };
  }
  if (DOCUMENT_EXTS.has(ext)) {
    return {
      category: "document",
      mimeType: rawMime || "application/octet-stream",
      isStreamable: false
    };
  }
  if (SOFTWARE_EXTS.has(ext)) {
    return {
      category: "software",
      mimeType: "application/octet-stream",
      isStreamable: false
    };
  }
  return {
    category: "document",
    mimeType: rawMime || "application/octet-stream",
    isStreamable: false
  };
}
__name(classifyMedia, "classifyMedia");
function extractMediaFromTelegramMessage(message) {
  let mediaObj = null;
  let rawType = "document";
  if (message.document) {
    mediaObj = message.document;
    rawType = "document";
  } else if (message.video) {
    mediaObj = message.video;
    rawType = "video";
  } else if (message.audio) {
    mediaObj = message.audio;
    rawType = "audio";
  } else if (message.animation) {
    mediaObj = message.animation;
    rawType = "animation";
  } else if (message.voice) {
    mediaObj = message.voice;
    rawType = "voice";
  } else if (message.photo && Array.isArray(message.photo)) {
    mediaObj = message.photo[message.photo.length - 1];
    rawType = "photo";
  }
  if (!mediaObj)
    return null;
  let fileName = mediaObj.file_name;
  if (!fileName) {
    if (rawType === "photo")
      fileName = `photo_${message.message_id}.jpg`;
    else if (rawType === "video")
      fileName = `video_${message.message_id}.mp4`;
    else if (rawType === "audio")
      fileName = `audio_${message.message_id}.mp3`;
    else if (rawType === "animation")
      fileName = `animation_${message.message_id}.mp4`;
    else if (rawType === "voice")
      fileName = `voice_${message.message_id}.ogg`;
    else
      fileName = `file_${message.message_id}`;
  }
  const fileSize = mediaObj.file_size || 0;
  const rawMime = mediaObj.mime_type || "";
  const fileUniqueId = mediaObj.file_unique_id || String(message.message_id);
  const fileId = mediaObj.file_id;
  const { category, mimeType, isStreamable } = classifyMedia(fileName, rawMime, rawType);
  return {
    file_id: fileId,
    file_unique_id: fileUniqueId,
    file_name: fileName,
    file_size: fileSize,
    mime_type: mimeType,
    category,
    is_streamable: isStreamable
  };
}
__name(extractMediaFromTelegramMessage, "extractMediaFromTelegramMessage");

// src/storage/kv.ts
var memoryStore = /* @__PURE__ */ new Map();
function generateFileHash(messageId, prefix = "stream-") {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let entropy = "";
  for (let i = 0; i < 12; i++) {
    entropy += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return `${prefix}${entropy}${messageId}`;
}
__name(generateFileHash, "generateFileHash");
async function saveFile(env, fileHash, data) {
  if (env.STREAM_KV) {
    await env.STREAM_KV.put(fileHash, JSON.stringify(data), {
      // Retain files for 1 year (expiration in seconds)
      expirationTtl: 31536e3
    });
  } else {
    memoryStore.set(fileHash, data);
  }
}
__name(saveFile, "saveFile");
async function getFile(env, fileHash) {
  if (env.STREAM_KV) {
    const raw = await env.STREAM_KV.get(fileHash, "json");
    return raw;
  }
  return memoryStore.get(fileHash) || null;
}
__name(getFile, "getFile");
async function incrementViews(env, fileHash, fileData) {
  fileData.views = (fileData.views || 0) + 1;
  await saveFile(env, fileHash, fileData);
}
__name(incrementViews, "incrementViews");
async function incrementDownloads(env, fileHash, fileData) {
  fileData.downloads = (fileData.downloads || 0) + 1;
  await saveFile(env, fileHash, fileData);
}
__name(incrementDownloads, "incrementDownloads");
function formatBytes(bytes) {
  if (bytes === 0)
    return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}
__name(formatBytes, "formatBytes");

// src/bot/messages.ts
var CATEGORY_LABELS = {
  video: "\u{1F3AC} Video",
  audio: "\u{1F3B5} Audio / Music",
  image: "\u{1F5BC}\uFE0F Image / Photo",
  apk: "\u{1F4F1} Android App (APK)",
  archive: "\u{1F5DC}\uFE0F Compressed Archive",
  pdf: "\u{1F4C4} PDF Document",
  software: "\u{1F4BB} Software / Executable",
  document: "\u{1F4C1} Document / File"
};
function buildMediaCard(media, publicBaseUrl, fileHash, updatesChannel) {
  const streamUrl = `${publicBaseUrl}/watch/${fileHash}`;
  const downloadUrl = `${publicBaseUrl}/${fileHash}`;
  const sizeFormatted = formatBytes(media.file_size);
  const categoryLabel = CATEGORY_LABELS[media.category] || "\u{1F4C1} File";
  const isLocal = publicBaseUrl.includes("localhost") || publicBaseUrl.includes("127.0.0.1");
  const footerChannel = updatesChannel ? `

\u{1F6E0} **Join ${updatesChannel} for latest updates!**` : "";
  if (media.is_streamable) {
    const text = `\u2705 **Your Links are Ready!**

\u{1F4C1} **Name:**
\`${media.file_name}\`

\u{1F4E6} **Size:** \`${sizeFormatted}\`
\u{1F3F7} **Type:** \`${categoryLabel}\`

\u{1F3AC} **Stream:**
${streamUrl}

\u{1F4E5} **Download:**
${downloadUrl}${footerChannel}`;
    const inline_keyboard = [];
    if (!isLocal) {
      inline_keyboard.push([
        { text: "\u{1F680} Download Now", url: downloadUrl },
        { text: "\u{1F3AC} Watch Online", url: streamUrl }
      ]);
    }
    const secondRow = [];
    if (updatesChannel) {
      secondRow.push({ text: "\u{1F6E0} Updates Channel", url: `https://t.me/${updatesChannel.replace("@", "")}` });
    }
    secondRow.push({ text: "\u274C Close", callback_data: "close_data" });
    inline_keyboard.push(secondRow);
    return {
      text,
      reply_markup: { inline_keyboard }
    };
  } else {
    const text = `\u2705 **Your Download Link is Ready!**

\u{1F4C1} **Name:**
\`${media.file_name}\`

\u{1F4E6} **Size:** \`${sizeFormatted}\`
\u{1F3F7} **Type:** \`${categoryLabel}\`

\u{1F4E5} **Direct Download:**
${downloadUrl}${footerChannel}`;
    const inline_keyboard = [];
    if (!isLocal) {
      inline_keyboard.push([
        { text: media.category === "apk" ? "\u{1F4E5} Download APK" : "\u{1F680} Download File", url: downloadUrl }
      ]);
    }
    const secondRow = [];
    if (updatesChannel) {
      secondRow.push({ text: "\u{1F6E0} Updates Channel", url: `https://t.me/${updatesChannel.replace("@", "")}` });
    }
    secondRow.push({ text: "\u274C Close", callback_data: "close_data" });
    inline_keyboard.push(secondRow);
    return {
      text,
      reply_markup: { inline_keyboard }
    };
  }
}
__name(buildMediaCard, "buildMediaCard");
function buildStartMessage(name, updatesChannel) {
  const text = `\u{1F44B} **Hello ${name}!**

\u26A1 I am a high-speed **Telegram File to Stream & Direct Download Link Bot** (100% Serverless on Cloudflare Edge).

\u{1F4E4} **Send or forward me any file, video, audio, APK, or document**, and I will instantly generate:
\u2022 \u{1F3AC} **Fast Web Video Stream Link** (with Range & Seek support)
\u2022 \u{1F4E5} **Direct Download Link** (powered by Cloudflare Global CDN)

Try sending a file now!`;
  const inline_keyboard = [];
  const row1 = [];
  if (updatesChannel) {
    row1.push({ text: "\u{1F6E0} Updates Channel", url: `https://t.me/${updatesChannel.replace("@", "")}` });
  }
  row1.push({ text: "\u{1F4D6} Help", callback_data: "help_data" });
  inline_keyboard.push(row1);
  inline_keyboard.push([{ text: "\u2139\uFE0F About", callback_data: "about_data" }]);
  return {
    text,
    reply_markup: { inline_keyboard }
  };
}
__name(buildStartMessage, "buildStartMessage");
async function callTelegramApi(botToken, method, payload) {
  const res = await fetch(`https://api.telegram.org/bot${botToken}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return await res.json();
}
__name(callTelegramApi, "callTelegramApi");

// src/bot/webhook.ts
async function handleTelegramWebhook(request, env) {
  const update = await request.json();
  const botToken = env.BOT_TOKEN;
  const updatesChannel = (env.UPDATES_CHANNEL || "").trim();
  const hashPrefix = env.HASH_PREFIX || "stream-";
  const url = new URL(request.url);
  const publicBaseUrl = url.origin;
  if (update.message) {
    const msg = update.message;
    const chatId = msg.chat.id;
    const text = (msg.text || "").trim();
    if (text === "/start" || text.startsWith("/start ")) {
      const firstName = msg.from ? msg.from.first_name : "there";
      const reply = buildStartMessage(firstName, updatesChannel);
      await callTelegramApi(botToken, "sendMessage", {
        chat_id: chatId,
        text: reply.text,
        parse_mode: "Markdown",
        reply_markup: reply.reply_markup
      });
      return new Response("OK");
    }
    if (text === "/help") {
      const helpText = `\u{1F4D6} **How to Use This Bot:**

1. **Send or forward any media** (Video, Document, Audio, APK, Photo) to this bot.
2. The bot will automatically generate an ultra-fast streaming & direct download link.
3. Open the link to stream live in browser/VLC or download with 1-click!

\u26A1 **Features:**
\u2022 100% Serverless on Cloudflare Edge
\u2022 Video seek & scrub support (HTTP 206 Partial Content)
\u2022 Fast global CDN downloads`;
      await callTelegramApi(botToken, "sendMessage", {
        chat_id: chatId,
        text: helpText,
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [[{ text: "\u{1F519} Back", callback_data: "start_data" }]]
        }
      });
      return new Response("OK");
    }
    const media = extractMediaFromTelegramMessage(msg);
    if (media) {
      const statusMsg = await callTelegramApi(botToken, "sendMessage", {
        chat_id: chatId,
        text: "\u26A1 **Generating ultra-fast link on Cloudflare Edge...**",
        parse_mode: "Markdown",
        reply_to_message_id: msg.message_id
      });
      try {
        let storageFileId = media.file_id;
        if (env.BIN_CHANNEL && env.BIN_CHANNEL !== "0") {
          try {
            const forwarded = await callTelegramApi(botToken, "forwardMessage", {
              chat_id: env.BIN_CHANNEL,
              from_chat_id: chatId,
              message_id: msg.message_id
            });
            if (forwarded && forwarded.result) {
              const fMedia = extractMediaFromTelegramMessage(forwarded.result);
              if (fMedia)
                storageFileId = fMedia.file_id;
            }
          } catch (err) {
            console.warn("Could not forward to BIN_CHANNEL:", err);
          }
        }
        const fileHash = generateFileHash(msg.message_id, hashPrefix);
        await saveFile(env, fileHash, {
          file_id: storageFileId,
          file_unique_id: media.file_unique_id,
          file_name: media.file_name,
          file_size: media.file_size,
          mime_type: media.mime_type,
          category: media.category,
          is_streamable: media.is_streamable,
          user_id: msg.from ? msg.from.id : chatId,
          created_at: Math.floor(Date.now() / 1e3),
          views: 0,
          downloads: 0
        });
        const card = buildMediaCard(media, publicBaseUrl, fileHash, updatesChannel);
        if (statusMsg && statusMsg.result) {
          await callTelegramApi(botToken, "editMessageText", {
            chat_id: chatId,
            message_id: statusMsg.result.message_id,
            text: card.text,
            parse_mode: "Markdown",
            reply_markup: card.reply_markup,
            disable_web_page_preview: true
          });
        }
      } catch (err) {
        console.error("Error processing media webhook:", err);
        if (statusMsg && statusMsg.result) {
          await callTelegramApi(botToken, "editMessageText", {
            chat_id: chatId,
            message_id: statusMsg.result.message_id,
            text: `\u274C **Failed to generate link.**

\`Error: ${err.message || err}\``,
            parse_mode: "Markdown"
          });
        }
      }
      return new Response("OK");
    }
  }
  if (update.callback_query) {
    const cb = update.callback_query;
    const data = cb.data;
    const chatId = cb.message ? cb.message.chat.id : cb.from.id;
    const messageId = cb.message ? cb.message.message_id : void 0;
    if (data === "start_data" && messageId) {
      const reply = buildStartMessage(cb.from.first_name || "there", updatesChannel);
      await callTelegramApi(botToken, "editMessageText", {
        chat_id: chatId,
        message_id: messageId,
        text: reply.text,
        parse_mode: "Markdown",
        reply_markup: reply.reply_markup
      });
    } else if (data === "help_data" && messageId) {
      const helpText = `\u{1F4D6} **How to Use This Bot:**

1. **Send or forward any media** (Video, Document, Audio, APK, Photo) to this bot.
2. The bot will automatically generate an ultra-fast streaming & direct download link.
3. Open the link to stream live in browser/VLC or download with 1-click!`;
      await callTelegramApi(botToken, "editMessageText", {
        chat_id: chatId,
        message_id: messageId,
        text: helpText,
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [[{ text: "\u{1F519} Back", callback_data: "start_data" }]]
        }
      });
    } else if (data === "about_data" && messageId) {
      const aboutText = `\u2139\uFE0F **About This Bot:**

\u2022 **Name:** High-Speed Stream & Download Bot \u26A1
\u2022 **Architecture:** 100% Serverless on Cloudflare Edge
\u2022 **Streaming:** HTTP 206 Partial Content (Byte-Range Seeking)
\u2022 **CDN:** Cloudflare Global Edge Network (300+ Cities)`;
      await callTelegramApi(botToken, "editMessageText", {
        chat_id: chatId,
        message_id: messageId,
        text: aboutText,
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [[{ text: "\u{1F519} Back", callback_data: "start_data" }]]
        }
      });
    } else if (data === "close_data" && messageId) {
      await callTelegramApi(botToken, "deleteMessage", {
        chat_id: chatId,
        message_id: messageId
      });
    }
    await callTelegramApi(botToken, "answerCallbackQuery", {
      callback_query_id: cb.id
    });
    return new Response("OK");
  }
  return new Response("OK");
}
__name(handleTelegramWebhook, "handleTelegramWebhook");

// src/streaming/range.ts
function parseRangeHeader(rangeHeader, fileSize) {
  if (!rangeHeader || !rangeHeader.startsWith("bytes=")) {
    return { start: 0, end: fileSize - 1, isRange: false };
  }
  const parts = rangeHeader.replace("bytes=", "").trim().split("-");
  if (parts.length !== 2) {
    return { start: 0, end: fileSize - 1, isRange: false };
  }
  const startStr = parts[0].trim();
  const endStr = parts[1].trim();
  let start = 0;
  let end = fileSize - 1;
  if (startStr && endStr) {
    start = parseInt(startStr, 10);
    end = Math.min(parseInt(endStr, 10), fileSize - 1);
  } else if (startStr) {
    start = parseInt(startStr, 10);
    end = fileSize - 1;
  } else if (endStr) {
    const length = parseInt(endStr, 10);
    start = Math.max(0, fileSize - length);
    end = fileSize - 1;
  }
  start = Math.max(0, Math.min(start, fileSize - 1));
  end = Math.max(start, Math.min(end, fileSize - 1));
  return { start, end, isRange: true };
}
__name(parseRangeHeader, "parseRangeHeader");

// src/streaming/streamer.ts
async function handleFileStreaming(request, fileData, fileHash, env) {
  const botToken = env.BOT_TOKEN;
  const fileId = fileData.file_id;
  const getFileRes = await fetch(`https://api.telegram.org/bot${botToken}/getFile?file_id=${fileId}`);
  const getFileData = await getFileRes.json();
  if (!getFileData.ok || !getFileData.result || !getFileData.result.file_path) {
    return new Response(JSON.stringify({
      error: "Failed to resolve Telegram file path",
      details: getFileData.description || "Unknown error"
    }, null, 2), {
      status: 404,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
    });
  }
  const filePath = getFileData.result.file_path;
  const telegramDownloadUrl = `https://api.telegram.org/file/bot${botToken}/${filePath}`;
  const fileSize = fileData.file_size || getFileData.result.file_size || 0;
  const rangeHeader = request.headers.get("Range");
  const { start, end, isRange } = parseRangeHeader(rangeHeader, fileSize);
  const contentLength = end - start + 1;
  const fetchHeaders = new Headers();
  if (isRange && fileSize > 0) {
    fetchHeaders.set("Range", `bytes=${start}-${end}`);
  }
  const tgResponse = await fetch(telegramDownloadUrl, {
    method: request.method,
    headers: fetchHeaders
  });
  if (start === 0) {
    await incrementDownloads(env, fileHash, fileData);
  }
  const clientHeaders = new Headers();
  clientHeaders.set("Content-Type", fileData.mime_type || "application/octet-stream");
  clientHeaders.set("Accept-Ranges", "bytes");
  clientHeaders.set("Access-Control-Allow-Origin", "*");
  clientHeaders.set("Access-Control-Allow-Headers", "Range, Content-Type");
  clientHeaders.set("Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges, Content-Disposition");
  clientHeaders.set("Cache-Control", "public, max-age=86400");
  clientHeaders.set("X-Served-By", "Cloudflare-Edge-Streamer");
  const url = new URL(request.url);
  const isStream = url.searchParams.get("stream") === "1" || isRange || fileData.is_streamable;
  const disposition = isStream ? "inline" : "attachment";
  const safeFilename = encodeURIComponent(fileData.file_name);
  clientHeaders.set("Content-Disposition", `${disposition}; filename="${fileData.file_name}"; filename*=UTF-8''${safeFilename}`);
  if (fileSize > 0) {
    clientHeaders.set("Content-Length", String(contentLength));
  }
  let statusCode = tgResponse.status;
  if (isRange && fileSize > 0) {
    clientHeaders.set("Content-Range", `bytes ${start}-${end}/${fileSize}`);
    statusCode = 206;
  }
  return new Response(tgResponse.body, {
    status: statusCode,
    headers: clientHeaders
  });
}
__name(handleFileStreaming, "handleFileStreaming");

// src/views/player.ts
function renderPlayerHtml(fileData, fileHash, publicBaseUrl, updatesChannel) {
  const fileName = fileData.file_name || `file_${fileHash}`;
  const formattedSize = formatBytes(fileData.file_size);
  const mimeType = fileData.mime_type || "application/octet-stream";
  const rawStreamUrl = `${publicBaseUrl}/${fileHash}?stream=1`;
  const downloadUrl = `${publicBaseUrl}/${fileHash}`;
  const category = fileData.category;
  const channelBtnHtml = updatesChannel ? `<a href="https://t.me/${updatesChannel.replace("@", "")}" target="_blank" class="channel-btn">
         <span>\u{1F6E0} ${updatesChannel}</span>
       </a>` : "";
  let mediaDisplayHtml = "";
  if (category === "image" || mimeType.startsWith("image/")) {
    mediaDisplayHtml = `<img src="${rawStreamUrl}" alt="${fileName}" class="image-preview" loading="lazy" />`;
  } else if (category === "audio" || mimeType.startsWith("audio/")) {
    mediaDisplayHtml = `
      <div class="audio-wrapper">
        <div class="audio-icon">\u{1F3B5}</div>
        <audio id="player" playsinline controls preload="metadata">
          <source src="${rawStreamUrl}" type="${mimeType}">
          Your browser does not support audio playback.
        </audio>
      </div>`;
  } else if (category === "video" || mimeType.startsWith("video/")) {
    mediaDisplayHtml = `
      <video id="player" playsinline controls preload="metadata">
        <source src="${rawStreamUrl}" type="${mimeType}">
        Your browser does not support HTML5 video streaming.
      </video>`;
  } else if (category === "apk" || mimeType.includes("android.package-archive") || fileName.endsWith(".apk")) {
    mediaDisplayHtml = `
      <div class="document-wrapper">
        <div class="document-icon-box icon-apk">\u{1F916}</div>
        <div class="doc-title">${fileName}</div>
        <div class="doc-subtitle">Android Application Package (APK) \u2022 Direct Cloudflare Edge Download</div>
      </div>`;
  } else if (category === "archive") {
    mediaDisplayHtml = `
      <div class="document-wrapper">
        <div class="document-icon-box icon-archive">\u{1F5DC}\uFE0F</div>
        <div class="doc-title">${fileName}</div>
        <div class="doc-subtitle">Compressed Archive \u2022 Direct Cloudflare Edge Download</div>
      </div>`;
  } else {
    mediaDisplayHtml = `
      <div class="document-wrapper">
        <div class="document-icon-box icon-doc">\u{1F4C4}</div>
        <div class="doc-title">${fileName}</div>
        <div class="doc-subtitle">Document / File \u2022 Direct Cloudflare Edge Download</div>
      </div>`;
  }
  const isApk = category === "apk" || fileName.endsWith(".apk");
  const mainBtnClass = isApk ? "btn-apk" : "btn-primary";
  const mainBtnText = isApk ? `\u{1F4E5} Download APK (${formattedSize})` : "\u{1F680} Download Now";
  const vlcBtnHtml = category === "video" || category === "audio" ? `<a href="vlc://${rawStreamUrl}" class="btn btn-vlc"><span>\u{1F4FA} Open in VLC</span></a>` : "";
  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${fileName} - Stream Bot \u26A1</title>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />

    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-card: rgba(18, 24, 38, 0.85);
            --border-color: rgba(255, 255, 255, 0.08);
            --accent: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.35);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --apk-color: #22c55e;
            --apk-glow: rgba(34, 197, 94, 0.35);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        body {
            background-color: var(--bg-primary);
            background-image: 
                radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.12) 0px, transparent 50%);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 24px 16px;
        }

        .container {
            width: 100%;
            max-width: 960px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 14px 24px;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 700;
            font-size: 1.25rem;
            color: var(--text-primary);
            text-decoration: none;
        }

        .brand-icon {
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            border-radius: 10px;
            width: 34px;
            height: 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            box-shadow: 0 4px 12px var(--accent-glow);
        }

        .channel-btn {
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 10px;
            padding: 8px 16px;
            font-size: 0.9rem;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.2s ease;
        }

        .channel-btn:hover {
            background: rgba(59, 130, 246, 0.25);
            transform: translateY(-1px);
        }

        .media-wrapper {
            width: 100%;
            background: #000;
            border-radius: 20px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.6);
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .image-preview {
            max-width: 100%;
            max-height: 70vh;
            object-fit: contain;
            border-radius: 20px;
            background: #000;
        }

        .document-wrapper {
            width: 100%;
            padding: 60px 24px;
            background: var(--bg-card);
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            gap: 20px;
        }

        .document-icon-box {
            width: 100px;
            height: 100px;
            border-radius: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3.5rem;
        }

        .icon-apk {
            background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(16, 185, 129, 0.3));
            border: 1px solid rgba(34, 197, 94, 0.4);
            box-shadow: 0 10px 25px var(--apk-glow);
        }

        .icon-archive {
            background: linear-gradient(135deg, rgba(234, 179, 8, 0.2), rgba(249, 115, 22, 0.3));
            border: 1px solid rgba(234, 179, 8, 0.4);
        }

        .icon-doc {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.3));
            border: 1px solid rgba(59, 130, 246, 0.4);
        }

        .doc-title {
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--text-primary);
            max-width: 80%;
            word-break: break-word;
        }

        .doc-subtitle {
            color: var(--text-secondary);
            font-size: 0.95rem;
        }

        .audio-wrapper {
            width: 100%;
            padding: 40px 24px;
            background: var(--bg-card);
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
        }

        .audio-icon {
            font-size: 3rem;
            background: rgba(59, 130, 246, 0.15);
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .plyr {
            width: 100%;
            border-radius: 20px;
            --plyr-color-main: #3b82f6;
        }

        .info-card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 18px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 18px;
        }

        .file-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            flex-wrap: wrap;
        }

        .file-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
            word-break: break-word;
            line-height: 1.4;
        }

        .meta-badges {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
        }

        .badge {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 0.82rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .badge-size {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border-color: rgba(16, 185, 129, 0.25);
        }

        .badge-apk {
            background: rgba(34, 197, 94, 0.15);
            color: #4ade80;
            border-color: rgba(34, 197, 94, 0.25);
        }

        .actions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
        }

        .btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 20px;
            border-radius: 12px;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s ease;
            border: none;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--accent), #2563eb);
            color: #fff;
            box-shadow: 0 4px 14px var(--accent-glow);
        }

        .btn-apk {
            background: linear-gradient(135deg, #16a34a, #15803d);
            color: #fff;
            box-shadow: 0 4px 14px var(--apk-glow);
        }

        .btn-primary:hover, .btn-apk:hover {
            opacity: 0.95;
            transform: translateY(-2px);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateY(-2px);
        }

        .btn-vlc {
            background: rgba(249, 115, 22, 0.15);
            border: 1px solid rgba(249, 115, 22, 0.3);
            color: #fb923c;
        }

        .btn-vlc:hover {
            background: rgba(249, 115, 22, 0.25);
            transform: translateY(-2px);
        }

        .footer {
            margin-top: auto;
            padding-top: 24px;
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .footer a {
            color: #60a5fa;
            text-decoration: none;
        }

        .toast {
            position: fixed;
            bottom: 24px;
            background: #10b981;
            color: #fff;
            padding: 10px 20px;
            border-radius: 10px;
            font-weight: 500;
            box-shadow: 0 6px 16px rgba(0,0,0,0.3);
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            z-index: 100;
        }
        .toast.show {
            opacity: 1;
        }
    </style>
</head>
<body>
    <div class="container">
        <nav class="navbar">
            <a href="/" class="brand">
                <span class="brand-icon">\u26A1</span>
                <span>Stream Bot</span>
            </a>
            ${channelBtnHtml}
        </nav>

        <div class="media-wrapper">
            ${mediaDisplayHtml}
        </div>

        <div class="info-card">
            <div class="file-header">
                <div>
                    <h1 class="file-title">${fileName}</h1>
                    <div class="meta-badges">
                        <span class="badge badge-size">\u{1F4E6} ${formattedSize}</span>
                        ${isApk ? '<span class="badge badge-apk">\u{1F4F1} Android App</span>' : `<span class="badge">${mimeType}</span>`}
                    </div>
                </div>
            </div>

            <div class="actions-grid">
                <a href="${downloadUrl}" class="btn ${mainBtnClass}" download>
                    <span>${mainBtnText}</span>
                </a>
                <button onclick="copyLink()" class="btn btn-secondary">
                    <span>\u{1F4CB} Copy Link</span>
                </button>
                ${vlcBtnHtml}
            </div>
        </div>

        <div class="footer">
            Powered by <strong>Stream Bot \u26A1</strong> | 100% Serverless Cloudflare Edge Streaming
        </div>
    </div>

    <div id="toast" class="toast">Link copied to clipboard!</div>

    <script src="https://cdn.plyr.io/3.7.8/plyr.js"><\/script>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const playerElem = document.querySelector('#player');
            if (playerElem) {
                new Plyr(playerElem, {
                    controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'mute', 'volume', 'captions', 'settings', 'pip', 'airplay', 'fullscreen'],
                    seekTime: 10,
                    speed: { selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] }
                });
            }
        });

        function copyLink() {
            navigator.clipboard.writeText("${downloadUrl}").then(() => {
                const toast = document.getElementById('toast');
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 2000);
            });
        }
    <\/script>
</body>
</html>`;
}
__name(renderPlayerHtml, "renderPlayerHtml");

// src/index.ts
var src_default = {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;
    const botToken = env.BOT_TOKEN;
    const updatesChannel = (env.UPDATES_CHANNEL || "").trim();
    if (path === "/webhook" && request.method === "POST") {
      return await handleTelegramWebhook(request, env);
    }
    if (path === "/setWebhook" && request.method === "GET") {
      const webhookUrl = `${url.origin}/webhook`;
      const tgRes = await fetch(`https://api.telegram.org/bot${botToken}/setWebhook?url=${encodeURIComponent(webhookUrl)}`);
      const result = await tgRes.json();
      return new Response(JSON.stringify({
        status: result.ok ? "Success" : "Failed",
        webhookUrl,
        telegram_response: result
      }, null, 2), {
        status: result.ok ? 200 : 500,
        headers: { "Content-Type": "application/json" }
      });
    }
    if (path === "/deleteWebhook" && request.method === "GET") {
      const tgRes = await fetch(`https://api.telegram.org/bot${botToken}/deleteWebhook`);
      const result = await tgRes.json();
      return new Response(JSON.stringify(result, null, 2), {
        headers: { "Content-Type": "application/json" }
      });
    }
    const watchMatch = path.match(/^\/watch\/([a-zA-Z0-9_-]+)$/);
    if (watchMatch && request.method === "GET") {
      const fileHash = watchMatch[1];
      const fileData = await getFile(env, fileHash);
      if (!fileData) {
        return new Response(`
          <!DOCTYPE html>
          <html>
          <head><title>File Not Found</title></head>
          <body style="background:#0b0f19;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
            <div style="text-align:center;">
              <h1 style="font-size:3rem;margin-bottom:10px;">404</h1>
              <p style="color:#94a3b8;">This file link has expired or does not exist.</p>
              <a href="/" style="color:#3b82f6;text-decoration:none;">Go Home</a>
            </div>
          </body>
          </html>
        `, {
          status: 404,
          headers: { "Content-Type": "text/html; charset=utf-8" }
        });
      }
      await incrementViews(env, fileHash, fileData);
      const html = renderPlayerHtml(fileData, fileHash, url.origin, updatesChannel);
      return new Response(html, {
        status: 200,
        headers: { "Content-Type": "text/html; charset=utf-8" }
      });
    }
    const fileMatch = path.match(/^\/([a-zA-Z0-9_-]+)$/);
    if (fileMatch && !["favicon.ico", "status", "webhook", "setWebhook", "deleteWebhook"].includes(fileMatch[1])) {
      const fileHash = fileMatch[1];
      const fileData = await getFile(env, fileHash);
      if (!fileData) {
        return new Response(JSON.stringify({
          error: "File Not Found",
          message: "The requested file hash does not exist or has expired."
        }, null, 2), {
          status: 404,
          headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
        });
      }
      return await handleFileStreaming(request, fileData, fileHash, env);
    }
    if (path === "/" || path === "/status") {
      return new Response(JSON.stringify({
        status: "Online \u26A1",
        name: "Stream Bot (100% Serverless Cloudflare Edge)",
        version: "2.0.0",
        edge_datacenter: request.cf?.colo || "Global",
        bot_configured: Boolean(botToken),
        kv_storage: Boolean(env.STREAM_KV),
        features: [
          "Telegram Webhook Handler (POST /webhook)",
          "1-Click Webhook Registration (GET /setWebhook)",
          "Live Video Player with Scrubbing (GET /watch/:hash)",
          "HTTP 206 Partial Content Direct Stream (GET /:hash)",
          "Android APK & Compressed Archive Download Hubs",
          "DDoS Protection & Global CDN Caching"
        ]
      }, null, 2), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*"
        }
      });
    }
    return new Response("Not Found", { status: 404 });
  }
};
export {
  src_default as default
};
//# sourceMappingURL=index.js.map
