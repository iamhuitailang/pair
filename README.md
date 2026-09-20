# 🏕️ 一起去野（YeYou）

户外组队出行全栈项目：用户可以发起/加入户外活动（徒步、露营、骑行、野餐、攀岩），组队出行，分享路线和经验。

## 技术栈

- **后端**：纯 Node.js（零第三方依赖），内置 `node:http` + `node:sqlite`
- **前端**：纯 HTML + CSS + 原生 JS（无框架），移动端 M 站适配
- **数据库**：SQLite，所有数据表统一 `tb_yeyou_` 前缀

## 快速开始

```bash
node server/index.js
# 打开 http://localhost:8080/login.html
```

演示账号：

| 账号 | 密码 | 角色 |
|---|---|---|
| demo | 123456 | 普通用户 |
| momo | 123456 | 普通用户 |
| leader | 123456 | 领队（发官方活动、签到） |
| admin | admin123 | 管理员（审核、用户管理） |

## 目录结构

```
server/                     # 后端
  index.js                  # 服务入口（API 路由 + 静态资源托管）
  config.js                 # 配置
  routes.js                 # 路由表
  common/                   # 公共层（db / 统一返回 / 鉴权 / 工具）
  model/yeyou/              # 数据层（建表 + 各表 CRUD，表名 tb_yeyou_*）
  business/yeyou/           # 业务层
  controller/yeyou/         # 控制器层
  test/api.test.js          # API 联调测试（49 项）
  data/yeyou.db             # SQLite 数据库（首次启动自动建表+种子数据）
yeyou_web/                  # 用户端前端（M 站）
  login.html                # 登录/注册
  index.html                # 首页动态流
  activities.html           # 活动列表（类型/状态筛选、搜索）
  activity-detail.html      # 活动详情（报名/签到/评论/评价）
  activity-create.html      # 发起活动
  post-detail.html          # 动态详情（点赞/评论/关注）
  profile.html              # 个人中心（统计/徽章/足迹地图/装备库/我的活动）
  admin.html                # 管理后台（活动审核/用户管理/内容审核）
  css/common.css            # 自然主题全局样式
  js/                       # 按页面拆分的 JS 模块
```

## 接口规范

- 统一前缀 `/api/yeyou`
- 统一返回结构：`{ "code": 200, "msg": "success", "data": ... }`
- 鉴权：请求头 `Authorization: Bearer <token>`，未登录返回 `code: 401`，前端自动跳转登录页

主要接口：

| 模块 | 接口 |
|---|---|
| 用户 | `POST /user/register` `POST /user/login` `GET/PUT /user/profile` |
| 活动 | `GET /activity/list` `GET /activity/:id` `POST /activity` `PUT/DELETE /activity/:id` `POST /activity/:id/status` |
| 报名 | `POST /activity/:id/join` `POST /activity/:id/cancel` `POST /enrollment/:id/checkin` `GET /my/activities` |
| 动态 | `GET /post/feed` `POST /post` `POST /post/:id/like` |
| 评论 | `GET /comment/list` `POST /comment` `DELETE /comment/:id` |
| 评价 | `POST /review` `GET /review/activity/:id` |
| 关注 | `POST /follow/:id` `GET /follow/following/:id` |
| 装备/足迹/成就 | `GET|POST /gear` `GET|POST /footprint` `GET /achievement/my` |
| 管理员 | `GET /admin/users` `POST /admin/activity/:id/audit` `POST /admin/user/:id/status` |

## 测试

```bash
node server/test/api.test.js   # 49 项 API 联调测试
```
