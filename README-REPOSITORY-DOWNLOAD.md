# GitHub 仓库下载与处理指南

本文档提供了 CodeInterpreter AI 项目中 GitHub 仓库下载与处理功能的详细说明。

## 功能概述

CodeInterpreter AI 能够通过 GitHub OAuth 认证获取用户的访问令牌，然后使用该令牌下载用户指定的 GitHub 仓库。下载完成后，系统将对仓库代码进行处理（后续实现），以便用户能够通过自然语言提问来理解代码。

## 实现细节

### 后端实现

1. **仓库管理器 (`repository_manager.py`)**
   - 使用异步方式克隆 GitHub 仓库
   - 通过 Git 命令行工具实现仓库克隆
   - 提供任务状态跟踪和管理
   - 实现错误处理和安全措施

2. **API 端点 (`repository.py`)**
   - `/api/repository`: 接收仓库 URL 并启动处理任务
   - `/api/repository/status/{task_id}`: 获取任务处理状态

### 前端实现

1. **仓库提交表单 (`App.js`)**
   - 验证输入的 GitHub 仓库 URL
   - 发送请求到后端 API
   - 显示处理状态和结果

2. **任务状态组件 (`TaskStatus.js`)**
   - 实时轮询任务状态
   - 显示任务进度和结果
   - 处理错误情况

## 使用流程

1. 用户通过 GitHub OAuth 认证登录
2. 用户输入 GitHub 仓库 URL 并提交
3. 系统验证 URL 格式和用户认证状态
4. 系统创建异步任务，开始下载仓库
5. 前端显示任务状态模态框，实时更新进度
6. 下载完成后，系统进入处理阶段（后续实现）
7. 处理完成后，用户可以开始提问（后续实现）

## 技术实现

### 仓库克隆

系统使用 Git 命令行工具克隆仓库，通过以下方式实现：

```python
# 构建带有访问令牌的 URL
auth_url = re.sub(r'(https?://)', f'\\1{access_token}@', repo_url)

# 使用 asyncio 异步执行 git clone 命令
process = await asyncio.create_subprocess_exec(
    'git', 'clone', auth_url, repo_dir,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
```

### 任务状态管理

系统使用内存字典存储任务状态，每个任务包含以下信息：

- 任务 ID
- 仓库 URL
- 会话 ID
- 状态（pending, downloading, processing, completed, failed）
- 创建时间和更新时间
- 状态消息和错误信息（如果有）

### 异步处理

系统使用 Python 的 `asyncio` 实现异步处理，避免长时间运行的任务阻塞 Web 服务器：

```python
# 创建异步任务
task = asyncio.create_task(process_repository(repo_url, access_token, task_id, session_id))
```

## 安全考虑

1. **访问令牌保护**
   - 访问令牌仅在后端使用，不暴露给前端
   - 在日志和错误消息中隐藏访问令牌

2. **仓库隔离**
   - 每个仓库下载到独立的目录，避免冲突
   - 使用会话 ID 和仓库 ID 创建唯一目录

3. **错误处理**
   - 捕获并记录所有异常
   - 向用户提供友好的错误消息

## 后续改进

1. **持久化存储**
   - 使用数据库存储任务状态，而不是内存字典
   - 实现服务器重启后的任务恢复

2. **任务队列**
   - 使用专业的任务队列系统（如 Celery）替代简单的 asyncio 实现
   - 添加任务优先级和资源限制

3. **WebSocket 通知**
   - 使用 WebSocket 替代轮询，实现实时状态更新
   - 减少服务器负载和网络流量

4. **并行处理**
   - 实现多仓库并行下载和处理
   - 添加任务调度和资源分配
