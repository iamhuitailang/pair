#!/usr/bin/env node
// 零依赖样例生成器：所有图片由本脚本现场合成，不存在第三方版权问题。
// 正例：合法 PNG/JPEG/GIF/WebP + 一个合法图片 ZIP；
// 负例：伪装扩展名、zip-slip、条目超限、解压总量超限，供手工验证隔离流程。
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const POS_DIR = path.join(__dirname, '..', 'samples', 'positive');
const NEG_DIR = path.join(__dirname, '..', 'samples', 'negative');
fs.mkdirSync(POS_DIR, { recursive: true });
fs.mkdirSync(NEG_DIR, { recursive: true });

// ---------- CRC32（PNG / ZIP 共用） ----------
const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(buf) {
  let c = 0xffffffff;
  for (const b of buf) c = CRC_TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

// ---------- PNG 合成 ----------
function makePng(width, height, rgb, randomFill = false) {
  const chunk = (type, data) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const body = Buffer.concat([Buffer.from(type, 'ascii'), data]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(body));
    return Buffer.concat([len, body, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // color type: truecolor RGB
  const raw = Buffer.alloc(height * (1 + width * 3));
  let seed = 0x12345678;
  const nextRand = () => {
    // xorshift32：确定性伪随机，无需额外依赖
    seed = (seed ^ (seed << 13)) >>> 0;
    seed = (seed ^ (seed >>> 17)) >>> 0;
    seed = (seed ^ (seed << 5)) >>> 0;
    return seed & 0xff;
  };
  for (let y = 0; y < height; y++) {
    const rowStart = y * (1 + width * 3);
    raw[rowStart] = 0; // filter: none
    for (let x = 0; x < width; x++) {
      raw[rowStart + 1 + x * 3] = randomFill ? nextRand() : rgb[0];
      raw[rowStart + 2 + x * 3] = randomFill ? nextRand() : rgb[1];
      raw[rowStart + 3 + x * 3] = randomFill ? nextRand() : rgb[2];
    }
  }
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0))
  ]);
}

// ---------- GIF 合成（GIF89a，1x1 全局色表） ----------
function makeGif(rgb) {
  const header = Buffer.from('GIF89a', 'ascii');
  const lsd = Buffer.from([0x01, 0x00, 0x01, 0x00, 0x00, 0x00]); // 1x1, GCT size 2
  const gct = Buffer.from([...rgb, 0, 0, 0]);
  // image descriptor + 最小 LZW 图像数据（固定 1x1 像素，索引 0）
  const img = Buffer.from([
    0x2c, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00,
    0x02, 0x02, 0x4c, 0x01, 0x00, 0x3b
  ]);
  return Buffer.concat([header, lsd, gct, img]);
}

