import { FileRecord, incrementDownloads } from "../storage/kv";
import { parseRangeHeader } from "./range";

export async function handleFileStreaming(
  request: Request,
  fileData: FileRecord,
  fileHash: string,
  env: { BOT_TOKEN: string; STREAM_KV?: KVNamespace }
): Promise<Response> {
  const botToken = env.BOT_TOKEN;
  const fileId = fileData.file_id;

  // 1. Resolve Telegram File Path
  const getFileRes = await fetch(`https://api.telegram.org/bot${botToken}/getFile?file_id=${fileId}`);
  const getFileData: any = await getFileRes.json();

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

  // 2. Parse Range Header
  const rangeHeader = request.headers.get("Range");
  const { start, end, isRange } = parseRangeHeader(rangeHeader, fileSize);
  const contentLength = (end - start) + 1;

  // 3. Prepare Outbound Telegram Request Headers
  const fetchHeaders = new Headers();
  if (isRange && fileSize > 0) {
    fetchHeaders.set("Range", `bytes=${start}-${end}`);
  }

  const tgResponse = await fetch(telegramDownloadUrl, {
    method: request.method,
    headers: fetchHeaders
  });

  // Track download metrics
  if (start === 0) {
    await incrementDownloads(env, fileHash, fileData);
  }

  // 4. Construct Client Response with Range & CORS Headers
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
