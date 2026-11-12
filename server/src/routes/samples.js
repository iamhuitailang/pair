import { Router } from 'express';
import fs from 'node:fs';
import path from 'node:path';
import { SAMPLES_DIR } from '../config.js';
import { contentDisposition } from '../storage.js';
import { logAudit } from '../db.js';

const router = Router();

// 白名单来自脚本生成的 manifest（位于 positive 目录），禁止按用户输入拼路径
function loadManifest() {
  const p = path.join(SAMPLES_DIR, 'positive', 'manifest.json');
  if (!fs.existsSync(p)) return { positive: [] };
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

router.get('/', (_req, res) => {
  const manifest = loadManifest();
  // 只暴露可合法使用的正例；负例用于手工测试，不对外列出
  res.json({ samples: manifest.positive || [] });
});

router.get('/:name/download', (req, res) => {
  const manifest = loadManifest();
  const allowed = new Set((manifest.positive || []).map((s) => s.file));
  const name = path.basename(req.params.name);
  if (!allowed.has(name)) {
    return res.status(404).json({ error: '样例不存在' });
  }
  const target = path.join(SAMPLES_DIR, 'positive', name);
  if (!fs.existsSync(target)) return res.status(404).json({ error: '样例文件缺失' });
  logAudit('sample.download', `下载样例 ${name}`);
  res.setHeader('Content-Disposition', contentDisposition(name));
  res.download(target, name);
});

export default router;
