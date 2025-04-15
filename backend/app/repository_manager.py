import os
import shutil
import tempfile
import logging
import asyncio
import subprocess
import uuid
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import re
from urllib.parse import urlparse
from .code_chunker import CodeChunker, CodeChunk
from .embedding_manager import process_chunks_embeddings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 仓库状态常量
REPO_STATUS_PENDING = "pending"
REPO_STATUS_DOWNLOADING = "downloading"
REPO_STATUS_PROCESSING = "processing"
REPO_STATUS_CHUNKING = "chunking"
REPO_STATUS_EMBEDDING = "embedding"
REPO_STATUS_COMPLETED = "completed"
REPO_STATUS_FAILED = "failed"

# 仓库存储目录
REPOS_DIR = os.path.join(tempfile.gettempdir(), "code_interpreter_repos")

# 确保仓库存储目录存在
os.makedirs(REPOS_DIR, exist_ok=True)

# 存储仓库处理状态的内存字典
# 在实际生产环境中，应该使用数据库存储
repo_status: Dict[str, Dict] = {}

def get_repo_id_from_url(repo_url: str) -> str:
    """
    从GitHub仓库URL中提取仓库ID
    格式: {owner}_{repo_name}
    """
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if len(path_parts) < 2:
        raise ValueError("无效的GitHub仓库URL")
    
    owner = path_parts[0]
    repo_name = path_parts[1]
    
    # 移除.git后缀（如果有）
    repo_name = repo_name.replace('.git', '')
    
    return f"{owner}_{repo_name}"

def get_repo_dir(repo_id: str, session_id: str) -> str:
    """
    获取仓库存储目录
    """
    # 使用会话ID和仓库ID创建唯一目录，避免冲突
    unique_dir = f"{session_id[:8]}_{repo_id}"
    return os.path.join(REPOS_DIR, unique_dir)

def create_repo_status(repo_url: str, session_id: str) -> str:
    """
    创建仓库处理状态记录
    """
    repo_id = get_repo_id_from_url(repo_url)
    task_id = str(uuid.uuid4())
    
    repo_status[task_id] = {
        "repo_url": repo_url,
        "repo_id": repo_id,
        "session_id": session_id,
        "status": REPO_STATUS_PENDING,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "message": "任务已创建，等待处理",
        "error": None
    }
    
    return task_id

def update_repo_status(task_id: str, status: str, message: str = None, error: str = None) -> None:
    """
    更新仓库处理状态
    """
    if task_id not in repo_status:
        logger.error(f"任务ID不存在: {task_id}")
        return
    
    repo_status[task_id].update({
        "status": status,
        "updated_at": datetime.now().isoformat()
    })
    
    if message:
        repo_status[task_id]["message"] = message
    
    if error:
        repo_status[task_id]["error"] = error
    
    logger.info(f"任务状态更新 - ID: {task_id}, 状态: {status}, 消息: {message}")

def get_repo_status(task_id: str) -> Optional[Dict]:
    """
    获取仓库处理状态
    """
    return repo_status.get(task_id)

async def clone_repository(repo_url: str, access_token: str, task_id: str, session_id: str) -> Tuple[bool, str]:
    """
    克隆GitHub仓库
    
    Args:
        repo_url: GitHub仓库URL
        access_token: GitHub访问令牌
        task_id: 任务ID
        session_id: 会话ID
        
    Returns:
        (成功标志, 消息或错误)
    """
    try:
        # 更新状态为下载中
        update_repo_status(task_id, REPO_STATUS_DOWNLOADING, "正在下载仓库...")
        
        # 从URL中提取仓库ID
        repo_id = get_repo_id_from_url(repo_url)
        
        # 获取仓库存储目录
        repo_dir = get_repo_dir(repo_id, session_id)
        
        # 如果目录已存在，先删除
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
        
        # 确保父目录存在
        os.makedirs(os.path.dirname(repo_dir), exist_ok=True)
        
        # 构建带有访问令牌的URL
        # 注意：这里使用了正则表达式替换，以避免在日志中暴露令牌
        auth_url = re.sub(r'(https?://)', f'\\1{access_token}@', repo_url)
        
        # 使用git命令克隆仓库
        logger.info(f"开始克隆仓库: {repo_url} 到 {repo_dir}")
        
        # 使用subprocess执行git命令
        process = await asyncio.create_subprocess_exec(
            'git', 'clone', auth_url, repo_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # 检查命令执行结果
        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            # 确保不在错误消息中暴露访问令牌
            error_msg = error_msg.replace(access_token, '********')
            logger.error(f"克隆仓库失败: {error_msg}")
            update_repo_status(task_id, REPO_STATUS_FAILED, "克隆仓库失败", error_msg)
            return False, error_msg
        
        # 更新状态为处理中
        update_repo_status(task_id, REPO_STATUS_PROCESSING, f"仓库已下载，准备处理")
        
        return True, repo_dir
    
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"克隆仓库时发生错误: {error_msg}")
        update_repo_status(task_id, REPO_STATUS_FAILED, "克隆仓库时发生错误", error_msg)
        return False, error_msg

