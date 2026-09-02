export interface ByteRange {
  start: number;
  end: number;
  isRange: boolean;
}

export function parseRangeHeader(rangeHeader: string | null, fileSize: number): ByteRange {
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
