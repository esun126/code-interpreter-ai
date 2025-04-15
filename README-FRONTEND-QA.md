# 前端 - 用户提问界面与结果展示实现指南

本文档提供了 CodeInterpreter AI 项目中前端用户提问界面与结果展示功能的详细说明。

## 功能概述

用户提问界面与结果展示是 CodeInterpreter AI 的核心交互功能，允许用户向已处理的 GitHub 仓库提问，并获取基于代码内容的智能回答。该功能通过 RAG（检索增强生成）技术，结合向量检索和大型语言模型，为用户提供准确、相关的代码解释和分析。

## 实现细节

### 问答面板组件 (`QuestionPanel.js`)

问答面板是一个专门的 React 组件，用于处理用户提问和展示回答。主要功能包括：

1. **用户输入**：提供文本区域，让用户输入关于代码库的问题。

2. **API 调用**：将用户问题发送到后端 `/api/repository/question` 端点，获取 LLM 生成的回答。

3. **结果展示**：清晰地展示 LLM 的回答、相关代码块和元数据。

4. **对话历史**：记录用户的问题和 LLM 的回答，形成对话历史。

5. **错误处理**：处理 API 调用错误、认证失败等异常情况，提供友好的错误信息。

### 与主应用的集成 (`App.js`)

问答面板与主应用的集成主要通过以下方式实现：

1. **条件渲染**：仅在仓库处理完成后显示问答面板，避免用户在仓库未处理完成时提问。

2. **状态检查**：在任务状态模态框关闭后，检查任务是否已完成，如果已完成则显示问答面板。

3. **错误传递**：将问答面板中的错误传递给主应用，统一显示错误信息。

## 用户界面

### 问答面板

问答面板包含以下 UI 元素：

1. **标题和说明**：清晰地说明面板的用途和使用方法。

2. **问题输入区**：文本区域，供用户输入问题，包含示例提示。

3. **提问按钮**：点击后发送问题到后端，并显示加载状态。

4. **回答区域**：显示 LLM 的回答，包含模型信息和 token 使用情况。

5. **代码块区域**：显示与问题相关的代码块，包含文件路径、行号和语言信息。

6. **对话历史**：显示用户的问题和 LLM 的回答，形成对话历史。

### 样式设计

问答面板的样式设计注重清晰、专业和易用：

1. **卡片式布局**：使用白色背景、圆角和阴影，形成卡片式布局，与主应用风格一致。

2. **代码块样式**：使用等宽字体、语法高亮和滚动条，方便用户阅读代码。

3. **状态指示**：使用加载动画、颜色和图标，清晰地指示操作状态。

4. **响应式设计**：适应不同屏幕尺寸，提供良好的移动端体验。

## 数据流程

用户提问的完整流程如下：

1. **用户输入**：用户在文本区域输入问题。

2. **表单验证**：验证问题不为空，仓库 URL 有效。

3. **API 调用**：将问题和仓库 URL 发送到后端 `/api/repository/question` 端点。

4. **加载状态**：显示加载动画，提示用户等待。

5. **结果处理**：接收后端响应，解析回答、代码块和元数据。

6. **结果展示**：显示回答、代码块和元数据，更新对话历史。

7. **错误处理**：如果 API 调用失败，显示友好的错误信息。

## 技术实现

### 状态管理

组件使用 React 的 `useState` 钩子管理多个状态：

```javascript
const [question, setQuestion] = useState('');
const [isLoading, setIsLoading] = useState(false);
const [answer, setAnswer] = useState(null);
const [history, setHistory] = useState([]);
const [error, setError] = useState(null);
```

### API 调用

组件使用 Axios 库调用后端 API：

```javascript
const response = await axios.post(
  '/api/repository/question',
  {
    question: question,
    repo_url: repoUrl,
    n_results: 5
  },
  {
    headers: { 'session_id': sessionId }
  }
);
```

### 结果展示

组件使用条件渲染和映射函数展示结果：

```javascript
{answer && !isLoading && (
  <div className="answer-container">
    <h3>回答</h3>
    <div className="answer-content">
      {answer.answer.split('\n').map((paragraph, index) => (
        <p key={index}>{paragraph}</p>
      ))}
    </div>
    
    <div className="answer-meta">
      <p>
        <small>模型：{answer.model} | 提示词Token：{answer.prompt_tokens} | 
        完成Token：{answer.completion_tokens} | 总Token：{answer.total_tokens}</small>
      </p>
    </div>
    
    {renderCodeChunks(answer.chunks)}
  </div>
)}
```

### 代码块渲染

组件使用专门的函数渲染代码块：

```javascript
const renderCodeChunks = (chunks) => {
  if (!chunks || chunks.length === 0) {
    return <p>未找到相关代码块</p>;
  }

  return (
    <div className="code-chunks">
      <h4>相关代码块：</h4>
      {chunks.map((chunk, index) => (
        <div key={index} className="code-chunk">
          <div className="code-chunk-header">
            <span className="code-chunk-file">{chunk.metadata.file_path}</span>
            <span className="code-chunk-lines">行 {chunk.metadata.start_line}-{chunk.metadata.end_line}</span>
            <span className="code-chunk-language">{chunk.metadata.language}</span>
          </div>
          <pre className="code-chunk-content">
            <code>{chunk.content}</code>
          </pre>
        </div>
      ))}
    </div>
  );
};
```

## 使用流程

1. 用户提交 GitHub 仓库 URL
2. 系统处理仓库（下载、分块、嵌入）
3. 处理完成后，显示问答面板
4. 用户在问答面板中输入问题
5. 系统调用后端 API，获取回答
6. 系统显示回答、相关代码块和元数据
7. 用户可以继续提问，形成对话历史

## 后续改进

1. **代码高亮**：使用 Prism.js 或 Highlight.js 等库，为代码块添加语法高亮。

2. **Markdown 渲染**：使用 Markdown 渲染库，支持 LLM 回答中的格式化内容。

3. **流式响应**：实现流式响应，让用户能够实时看到 LLM 生成的回答。

4. **代码折叠**：为长代码块添加折叠功能，提高可读性。

5. **代码搜索**：添加代码搜索功能，让用户能够在代码库中搜索特定内容。
