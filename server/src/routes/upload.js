import { Router } from 'express';
import multer from 'multer';
import fs from 'node:fs';
import { TMP_DIR, LIMITS } from '../config.js';
import { inspectUpload } from '../inspector.js';
import { generateStoredName, sanitizeOriginalName, moveToDir } from '../storage.js';
import { db, insertFile, logAudit, toFileDto } from '../db.js';

// 临时文件也使用服务端随机名，绝不采用客户端文件名
const upload = multer({
  storage: multer.diskStorage({
    destination: TMP_DIR,
    filename: (_req, _file, cb) => cb(null, generateStoredName('.part'))
  }),
  limits: { fileSize: LIMITS.MAX_UPLOAD_BYTES, files: 1 },
  fileFilter: (_req, _file, cb) => cb(null, true) // 类型不靠 multer 判断，统一进检查流水线
});

const runMulter = (req, res) =>
  new Promise((resolve, reject) => {
    upload.single('file')(req, res, (err) => (err ? reject(err) : resolve()));
  });

const router = Router();

// 记录一条隔离文件（物理文件可能存在也可能不存在，如超限被 multer 截断的情况）
function recordQuarantine({ originalName, ext, detectedType, browserMime, sizeBytes, reason, tmpPath }) {
  const storedName = generateStoredName(ext || '.bin');
  let moved = false;
  if (tmpPath && fs.existsSync(tmpPath)) {
    moveToDir(tmpPath, storedName, 'quarantine');
    moved = true;
  }
  const info = insertFile({
    storedName,
    originalName,
    extension: ext || '',
    detectedType,
    browserMime,
    sizeBytes,
    sha256: 'unavailable',
    status: 'quarantined',
    rejectReason: reason,
    zipEntries: null,
    zipTotalBytes: null
  });
  logAudit(
    'upload.quarantined',
    `${reason}${moved ? '' : '（无物理文件，未进入隔离目录）'}`,
    Number(info.lastInsertRowid),
    storedName
  );
  return db.prepare('SELECT * FROM files WHERE id = ?').get(info.lastInsertRowid);
}

router.post('/', async (req, res) => {
  let multerFile;
  let originalName = 'unknown';
  let browserMime = null;
  let sizeBytes = 0;
  let tmpPath = null;

  try {
    try {
      await runMulter(req, res);
    } catch (multerErr) {
      // 超限也要留档：隔离记录 + 审计，但不提供取回。
      // 此时 multer 已删除临时文件，文件名取前端附加头（同样不可信，仅展示用）。
      if (multerErr.code === 'LIMIT_FILE_SIZE') {
        const row = recordQuarantine({
          originalName: sanitizeOriginalName(req.headers['x-filename'] || 'unknown'),
          ext: '',
          detectedType: null,
          browserMime: null,
          sizeBytes: LIMITS.MAX_UPLOAD_BYTES,
          reason: `文件大小超过上传硬上限 ${LIMITS.MAX_UPLOAD_BYTES} 字节，传输被中断`,
          tmpPath: null
        });
        return res.status(413).json({ status: 'quarantined', file: toFileDto(row) });
      }
      throw multerErr;
    }

    if (!req.file) {
      return res.status(400).json({ error: '缺少上传文件（字段名应为 file）' });
    }

    multerFile = req.file;
    tmpPath = multerFile.path;
    originalName = sanitizeOriginalName(multerFile.originalname);
    browserMime = multerFile.mimetype || null;
    sizeBytes = multerFile.size;

    const result = await inspectUpload({ tmpPath, originalName, browserMime, sizeBytes });

    if (!result.ok) {
      const row = recordQuarantine({
        originalName,
        ext: result.ext,
        detectedType: result.detectedType,
        browserMime,
        sizeBytes,
        reason: result.reason,
        tmpPath
      });
      tmpPath = null; // 已移动，避免 finally 重复清理
      return res.status(200).json({ status: 'quarantined', file: toFileDto(row) });
    }

    const storedName = generateStoredName(result.ext);
    moveToDir(tmpPath, storedName, 'approved');
    tmpPath = null;

    const info = insertFile({
      storedName,
      originalName,
      extension: result.ext,
      detectedType: result.detectedType,
      browserMime,
      sizeBytes,
      sha256: result.sha256,
      status: 'approved',
      rejectReason: null,
      zipEntries: result.zipInfo?.entries ?? null,
      zipTotalBytes: result.zipInfo?.totalBytes ?? null
    });
    logAudit('upload.approved', `通过检查，识别类型 ${result.detectedType}`, Number(info.lastInsertRowid), storedName);
    const row = db.prepare('SELECT * FROM files WHERE id = ?').get(info.lastInsertRowid);
    return res.status(201).json({ status: 'approved', file: toFileDto(row) });
  } catch (err) {
    logAudit('upload.error', err.message);
    return res.status(500).json({ error: '服务端处理失败' });
  } finally {
    // 任何异常路径都不允许临时文件残留
    if (tmpPath && fs.existsSync(tmpPath)) {
      fs.promises.unlink(tmpPath).catch(() => {});
    }
  }
});

export default router;
