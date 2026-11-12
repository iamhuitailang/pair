import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { APPROVED_DIR, QUARANTINE_DIR } from './config.js';

// 存储名完全由服务端随机生成，客户端提供的文件名只做展示，不参与任何路径拼接
export function generateStoredName(ext) {
  const suffix = ext && ext.startsWith('.') ? ext.toLowerCase() : '';
  return `${crypto.randomUUID()}-${crypto.randomBytes(8).toString('hex')}${suffix}`;
}

// 展示用的原始文件名：剥离任何目录成分，防止前端/日志里出现路径
export function sanitizeOriginalName(name) {
  const base = path.basename(String(name || 'unknown')).replace(/[\x00-\x1f]/g, '');
  return base.slice(0, 200) || 'unknown';
}

function assertInside(baseDir, targetPath) {
  const realBase = fs.realpathSync(baseDir);
  const realTarget = fs.realpathSync(path.dirname(targetPath));
  if (realTarget !== realBase && !realTarget.startsWith(realBase + path.sep)) {
    throw new Error(`路径越界: 目标 ${realTarget} 不在 ${realBase} 之内`);
  }
}

// 安全落盘：先确认目标目录 realpath，再 rename；存储名不含目录分隔符
export function moveToDir(tmpPath, storedName, zone) {
  const baseDir = zone === 'approved' ? APPROVED_DIR : QUARANTINE_DIR;
  const target = path.join(baseDir, storedName);
  assertInside(baseDir, target);
  fs.renameSync(tmpPath, target);
  // 落盘后再校验一次最终 realpath，杜绝符号链接等意外
  assertInside(baseDir, target);
  return target;
}

// 隔离清理专用：只允许删除 quarantine 目录 realpath 内的文件，
// 即使数据库记录被篡改也不会波及 approved
export function safeRemoveQuarantine(storedName) {
  const base = path.basename(storedName); // 拒绝任何带目录的输入
  if (base !== storedName) throw new Error('非法存储名');
  const target = path.join(QUARANTINE_DIR, base);
  assertInside(QUARANTINE_DIR, target);
  if (fs.existsSync(target)) {
    fs.unlinkSync(target);
    return true;
  }
  return false;
}

// 下载专用：只解析 approved 目录内的文件
export function resolveApprovedPath(storedName) {
  const base = path.basename(storedName);
  if (base !== storedName) throw new Error('非法存储名');
  const target = path.join(APPROVED_DIR, base);
  assertInside(APPROVED_DIR, target);
  if (!fs.existsSync(target)) return null;
  return target;
}

// Content-Disposition 用：ASCII 回退名 + RFC 5987 编码名
export function contentDisposition(filename) {
  const ascii = filename.replace(/[^\x20-\x7e]/g, '_').replace(/["\\]/g, '_');
  const encoded = encodeURIComponent(filename);
  return `attachment; filename="${ascii}"; filename*=UTF-8''${encoded}`;
}
