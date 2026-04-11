# 🐾 PetPix Studio

AI 宠物数字内容服务 — 让你的毛孩子变身艺术大片主角。

## 快速启动

```bash
cd petpix-studio
python server.py
```

访问 http://localhost:8000

## 功能

- **宠物照片上传** — 支持 JPG/PNG，拖拽或点击上传
- **AI 风格化** — 守护神、中秋限定等风格（API 余额不足时自动 mock）
- **套系购买** — 体验版/写真/守护神/全能礼包
- **模拟支付** — 微信支付/支付宝（mock）
- **订单管理** — 内存订单系统（重启后清空）

## API

| Method | Path | 说明 |
|--------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/styles | 获取风格列表 |
| POST | /api/generate | 生成图片（multipart: file + style） |
| GET | /api/pricing | 获取定价方案 |
| POST | /api/order/create | 创建订单 |
| POST | /api/order/pay | 模拟支付 |
| GET | /api/orders | 查询所有订单 |
| GET | /api/order/:id | 查询单个订单 |
| POST | /api/share | 生成分享链接 |

## 文件结构

```
petpix-studio/
├── server.py          # HTTP 服务（纯标准库）
├── mock_order.py      # 内存 Mock 订单系统
├── generator.py       # 图片生成逻辑
├── styles.py          # 风格配置
├── static/
│   └── index.html     # H5 单页应用
├── outputs/           # 生成的图片
└── uploads/           # 用户上传
```

## 技术栈

- 后端：Python 标准库（http.server）
- 前端：纯 HTML + CSS + JS，零依赖
- 配色：珊瑚粉 #FF6B6B + 奶油白 #FFF9F5
- 适配：iPhone SE ~ iPhone 15 Pro Max
