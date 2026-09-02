import { extractMediaFromTelegramMessage } from "./media";
import { buildMediaCard, buildStartMessage, callTelegramApi } from "./messages";
import { saveFile, generateFileHash } from "../storage/kv";

export async function handleTelegramWebhook(
  request: Request,
  env: {
    BOT_TOKEN: string;
    STREAM_KV?: KVNamespace;
    BIN_CHANNEL?: string;
    UPDATES_CHANNEL?: string;
    HASH_PREFIX?: string;
  }
): Promise<Response> {
  const update: any = await request.json();
  const botToken = env.BOT_TOKEN;
  const updatesChannel = (env.UPDATES_CHANNEL || "").trim();
  const hashPrefix = env.HASH_PREFIX || "stream-";
  const url = new URL(request.url);
  const publicBaseUrl = url.origin;

  // 1. Handle Message Updates
  if (update.message) {
    const msg = update.message;
    const chatId = msg.chat.id;
    const text = (msg.text || "").trim();

    // /start command
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

    // /help command
    if (text === "/help") {
      const helpText = 
`📖 **How to Use This Bot:**

1. **Send or forward any media** (Video, Document, Audio, APK, Photo) to this bot.
2. The bot will automatically generate an ultra-fast streaming & direct download link.
3. Open the link to stream live in browser/VLC or download with 1-click!

⚡ **Features:**
• 100% Serverless on Cloudflare Edge
• Video seek & scrub support (HTTP 206 Partial Content)
• Fast global CDN downloads`;

      await callTelegramApi(botToken, "sendMessage", {
        chat_id: chatId,
        text: helpText,
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [[{ text: "🔙 Back", callback_data: "start_data" }]]
        }
      });
      return new Response("OK");
    }

    // Media file processing
    const media = extractMediaFromTelegramMessage(msg);
    if (media) {
      // Send temporary status indicator
      const statusMsg = await callTelegramApi(botToken, "sendMessage", {
        chat_id: chatId,
        text: "⚡ **Generating ultra-fast link on Cloudflare Edge...**",
        parse_mode: "Markdown",
        reply_to_message_id: msg.message_id
      });

      try {
        let storageFileId = media.file_id;

        // Optionally forward to BIN_CHANNEL if configured
        if (env.BIN_CHANNEL && env.BIN_CHANNEL !== "0") {
          try {
            const forwarded = await callTelegramApi(botToken, "forwardMessage", {
              chat_id: env.BIN_CHANNEL,
              from_chat_id: chatId,
              message_id: msg.message_id
            });
            if (forwarded && forwarded.result) {
              const fMedia = extractMediaFromTelegramMessage(forwarded.result);
              if (fMedia) storageFileId = fMedia.file_id;
            }
          } catch (err) {
            console.warn("Could not forward to BIN_CHANNEL:", err);
          }
        }

        const fileHash = generateFileHash(msg.message_id, hashPrefix);

        // Save metadata into Cloudflare KV
        await saveFile(env, fileHash, {
          file_id: storageFileId,
          file_unique_id: media.file_unique_id,
          file_name: media.file_name,
          file_size: media.file_size,
          mime_type: media.mime_type,
          category: media.category,
          is_streamable: media.is_streamable,
          user_id: msg.from ? msg.from.id : chatId,
          created_at: Math.floor(Date.now() / 1000),
          views: 0,
          downloads: 0
        });

        // Build rich reply card
        const card = buildMediaCard(media, publicBaseUrl, fileHash, updatesChannel);

        // Edit status message with complete result
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
      } catch (err: any) {
        console.error("Error processing media webhook:", err);
        if (statusMsg && statusMsg.result) {
          await callTelegramApi(botToken, "editMessageText", {
            chat_id: chatId,
            message_id: statusMsg.result.message_id,
            text: `❌ **Failed to generate link.**\n\n\`Error: ${err.message || err}\``,
            parse_mode: "Markdown"
          });
        }
      }
      return new Response("OK");
    }
  }

  // 2. Handle Callback Queries
  if (update.callback_query) {
    const cb = update.callback_query;
    const data = cb.data;
    const chatId = cb.message ? cb.message.chat.id : cb.from.id;
    const messageId = cb.message ? cb.message.message_id : undefined;

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
      const helpText = 
`📖 **How to Use This Bot:**

1. **Send or forward any media** (Video, Document, Audio, APK, Photo) to this bot.
2. The bot will automatically generate an ultra-fast streaming & direct download link.
3. Open the link to stream live in browser/VLC or download with 1-click!`;

      await callTelegramApi(botToken, "editMessageText", {
        chat_id: chatId,
        message_id: messageId,
        text: helpText,
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [[{ text: "🔙 Back", callback_data: "start_data" }]]
        }
      });
    } else if (data === "about_data" && messageId) {
      const aboutText = 
`ℹ️ **About This Bot:**

• **Name:** High-Speed Stream & Download Bot ⚡
• **Architecture:** 100% Serverless on Cloudflare Edge
• **Streaming:** HTTP 206 Partial Content (Byte-Range Seeking)
• **CDN:** Cloudflare Global Edge Network (300+ Cities)`;

      await callTelegramApi(botToken, "editMessageText", {
        chat_id: chatId,
        message_id: messageId,
        text: aboutText,
        parse_mode: "Markdown",
        reply_markup: {
          inline_keyboard: [[{ text: "🔙 Back", callback_data: "start_data" }]]
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
