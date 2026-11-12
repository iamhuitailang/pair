# 网页采集与变更追踪工具

一个纯本地运行的演示项目：配置采集规则后，程序沿页面链接采集标题、正文和更新时间，
保存每一轮结果，并标记页面的 **新增（new）/ 修改（modified）/ 未变（unchanged）/ 消失（disappeared）/ 错误（error）**。
前端可查看采集记录、两轮运行之间的内容 diff，并导出结果。

- 后端：FastAPI + SQLite（标准库 sqlite3，无需外部服务）
- 前端：Vue 3 + Vite
- 采集目标：`sample_site/` 本地静态站点，**演示全程不依赖外网**
- 不使用 Docker

## 目录结构

```
backend/        FastAPI 后端（采集引擎、API、SQLite 持久化）
frontend/       Vue 3 前端
sample_site/    本地演示站点（静态 HTML）
  change_site.py  一键制造/恢复站点变化，用于演示变更追踪
```

## 快速开始

需要 Python 3.10+ 和 Node 18+。

```bash
# 1. 启动样例站点（采集目标，端口 8080）
python3 -m http.server 8080 --directory sample_site

# 2. 启动后端（端口 8000）
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8000

# 3. 启动前端（端口 5173，/api 已代理到 8000）
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173 ，在「采集规则」页新建规则：

| 字段 | 推荐值（针对样例站点） |
| --- | --- |
| 起始地址 | `http://127.0.0.1:8080/index.html` |
| 标题选择器 | `h1` |
| 正文选择器 | `.content` |
| 更新时间选择器 | `.updated` |
| 下一页选择器 | `a.next-page` |
| 链接范围 | 页面内全部链接 |

## 演示变更追踪

```bash
# 第一轮采集（全部为 new，作为基线）后：
python3 sample_site/change_site.py apply
# 模拟：修改资料二、下线资料三、新增资料八

# 回到页面再次「运行」，第二轮即可看到：
#   modified=3（资料二 + 两个列表页）、disappeared=1（资料三）、new=1（资料八）
# 在运行详情页点「与上一轮对比」可逐行查看正文 diff。

# 演示完恢复站点：
python3 sample_site/change_site.py restore
```

## 采集范围与规则说明

- **同域限制**：只采集与起始地址（或「允许域名」）host:port 完全相同的链接，
  外链、`mailto:`、`javascript:` 等一律忽略。
- **URL 规范化**：协议/域名小写、去默认端口、去 fragment、查询参数排序、
  剔除 `utm_*` 等跟踪参数、去末尾斜杠。规范化后的 URL 是去重与增量对比的唯一键。
- **去重**：同一轮内相同规范化 URL 只入队一次；每轮受 `max_pages`（页数）和
  `max_depth`（深度）限制。
- **分页**：配置「下一页选择器」（如 `a.next-page`）后，分页链接会被一并跟随；
  「链接范围」设为 `仅跟随下一页` 时可只翻页不抓正文链接。
- **增量运行**：每轮与上一轮已完成运行按 URL 对比正文 SHA-256，标记
  new / modified / unchanged；上一轮有而本轮未访问到的页面标记为 disappeared。
  每轮快照完整入库，历史结果永不覆盖。

## 限速与重试策略

- **限速**：单工作线程串行抓取，同一规则两次请求之间至少间隔 `delay_seconds`
  秒（默认 0.5s），不会并发打目标站。
- **超时**：每次请求超时 `timeout_seconds` 秒（默认 10s）。
- **重试**：仅对 **5xx / 429 / 网络错误** 重试，指数退避（0.5s、1s、2s…，上限 5s），
  最多 `max_retries` 次（默认 2）；**4xx（如 404）不重试**，直接记为 error。
- 请求携带标识 UA：`LocalCrawlTracker/1.0`。

## API 概览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/POST | `/api/rules` | 规则列表 / 新建 |
| GET/PUT/DELETE | `/api/rules/{id}` | 规则详情 / 更新 / 删除 |
| POST | `/api/rules/{id}/run` | 启动一轮采集（排队执行） |
| GET | `/api/runs?rule_id=` | 运行列表（含排队/处理中/完成计数） |
| GET | `/api/runs/{id}` | 运行详情 |
| GET | `/api/runs/{id}/pages?status=` | 当轮页面（可按状态筛选） |
| GET | `/api/runs/{id}/diff?compare_to=` | 与上一轮（或指定轮）正文 diff |
| GET | `/api/pages/{id}/diff` | 单页 diff |
| GET | `/api/runs/{id}/export?format=json\|csv` | 导出当轮结果 |

## 持久化

规则、运行记录、每轮页面快照全部保存在 `backend/data/crawler.db`（SQLite，WAL 模式），
重启服务后历史结果与规则均保留。删除该文件即可重置全部数据。
