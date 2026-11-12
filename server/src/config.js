import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 所有数据都收敛在项目根 data/ 下，绝对路径只在服务端内部使用，不写入任何 API 响应
export const ROOT_DIR = path.resolve(__dirname, '../..');
export const DATA_DIR = path.join(ROOT_DIR, 'data');
export const APPROVED_DIR = path.join(DATA_DIR, 'approved');
export const QUARANTINE_DIR = path.join(DATA_DIR, 'quarantine');
export const TMP_DIR = path.join(DATA_DIR, 'tmp');
export const DB_FILE = path.join(DATA_DIR, 'workbench.sqlite');
// config.js 位于 server/src/，样例位于 server/samples/
export const SERVER_DIR = path.resolve(__dirname, '..');
export const SAMPLES_DIR = path.join(SERVER_DIR, 'samples');

export const LIMITS = Object.freeze({
  MAX_UPLOAD_BYTES: 10 * 1024 * 1024, // 单文件 10 MiB（含 ZIP 容器本身）
  ZIP_MAX_ENTRIES: 100, // 解压后条目数量上限
  ZIP_MAX_TOTAL_BYTES: 50 * 1024 * 1024 // 解压后总大小上限 50 MiB
});

// 允许的“格式族” -> 可信魔数识别结果与合法扩展名
export const ALLOWED_TYPES = Object.freeze({
  png: { mime: 'image/png', extensions: ['.png'] },
  jpeg: { mime: 'image/jpeg', extensions: ['.jpg', '.jpeg'] },
  gif: { mime: 'image/gif', extensions: ['.gif'] },
  webp: { mime: 'image/webp', extensions: ['.webp'] },
  zip: { mime: 'application/zip', extensions: ['.zip'] }
});

export const ALLOWED_EXTENSIONS = Object.freeze(
  Object.values(ALLOWED_TYPES).flatMap((t) => t.extensions)
);

// ZIP 内部允许出现的文件格式（只允许图片，目录条目单独放行）
export const ZIP_INNER_ALLOWED = Object.freeze(['png', 'jpeg', 'gif', 'webp']);

export const PORT = Number(process.env.PORT) || 3000;

export function ensureDirs() {
  for (const dir of [DATA_DIR, APPROVED_DIR, QUARANTINE_DIR, TMP_DIR]) {
    fs.mkdirSync(dir, { recursive: true });
  }
}
