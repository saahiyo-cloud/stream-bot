import { FileRecord, formatBytes } from "../storage/kv";

export function renderPlayerHtml(
  fileData: FileRecord,
  fileHash: string,
  publicBaseUrl: string,
  updatesChannel: string
): string {
  const fileName = fileData.file_name || `file_${fileHash}`;
  const formattedSize = formatBytes(fileData.file_size);
  const mimeType = fileData.mime_type || "application/octet-stream";
  const rawStreamUrl = `${publicBaseUrl}/${fileHash}?stream=1`;
  const downloadUrl = `${publicBaseUrl}/${fileHash}`;
  const category = fileData.category;

  // Header Channel Button
  const channelBtnHtml = updatesChannel
    ? `<a href="https://t.me/${updatesChannel.replace('@', '')}" target="_blank" class="channel-btn">
         <span>🛠 ${updatesChannel}</span>
       </a>`
    : "";

  // Media Frame Content
  let mediaDisplayHtml = "";

  if (category === "image" || mimeType.startsWith("image/")) {
    mediaDisplayHtml = `<img src="${rawStreamUrl}" alt="${fileName}" class="image-preview" loading="lazy" />`;
  } else if (category === "audio" || mimeType.startsWith("audio/")) {
    mediaDisplayHtml = `
      <div class="audio-wrapper">
        <div class="audio-icon">🎵</div>
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
        <div class="document-icon-box icon-apk">🤖</div>
        <div class="doc-title">${fileName}</div>
        <div class="doc-subtitle">Android Application Package (APK) • Direct Cloudflare Edge Download</div>
      </div>`;
  } else if (category === "archive") {
    mediaDisplayHtml = `
      <div class="document-wrapper">
        <div class="document-icon-box icon-archive">🗜️</div>
        <div class="doc-title">${fileName}</div>
        <div class="doc-subtitle">Compressed Archive • Direct Cloudflare Edge Download</div>
      </div>`;
  } else {
    mediaDisplayHtml = `
      <div class="document-wrapper">
        <div class="document-icon-box icon-doc">📄</div>
        <div class="doc-title">${fileName}</div>
        <div class="doc-subtitle">Document / File • Direct Cloudflare Edge Download</div>
      </div>`;
  }

  // Action Buttons
  const isApk = category === "apk" || fileName.endsWith(".apk");
  const mainBtnClass = isApk ? "btn-apk" : "btn-primary";
  const mainBtnText = isApk ? `📥 Download APK (${formattedSize})` : "🚀 Download Now";
  const vlcBtnHtml = (category === "video" || category === "audio")
    ? `<a href="vlc://${rawStreamUrl}" class="btn btn-vlc"><span>📺 Open in VLC</span></a>`
    : "";

  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${fileName} - Stream Bot ⚡</title>
    
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
                <span class="brand-icon">⚡</span>
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
                        <span class="badge badge-size">📦 ${formattedSize}</span>
                        ${isApk ? '<span class="badge badge-apk">📱 Android App</span>' : `<span class="badge">${mimeType}</span>`}
                    </div>
                </div>
            </div>

            <div class="actions-grid">
                <a href="${downloadUrl}" class="btn ${mainBtnClass}" download>
                    <span>${mainBtnText}</span>
                </a>
                <button onclick="copyLink()" class="btn btn-secondary">
                    <span>📋 Copy Link</span>
                </button>
                ${vlcBtnHtml}
            </div>
        </div>

        <div class="footer">
            Powered by <strong>Stream Bot ⚡</strong> | 100% Serverless Cloudflare Edge Streaming
        </div>
    </div>

    <div id="toast" class="toast">Link copied to clipboard!</div>

    <script src="https://cdn.plyr.io/3.7.8/plyr.js"></script>
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
    </script>
</body>
</html>`;
}
