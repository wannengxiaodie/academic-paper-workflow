# 医学职称论文写作全流程自动化平台 - 部署指南

## 架构概述

- **前端**：单页 HTML 应用，部署到 GitHub Pages
- **后端**：FastAPI Python 服务，部署到 Vercel / Render / Railway / 自有服务器

---

## 一、前端部署（GitHub Pages）

### 自动部署

1. 推送代码到 GitHub 仓库的 `main` 分支
2. GitHub Actions 会自动执行部署（已配置 `.github/workflows/deploy-pages.yml`）
3. 在仓库 Settings → Pages 中选择 `GitHub Actions` 作为来源

### 手动验证

访问：`https://<你的用户名>.github.io/<仓库名>/`

### 配置后端地址

前端页面打开后，点击右上角状态指示器（"演示模式"或"后端已连接"），输入后端 API 地址即可。

也可以通过 URL 参数直接指定：
```
https://<你的用户名>.github.io/<仓库名>/?api=https://your-backend.example.com
```

---

## 二、后端部署

### 方式 1：Vercel（推荐，免费）

1. 登录 [vercel.com](https://vercel.com)
2. Import Project → 选择你的 GitHub 仓库
3. Framework Preset 选 `Other`
4. Build Command 留空
5. Output Directory 留空
6. 点击 Deploy

部署成功后会得到一个域名，如 `https://your-project.vercel.app`

> 注意：Vercel 是 Serverless 部署，不支持长连接/WebSocket，SSE 可能有超时限制。

### 方式 2：Render（推荐，免费额度）

1. 登录 [render.com](https://render.com)
2. New → Web Service
3. 连接你的 GitHub 仓库
4. 配置：
   - Runtime: `Docker`
   - Build Command: 留空
   - Start Command: 留空
5. 选择免费套餐（Free）
6. 点击 Create Web Service

部署成功后得到一个 `onrender.com` 域名。

### 方式 3：Railway

1. 登录 [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo
3. 选择仓库
4. 自动检测 Dockerfile 并部署

### 方式 4：自有服务器（Docker）

```bash
# 克隆代码
git clone <你的仓库地址>
cd academic-paper-workflow

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

服务默认监听 `8000` 端口。

### 方式 5：自有服务器（直接运行）

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 三、环境变量配置

后端支持以下环境变量（均可选）：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ENV` | 运行环境 (development/production) | development |
| `PORT` | 服务端口 | 8000 |
| `OPENAI_API_KEY` | OpenAI API Key（用于 AI 写作增强） | 空 |
| `ANTHROPIC_API_KEY` | Anthropic API Key | 空 |

### 各平台环境变量设置位置

- **Vercel**: Settings → Environment Variables
- **Render**: Environment → Environment Variables
- **Railway**: Variables
- **Docker**: `docker-compose.yml` 中添加

---

## 四、Nginx 反向代理配置（可选）

如果使用自有服务器并需要绑定域名：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
}
```

---

## 五、健康检查

部署后验证服务是否正常：

```bash
curl https://your-backend.example.com/health
```

正常返回：
```json
{
  "success": true,
  "message": "healthy",
  "data": {
    "version": "1.0.0",
    "journals_count": 57,
    "ai_enabled": false
  }
}
```

---

## 六、项目结构

```
.
├── backend/                  # 后端 FastAPI 服务
│   ├── main.py              # 主入口
│   ├── config.py            # 配置
│   ├── requirements.txt     # Python 依赖
│   ├── agents/              # Agent 层
│   ├── services/            # 服务层
│   ├── data/                # 数据层
│   ├── models/              # 数据模型
│   └── utils/               # 工具函数
├── pages/                   # 前端页面
│   └── index.html
├── .github/workflows/       # GitHub Actions
│   └── deploy-pages.yml     # Pages 自动部署
├── Dockerfile               # Docker 镜像
├── docker-compose.yml       # Docker Compose
├── vercel.json              # Vercel 配置
└── DEPLOY.md                # 本文件
```
