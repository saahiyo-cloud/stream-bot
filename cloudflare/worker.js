/**
 * Cloudflare Worker Reverse Proxy for Telegram Stream & Download Bot
 */

const BACKEND_ORIGIN = "https://saahiyo-stream-bot.hf.space";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = (env && env.BACKEND_ORIGIN) ? env.BACKEND_ORIGIN : BACKEND_ORIGIN;

    // Handle preflight OPTIONS request
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
          "Access-Control-Allow-Headers": "Range, Content-Type, Authorization",
          "Access-Control-Max-Age": "86400"
        }
      });
    }

    const targetUrl = new URL(url.pathname + url.search, origin);

    // Create a new subrequest cleanly
    const proxyReq = new Request(targetUrl.toString(), {
      method: request.method,
      headers: request.headers,
      redirect: "follow"
    });

    try {
      const response = await fetch(proxyReq);

      const modifiedHeaders = new Headers(response.headers);
      modifiedHeaders.set("Access-Control-Allow-Origin", "*");
      modifiedHeaders.set("Access-Control-Allow-Headers", "Range, Content-Type");
      modifiedHeaders.set("Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges, Content-Disposition");
      modifiedHeaders.set("X-Served-By", "Cloudflare-Edge-Streamer");

      return new Response(response.body, {
        status: response.status,
        headers: modifiedHeaders
      });

    } catch (err) {
      return new Response(JSON.stringify({
        error: "Backend Gateway Error",
        message: err.message
      }, null, 2), {
        status: 502,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
      });
    }
  }
};
