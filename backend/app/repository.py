from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from pydantic import BaseModel, HttpUrl, validator
import re
from typing import Dict, Optional, List, Any
import logging
import asyncio
from .auth import tokens
from .repository_manager import (
    start_repository_processing,
    get_repo_status,
    get_task_chunks,
    REPO_STATUS_PENDING,
    REPO_STATUS_DOWNLOADING,
    REPO_STATUS_PROCESSING,
    REPO_STATUS_CHUNKING,
    REPO_STATUS_EMBEDDING,
    REPO_STATUS_COMPLETED,
    REPO_STATUS_FAILED
)
from .embedding_manager import embedding_manager
from .llm_service import llm_service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api", tags=["仓库"])

# 定义请求模型
class RepositoryRequest(BaseModel):
    repo_url: HttpUrl
    
    @validator('repo_url')
    def validate_github_url(cls, v):
        # 验证URL是否为GitHub仓库URL
        github_pattern = r'^https?://github\.com/[\w.-]+/[\w.-]+/?$'
        if not re.match(github_pattern, str(v)):
            raise ValueError('URL必须是有效的GitHub仓库地址，例如：https://github.com/username/repository')
        return v

# 定义响应模型
class RepositoryResponse(BaseModel):
    message: str
    repo_url: str
    status: str
    task_id: str

# 辅助函数：从会话ID获取访问令牌
def get_access_token(session_id: str) -> str:
    """
    从会话ID获取访问令牌
    """
    if session_id not in tokens:
        raise HTTPException(status_code=401, detail="无效的会话ID")
    
    return tokens[session_id]["access_token"]

# 定义代码块响应模型
class CodeChunkInfo(BaseModel):
    chunk_id: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    content_length: int

# 定义嵌入信息响应模型
class EmbeddingInfo(BaseModel):
    status: str
    message: str
    collection_name: Optional[str] = None
    count: int = 0

# 定义任务状态响应模型
class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    message: str
    repo_url: str
    error: Optional[str] = None
    created_at: str
    updated_at: str
    chunks: Optional[List[CodeChunkInfo]] = None
    embedding: Optional[EmbeddingInfo] = None

# 路由：接收仓库URL
@router.post("/repository", response_model=RepositoryResponse)
async def process_repository(
    request: RepositoryRequest,
    background_tasks: BackgroundTasks,
    session_id: Optional[str] = Header(None)
):
    """
    接收GitHub仓库URL并开始处理
    """
    # 验证会话ID
    if not session_id:
        raise HTTPException(status_code=401, detail="未提供会话ID")
    
    try:
        # 获取访问令牌
        access_token = get_access_token(session_id)
        
        # 记录接收到的仓库URL（仅用于调试）
        logger.info(f"接收到仓库URL: {request.repo_url}")
        
        # 启动仓库处理任务
        task_id = start_repository_processing(
            str(request.repo_url),
            access_token,
            session_id
        )
        
        # 获取初始任务状态
        task_status = get_repo_status(task_id)
        
        if not task_status:
            raise HTTPException(status_code=500, detail="创建任务失败")
        
        return RepositoryResponse(
            message="仓库处理任务已创建",
            repo_url=str(request.repo_url),
            status=task_status["status"],
            task_id=task_id
        )
    except Exception as e:
        logger.error(f"处理仓库URL时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理仓库URL时发生错误: {str(e)}")

