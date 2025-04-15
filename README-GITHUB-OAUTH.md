# GitHub OAuth 配置指南

本文档提供了如何为 CodeInterpreter AI 项目配置 GitHub OAuth 的详细步骤。

## 1. 创建 GitHub OAuth 应用

1. 登录您的 GitHub 账户
2. 点击右上角的头像，选择 "Settings"
3. 在左侧菜单中，选择 "Developer settings"
4. 点击 "OAuth Apps"
5. 点击 "New OAuth App" 按钮
6. 填写应用信息：
   - **Application name**: CodeInterpreter AI
   - **Homepage URL**: http://localhost:3000
   - **Application description**: 一个智能代码解释器应用，能够分析、解释和执行GitHub仓库代码
   - **Authorization callback URL**: http://localhost:8000/auth/github/callback
7. 点击 "Register application" 按钮

## 2. 获取客户端 ID 和密钥

注册应用后，GitHub 会显示您的 Client ID。点击 "Generate a new client secret" 按钮生成 Client Secret。

**重要提示**：请妥善保管您的 Client Secret，不要将其提交到版本控制系统中。

## 3. 配置环境变量

1. 在项目的 `backend` 目录中，复制 `.env.example` 文件并重命名为 `.env`：

```bash
cd backend
cp .env.example .env
```

2. 编辑 `.env` 文件，填入您的 GitHub OAuth 应用的 Client ID 和 Client Secret：

```
# GitHub OAuth 配置
GITHUB_CLIENT_ID=您的客户端ID
GITHUB_CLIENT_SECRET=您的客户端密钥
REDIRECT_URI=http://localhost:8000/auth/github/callback
FRONTEND_URL=http://localhost:3000

# 服务器配置
HOST=0.0.0.0
PORT=8000
```

## 4. 启动应用

配置完成后，您可以启动应用：

1. 启动后端服务：

```bash
cd backend
python -m app.main
```

2. 启动前端服务：

```bash
cd frontend
npm start
```

## 5. 测试 OAuth 流程

1. 打开浏览器，访问 http://localhost:3000
2. 点击 "连接GitHub并授权" 按钮
3. 您将被重定向到 GitHub 授权页面
4. 授权后，您将被重定向回应用，并显示您的 GitHub 用户信息

## 6. 常见问题

### 授权失败

如果授权过程中出现错误，请检查：

1. Client ID 和 Client Secret 是否正确
2. 回调 URL 是否与 GitHub OAuth 应用中配置的一致
3. 后端服务是否正常运行

### 跨域问题

如果遇到跨域问题，请确保：

1. 前端的 `package.json` 中已配置正确的代理：`"proxy": "http://localhost:8000"`
2. 后端的 CORS 中间件已正确配置

### 令牌存储

当前实现将令牌存储在内存中，这意味着重启服务器后，所有用户都需要重新授权。在生产环境中，应该使用数据库或其他持久化存储方式来保存令牌。
