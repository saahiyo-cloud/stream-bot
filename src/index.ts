import { handleTelegramWebhook } from "./bot/webhook";
import { getFile, incrementViews } from "./storage/kv";
import { handleFileStreaming } from "./streaming/streamer";
import { renderPlayerHtml } from "./views/player";

export interface Env {
  BOT_TOKEN: string;
  API_ID?: string;
  API_HASH?: string;
  BIN_CHANNEL?: string;
  UPDATES_CHANNEL?: string;
  HASH_PREFIX?: string;
  STREAM_KV?: KVNamespace;
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const botToken = env.BOT_TOKEN;
    const updatesChannel = (env.UPDATES_CHANNEL || "").trim();

    // 1. Telegram Webhook Endpoint
    if (path === "/webhook" && request.method === "POST") {
      return await handleTelegramWebhook(request, env);
    }

    // 2. 1-Click Telegram Webhook Auto-Setter
    if (path === "/setWebhook" && request.method === "GET") {
      const webhookUrl = `${url.origin}/webhook`;
      const tgRes = await fetch(`https://api.telegram.org/bot${botToken}/setWebhook?url=${encodeURIComponent(webhookUrl)}`);
      const result: any = await tgRes.json();
      return new Response(JSON.stringify({
        status: result.ok ? "Success" : "Failed",
        webhookUrl,
        telegram_response: result
      }, null, 2), {
        status: result.ok ? 200 : 500,
        headers: { "Content-Type": "application/json" }
      });
    }

    // 3. Webhook Unregister / Delete
    if (path === "/deleteWebhook" && request.method === "GET") {
      const tgRes = await fetch(`https://api.telegram.org/bot${botToken}/deleteWebhook`);
      const result = await tgRes.json();
      return new Response(JSON.stringify(result, null, 2), {
        headers: { "Content-Type": "application/json" }
      });
    }

    // 4. Web Video Player & Document Hub: GET /watch/:fileHash
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

    // 5. Direct Streaming & File Download: GET /:fileHash
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

    // 6. Root & Health Status Endpoint
    if (path === "/" || path === "/status") {
      return new Response(JSON.stringify({
        status: "Online ⚡",
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
