# 游戏事件回放分析平台

服务端接收一局游戏产生的事件，整理成时间线并汇总对局结果；网页端按玩家/日期/状态筛选对局，查看原始事件、异常和统计指标，并支持导出。

- 后端：FastAPI + SQLite（stdlib sqlite3，无 ORM）
- 前端：Vue 3 + Vite，构建后由 FastAPI 托管，本地单进程运行，无需 Docker
- 所有统计指标由服务端从原始事件重算，**客户端上报的任何统计结果一律不可信**

## 本地启动

```bash
# 后端（Python 3.11+）
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8010

# 前端（首次或前端代码变更后）
cd frontend
npm install
npm run build        # 产物 frontend/dist 由 FastAPI 托管

# 打开 http://localhost:8010
```

前端开发调试也可 `npm run dev`（Vite 已配置 `/api` 代理到 8000 端口）。

## 事件格式

`POST /api/events/batch`，请求体 `{"events": [...]}`，单批最多 500 条，请求体上限 1MB（超限返回 413）。每条事件：

| 字段 | 类型 | 说明 |
|---|---|---|
| `event_id` | string | 全局唯一，幂等键 |
| `session_id` | string | 对局 ID |
| `player_id` | string | 玩家 ID |
| `event_type` | string | 事件类型 |
| `occurred_at` | ISO8601 | **必须带时区**，服务端归一化为 UTC |
| `sequence` | int ≥ 0 | 序号，**由每个玩家客户端独立维护**（按 `(session_id, player_id)` 各自计数） |
| `schema_version` | int | 数据格式版本，当前支持 `{1}` |
| `payload` | object | 事件负载 |

接口逐条返回结果，一条坏事件不影响同批其他事件：

```json
{"total": 3, "accepted": 1, "duplicates": 1, "rejected": 1,
 "results": [
   {"event_id": "e1", "status": "accepted", "reason": null},
   {"event_id": "e2", "status": "duplicate", "reason": null},
   {"event_id": "e3", "status": "rejected", "reason": "unsupported_schema_version:99"}
 ]}
```

## 重复、乱序、迟到事件的处理规则

- **重复提交**：`event_id` 已存在且内容哈希一致 → 返回 `duplicate`，不重复入库、不重复计数；`event_id` 相同但内容不同 → `rejected: event_id_conflict`。
- **未知 schema_version**：直接拒收（`unsupported_schema_version`），绝不按当前版本悄悄解释。
- **乱序**：不影响接收。时间线展示按 `(occurred_at, event_id)` 排序；异常检测按每个玩家的 `sequence` 顺序进行。
- **迟到事件**：格式合法即**总是接收**，入库后该对局的分析结果自动重算（缓存按事件数失效）。迟到事件若导致序号与时间顺序矛盾，会被标记为「时间倒退」异常——这是规则的自然结果，便于发现客户端时钟或补传问题。
- 原始事件入库后不可变，永远保留。

## 时间线重建与指标计算

分析是纯函数 `analyze(events, rules_version)`（`backend/app/analysis.py`）：相同原始事件 + 相同规则版本必得相同结果。结果按 `(session_id, rules_version)` 缓存；规则升级时 bump `RULES_VERSION`，新旧结果共存，可用 `GET /api/sessions/{id}?rules_version=` 区分。

**异常检测**（sequence 按 `(session_id, player_id)` 分组检查）：

| 异常 | 判定 |
|---|---|
| `missing_sequence` | 某玩家 `0..max(sequence)` 中未出现的序号 |
| `duplicate_sequence` | 同一玩家同一 sequence 出现多个不同 event_id |
| `time_regression` | 按 sequence 排序后，occurred_at 早于前一事件 |
| `unknown_event_type` | event_type 不在已知类型表内 |

**指标**：

- 局时长 = `max(occurred_at) − min(occurred_at)`
- 关键行为次数 = 按 `event_type` 对原始事件计数
- 胜负状态：有 `game_end` 事件 → `finished`，胜者取**首个**（按 occurred_at）`game_end` 的 `payload.winner_player_id`；否则 `in_progress`
- 事件完整率 = 各玩家「实际收到的不同 sequence 数」之和 ÷ 各玩家「max(sequence)+1」之和

## 网页端

- 对局列表：按日期范围、玩家 ID、对局状态（已结束/进行中）筛选；展示时长、胜者、完整率、异常数；「导出 CSV / 导出 JSON」带当前筛选条件。
- 对局详情：指标面板、异常列表、完整时间线（异常行高亮，点击展开原始 payload），可下载本局 JSON。

## 用示例数据验证乱序 / 重试 / 坏事件

启动服务后运行：

```bash
cd backend
python scripts/generate_sample_data.py http://localhost:8010
```

脚本注入 5 批数据并打印每批的接收结果：

1. **s-normal**：正常对局，9 条全部接收。
2. **s-ooo**：同批乱序 + 缺序号 [1,2] + 时间倒退 → 详情页可见对应异常，时间线仍按时间排序，完整率 4/6。
3. **整批重试** s-normal → 全部 `duplicate`，事件数不翻倍。
4. **s-mixed**：7 条中 4 条坏事件（缺字段 / 未知版本 / 非法时间 / 负序号）被逐条拒收，3 条好事件正常接收；`teleport_hack` 被标记未知类型。
5. **迟到事件**：s-normal 结束后补发一条更早发生的事件 → 接收并重算，完整率 100%，因序号与时间矛盾被标记时间倒退。

## 测试

```bash
cd backend
.venv/bin/python -m pytest tests/ -q
```

覆盖：去重不重复计数、event_id 冲突、部分失败、批次/请求体大小限制、未知版本拒收、分析确定性（输入乱序结果一致）、缺失/重复/倒退/未知类型检测、完整率与胜负计算、客户端上报统计被忽略。

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/events/batch` | 批量写入，逐条返回结果 |
| GET | `/api/sessions` | 对局列表（date_from/date_to/player_id/status/page） |
| GET | `/api/sessions/{id}` | 时间线 + 异常 + 指标（可指定 rules_version） |
| GET | `/api/sessions/export?format=csv\|json` | 按筛选条件导出 |
| GET | `/api/meta` | 支持的 schema_version、当前 rules_version、已知事件类型 |
