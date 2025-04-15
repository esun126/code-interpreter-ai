# 代码分块 (Code Chunking) 实现指南

本文档提供了 CodeInterpreter AI 项目中代码分块功能的详细说明。

## 功能概述

代码分块是将下载的 GitHub 仓库代码分割成更小、更易于处理的片段的过程。这些代码块将用于后续的向量化和语义搜索，使 AI 能够更好地理解和回答关于代码的问题。

## 实现细节

### 代码分块器 (`code_chunker.py`)

代码分块器是一个专门的类，用于遍历代码仓库并将代码文件分割成小块。主要功能包括：

1. **文件过滤**：识别并过滤掉非代码文件（如图片、二进制文件、配置文件等）和不需要处理的目录（如 `.git`、`node_modules` 等）。

2. **语言识别**：根据文件扩展名识别编程语言，支持多种主流编程语言。

3. **分块策略**：实现了两种分块策略：
   - **按文件分块**：每个文件作为一个块
   - **按固定大小+重叠分块**：将文件内容按固定字符数分割，块之间有重叠以保证语义连续性

4. **元数据生成**：为每个代码块生成元数据，包括文件路径、行号范围、编程语言等。

### 与仓库管理器的集成 (`repository_manager.py`)

仓库管理器负责下载 GitHub 仓库并调用代码分块器处理代码。主要集成点包括：

1. **处理流程**：下载仓库后，更新任务状态为"分块中"，然后调用代码分块器处理代码。

2. **结果存储**：将分块结果存储在任务状态中，包括每个块的元数据（不包括内容，以节省内存）。

3. **状态更新**：处理完成后，更新任务状态为"已完成"，并记录生成的代码块数量。

### API 端点 (`repository.py`)

新增了用于获取代码块信息的 API 端点：

1. **获取任务状态**：更新了 `/api/repository/status/{task_id}` 端点，在任务完成时返回代码块信息。

2. **获取代码块列表**：新增了 `/api/repository/{task_id}/chunks` 端点，用于获取任务的所有代码块信息。

## 数据结构

### 代码块 (`CodeChunk`)

代码块是一个数据类，包含以下字段：

```python
@dataclass
class CodeChunk:
    content: str       # 代码块内容
    file_path: str     # 文件路径
    start_line: int    # 起始行号
    end_line: int      # 结束行号
    language: str      # 编程语言
    chunk_id: str      # 块ID（格式：file_path:start_line-end_line）
```

### 代码块信息 (API 响应)

API 返回的代码块信息包含以下字段：

```python
class CodeChunkInfo(BaseModel):
    chunk_id: str          # 块ID
    file_path: str         # 文件路径
    start_line: int        # 起始行号
    end_line: int          # 结束行号
    language: str          # 编程语言
    content_length: int    # 内容长度（字符数）
```

## 使用流程

1. 用户提交 GitHub 仓库 URL
2. 系统下载仓库代码
3. 系统调用代码分块器处理代码
4. 系统将分块结果存储在任务状态中
5. 用户可以通过 API 获取代码块信息

## 技术实现

### 文件过滤

系统使用预定义的列表过滤掉不需要处理的文件和目录：

```python
# 要忽略的目录
IGNORED_DIRS = {
    '.git', 'node_modules', 'venv', 'env', '.env', '__pycache__', 
    # ...更多
}

# 要忽略的文件
IGNORED_FILES = {
    'LICENSE', 'LICENCE', 'NOTICE', 'PATENTS', 'AUTHORS',
    # ...更多
}

# 要忽略的文件扩展名
IGNORED_EXTENSIONS = {
    # 图片
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp',
    # ...更多
}
```

### 语言识别

系统使用文件扩展名映射到编程语言：

```python
# 支持的编程语言及其文件扩展名
SUPPORTED_LANGUAGES = {
    'python': ['.py', '.pyx', '.pyi', '.pyw'],
    'javascript': ['.js', '.jsx', '.ts', '.tsx'],
    # ...更多
}
```

### 分块策略

系统实现了两种分块策略：

1. **按文件分块**：简单地将每个文件作为一个块。

2. **按固定大小+重叠分块**：将文件内容按行分割，当累积的字符数超过指定大小时创建一个新块，并保留一部分重叠内容：

```python
# 分割文件内容
chunks = []
lines = content.split('\n')
current_chunk = []
current_chunk_size = 0
start_line = 1

for i, line in enumerate(lines, 1):
    line_with_newline = line + '\n'
    line_size = len(line_with_newline)
    
    # 如果当前行加上当前块大小超过了块大小，并且当前块不为空，则创建新块
    if current_chunk_size + line_size > self.chunk_size and current_chunk:
        # 创建代码块
        chunk_content = ''.join(current_chunk)
        chunk_id = f"{rel_path}:{start_line}-{i-1}"
        chunk = CodeChunk(...)
        chunks.append(chunk)
        
        # 计算重叠部分
        overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
        current_chunk = current_chunk[overlap_start:]
        # ...
```

## 后续改进

1. **更智能的分块策略**：实现基于语法结构的分块，使用 `tree-sitter` 等库解析代码语法树，按函数、类或逻辑块分割。

2. **内容存储**：将代码块内容存储到数据库或文件系统中，而不是内存中，以支持更大的代码库。

3. **并行处理**：实现多线程或多进程处理，加快大型代码库的分块速度。

4. **语言特定处理**：针对不同的编程语言实现特定的处理逻辑，如忽略注释、提取文档字符串等。

5. **块质量评估**：实现对代码块质量的评估，如语义完整性、上下文依赖性等，以优化分块结果。
