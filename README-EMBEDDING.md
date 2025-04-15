# 嵌入生成与向量存储实现指南

本文档提供了 CodeInterpreter AI 项目中嵌入生成与向量存储功能的详细说明。

## 功能概述

嵌入生成与向量存储是将代码块转换为向量表示并存储到向量数据库的过程。这些向量表示使得系统能够进行语义搜索，找到与用户查询语义相似的代码块，从而实现更智能的代码理解和问答功能。

## 实现细节

### 嵌入管理器 (`embedding_manager.py`)

嵌入管理器是一个专门的类，用于生成代码块的嵌入向量并存储到向量数据库。主要功能包括：

1. **嵌入模型集成**：使用 `sentence-transformers` 库加载预训练的文本嵌入模型，默认使用 `all-MiniLM-L6-v2` 模型。

2. **向量数据库集成**：使用 ChromaDB 作为向量数据库，支持持久化存储和高效的相似性搜索。

3. **代码块存储**：将代码块内容及其元数据存储到向量数据库的集合中，每个仓库对应一个集合。

4. **相似性搜索**：提供查询功能，根据用户输入查找语义相似的代码块。

### 与仓库管理器的集成 (`repository_manager.py`)

仓库管理器负责下载 GitHub 仓库、分块代码，并调用嵌入管理器处理代码块。主要集成点包括：

1. **处理流程**：在代码分块后，更新任务状态为"嵌入中"，然后调用嵌入管理器处理代码块。

2. **结果存储**：将嵌入结果存储在任务状态中，包括状态、消息、集合名称和数量等信息。

3. **状态更新**：处理完成后，更新任务状态为"已完成"，并记录生成的代码块数量和嵌入结果。

### API 端点 (`repository.py`)

新增了用于查询代码的 API 端点：

1. **查询代码**：添加了 `/api/repository/query` 端点，接收查询文本和仓库 URL，返回与查询语义相似的代码块。

2. **任务状态**：更新了 `/api/repository/status/{task_id}` 端点，添加了嵌入信息。

## 数据结构

### 嵌入信息 (API 响应)

API 返回的嵌入信息包含以下字段：

```python
class EmbeddingInfo(BaseModel):
    status: str          # 状态（success 或 error）
    message: str         # 消息
    collection_name: Optional[str] = None  # 集合名称
    count: int = 0       # 嵌入数量
```

### 查询请求

查询请求包含以下字段：

```python
class QueryRequest(BaseModel):
    query: str           # 查询文本
    repo_url: HttpUrl    # 仓库 URL
    n_results: int = 5   # 返回结果数量
```

### 查询结果

查询结果包含以下字段：

```python
class ChunkSearchResult(BaseModel):
    content: str         # 代码块内容
    metadata: Dict[str, Any]  # 元数据
    id: str              # 块 ID
    distance: Optional[float] = None  # 距离（相似度）
```

## 使用流程

1. 用户提交 GitHub 仓库 URL
2. 系统下载仓库代码
3. 系统对代码进行分块
4. 系统生成代码块的嵌入向量并存储到向量数据库
5. 用户可以通过 API 查询与特定文本语义相似的代码块

## 技术实现

### 嵌入模型

系统使用 `sentence-transformers` 库加载预训练的文本嵌入模型：

```python
# 嵌入模型配置
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"  # 快速但质量适中的模型
# 其他可选模型: "bge-large-en", "all-mpnet-base-v2"

def _load_model(self):
    """
    加载嵌入模型（延迟加载）
    """
    if self.model is None:
        logger.info(f"加载嵌入模型: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
```

### 向量数据库

系统使用 ChromaDB 作为向量数据库，支持持久化存储和高效的相似性搜索：

```python
# ChromaDB配置
CHROMA_PERSIST_DIRECTORY = os.path.join(tempfile.gettempdir(), "code_interpreter_chroma")
os.makedirs(CHROMA_PERSIST_DIRECTORY, exist_ok=True)

# 初始化ChromaDB客户端
self.chroma_client = chromadb.PersistentClient(
    path=CHROMA_PERSIST_DIRECTORY,
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)
```

### 代码块存储

系统将代码块内容及其元数据存储到向量数据库的集合中：

```python
# 批量添加到集合
logger.info(f"开始将 {len(chunks)} 个代码块添加到集合: {collection.name}")

# 使用批处理，每批最多100个文档
batch_size = 100
total_added = 0

for i in tqdm(range(0, len(ids), batch_size), desc="存储代码块"):
    batch_ids = ids[i:i+batch_size]
    batch_documents = documents[i:i+batch_size]
    batch_metadatas = metadatas[i:i+batch_size]
    
    collection.add(
        ids=batch_ids,
        documents=batch_documents,
        metadatas=batch_metadatas
    )
    
    total_added += len(batch_ids)
```

### 相似性搜索

系统提供查询功能，根据用户输入查找语义相似的代码块：

```python
# 查询相似代码块
results = collection.query(
    query_texts=[query],
    n_results=n_results
)
```

## 后续改进

1. **更高质量的嵌入模型**：使用更专业的代码嵌入模型，如 CodeBERT、GraphCodeBERT 等，以提高代码理解的准确性。

2. **多模型支持**：允许用户选择不同的嵌入模型，以平衡速度和质量。

3. **分布式存储**：实现分布式向量数据库，以支持更大规模的代码库和更高的并发查询。

4. **查询优化**：实现更复杂的查询策略，如混合检索、重排序等，以提高搜索结果的质量。

5. **增量更新**：支持仓库代码的增量更新，只处理变更的文件，以提高效率。
