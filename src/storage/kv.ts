export interface FileRecord {
  file_id: string;
  file_unique_id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  category: string;
  is_streamable: boolean;
  user_id: number;
  created_at: number;
  views: number;
  downloads: number;
}

// In-memory fallback map for preview / local runs without KV bound
const memoryStore = new Map<string, FileRecord>();

export function generateFileHash(messageId: number | string, prefix: string = "stream-"): string {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let entropy = "";
  for (let i = 0; i < 12; i++) {
    entropy += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return `${prefix}${entropy}${messageId}`;
}

export async function saveFile(
  env: { STREAM_KV?: KVNamespace },
  fileHash: string,
  data: FileRecord
): Promise<void> {
  if (env.STREAM_KV) {
    await env.STREAM_KV.put(fileHash, JSON.stringify(data), {
      // Retain files for 1 year (expiration in seconds)
      expirationTtl: 31536000
    });
  } else {
    memoryStore.set(fileHash, data);
  }
}

export async function getFile(
  env: { STREAM_KV?: KVNamespace },
  fileHash: string
): Promise<FileRecord | null> {
  if (env.STREAM_KV) {
    const raw = await env.STREAM_KV.get(fileHash, "json");
    return raw as FileRecord | null;
  }
  return memoryStore.get(fileHash) || null;
}

export async function incrementViews(
  env: { STREAM_KV?: KVNamespace },
  fileHash: string,
  fileData: FileRecord
): Promise<void> {
  fileData.views = (fileData.views || 0) + 1;
  await saveFile(env, fileHash, fileData);
}

export async function incrementDownloads(
  env: { STREAM_KV?: KVNamespace },
  fileHash: string,
  fileData: FileRecord
): Promise<void> {
  fileData.downloads = (fileData.downloads || 0) + 1;
  await saveFile(env, fileHash, fileData);
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}
