import { Router } from 'express';
import { db, logAudit, toFileDto } from '../db.js';
import { safeRemoveQuarantine } from '../storage.js';

const router = Router();

// 隔离区列表：只给状态和拒收原因，不提供任何下载/取回接口
router.get('/', (_req, res) => {
  const rows = db
    .prepare("SELECT * FROM files WHERE status = 'quarantined' ORDER BY id DESC")
    .all();
  res.json({ files: rows.map(toFileDto) });
});

// 清理单个隔离文件：删除前用 realpath 守卫限定在 quarantine 目录，
// approved 目录在文件系统层面就不可达，杜绝误删已通过检查的文件。
router.delete('/:id', (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ error: '非法 id' });

  const row = db.prepare('SELECT * FROM files WHERE id = ?').get(id);
  if (!row || row.status !== 'quarantined') {
    return res.status(404).json({ error: '隔离记录不存在' });
  }

  let removed = false;
  try {
    removed = safeRemoveQuarantine(row.stored_name);
  } catch (err) {
    logAudit('quarantine.cleanup.blocked', err.message, row.id, row.stored_name);
    return res.status(400).json({ error: `清理被安全守卫拦截: ${err.message}` });
  }

  // 先写审计日志（此时 files 行还在，满足外键），再删记录
  logAudit(
    'quarantine.cleanup.deleted',
    removed ? '物理隔离文件已删除' : '记录清理（无物理文件，如超限截断场景）',
    id,
    row.stored_name
  );
  db.prepare('DELETE FROM files WHERE id = ?').run(id);
  res.json({ ok: true, removedPhysicalFile: removed });
});

// 一键清理全部隔离文件：逐条走同一个 realpath 守卫，绝不做目录级 rm
router.post('/purge', (_req, res) => {
  const rows = db.prepare("SELECT * FROM files WHERE status = 'quarantined'").all();
  let removed = 0;
  let records = 0;
  for (const row of rows) {
    try {
      if (safeRemoveQuarantine(row.stored_name)) removed += 1;
    } catch (err) {
      logAudit('quarantine.cleanup.blocked', err.message, row.id, row.stored_name);
      continue;
    }
    // 先写审计日志再删 files 行，满足外键约束
    logAudit('quarantine.cleanup.deleted', '批量清理', row.id, row.stored_name);
    db.prepare('DELETE FROM files WHERE id = ?').run(row.id);
    records += 1;
  }
  res.json({ ok: true, deletedRecords: records, deletedPhysicalFiles: removed, zone: 'quarantine-only' });
});

export default router;