// ---------- 最小 ZIP 写入器（store，无压缩） ----------
function dosTime(date = new Date(2026, 0, 1, 0, 0, 0)) {
  return ((date.getHours() << 11) | (date.getMinutes() << 5) | (date.getSeconds() / 2)) & 0xffff;
}
function dosDate(date = new Date(2026, 0, 1)) {
  return (((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate()) & 0xffff;
}
function makeZip(entries) {
  // entries: [{ name, data: Buffer, deflate?: boolean }]
  const locals = [];
  const centrals = [];
  let offset = 0;
  for (const e of entries) {
    const nameBuf = Buffer.from(e.name, 'utf8');
    const crc = crc32(e.data);
    const method = e.deflate ? 8 : 0;
    const payload = e.deflate ? zlib.deflateRawSync(e.data) : e.data;
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0, 6);
    local.writeUInt16LE(method, 8); // 0=store, 8=deflate
    local.writeUInt16LE(dosTime(), 10);
    local.writeUInt16LE(dosDate(), 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(payload.length, 18); // 压缩后大小
    local.writeUInt32LE(e.data.length, 22); // 原始大小
    local.writeUInt16LE(nameBuf.length, 26);
    local.writeUInt16LE(0, 28);
    const localFull = Buffer.concat([local, nameBuf, payload]);
    locals.push(localFull);

    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0, 8);
    central.writeUInt16LE(method, 10);
    central.writeUInt16LE(dosTime(), 12);
    central.writeUInt16LE(dosDate(), 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(payload.length, 20); // 压缩后大小
    central.writeUInt32LE(e.data.length, 24); // 原始大小
    central.writeUInt16LE(nameBuf.length, 28);
    central.writeUInt32LE(offset, 42);
    centrals.push(Buffer.concat([central, nameBuf]));
    offset += localFull.length;
  }
  const centralBuf = Buffer.concat(centrals);
  const localBuf = Buffer.concat(locals);
  const eocd = Buffer.alloc(22);
  eocd.writeUInt32LE(0x06054b50, 0);
  eocd.writeUInt16LE(entries.length, 8);
  eocd.writeUInt16LE(entries.length, 10);
  eocd.writeUInt32LE(centralBuf.length, 12);
  eocd.writeUInt32LE(localBuf.length, 16);
  return Buffer.concat([localBuf, centralBuf, eocd]);
}

// ---------- 开始生成 ----------
const pngBlue = makePng(32, 32, [42, 112, 224]);
const pngGreen = makePng(48, 24, [60, 170, 90]);
const gifOne = makeGif([220, 80, 80]);
fs.writeFileSync(path.join(POS_DIR, 'sample-blue.png'), pngBlue);
fs.writeFileSync(path.join(POS_DIR, 'sample-green.png'), pngGreen);
fs.writeFileSync(path.join(POS_DIR, 'sample-red.gif'), gifOne);

// JPEG / WebP：借助 macOS 自带 sips 从刚生成的 PNG 转换（无第三方版权素材）
try {
  execFileSync('sips', ['-s', 'format', 'jpeg', path.join(POS_DIR, 'sample-blue.png'), '--out', path.join(POS_DIR, 'sample-blue.jpg')]);
  console.log('  jpeg ok (via sips)');
} catch (e) {
  console.warn('  jpeg skipped: sips 不可用');
}
try {
  execFileSync('sips', ['-s', 'format', 'webp', path.join(POS_DIR, 'sample-green.png'), '--out', path.join(POS_DIR, 'sample-green.webp')]);
  console.log('  webp ok (via sips)');
} catch (e) {
  console.warn('  webp skipped: 当前 sips 不支持 webp');
}

// 合法 ZIP：两张自制图片
const goodZip = makeZip([
  { name: 'images/blue.png', data: pngBlue },
  { name: 'images/green.png', data: pngGreen }
]);
fs.writeFileSync(path.join(POS_DIR, 'sample-images.zip'), goodZip);

// ---------- 负例（不进 manifest 正例列表，仅供手工测试） ----------
// 1. 文本内容伪装成 .png
fs.writeFileSync(path.join(NEG_DIR, 'fake.png'), Buffer.from('this is plain text, not a png at all\n', 'utf8'));
// 2. 真 PNG 但扩展名是 .gif
fs.writeFileSync(path.join(NEG_DIR, 'mismatched.gif'), pngBlue);
// 3. zip-slip：条目名带 ../ 越界
const slipZip = makeZip([{ name: '../../../evil.png', data: pngBlue }]);
fs.writeFileSync(path.join(NEG_DIR, 'zip-slip.zip'), slipZip);
// 4. ZIP 内含非图片（文本）
const innerTextZip = makeZip([{ name: 'notes/readme.txt', data: Buffer.from('hello\n', 'utf8') }]);
fs.writeFileSync(path.join(NEG_DIR, 'zip-with-text.zip'), innerTextZip);
// 5. 条目数量超限（>100）
const many = [];
for (let i = 0; i < 105; i++) many.push({ name: `p/${i}.png`, data: pngBlue });
fs.writeFileSync(path.join(NEG_DIR, 'zip-too-many-entries.zip'), makeZip(many));
// 6. 解压总量超限：51MiB 全零数据，deflate 压缩后容器仅几十 KB，
//    可穿过 10MB 上传硬限制，真正触发 50MiB 解压总量校验
const zeros = Buffer.alloc(51 * 1024 * 1024);
fs.writeFileSync(
  path.join(NEG_DIR, 'zip-too-big-uncompressed.zip'),
  makeZip([{ name: 'zeros.bin', data: zeros, deflate: true }])
);
// 7. 超过上传大小上限的原始 PNG（随机像素不可压缩，压缩后仍 > 10 MiB）
const bigW = 256;
const bigH = Math.ceil((11 * 1024 * 1024) / (1 + bigW * 3));
fs.writeFileSync(path.join(NEG_DIR, 'too-large.png'), makePng(bigW, bigH, [1, 2, 3], true));

// ---------- manifest（仅正例，白名单下载用） ----------
const positive = fs.readdirSync(POS_DIR)
  .filter((f) => f !== 'manifest.json')
  .map((f) => ({
    file: f,
    sizeBytes: fs.statSync(path.join(POS_DIR, f)).size,
    kind: f.endsWith('.zip') ? 'zip' : 'image',
    description: {
      'sample-blue.png': '自制 32x32 蓝色 PNG',
      'sample-green.png': '自制 48x24 绿色 PNG',
      'sample-red.gif': '自制 1x1 红色 GIF',
      'sample-blue.jpg': '由 PNG 经 sips 转换的 JPEG',
      'sample-green.webp': '由 PNG 经 sips 转换的 WebP',
      'sample-images.zip': '含两张自制图片的合法 ZIP'
    }[f] || '自制样例'
  }));
fs.writeFileSync(path.join(POS_DIR, 'manifest.json'), JSON.stringify({ positive }, null, 2));
console.log(`样例生成完成：正例 ${positive.length} 个 -> samples/positive，负例 7 组 -> samples/negative`);
