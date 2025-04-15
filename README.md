# CodeInterpreter AI

CodeInterpreter AI 是一个智能代码解释器应用，允许用户输入 GitHub 仓库地址，通过 OAuth 授权访问，然后通过与 LLM 交互来提问并理解该仓库的代码内容。

## 功能特点

- **GitHub OAuth 认证**：安全地连接到用户的 GitHub 账户
- **代码仓库下载**：自动下载和处理 GitHub 仓库
- **代码分块**：将代码分割成小块，便于分析和理解
- **向量嵌入**：使用先进的嵌入模型将代码转换为向量表示
- **语义搜索**：基于用户问题查找相关代码块
- **智能问答**：使用 LLM 基于检索到的代码块回答用户问题
- **对话历史**：记录用户问题和 AI 回答，形成对话历史

## 技术栈

- **前端**：React、React Router、Axios
- **后端**：Python FastAPI
- **数据库**：PostgreSQL（可选 SQLite）
- **向量数据库**：ChromaDB
- **任务队列**：Celery + Redis
- **嵌入模型**：Sentence Transformers (all-MiniLM-L6-v2)
- **LLM**：OpenAI GPT API

## 系统架构

![系统架构](docs/architecture.png)

系统由以下主要组件组成：

1. **前端应用**：用户界面，包括仓库提交、认证和问答界面
2. **后端 API**：处理认证、仓库下载、代码处理和问答请求
3. **任务队列**：处理长时间运行的任务，如仓库下载和代码处理
4. **向量数据库**：存储代码块的向量表示，支持语义搜索
5. **关系数据库**：存储用户、会话、仓库和任务信息

## 安装与设置

### 前提条件

- Docker 和 Docker Compose
- GitHub OAuth 应用（用于认证）
- OpenAI API 密钥（用于 LLM 问答）

### 使用 Docker Compose

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/code-interpreter-ai.git
cd code-interpreter-ai
```

2. 创建环境配置文件：

```bash
cp backend/.env.example backend/.env
```

3. 编辑 `.env` 文件，填入必要的配置：

```
# GitHub OAuth 配置
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_REDIRECT_URI=http://localhost:3000/auth/callback

# OpenAI API 配置
OPENAI_API_KEY=your_openai_api_key
```

4. 启动服务：

```bash
docker-compose up -d
```

5. 访问应用：

打开浏览器，访问 http://localhost:3000

### 手动安装

#### 后端

1. 进入后端目录：

```bash
cd backend
```

2. 创建虚拟环境：

```bash
python -m venv venv
source venv/bin/activate  # 在 Windows 上使用 venv\Scripts\activate
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 创建环境配置文件：

```bash
cp .env.example .env
```

5. 编辑 `.env` 文件，填入必要的配置

6. 启动 Redis（用于 Celery）：

```bash
# 使用 Docker 启动 Redis
docker run -d -p 6379:6379 redis:alpine
```

7. 启动 Celery Worker：

```bash
celery -A app.celery_worker.celery_app worker --loglevel=info
```

8. 启动后端服务：

```bash
uvicorn app.main:app --reload
```

#### 前端

1. 进入前端目录：

```bash
cd frontend
```

2. 安装依赖：

```bash
npm install
```

3. 启动开发服务器：

```bash
npm start
```

## 使用指南

1. 打开应用，点击"连接 GitHub 并授权"按钮
2. 登录 GitHub 并授权应用访问您的仓库
3. 输入 GitHub 仓库 URL，点击"分析仓库"按钮
4. 等待仓库处理完成
5. 在问答面板中输入问题，点击"提问"按钮
6. 查看 AI 生成的回答和相关代码块

## API 文档

启动后端服务后，可以访问 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 开发指南

项目采用分段式提示词驱动开发，每个功能模块都有详细的文档：

- [GitHub OAuth 认证](README-GITHUB-OAUTH.md)
- [仓库下载与处理](README-REPOSITORY-DOWNLOAD.md)
- [代码分块](README-CODE-CHUNKING.md)
- [嵌入生成与向量存储](README-EMBEDDING.md)
- [RAG 检索与 LLM 问答](README-RAG-LLM.md)
- [前端问答界面](README-FRONTEND-QA.md)

## 贡献指南

1. Fork 仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add some amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件

## 联系方式

如有问题或建议，请提交 Issue 或联系项目维护者。

# PROMPT_SEGMENT_9_COMPLETE
