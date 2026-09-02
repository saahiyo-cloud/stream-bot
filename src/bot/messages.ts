import { ExtractedMedia } from "./media";
import { formatBytes } from "../storage/kv";

const CATEGORY_LABELS: Record<string, string> = {
  video: "🎬 Video",
  audio: "🎵 Audio / Music",
  image: "🖼️ Image / Photo",
  apk: "📱 Android App (APK)",
  archive: "🗜️ Compressed Archive",
  pdf: "📄 PDF Document",
  software: "💻 Software / Executable",
  document: "📁 Document / File"
};

export function buildMediaCard(
  media: ExtractedMedia,
  publicBaseUrl: string,
  fileHash: string,
  updatesChannel: string
): { text: string; reply_markup: any } {
  const streamUrl = `${publicBaseUrl}/watch/${fileHash}`;
  const downloadUrl = `${publicBaseUrl}/${fileHash}`;
  const sizeFormatted = formatBytes(media.file_size);
  const categoryLabel = CATEGORY_LABELS[media.category] || "📁 File";

  const isLocal = publicBaseUrl.includes("localhost") || publicBaseUrl.includes("127.0.0.1");
  const footerChannel = updatesChannel ? `\n\n🛠 **Join ${updatesChannel} for latest updates!**` : "";

  if (media.is_streamable) {
    const text = 
`✅ **Your Links are Ready!**

📁 **Name:**
\`${media.file_name}\`

📦 **Size:** \`${sizeFormatted}\`
🏷 **Type:** \`${categoryLabel}\`

🎬 **Stream:**
${streamUrl}

📥 **Download:**
${downloadUrl}${footerChannel}`;

    const inline_keyboard: any[][] = [];

    if (!isLocal) {
      inline_keyboard.push([
        { text: "🚀 Download Now", url: downloadUrl },
        { text: "🎬 Watch Online", url: streamUrl }
      ]);
    }

    const secondRow: any[] = [];
    if (updatesChannel) {
      secondRow.push({ text: "🛠 Updates Channel", url: `https://t.me/${updatesChannel.replace("@", "")}` });
    }
    secondRow.push({ text: "❌ Close", callback_data: "close_data" });
    inline_keyboard.push(secondRow);

    return {
      text,
      reply_markup: { inline_keyboard }
    };
  } else {
    // Non-streamable APK / Archive / Document
    const text = 
`✅ **Your Download Link is Ready!**

📁 **Name:**
\`${media.file_name}\`

📦 **Size:** \`${sizeFormatted}\`
🏷 **Type:** \`${categoryLabel}\`

📥 **Direct Download:**
${downloadUrl}${footerChannel}`;

    const inline_keyboard: any[][] = [];

    if (!isLocal) {
      inline_keyboard.push([
        { text: media.category === "apk" ? "📥 Download APK" : "🚀 Download File", url: downloadUrl }
      ]);
    }

    const secondRow: any[] = [];
    if (updatesChannel) {
      secondRow.push({ text: "🛠 Updates Channel", url: `https://t.me/${updatesChannel.replace("@", "")}` });
    }
    secondRow.push({ text: "❌ Close", callback_data: "close_data" });
    inline_keyboard.push(secondRow);

    return {
      text,
      reply_markup: { inline_keyboard }
    };
  }
}

export function buildStartMessage(name: string, updatesChannel: string): { text: string; reply_markup: any } {
  const text = 
`👋 **Hello ${name}!**

⚡ I am a high-speed **Telegram File to Stream & Direct Download Link Bot** (100% Serverless on Cloudflare Edge).

📤 **Send or forward me any file, video, audio, APK, or document**, and I will instantly generate:
• 🎬 **Fast Web Video Stream Link** (with Range & Seek support)
• 📥 **Direct Download Link** (powered by Cloudflare Global CDN)

Try sending a file now!`;

  const inline_keyboard: any[][] = [];
  const row1: any[] = [];
  if (updatesChannel) {
    row1.push({ text: "🛠 Updates Channel", url: `https://t.me/${updatesChannel.replace("@", "")}` });
  }
  row1.push({ text: "📖 Help", callback_data: "help_data" });
  inline_keyboard.push(row1);
  inline_keyboard.push([{ text: "ℹ️ About", callback_data: "about_data" }]);

  return {
    text,
    reply_markup: { inline_keyboard }
  };
}

export async function callTelegramApi(botToken: string, method: string, payload: any): Promise<any> {
  const res = await fetch(`https://api.telegram.org/bot${botToken}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return await res.json();
}
