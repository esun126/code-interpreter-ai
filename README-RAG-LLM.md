# RAG 检索与 LLM 问答接口实现指南

本文档提供了 CodeInterpreter AI 项目中 RAG 检索与 LLM 问答接口功能的详细说明。

## 功能概述

RAG（检索增强生成）是一种结合检索系统和生成式 AI 的技术，能够让 LLM（大型语言模型）基于检索到的相关信息生成更准确、更有依据的回答。在 CodeInterpreter AI 中，我们使用 RAG 技术来实现代码理解和问答功能，让用户能够通过自然语言提问来理解 GitHub 仓库中的代码。

## 实现细节

### LLM 服务 (`llm_service.py`)

LLM 服务是一个专门的类，用于调用大型语言模型进行代码问答。主要功能包括：

1. **LLM 集成**：使用 OpenAI API 调用 GPT 模型，默认使用 `gpt-3.5-turbo` 模型。

2. **提示词构建**：根据用户问题和检索到的代码块构建提示词，包括格式化代码块、添加元数据等。

3. **Token 管理**：使用 `tiktoken` 库计算 token 数量，确保不超过模型的最大上下文长度，必要时进行截断。

4. **错误处理**：处理 API 调用错误、token 超限等异常情况，提供友好的错误信息。

5. **模拟模式**：当未提供 API 密钥时，提供模拟模式，返回预设的回答。

### API 端点 (`repository.py`)

新增了用于问答的 API 端点：

1. **问答端点**：添加了 `/api/repository/question` 端点，接收用户问题和仓库 URL，返回 LLM 生成的回答。

2. **请求和响应模型**：定义了 `QuestionRequest` 和 `QuestionResponse` 模型，包含问题、回答、模型信息、token 使用情况等。

## 数据流程

RAG 问答的完整流程如下：

1. **用户提问**：用户提交问题和仓库 URL。

2. **向量检索**：使用嵌入模型将问题转换为向量，在向量数据库中检索最相关的代码块。

3. **提示词构建**：将检索到的代码块和用户问题组合成提示词。

4. **LLM 调用**：将提示词发送给 LLM，获取生成的回答。

5. **结果返回**：将 LLM 的回答、检索到的代码块和相关元数据返回给用户。

## 技术实现

### 提示词构建

系统使用精心设计的提示词模板，将用户问题和检索到的代码块组合成提示词：

```python
prompt_template = """你是一个专业的代码解释器，擅长分析和解释代码。请根据以下代码片段回答用户的问题。

用户问题："{question}"

以下是可能相关的代码片段：

{code_chunks}

请根据以上代码片段回答用户的问题。如果代码片段中没有足够的信息来回答问题，请明确指出，并尽可能根据已有信息提供有用的见解。
回答应该清晰、准确、专业，并直接针对用户的问题。
"""
```

### Token 管理

系统使用 `tiktoken` 库计算 token 数量，确保不超过模型的最大上下文长度：

```python
def count_tokens(self, text: str) -> int:
    """
    计算文本的token数量
    """
    if self.tokenizer:
        return len(self.tokenizer.encode(text))
    else:
        # 如果没有tokenizer，使用简单的估算
        return len(text) // 4
```

当提示词超过最大 token 数量时，系统会智能地截断代码块：

```python
# 如果提示词超过最大token数量，需要截断代码块
if prompt_tokens > max_tokens:
    # 计算需要保留的token数量
    remaining_tokens = max_tokens - self.count_tokens(prompt_template.format(
        question=question,
        code_chunks=""
    ))
    
    # 截断代码块
    truncated_chunks = []
    current_tokens = 0
    
    for chunk in formatted_chunks:
        chunk_tokens = self.count_tokens(chunk)
        
        if current_tokens + chunk_tokens <= remaining_tokens:
            truncated_chunks.append(chunk)
            current_tokens += chunk_tokens
        else:
            # 尝试截断当前代码块
            available_tokens = remaining_tokens - current_tokens
            if available_tokens > 100:  # 确保至少有100个token可用
                truncated_chunk = self.truncate_text(chunk, available_tokens)
                truncated_chunks.append(truncated_chunk)
            
            break
```

### LLM 调用

系统使用 OpenAI API 调用 GPT 模型：

```python
# 调用OpenAI API
response = self.client.chat.completions.create(
    model=self.model,
    messages=[
        {"role": "system", "content": "你是一个专业的代码解释器，擅长分析和解释代码。"},
        {"role": "user", "content": prompt}
    ],
    max_tokens=MAX_RESPONSE_LENGTH,
    temperature=0.3,  # 使用较低的温度以获得更确定性的回答
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0
)
```

### 错误处理

系统提供了全面的错误处理，确保在各种异常情况下都能提供友好的错误信息：

```python
try:
    # 调用LLM API
    # ...
except Exception as e:
    logger.error(f"调用LLM API时发生错误: {str(e)}")
    return {
        "answer": f"调用LLM API时发生错误: {str(e)}",
        "model": self.model,
        "prompt_tokens": self.count_tokens(prompt),
        "completion_tokens": 0,
        "total_tokens": self.count_tokens(prompt),
        "error": str(e)
    }
```

## 使用流程

1. 用户提交 GitHub 仓库 URL
2. 系统下载仓库代码
3. 系统对代码进行分块
4. 系统生成代码块的嵌入向量并存储到向量数据库
5. 用户提交问题
6. 系统检索相关代码块
7. 系统构建提示词并调用 LLM
8. 系统返回 LLM 生成的回答和相关代码块

## 配置

系统支持通过环境变量配置 LLM 服务：

```
# OpenAI API 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo
```

## 后续改进

1. **多模型支持**：支持更多的 LLM 模型，如 Gemini、Claude、Llama 等。

2. **流式响应**：实现流式响应，让用户能够实时看到 LLM 生成的回答。

3. **上下文管理**：实现对话历史管理，让用户能够进行多轮对话。

4. **提示词优化**：优化提示词模板，提高回答质量。

5. **代码执行**：实现代码执行功能，让用户能够在问答过程中执行代码。
