import fs from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';
import { ALLOWED_TYPES, LIMITS } from './config.js';
import { detectType, browserMimeConflict } from './signatures.js';
import { inspectZip } from './zip-inspect.js';

function sha256OfFile(filePath) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash('sha256');
    const stream = fs.createReadStream(filePath);
    stream.on('error', reject);
    stream.on('data', (c) => hash.update(c));
    stream.on('end', () => resolve(hash.digest('hex')));
  });
}

// 检查流水线。输入为 multer 已落在 tmp 的文件，输出检查结论；
// 注意：文件名/扩展名/浏览器 MIME 全部视为不可信数据，仅实际魔数用于类型判定。
export async function inspectUpload({ tmpPath, originalName, browserMime, sizeBytes }) {
  const ext = path.extname(originalName).toLowerCase();
  const fd = await fs.promises.open(tmpPath, 'r');
  let header;
  try {
    header = Buffer.alloc(512);
    const { bytesRead } = await fd.read(header, 0, 512, 0);
    header = header.subarray(0, bytesRead);
  } finally {
    await fd.close();
  }

  const detectedType = detectType(header);

  // 1. 实际内容是否可识别
  if (!detectedType) {
    return reject('文件头魔数无法识别为任何允许的格式', ext, null);
  }

  // 2. 实际格式是否在允许清单内
  if (!ALLOWED_TYPES[detectedType]) {
    return reject(`实际格式 ${detectedType} 不在允许清单内`, ext, detectedType);
  }

  // 3. 扩展名与实际内容是否一致（扩展名不可信，但可用于发现伪装）
  const allowedExts = ALLOWED_TYPES[detectedType].extensions;
  if (!ext || !allowedExts.includes(ext)) {
    return reject(
      `扩展名 ${ext || '(无)'} 与实际内容 ${detectedType.toUpperCase()} 不匹配`,
      ext,
      detectedType
    );
  }

  // 4. 浏览器声明 MIME 与实际内容冲突
  if (browserMimeConflict(detectedType, browserMime)) {
    return reject(
      `浏览器声明的 MIME 类型 ${browserMime} 与实际内容 ${detectedType.toUpperCase()} 冲突`,
      ext,
      detectedType
    );
  }

  // 5. 大小检查（容器大小，上传层 multer 也会硬限制）
  if (sizeBytes > LIMITS.MAX_UPLOAD_BYTES) {
    return reject(
      `文件大小 ${sizeBytes} 字节超过上限 ${LIMITS.MAX_UPLOAD_BYTES} 字节`,
      ext,
      detectedType
    );
  }

  // 6. ZIP 专项检查（数量 / 总解压大小 / 目录范围 / 内部文件类型）
  let zipInfo = null;
  if (detectedType === 'zip') {
    try {
      zipInfo = await inspectZip(tmpPath);
    } catch (e) {
      return reject(e.message, ext, detectedType);
    }
  }

  const sha256 = await sha256OfFile(tmpPath);
  return {
    ok: true,
    ext,
    detectedType,
    sha256,
    zipInfo
  };
}

function reject(reason, ext, detectedType) {
  return { ok: false, reason, ext, detectedType };
}
