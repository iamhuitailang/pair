# 一起去野 🌿

户外活动组队全栈项目：用户可以发起 / 报名徒步、露营、骑行、野餐、攀岩等户外活动，组队出行、签到互评，并在社区分享照片、路线与装备。

- 后端：原生 Node.js（内置 `http`，**零第三方依赖**），model / business / controller 分层
- 数据：统一存放在 `model/yeyou/` 下，每张表一个 `tb_yeyou_*.json` 文件（含基础增删改查）
- 用户端：纯 HTML + CSS + 原生 JavaScript（M 站移动端），代码按页面 / 样式 / 逻辑拆分，位于 `yeyou_web/`
- 前后端同源部署：同一个 Node 服务同时提供 API 与静态页面，开箱即用

## 快速开始

```bash
npm start
# 或
node server.js
```

浏览器打开 http://localhost:3000 （建议使用手机模式 / 390px 宽度浏览）

首次启动会自动写入演示数据。演示账号（密码均为 `123456`）：

| 角色 | 手机号 |
| --- | --- |
| 普通用户（小鹿） | 13800000004 |
| 认证领队（山风） | 13800000002 |
| 管理员（山野管家） | 13800000001 |

## 功能一览

- **活动模块**：发起活动（标题/类型/时间/地点/集合点/人数/难度/AA 费用/里程爬升/路线）、列表筛选（时间·地点·类型·状态）、详情（示意地图集合点、路线、成员、评论）、报名/取消、领队手动签到、结束后队友互评
- **社交模块**：首页动态（照片/路线/装备）、关注/粉丝、关注流、点赞、评论、成就徽章（爬山次数/公里数/爬升）
- **个人中心**：足迹地图、数据统计、装备库 CRUD、我的活动（已报名/已发起/历史）、编辑资料、申请领队
- **角色体系**：普通用户 / 认证领队 / 管理员（活动审核、用户角色管理、内容审核）
- **登录守卫**：所有页面必须登录，token 存于 localStorage，接口返回 401 自动跳转登录页

## 目录结构

```
├── server.js                 # HTTP 入口（API + 静态站点）
├── controller/               # 接口层
│   ├── router.js             # 路由表 + 鉴权中间件
│   └── ctrl-*.js             # 各模块 controller
├── business/                 # 业务逻辑层
│   ├── bus-user.js           # 注册登录/资料/统计/足迹/徽章/领队
│   ├── bus-activity.js       # 活动/报名/签到/评价/评论
│   ├── bus-social.js         # 动态/点赞/关注
│   ├── bus-gear.js           # 装备库
│   └── bus-admin.js          # 管理后台
├── model/
│   └── yeyou/                # ★ 所有数据表（tb_yeyou_*.json）
│       ├── store.js          # 通用表对象（insert/update/remove/find）
│       ├── index.js          # 各表 model + schema + 枚举
│       └── seed.js           # 演示数据初始化
├── utils/                    # 统一响应 / 鉴权 token / 工具
├── yeyou_web/                # 用户端（纯 HTML/CSS/JS）
│   ├── pages/*.html
│   ├── css/                  # base / components / pages
│   ├── js/                   # api 封装 + 各页面逻辑（模块化拆分）
│   └── images/               # 内置风景 SVG 插画
└── API.md                    # 接口文档
```

## 数据表

`tb_yeyou_user`、`tb_yeyou_activity`、`tb_yeyou_signup`、`tb_yeyou_post`、`tb_yeyou_comment`、`tb_yeyou_review`、`tb_yeyou_follow`、`tb_yeyou_gear`、`tb_yeyou_post_like`、`tb_yeyou_achievement`、`tb_yeyou_checkin`，字段见 `model/yeyou/index.js` 的 `schema`。

## 说明

- JSON 文件存储是为了零依赖、易演示而设计的数据访问层（接口签名与常规 ORM 表对象一致），后续可平滑替换为 MySQL。
- 地图为内置示意地图（经纬度打点），无外部地图服务依赖。
