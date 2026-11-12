import { Router } from 'express';
import { db, toAuditDto } from '../db.js';

const router = Router();

// 全部状态变化的可查看记录（上传通过/拒收/下载/清理/拦截）
router.get('/', (req, res) => {
  const limit = Math.min(Number(req.query.limit) || 100, 500);
  const rows = db
    .prepare('SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?')
    .all(limit);
  res.json({ logs: rows.map(toAuditDto) });
});

export default router;
