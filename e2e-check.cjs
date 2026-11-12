const { chromium } = require('playwright');
const path = require('path');

const BASE = 'http://localhost:3210';
const POS = path.resolve(__dirname, 'server/samples/positive');
const NEG = path.resolve(__dirname, 'server/samples/negative');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto(BASE, { waitUntil: 'networkidle' });
  console.log('title:', await page.title());

  // 1. 上传合法 PNG（通过隐藏 input 设置文件）
  await page.setInputFiles('input[type=file]', [path.join(POS, 'sample-green.png')]);
  await page.waitForSelector('.upload-results li.ok');
  console.log('valid upload result:', (await page.locator('.upload-results li').innerText()).replace(/\n/g, ' | '));

  // 2. 上传伪装文件 -> 隔离
  await page.setInputFiles('input[type=file]', [path.join(NEG, 'fake.png')]);
  await page.waitForSelector('.upload-results li.bad');
  console.log('fake upload result:', (await page.locator('.upload-results li').innerText()).replace(/\n/g, ' | '));

  // 3. 隔离区页签可见拒收原因，且没有下载按钮
  await page.getByRole('button', { name: /隔离区/ }).click();
  await page.waitForSelector('.row-quarantine:visible');
  const qRows = await page.locator('.row-quarantine:visible').count();
  const reason = await page.locator('.reason-cell:visible').first().innerText();
  const qDownloadLinks = await page.locator('.row-quarantine:visible a').count();
  console.log(`quarantine rows=${qRows}, reason="${reason}", download links in quarantine=${qDownloadLinks}`);

  // 4. 已通过页签存在下载链接
  await page.getByRole('button', { name: /已通过/ }).click();
  await page.waitForSelector('.table:visible tbody tr');
  const approvedLinks = await page.locator('.table:visible tbody a').count();
  console.log('approved download links:', approvedLinks);

  // 5. 审计页签
  await page.getByRole('button', { name: /状态记录/ }).click();
  await page.waitForSelector('.table:visible tbody tr');
  const auditEvents = await page.locator('.table:visible tbody tr').count();
  console.log('audit events shown:', auditEvents);

  // 6. 样例页签并触发下载
  await page.getByRole('button', { name: /合法样例/ }).click();
  await page.waitForSelector('.sample-card:visible');
  const sampleCount = await page.locator('.sample-card').count();
  console.log('sample cards:', sampleCount);

  // 7. 页面文本不得出现本机绝对路径
  const bodyText = await page.locator('body').innerText();
  const leaks = bodyText.includes('/Users/');
  console.log('absolute path leaked in page text:', leaks);

  // 8. 隔离清理（单条），确认 approved 数量不变
  await page.getByRole('button', { name: /隔离区/ }).click();
  const beforeApproved = await page.locator('.pill-green').innerText();
  page.once('dialog', (d) => d.accept());
  await page.locator('.row-quarantine:visible .btn-danger').first().click();
  await page.waitForTimeout(300);
  await page.getByRole('button', { name: /已通过/ }).click();
  const afterApproved = await page.locator('.pill-green').innerText();
  console.log(`approved count before/after quarantine cleanup: ${beforeApproved} -> ${afterApproved}`);

  const pass = qRows >= 1 && reason && qDownloadLinks === 0 && approvedLinks >= 1 &&
    auditEvents >= 2 && sampleCount >= 4 && !leaks && beforeApproved === afterApproved && errors.length === 0;
  console.log('console errors:', errors);
  console.log(pass ? 'RESULT: PASS' : 'RESULT: FAIL');
  await browser.close();
  process.exit(pass ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
