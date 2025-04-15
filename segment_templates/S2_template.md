# PROMPT_SEGMENT_2: GitHub OAuth 认证流程

**依赖:** Segment 1 (项目结构和基础前端)

**任务:**
1.  **后端:**
    * 实现一个API端点（例如 `/auth/github`）用于启动GitHub OAuth流程，重定向用户到GitHub授权页面。你需要注册一个GitHub OAuth App来获取 Client ID 和 Client Secret（提示：可以在代码中使用占位符，实际值通过环境变量配置）。
    * 实现一个回调API端点（例如 `/auth/github/callback`），用于接收GitHub在用户授权后返回的 `code`。
    * 在该回调端点中，使用 `code`、Client ID 和 Client Secret 向GitHub请求获取 `access_token`。
    * **安全地**存储 `access_token` 与用户信息关联（初期可以简单地存储在内存或临时文件中，后续Segment再考虑持久化）。
2.  **前端:**
    * 修改 "连接GitHub并授权" 按钮的点击事件，使其调用后端的 `/auth/github` 端点，触发重定向。
    * （可选）在认证成功后，前端可以显示用户的GitHub用户名或头像，并更新UI状态表示已连接。

**预期产出:**
* 后端实现GitHub OAuth认证逻辑的API端点。
* 前端按钮触发认证流程。
* 成功获取并（临时）存储`access_token`的机制。
* 完成后，在相关的后端认证代码文件和前端组件文件末尾添加 `# PROMPT_SEGMENT_2_COMPLETE` 或 `// PROMPT_SEGMENT_2_COMPLETE` 注释。
* **总结:** 简要说明GitHub OAuth流程的实现方式，包括涉及的API端点和前端交互。