# 路由：获取任务状态
@router.get("/repository/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    获取仓库处理任务的状态
    """
    task_status = get_repo_status(task_id)
    
    if not task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取代码块信息（如果有）
    chunks = None
    if task_status["status"] == REPO_STATUS_COMPLETED:
        chunks_data = get_task_chunks(task_id)
        if chunks_data:
            chunks = [CodeChunkInfo(**chunk) for chunk in chunks_data]
    
    # 获取嵌入信息（如果有）
    embedding_info = None
    if "embedding" in task_status:
        embedding_info = EmbeddingInfo(**task_status["embedding"])
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task_status["status"],
        message=task_status["message"],
        repo_url=task_status["repo_url"],
        error=task_status.get("error"),
        created_at=task_status["created_at"],
        updated_at=task_status["updated_at"],
        chunks=chunks,
        embedding=embedding_info
    )

# 路由：获取任务的代码块
@router.get("/repository/{task_id}/chunks", response_model=List[CodeChunkInfo])
async def get_repository_chunks(task_id: str):
    """
    获取仓库处理任务的代码块
    """
    task_status = get_repo_status(task_id)
    
    if not task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task_status["status"] != REPO_STATUS_COMPLETED:
        raise HTTPException(status_code=400, detail="任务尚未完成，无法获取代码块")
    
    chunks_data = get_task_chunks(task_id)
    if not chunks_data:
        return []
    
    return [CodeChunkInfo(**chunk) for chunk in chunks_data]

# 定义查询请求模型
class QueryRequest(BaseModel):
    query: str
    repo_url: HttpUrl
    n_results: int = 5

# 定义查询结果响应模型
class ChunkSearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    id: str
    distance: Optional[float] = None

# 定义查询响应模型
class QueryResponse(BaseModel):
    results: List[ChunkSearchResult]
    query: str
    count: int

# 定义问答请求模型
class QuestionRequest(BaseModel):
    question: str
    repo_url: HttpUrl
    n_results: int = 5

# 定义问答响应模型
class QuestionResponse(BaseModel):
    answer: str
    question: str
    repo_url: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    chunks: List[ChunkSearchResult]
    error: Optional[str] = None

# 路由：查询代码（向量检索）
@router.post("/repository/query", response_model=QueryResponse)
async def query_repository(
    request: QueryRequest,
    session_id: Optional[str] = Header(None)
):
    """
    查询仓库代码（向量检索）
    """
    # 验证会话ID
    if not session_id:
        raise HTTPException(status_code=401, detail="未提供会话ID")
    
    try:
        # 获取访问令牌（仅用于验证用户身份）
        access_token = get_access_token(session_id)
        
        # 查询相似代码块
        similar_chunks = embedding_manager.query_similar_chunks(
            query=request.query,
            repo_url=str(request.repo_url),
            session_id=session_id,
            n_results=request.n_results
        )
        
        # 转换为响应模型
        results = [ChunkSearchResult(**chunk) for chunk in similar_chunks]
        
        return QueryResponse(
            results=results,
            query=request.query,
            count=len(results)
        )
    except Exception as e:
        logger.error(f"查询代码时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询代码时发生错误: {str(e)}")

# 路由：问答（RAG）
@router.post("/repository/question", response_model=QuestionResponse)
async def question_repository(
    request: QuestionRequest,
    session_id: Optional[str] = Header(None)
):
    """
    向仓库提问（RAG）
    """
    # 验证会话ID
    if not session_id:
        raise HTTPException(status_code=401, detail="未提供会话ID")
    
    try:
        # 获取访问令牌（仅用于验证用户身份）
        access_token = get_access_token(session_id)
        
        # 查询相似代码块
        similar_chunks = embedding_manager.query_similar_chunks(
            query=request.question,
            repo_url=str(request.repo_url),
            session_id=session_id,
            n_results=request.n_results
        )
        
        # 如果没有找到相关代码块
        if not similar_chunks:
            return QuestionResponse(
                answer="未找到与问题相关的代码块。请尝试重新表述问题，或者确认仓库中包含相关代码。",
                question=request.question,
                repo_url=str(request.repo_url),
                model="无",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                chunks=[]
            )
        
        # 调用LLM服务
        llm_response = llm_service.query(
            question=request.question,
            code_chunks=similar_chunks
        )
        
        # 转换为响应模型
        results = [ChunkSearchResult(**chunk) for chunk in similar_chunks]
        
        return QuestionResponse(
            answer=llm_response.get("answer", "无法获取回答"),
            question=request.question,
            repo_url=str(request.repo_url),
            model=llm_response.get("model", "未知"),
            prompt_tokens=llm_response.get("prompt_tokens", 0),
            completion_tokens=llm_response.get("completion_tokens", 0),
            total_tokens=llm_response.get("total_tokens", 0),
            chunks=results,
            error=llm_response.get("error")
        )
    except Exception as e:
        logger.error(f"问答时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"问答时发生错误: {str(e)}")

# PROMPT_SEGMENT_3_COMPLETE
# PROMPT_SEGMENT_4_COMPLETE
# PROMPT_SEGMENT_5_COMPLETE
# PROMPT_SEGMENT_6_COMPLETE
# PROMPT_SEGMENT_7_COMPLETE
