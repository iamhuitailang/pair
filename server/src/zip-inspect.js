import path from 'node:path';
import yauzl from 'yauzl';
import { LIMITS, ZIP_INNER_ALLOWED } from './config.js';
import { detectType } from './signatures.js';

// 纯流式校验 ZIP，全程不解压到磁盘，天然杜绝 zip-slip 落盘。
// 校验项：
//   1. 目录范围：条目名不得绝对路径 / 含 .. / 含反斜杠越界 / 含盘符
//   2. 条目数量 <= ZIP_MAX_ENTRIES（目录条目也计数）
//   3. 解压后总大小 <= ZIP_MAX_TOTAL_BYTES（累加 uncompressedSize，读取时再次累计）
//   4. 每个文件条目的魔数必须属于 ZIP_INNER_ALLOWED 的图片格式
export function inspectZip(filePath) {
  return new Promise((resolve, reject) => {
    yauzl.open(filePath, { lazyEntries: true, autoClose: true }, (err, zipfile) => {
      if (err) {
        reject(new Error(`ZIP 结构损坏，无法读取: ${err.message}`));
        return;
      }

      let entries = 0;
      let totalBytes = 0;
      const innerNames = [];

      const fail = (message) => {
        if (!zipfile.isClosed) zipfile.close();
        reject(new Error(message));
      };

      zipfile.readEntry();
      zipfile.on('entry', (entry) => {
        const rawName = entry.fileName;

        // ---- 目录范围检查 ----
        if (path.isAbsolute(rawName) || /^[a-zA-Z]:/.test(rawName) || rawName.includes('\\') ||
            rawName.split('/').some((seg) => seg === '..')) {
          fail(`ZIP 条目路径越界（疑似 zip-slip）: ${rawName}`);
          return;
        }

        entries += 1;
        if (entries > LIMITS.ZIP_MAX_ENTRIES) {
          fail(`ZIP 条目数量超过上限 ${LIMITS.ZIP_MAX_ENTRIES}`);
          return;
        }

        // yauzl 的 uncompressedSize 来自中央目录，先做第一道总量预算
        totalBytes += entry.uncompressedSize;
        if (totalBytes > LIMITS.ZIP_MAX_TOTAL_BYTES) {
          fail(`ZIP 解压后总大小超过上限 ${LIMITS.ZIP_MAX_TOTAL_BYTES} 字节`);
          return;
        }

        const isDir = /\/$/.test(rawName);
        if (isDir) {
          zipfile.readEntry();
          return;
        }

        innerNames.push(rawName);
        zipfile.openReadStream(entry, (streamErr, readStream) => {
          if (streamErr) {
            fail(`ZIP 条目读取失败: ${streamErr.message}`);
            return;
          }

          const chunks = [];
          let streamed = 0;
          // 只需要文件头做魔数识别，单条目读到 512 字节即可
          readStream.on('data', (chunk) => {
            streamed += chunk.length;
            if (streamed > LIMITS.ZIP_MAX_TOTAL_BYTES) {
              fail(`ZIP 解压后总大小超过上限 ${LIMITS.ZIP_MAX_TOTAL_BYTES} 字节`);
              readStream.destroy();
              return;
            }
            const need = 512 - chunks.reduce((n, c) => n + c.length, 0);
            if (need > 0) chunks.push(chunk.subarray(0, Math.min(need, chunk.length)));
          });
          readStream.on('end', () => {
            const header = Buffer.concat(chunks).subarray(0, 512);
            const innerType = detectType(header);
            if (!innerType || !ZIP_INNER_ALLOWED.includes(innerType)) {
              fail(`ZIP 内文件 "${rawName}" 不是允许的图片格式（实际识别: ${innerType || '未知'}）`);
              return;
            }
            zipfile.readEntry();
          });
          readStream.on('error', (e) => fail(`ZIP 条目读取失败: ${e.message}`));
        });
      });

      zipfile.on('end', () => {
        resolve({
          entries,
          totalBytes,
          fileCount: innerNames.length,
          innerNames
        });
      });
      zipfile.on('error', (e) => fail(e.message));
    });
  });
}
