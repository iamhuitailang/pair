import { ALLOWED_TYPES } from './config.js';

// 只依据文件头魔数判断真实类型，不参考文件名与浏览器声明的 MIME。
// 返回 ALLOWED_TYPES 的 key（png/jpeg/gif/webp/zip），无法识别返回 null。
export function detectType(buffer) {
  if (!buffer || buffer.length < 4) return null;

  // PNG: 89 50 4E 47 0D 0A 1A 0A
  if (
    buffer.length >= 8 &&
    buffer[0] === 0x89 &&
    buffer[1] === 0x50 &&
    buffer[2] === 0x4e &&
    buffer[3] === 0x47 &&
    buffer[4] === 0x0d &&
    buffer[5] === 0x0a &&
    buffer[6] === 0x1a &&
    buffer[7] === 0x0a
  ) {
    return 'png';
  }

  // JPEG: FF D8 FF
  if (buffer[0] === 0xff && buffer[1] === 0xd8 && buffer[2] === 0xff) {
    return 'jpeg';
  }

  // GIF: "GIF87a" / "GIF89a"
  if (
    buffer[0] === 0x47 &&
    buffer[1] === 0x49 &&
    buffer[2] === 0x46 &&
    buffer[3] === 0x38 &&
    (buffer[4] === 0x37 || buffer[4] === 0x39) &&
    buffer[5] === 0x61
  ) {
    return 'gif';
  }

  // RIFF....WEBP
  if (
    buffer.length >= 12 &&
    buffer[0] === 0x52 &&
    buffer[1] === 0x49 &&
    buffer[2] === 0x46 &&
    buffer[3] === 0x46 &&
    buffer[8] === 0x57 &&
    buffer[9] === 0x45 &&
    buffer[10] === 0x42 &&
    buffer[11] === 0x50
  ) {
    return 'webp';
  }

  // ZIP / 容器类（xlsx/jar 等同样以 PK 开头，这里统一识别为 zip）
  if (buffer[0] === 0x50 && buffer[1] === 0x4b) {
    return 'zip';
  }

  return null;
}

export function expectedMime(type) {
  return ALLOWED_TYPES[type]?.mime ?? null;
}

// 检查客户端浏览器声明的 MIME 是否与魔数识别结果一致。
// 浏览器对某些格式可能给出 application/octet-stream 这类空泛声明，不据此直接拒收，
// 只有“明确声明了具体 MIME 且与实际类型冲突”时才判为欺骗。
export function browserMimeConflict(detected, browserMime) {
  if (!browserMime) return false;
  const normalized = browserMime.split(';')[0].trim().toLowerCase();
  if (!normalized || normalized === 'application/octet-stream' || normalized === 'binary/octet-stream') {
    return false;
  }
  const expected = expectedMime(detected);
  return Boolean(expected) && normalized !== expected;
}
