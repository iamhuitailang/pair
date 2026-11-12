import express from 'express';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { PORT, LIMITS, ALLOWED_TYPES, ensureDirs } from './config.js';
import uploadRouter from './routes/upload.js';
import filesRouter from './routes/files.js';
import quarantineRouter from './routes/quarantine.js';
import auditRouter from './routes/audit.js';
import samplesRouter from './routes/samples.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
ensureDirs();

const app = express();
app.use(express.json());

app.get('/api/health', (_req, res) => {
  res.json({
    ok: true,
    dbReady: true, // 数据库在模块导入时已打开，失败进程会直接退出
    limits: {
      maxUploadBytes: LIMITS.MAX_UPLOAD_BYTES,
      zipMaxEntries: LIMITS.ZIP_MAX_ENTRIES,
      zipMaxTotalBytes: LIMITS.ZIP_MAX_TOTAL_BYTES
    },
    allowedTypes: Object.keys(ALLOWED_TYPES)
  });
});

app.use('/api/upload', uploadRouter);
app.use('/api/files', filesRouter);
app.use('/api/quarantine', quarantineRouter);
app.use('/api/audit', auditRouter);
app.use('/api/samples', samplesRouter);

app.use('/api', (_req, res) => res.status(404).json({ error: '接口不存在' }));

// 统一错误处理，不向页面泄漏堆栈或绝对路径（必须在路由之后注册）
app.use((err, _req, res, _next) => {
  console.error('[workbench] unhandled:', err.message);
  res.status(500).json({ error: '服务端内部错误' });
});

// 生产模式：托管 Vue 构建产物（dist 由前端构建生成）
const distDir = path.resolve(__dirname, '../../web/dist');
if (fs.existsSync(distDir)) {
  app.use(express.static(distDir));
  app.get(/^(?!\/api\/).*/, (_req, res) => res.sendFile(path.join(distDir, 'index.html')));
}

app.listen(PORT, () => {
  console.log(`[workbench] listening on http://localhost:${PORT}`);
});
