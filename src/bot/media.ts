export interface ExtractedMedia {
  file_id: string;
  file_unique_id: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  category: "video" | "audio" | "image" | "apk" | "archive" | "pdf" | "document" | "software";
  is_streamable: boolean;
}

const VIDEO_EXTS = new Set([".mp4", ".mkv", ".webm", ".avi", ".mov", ".wmv", ".flv", ".ts", ".m4v", ".3gp", ".mpg", ".mpeg"]);
const AUDIO_EXTS = new Set([".mp3", ".m4a", ".flac", ".wav", ".aac", ".opus", ".ogg", ".wma", ".mka"]);
const IMAGE_EXTS = new Set([".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg", ".ico"]);
const APK_EXTS = new Set([".apk", ".xapk", ".apks", ".aab"]);
const ARCHIVE_EXTS = new Set([".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".tgz"]);
const DOCUMENT_EXTS = new Set([".pdf", ".epub", ".mobi", ".docx", ".doc", ".xlsx", ".pptx", ".txt", ".csv", ".json"]);
const SOFTWARE_EXTS = new Set([".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm"]);

function getExtension(filename: string): string {
  const match = filename.match(/\.[0-9a-z]+$/i);
  return match ? match[0].toLowerCase() : "";
}

export function classifyMedia(fileName: string, rawMime: string, rawType: string): {
  category: ExtractedMedia["category"];
  mimeType: string;
  isStreamable: boolean;
} {
  const ext = getExtension(fileName);

  // 1. Video Detection
  if (rawType === "video" || rawType === "animation" || VIDEO_EXTS.has(ext) || (rawMime && rawMime.startsWith("video/"))) {
    return {
      category: "video",
      mimeType: rawMime && rawMime.startsWith("video/") ? rawMime : "video/mp4",
      isStreamable: true
    };
  }

  // 2. Audio Detection
  if (rawType === "audio" || rawType === "voice" || AUDIO_EXTS.has(ext) || (rawMime && rawMime.startsWith("audio/"))) {
    return {
      category: "audio",
      mimeType: rawMime && rawMime.startsWith("audio/") ? rawMime : "audio/mpeg",
      isStreamable: true
    };
  }

  // 3. Image Detection
  if (rawType === "photo" || IMAGE_EXTS.has(ext) || (rawMime && rawMime.startsWith("image/"))) {
    return {
      category: "image",
      mimeType: rawMime && rawMime.startsWith("image/") ? rawMime : "image/jpeg",
      isStreamable: true
    };
  }

  // 4. Android App (APK)
  if (APK_EXTS.has(ext) || (rawMime && rawMime.includes("android.package-archive"))) {
    return {
      category: "apk",
      mimeType: "application/vnd.android.package-archive",
      isStreamable: false
    };
  }

  // 5. Compressed Archive
  if (ARCHIVE_EXTS.has(ext) || (rawMime && (rawMime.includes("zip") || rawMime.includes("rar") || rawMime.includes("tar")))) {
    return {
      category: "archive",
      mimeType: rawMime || "application/zip",
      isStreamable: false
    };
  }

  // 6. PDF / Documents
  if (ext === ".pdf" || (rawMime && rawMime.includes("pdf"))) {
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

  // 7. Software
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

export function extractMediaFromTelegramMessage(message: any): ExtractedMedia | null {
  let mediaObj: any = null;
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

  if (!mediaObj) return null;

  let fileName = mediaObj.file_name;
  if (!fileName) {
    if (rawType === "photo") fileName = `photo_${message.message_id}.jpg`;
    else if (rawType === "video") fileName = `video_${message.message_id}.mp4`;
    else if (rawType === "audio") fileName = `audio_${message.message_id}.mp3`;
    else if (rawType === "animation") fileName = `animation_${message.message_id}.mp4`;
    else if (rawType === "voice") fileName = `voice_${message.message_id}.ogg`;
    else fileName = `file_${message.message_id}`;
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
