import os
import time
from celery import Celery
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session
from .database import SessionLocal, DatabaseManager
from .repository_manager import (
    get_repo_id_from_url,
    get_repo_dir,
    clone_repository_sync,
    REPO_STATUS_PENDING,
    REPO_STATUS_DOWNLOADING,
    REPO_STATUS_PROCESSING,
    REPO_STATUS_CHUNKING,
    REPO_STATUS_EMBEDDING,
    REPO_STATUS_COMPLETED,
    REPO_STATUS_FAILED
)
from .code_chunker import CodeChunker
from .embedding_manager import EmbeddingManager

# 配置Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("code_interpreter", broker=REDIS_URL, backend=REDIS_URL)

# 配置Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)

# 获取任务日志记录器
logger = get_task_logger(__name__)

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

@celery_app.task(bind=True, name="process_repository")
def process_repository_task(self, task_id: str, repo_url: str, access_token: str, session_id: str):
    """
    处理仓库的Celery任务
    
    Args:
        task_id: 任务ID
        repo_url: GitHub仓库URL
        access_token: GitHub访问令牌
        session_id: 会话ID
    """
    logger.info(f"开始处理仓库任务: {task_id}")
    
    # 获取数据库会话
    db = get_db()
    
    try:
        # 更新任务状态为下载中
        DatabaseManager.update_task_status(
            db, 
            task_id, 
            REPO_STATUS_DOWNLOADING, 
            "正在下载仓库..."
        )
        
        # 从URL中提取仓库ID
        repo_id = get_repo_id_from_url(repo_url)
        
        # 获取仓库存储目录
        repo_dir = get_repo_dir(repo_id, session_id)
        
        # 克隆仓库
        success, result = clone_repository_sync(repo_url, access_token, task_id, session_id, repo_dir)
        
        if not success:
            # 更新任务状态为失败
            DatabaseManager.update_task_status(
                db, 
                task_id, 
                REPO_STATUS_FAILED, 
                "克隆仓库失败", 
                result
            )
            return {"status": "failed", "message": result}
        
        # 更新任务状态为处理中
        DatabaseManager.update_task_status(
            db, 
            task_id, 
            REPO_STATUS_PROCESSING, 
            "仓库已下载，准备处理"
        )
        
        # 更新任务状态为分块中
        DatabaseManager.update_task_status(
            db, 
            task_id, 
            REPO_STATUS_CHUNKING, 
            "正在对代码进行分块..."
        )
        
        # 创建代码分块器
        chunker = CodeChunker(repo_dir)
        
        # 分块代码
        chunks = chunker.chunk_repository(by_file=False)
        
        # 更新任务状态为嵌入中
        DatabaseManager.update_task_status(
            db, 
            task_id, 
            REPO_STATUS_EMBEDDING, 
            f"正在生成嵌入向量并存储到向量数据库，共 {len(chunks)} 个代码块"
        )
        
        # 创建嵌入管理器
        embedding_manager = EmbeddingManager()
        
        # 存储代码块到数据库
        for chunk in chunks:
            DatabaseManager.create_code_chunk(
                db,
                task_id,
                chunk.chunk_id,
                chunk.file_path,
                chunk.start_line,
                chunk.end_line,
                chunk.language,
                chunk.content
            )
        
        # 生成嵌入向量并存储到向量数据库
        collection_name = embedding_manager.get_collection_name(repo_url, session_id)
        collection, is_new = embedding_manager.create_or_get_collection(repo_url, session_id)
        
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
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_documents = documents[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            
            collection.add(
                ids=batch_ids,
                documents=batch_documents,
                metadatas=batch_metadatas
            )
            
            total_added += len(batch_ids)
        
        # 获取仓库
        repository = db.query(Repository).filter_by(repo_url=repo_url).first()
        
        # 如果仓库存在，更新集合名称
        if repository:
            DatabaseManager.update_repository_collection(db, repository.id, collection_name)
        
        # 更新任务状态为已完成
        metadata = {
            "chunks_count": len(chunks),
            "embedding": {
                "collection_name": collection_name,
                "count": total_added
            }
        }
        
        DatabaseManager.update_task_status(
            db, 
            task_id, 
            REPO_STATUS_COMPLETED, 
            f"仓库处理已完成，共生成 {len(chunks)} 个代码块，并存储到向量数据库",
            metadata=metadata
        )
        
        logger.info(f"仓库任务处理完成: {task_id}")
        
        return {
            "status": "completed",
            "message": f"仓库处理已完成，共生成 {len(chunks)} 个代码块，并存储到向量数据库",
            "chunks_count": len(chunks),
            "collection_name": collection_name
        }
    
    except Exception as e:
        logger.exception(f"处理仓库任务时发生错误: {str(e)}")
        
        # 更新任务状态为失败
        DatabaseManager.update_task_status(
            db, 
            task_id, 
            REPO_STATUS_FAILED, 
            "处理仓库时发生错误", 
            str(e)
        )
        
        return {"status": "failed", "message": str(e)}
    
    finally:
        db.close()

# 辅助函数：同步克隆仓库
def clone_repository_sync(repo_url, access_token, task_id, session_id, repo_dir):
    """
    同步克隆仓库（用于Celery任务）
    """
    try:
        # 导入必要的模块
        import os
        import shutil
        import re
        import subprocess
        
        # 如果目录已存在，先删除
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
        
        # 确保父目录存在
        os.makedirs(os.path.dirname(repo_dir), exist_ok=True)
        
        # 构建带有访问令牌的URL
        auth_url = re.sub(r'(https?://)', f'\\1{access_token}@', repo_url)
        
        # 使用git命令克隆仓库
        logger.info(f"开始克隆仓库: {repo_url} 到 {repo_dir}")
        
        # 使用subprocess执行git命令
        process = subprocess.Popen(
            ['git', 'clone', auth_url, repo_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        # 检查命令执行结果
        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            # 确保不在错误消息中暴露访问令牌
            error_msg = error_msg.replace(access_token, '********')
            logger.error(f"克隆仓库失败: {error_msg}")
            return False, error_msg
        
        return True, repo_dir
    
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"克隆仓库时发生错误: {error_msg}")
        return False, error_msg

# PROMPT_SEGMENT_9_COMPLETE
