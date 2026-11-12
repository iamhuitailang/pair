import { DatabaseSync } from 'node:sqlite';
import { DB_FILE, ensureDirs } from './config.js';

ensureDirs();

export const db = new DatabaseSync(DB_FILE);

// WAL 模式让本地开发时读写互不阻塞；业务量很小，单连接即可
db.exec('PRAGMA journal_mode = WAL;');
db.exec('PRAGMA foreign_keys = ON;');

db.exec(`
CREATE TABLE IF NOT EXISTS files (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  stored_name     TEXT NOT NULL UNIQUE,
  original_name   TEXT NOT NULL,
  extension       TEXT NOT NULL,
  detected_type   TEXT,
  browser_mime    TEXT,
  size_bytes      INTEGER NOT NULL,
  sha256          TEXT NOT NULL,
  status          TEXT NOT NULL CHECK (status IN ('approved', 'quarantined')),
  reject_reason   TEXT,
  zip_entries     INTEGER,
  zip_total_bytes INTEGER,
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  file_id     INTEGER REFERENCES files(id) ON DELETE SET NULL,
  stored_name TEXT,
  event       TEXT NOT NULL,
  detail      TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
`);

const stmtInsertFile = db.prepare(`
INSERT INTO files
  (stored_name, original_name, extension, detected_type, browser_mime,
   size_bytes, sha256, status, reject_reason, zip_entries, zip_total_bytes)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);

const stmtInsertAudit = db.prepare(
  'INSERT INTO audit_logs (file_id, stored_name, event, detail) VALUES (?, ?, ?, ?)'
);

export function insertFile(row) {
  return stmtInsertFile.run(
    row.storedName,
    row.originalName,
    row.extension,
    row.detectedType ?? null,
    row.browserMime ?? null,
    row.sizeBytes,
    row.sha256,
    row.status,
    row.rejectReason ?? null,
    row.zipEntries ?? null,
    row.zipTotalBytes ?? null
  );
}

export function logAudit(event, detail = null, fileId = null, storedName = null) {
  stmtInsertAudit.run(fileId, storedName, event, detail);
}

// 统一的对外 DTO：只暴露相对标识与状态，绝不包含本机绝对路径
export function toFileDto(f) {
  return {
    id: f.id,
    originalName: f.original_name,
    extension: f.extension,
    detectedType: f.detected_type,
    browserMime: f.browser_mime,
    sizeBytes: f.size_bytes,
    sha256: f.sha256,
    status: f.status,
    rejectReason: f.reject_reason,
    zipEntries: f.zip_entries,
    zipTotalBytes: f.zip_total_bytes,
    createdAt: f.created_at,
    updatedAt: f.updated_at
  };
}

export function toAuditDto(a) {
  return {
    id: a.id,
    fileId: a.file_id,
    storedName: a.stored_name,
    event: a.event,
    detail: a.detail,
    createdAt: a.created_at
  };
}

export function countFileRows() {
  const row = db.prepare('SELECT COUNT(*) AS n FROM files').get();
  return row.n;
}
