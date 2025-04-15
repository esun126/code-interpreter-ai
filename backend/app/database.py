from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import os
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any
import logging
from loguru import logger

# 获取数据库URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./code_interpreter.db")

# 创建数据库引擎
engine = create_engine(DATABASE_URL)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 用户模型
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(String, unique=True, index=True)
    login = Column(String, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="user", cascade="all, delete-orphan")

# 会话模型
class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    access_token = Column(String)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="sessions")

# 仓库模型
class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    repo_url = Column(String, index=True)
    repo_name = Column(String)
    repo_owner = Column(String)
    collection_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="repositories")
    tasks = relationship("Task", back_populates="repository", cascade="all, delete-orphan")

# 任务模型
class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"))
    status = Column(String, index=True)  # pending, downloading, processing, chunking, embedding, completed, failed
    message = Column(String, nullable=True)
    error = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)  # 存储任务元数据，如代码块数量、嵌入信息等
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    repository = relationship("Repository", back_populates="tasks")
    chunks = relationship("CodeChunk", back_populates="task", cascade="all, delete-orphan")

# 代码块模型
class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("tasks.id"))
    chunk_id = Column(String, index=True)
    file_path = Column(String)
    start_line = Column(Integer)
    end_line = Column(Integer)
    language = Column(String)
    content = Column(Text)
    content_length = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    task = relationship("Task", back_populates="chunks")

# 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 创建数据库表
def create_tables():
    Base.metadata.create_all(bind=engine)

# 数据库操作类
class DatabaseManager:
    @staticmethod
    def create_user(db, github_id, login, name=None, email=None, avatar_url=None):
        """创建用户"""
        user = User(
            github_id=github_id,
            login=login,
            name=name,
            email=email,
            avatar_url=avatar_url
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_by_github_id(db, github_id):
        """通过GitHub ID获取用户"""
        return db.query(User).filter(User.github_id == github_id).first()
    
    @staticmethod
    def create_session(db, session_id, user_id, access_token, expires_in=3600):
        """创建会话"""
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        session = Session(
            id=session_id,
            user_id=user_id,
            access_token=access_token,
            expires_at=expires_at
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    
    @staticmethod
    def get_session(db, session_id):
        """获取会话"""
        return db.query(Session).filter(Session.id == session_id).first()
    
    @staticmethod
    def delete_session(db, session_id):
        """删除会话"""
        session = db.query(Session).filter(Session.id == session_id).first()
        if session:
            db.delete(session)
            db.commit()
            return True
        return False
    
    @staticmethod
    def create_repository(db, user_id, repo_url, repo_name, repo_owner):
        """创建仓库"""
        repository = Repository(
            user_id=user_id,
            repo_url=repo_url,
            repo_name=repo_name,
            repo_owner=repo_owner
        )
        db.add(repository)
        db.commit()
        db.refresh(repository)
        return repository
    
    @staticmethod
    def get_repository_by_url(db, user_id, repo_url):
        """通过URL获取仓库"""
        return db.query(Repository).filter(
            Repository.user_id == user_id,
            Repository.repo_url == repo_url
        ).first()
    
    @staticmethod
    def update_repository_collection(db, repository_id, collection_name):
        """更新仓库集合名称"""
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if repository:
            repository.collection_name = collection_name
            db.commit()
            db.refresh(repository)
            return repository
        return None
    
    @staticmethod
    def create_task(db, task_id, repository_id, status="pending", message=None):
        """创建任务"""
        task = Task(
            id=task_id,
            repository_id=repository_id,
            status=status,
            message=message
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    
    @staticmethod
    def get_task(db, task_id):
        """获取任务"""
        return db.query(Task).filter(Task.id == task_id).first()
    
    @staticmethod
    def update_task_status(db, task_id, status, message=None, error=None, metadata=None):
        """更新任务状态"""
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = status
            if message:
                task.message = message
            if error:
                task.error = error
            if metadata:
                task.metadata = metadata
            task.updated_at = datetime.now()
            db.commit()
            db.refresh(task)
            return task
        return None
    
    @staticmethod
    def create_code_chunk(db, task_id, chunk_id, file_path, start_line, end_line, language, content):
        """创建代码块"""
        code_chunk = CodeChunk(
            task_id=task_id,
            chunk_id=chunk_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            language=language,
            content=content,
            content_length=len(content)
        )
        db.add(code_chunk)
        db.commit()
        db.refresh(code_chunk)
        return code_chunk
    
    @staticmethod
    def get_code_chunks_by_task(db, task_id, limit=None):
        """获取任务的代码块"""
        query = db.query(CodeChunk).filter(CodeChunk.task_id == task_id)
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @staticmethod
    def get_code_chunk_by_id(db, chunk_id):
        """通过ID获取代码块"""
        return db.query(CodeChunk).filter(CodeChunk.chunk_id == chunk_id).first()

# 初始化数据库
def init_db():
    logger.info("初始化数据库...")
    create_tables()
    logger.info("数据库初始化完成")

# PROMPT_SEGMENT_9_COMPLETE
