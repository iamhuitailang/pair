import { Router } from 'express';
import { db, logAudit, toFileDto } from '../db.js';
import { resolveApprovedPath, sanitizeOriginalName, contentDisposition } from '../storage.js';

const router = Router();

// 已通过检查的文件列表（隔离文件不会出现在这里）
router.get('/', (_req, res) => {
  const rows = db
    .prepare("SELECT * FROM files WHERE status = 'approved' ORDER BY id DESC")
    .all();
  res.json({ files: rows.map(toFileDto) });
});

// 普通下载接口：只服务 approved 记录 + approved 目录 realpath 双重校验
router.get('/:id/download', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ error: '非法 id' });

  const row = db.prepare('SELECT * FROM files WHERE id = ?').get(id);
  if (!row || row.status !== 'approved') {
    // 隔离区文件即使猜到 id 也拿不到
    return res.status(404).json({ error: '文件不存在或不可下载' });
  }

  let filePath;
  try {
    filePath = resolveApprovedPath(row.stored_name);
  } catch {
    logAudit('download.blocked', '存储名校验失败', row.id, row.stored_name);
    return res.status(400).json({ error: '非法存储名' });
  }
  if (!filePath) {
    logAudit('download.missing', '物理文件缺失', row.id, row.stored_name);
    return res.status(404).json({ error: '物理文件缺失' });
  }

  logAudit('download.ok', `下载 ${row.original_name}`, row.id, row.stored_name);
  res.setHeader('Content-Type', 'application/octet-stream');
  res.setHeader('Content-Disposition', contentDisposition(sanitizeOriginalName(row.original_name)));
  res.download(filePath, sanitizeOriginalName(row.original_name), (err) => {
    if (err) logAudit('download.error', err.message, row.id, row.stored_name);
  });
});

export default router;
