# 本地文件接收与隔离工作台

上传文件必须通过服务端内容检查才能进入下载区；未通过检查的文件进入隔离区，只能查看状态与拒收原因，无法通过普通接口取回，清理时也不会误伤已通过检查的文件。所有状态变化均写入可查看的审计记录，页面与接口均不暴露本机绝对路径。

- 前端：Vue 3 + Vite（`web/`）
- 后端：Node.js + Express（`server/`），本地任务状态保存在 SQLite（Node 24 内置 `node:sqlite`，无需编译原生模块，**不使用 Docker**）

## 运行步骤

要求 Node.js ≥ 22（开发验证版本为 v24.15.0，用到内置 `node:sqlite`）。

```bash
# 1. 安装依赖
npm run install:all

# 2. 生成合法样例（零依赖脚本现场合成图片，无第三方版权问题）
npm run samples

# 3. 构建前端
npm run build

# 4. 启动后端（默认 3000 端口；如被占用可用 PORT=3210）
npm start
# 打开 http://localhost:3000
```

开发模式（前端热更新，`/api` 代理到 `http://localhost:3210`，可用 `VITE_API_TARGET` 覆盖）：

```bash
PORT=3210 npm run dev:server   # 终端 1
npm run dev:web                # 终端 2，打开 http://localhost:5173
```

## 限制策略（`server/src/config.js`）

| 项目 | 限制 |
| --- | --- |
| 单文件大小 | 10 MiB（multer 传输层硬限制 + 检查层复核） |
| 允许格式 | PNG / JPEG / GIF / WebP / ZIP |
| ZIP 条目数量 | ≤ 100 |
| ZIP 解压后总大小 | ≤ 50 MiB |
| ZIP 内部文件 | 仅允许上述图片格式，目录条目单独放行 |

## 安全设计与需求对照

### 1. 文件名、扩展名、浏览器 MIME 均不可信

- 类型判定只依据**文件头魔数**（`server/src/signatures.js`），不读取文件名与 `Content-Type` 做信任决策。
- 扩展名仅用于交叉比对：实际内容与扩展名不一致即拒收（如 PNG 内容改名 `.gif`）。
- 浏览器 MIME 只有在“明确声明了具体类型且与魔数冲突”时才拒收；`application/octet-stream` 这类空泛声明不影响判定。
- 原始文件名先经 `path.basename` 剥离目录成分并去除控制字符，仅用于展示与下载时的 `Content-Disposition`。

### 2. 服务端随机存储名，上传路径不可被用户控制

- 临时文件与最终存储名均由 `crypto.randomUUID() + 随机字节` 生成（`server/src/storage.js`），保留的扩展名取自服务端识别结果而非客户端输入。
- 落盘与下载前都执行 `realpath` 目录守卫，目标必须位于 `data/approved` 或 `data/quarantine` 之内；存储名再次经 `path.basename` 校验，拒绝任何含目录分隔符的输入。

### 3. ZIP 安全（`server/src/zip-inspect.js`，基于 yauzl 纯流式校验，不解压到磁盘）

- **目录范围**：拒绝绝对路径、盘符、反斜杠、包含 `..` 的条目名（zip-slip），yauzl 自身也会拦截非法相对路径。
- **数量**：条目计数超过 100 立即终止。
- **解压总量**：中央目录 `uncompressedSize` 预算 + 实际流式读取双重累计，超过 50 MiB 终止。
- **内部类型**：读取每个文件条目的头部魔数，非图片格式拒收。

### 4. 隔离区与普通下载隔离

- 检查不通过的文件移动到 `data/quarantine` 并记录拒收原因；不存在任何隔离文件下载路由，用已存在的 id 调下载接口返回 404。
- 超过上传硬上限被截断的请求同样写入隔离留痕与审计，但不产生物理文件。
- 清理接口逐条执行 `realpath` 守卫，**只可能删除 quarantine 目录内的文件**，不做目录级 `rm -rf`；即使数据库记录被篡改也无法触及 `data/approved`。

### 5. 审计留痕且不泄漏绝对路径

- SQLite 两张表：`files`（文件状态）与 `audit_logs`（上传通过/拒收、下载、清理、拦截等事件）。
- 对外 DTO（`toFileDto` / `toAuditDto`）只包含相对标识、状态、原因与时间，数据库与文件系统中的绝对路径不出现在任何 API 响应或页面文本中（已由 E2E 断言覆盖）。

## 目录结构

```
server/
  src/
    config.js          限制、允许类型、数据目录
    db.js              node:sqlite 表结构与 DTO（不输出绝对路径）
    signatures.js      魔数识别与 MIME 冲突判断
    zip-inspect.js     ZIP 流式安全校验
    inspector.js       上传检查流水线
    storage.js         随机存储名、realpath 守卫、安全删除
    routes/            upload / files / quarantine / audit / samples
    index.js           Express 入口，生产模式托管 web/dist
  scripts/generate-samples.js   样例与反例生成器
  samples/positive/    可合法使用的样例（manifest 白名单）
  samples/negative/    手工测试用反例（不对外提供下载）
web/                   Vue 3 界面（上传、已通过、隔离区、审计、样例四个页签）
data/                  运行后生成：approved/ quarantine/ tmp/ workbench.sqlite
e2e-check.cjs          Playwright 浏览器端到端检查（可选，需系统 Chrome）
```

## 样例说明

`npm run samples` 生成的全部素材均由脚本现场合成：PNG/GIF 为手工构造的最小合法文件，JPEG 由 macOS 自带 `sips` 从自制 PNG 转换，ZIP 由内置最小 ZIP 写入器打包，不存在第三方版权素材。

- 正例（`samples/positive`，页面“合法样例”可下载）：自制 PNG ×2、GIF、JPEG、合法图片 ZIP。
- 反例（`samples/negative`，仅供手工上传验证）：文本伪装 PNG、扩展名错配、zip-slip、ZIP 内含文本、条目超 100、解压总量超 50 MiB、单文件超 10 MiB。

## 接口一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/upload` | 单文件上传（multipart 字段 `file`），返回 approved/quarantined 结论 |
| GET | `/api/files` | 已通过文件列表 |
| GET | `/api/files/:id/download` | 仅 approved 文件可下载，隔离 id 返回 404 |
| GET | `/api/quarantine` | 隔离区列表（无下载路由） |
| DELETE | `/api/quarantine/:id` | 清理单条隔离文件（realpath 守卫） |
| POST | `/api/quarantine/purge` | 批量清理隔离区，approved 不受影响 |
| GET | `/api/audit` | 状态变化记录 |
| GET | `/api/samples` | 合法样例白名单 |
| GET | `/api/samples/:name/download` | 白名单内样例下载 |

## 本地验证

后端接口可直接用 curl 验证；浏览器流程可用：

```bash
npm install --no-save playwright@1.65.0   # 仅测试用，不写入依赖
node e2e-check.cjs                         # 使用系统 Chrome，断言隔离区无下载链接、无绝对路径泄漏等
```
