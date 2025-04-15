import os
import logging
import tempfile
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import asyncio
from tqdm import tqdm

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

from .code_chunker import CodeChunk

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 嵌入模型配置
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"  # 快速但质量适中的模型
# 其他可选模型: "bge-large-en", "all-mpnet-base-v2"

# ChromaDB配置
CHROMA_PERSIST_DIRECTORY = os.path.join(tempfile.gettempdir(), "code_interpreter_chroma")
os.makedirs(CHROMA_PERSIST_DIRECTORY, exist_ok=True)

# 存储仓库到集合的映射
# 在实际生产环境中，应该使用数据库存储
repo_collections: Dict[str, Dict] = {}

class EmbeddingManager:
    """
    嵌入管理器，用于生成代码块的嵌入向量并存储到向量数据库
    """
    
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        """
        初始化嵌入管理器
        
        Args:
            model_name: 嵌入模型名称
        """
        self.model_name = model_name
        self.model = None  # 延迟加载模型
        
        # 初始化ChromaDB客户端
        self.chroma_client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIRECTORY,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        logger.info(f"嵌入管理器初始化完成，使用模型: {model_name}")
        logger.info(f"ChromaDB持久化目录: {CHROMA_PERSIST_DIRECTORY}")
    
    def _load_model(self):
        """
        加载嵌入模型（延迟加载）
        """
        if self.model is None:
            logger.info(f"加载嵌入模型: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        为文本生成嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        self._load_model()
        embedding = self.model.encode(text, show_progress_bar=False)
        return embedding.tolist()
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成嵌入向量
        
        Args:
            texts: 输入文本列表
            
        Returns:
            嵌入向量列表
        """
        self._load_model()
        embeddings = self.model.encode(texts, show_progress_bar=True)
        return embeddings.tolist()
    
    def get_collection_name(self, repo_url: str, session_id: str) -> str:
        """
        获取仓库对应的集合名称
        
        Args:
            repo_url: 仓库URL
            session_id: 会话ID
            
        Returns:
            集合名称
        """
        # 使用仓库URL和会话ID的哈希作为集合名称
        # 这样可以确保同一个用户的同一个仓库使用同一个集合
        collection_id = f"{session_id[:8]}_{uuid.uuid5(uuid.NAMESPACE_URL, repo_url)}"
        return f"repo_{collection_id}"
    
    def create_or_get_collection(self, repo_url: str, session_id: str) -> Tuple[chromadb.Collection, bool]:
        """
        创建或获取仓库对应的集合
        
        Args:
            repo_url: 仓库URL
            session_id: 会话ID
            
        Returns:
            (集合, 是否新创建)
        """
        collection_name = self.get_collection_name(repo_url, session_id)
        
        # 检查集合是否已存在
        existing_collections = self.chroma_client.list_collections()
        existing_names = [c.name for c in existing_collections]
        
        if collection_name in existing_names:
            logger.info(f"获取已存在的集合: {collection_name}")
            collection = self.chroma_client.get_collection(
                name=collection_name,
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(self.model_name)
            )
            return collection, False
        else:
            logger.info(f"创建新集合: {collection_name}")
            collection = self.chroma_client.create_collection(
                name=collection_name,
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(self.model_name),
                metadata={"repo_url": repo_url, "created_at": datetime.now().isoformat()}
            )
            return collection, True
    
    def store_code_chunks(self, chunks: List[CodeChunk], repo_url: str, session_id: str, task_id: str) -> Dict[str, Any]:
        """
        将代码块存储到向量数据库
        
        Args:
            chunks: 代码块列表
            repo_url: 仓库URL
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            存储结果信息
        """
        if not chunks:
            logger.warning("没有代码块需要存储")
            return {"status": "error", "message": "没有代码块需要存储", "count": 0}
        
        # 创建或获取集合
        collection, is_new = self.create_or_get_collection(repo_url, session_id)
        
        # 如果集合已存在，先清空
        if not is_new:
            collection.delete(where={})
            logger.info(f"清空已存在的集合: {collection.name}")
        
        # 准备批量添加的数据
        ids = []
        documents = []
        metadatas = []
        
        # 处理每个代码块
        for chunk in chunks:
            # 使用chunk_id作为文档ID
            chunk_id = chunk.chunk_id
            
            # 代码块内容作为文档
            document = chunk.content
            
            # 元数据
            metadata = {
                "file_path": chunk.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "language": chunk.language,
                "task_id": task_id
            }
            
            ids.append(chunk_id)
            documents.append(document)
            metadatas.append(metadata)
        
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
        
        # 记录仓库到集合的映射
        repo_collections[repo_url] = {
            "collection_name": collection.name,
            "session_id": session_id,
            "task_id": task_id,
            "chunk_count": total_added,
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"成功将 {total_added} 个代码块添加到集合: {collection.name}")
        
        return {
            "status": "success",
            "message": f"成功存储 {total_added} 个代码块",
            "collection_name": collection.name,
            "count": total_added
        }
    
    def query_similar_chunks(self, query: str, repo_url: str, session_id: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        查询与输入文本最相似的代码块
        
        Args:
            query: 查询文本
            repo_url: 仓库URL
            session_id: 会话ID
            n_results: 返回结果数量
            
        Returns:
            相似代码块列表
        """
        # 获取集合
        collection_name = self.get_collection_name(repo_url, session_id)
        
        try:
            collection = self.chroma_client.get_collection(
                name=collection_name,
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(self.model_name)
            )
        except ValueError:
            logger.error(f"集合不存在: {collection_name}")
            return []
        
        # 查询相似代码块
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # 处理结果
        similar_chunks = []
        
        if results and results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                chunk = {
                    "content": doc,
                    "metadata": results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                    "id": results['ids'][0][i] if results['ids'] and results['ids'][0] else "",
                    "distance": results['distances'][0][i] if results['distances'] and results['distances'][0] else None
                }
                similar_chunks.append(chunk)
        
        return similar_chunks

# 创建全局嵌入管理器实例
embedding_manager = EmbeddingManager()

async def process_chunks_embeddings(chunks: List[CodeChunk], repo_url: str, session_id: str, task_id: str) -> Dict[str, Any]:
    """
    处理代码块嵌入的异步函数
    
    Args:
        chunks: 代码块列表
        repo_url: 仓库URL
        session_id: 会话ID
        task_id: 任务ID
        
    Returns:
        处理结果
    """
    # 这里使用全局嵌入管理器实例
    # 注意：在实际生产环境中，应该使用更健壮的方式管理嵌入管理器实例
    global embedding_manager
    
    # 存储代码块
    result = embedding_manager.store_code_chunks(chunks, repo_url, session_id, task_id)
    
    return result

def get_repo_collection_info(repo_url: str) -> Optional[Dict[str, Any]]:
    """
    获取仓库集合信息
    
    Args:
        repo_url: 仓库URL
        
    Returns:
        集合信息
    """
    return repo_collections.get(repo_url)

# PROMPT_SEGMENT_6_COMPLETE