# 注意：以下是异步处理的示例实现
# 在实际生产环境中，应该使用更健壮的任务队列系统，如Celery

# 存储正在运行的任务
running_tasks = {}

def start_repository_processing(repo_url: str, access_token: str, session_id: str) -> str:
    """
    启动仓库处理任务
    
    Args:
        repo_url: GitHub仓库URL
        access_token: GitHub访问令牌
        session_id: 会话ID
        
    Returns:
        task_id: 任务ID
    """
    # 创建任务状态记录
    task_id = create_repo_status(repo_url, session_id)
    
    # 创建异步任务
    task = asyncio.create_task(process_repository(repo_url, access_token, task_id, session_id))
    
    # 存储任务引用
    running_tasks[task_id] = task
    
    return task_id

async def process_repository(repo_url: str, access_token: str, task_id: str, session_id: str) -> None:
    """
    处理仓库的异步任务
    
    Args:
        repo_url: GitHub仓库URL
        access_token: GitHub访问令牌
        task_id: 任务ID
        session_id: 会话ID
    """
    try:
        # 克隆仓库
        success, result = await clone_repository(repo_url, access_token, task_id, session_id)
        
        if not success:
            return
        
        repo_dir = result
        
        # 更新状态为分块中
        update_repo_status(task_id, REPO_STATUS_CHUNKING, "正在对代码进行分块...")
        
        # 创建代码分块器
        chunker = CodeChunker(repo_dir)
        
        # 分块代码
        chunks = chunker.chunk_repository(by_file=False)
        
        # 更新状态为嵌入中
        update_repo_status(
            task_id, 
            REPO_STATUS_EMBEDDING, 
            f"正在生成嵌入向量并存储到向量数据库，共 {len(chunks)} 个代码块"
        )
        
        # 生成嵌入向量并存储到向量数据库
        embedding_result = await process_chunks_embeddings(chunks, repo_url, session_id, task_id)
        
        # 记录分块和嵌入结果
        update_repo_status(
            task_id, 
            REPO_STATUS_COMPLETED, 
            f"仓库处理已完成，共生成 {len(chunks)} 个代码块，并存储到向量数据库"
        )
        
        # 存储分块结果元数据（不包含内容，以节省内存）
        repo_status[task_id]["chunks"] = [
            {
                "chunk_id": chunk.chunk_id,
                "file_path": chunk.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "language": chunk.language,
                "content_length": len(chunk.content)
            }
            for chunk in chunks
        ]
        
        # 存储嵌入结果
        repo_status[task_id]["embedding"] = {
            "status": embedding_result.get("status"),
            "message": embedding_result.get("message"),
            "collection_name": embedding_result.get("collection_name"),
            "count": embedding_result.get("count")
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"处理仓库时发生错误: {error_msg}")
        update_repo_status(task_id, REPO_STATUS_FAILED, "处理仓库时发生错误", error_msg)
    
    finally:
        # 从运行任务中移除
        if task_id in running_tasks:
            del running_tasks[task_id]

# 获取任务的代码块
def get_task_chunks(task_id: str) -> List[Dict]:
    """
    获取任务的代码块信息
    
    Args:
        task_id: 任务ID
        
    Returns:
        代码块信息列表
    """
    if task_id not in repo_status:
        return []
    
    return repo_status[task_id].get("chunks", [])

# PROMPT_SEGMENT_4_COMPLETE
# PROMPT_SEGMENT_5_COMPLETE
# PROMPT_SEGMENT_6_COMPLETE
