from fastapi import APIRouter, HTTPException, Request, Depends, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx
import os
import secrets
import json
from typing import Dict, Optional
from datetime import datetime

# 创建路由器
router = APIRouter(prefix="/auth", tags=["认证"])

# 从环境变量获取GitHub OAuth配置
# 在实际部署时，这些值应该通过环境变量提供
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "your_github_client_id")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "your_github_client_secret")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/github/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# 内存存储，用于临时保存用户会话和令牌
# 注意：在生产环境中，应该使用更安全的存储方式，如数据库
sessions: Dict[str, Dict] = {}
tokens: Dict[str, Dict] = {}

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_info: Optional[Dict] = None

@router.get("/github")
async def github_login():
    """
    启动GitHub OAuth流程，重定向用户到GitHub授权页面
    """
    # 生成随机状态参数，用于防止CSRF攻击
    state = secrets.token_urlsafe(16)
    
    # 构建GitHub授权URL
    auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={state}"
        f"&scope=repo"  # 请求访问仓库的权限
    )
    
    # 存储状态参数，用于后续验证
    sessions[state] = {
        "created_at": datetime.now().isoformat()
    }
    
    # 重定向用户到GitHub授权页面
    return RedirectResponse(url=auth_url)

@router.get("/github/callback")
async def github_callback(code: str, state: str):
    """
    处理GitHub OAuth回调，获取访问令牌
    """
    # 验证状态参数，防止CSRF攻击
    if state not in sessions:
        raise HTTPException(status_code=400, detail="无效的状态参数")
    
    # 删除已使用的状态参数
    del sessions[state]
    
    # 使用授权码获取访问令牌
    async with httpx.AsyncClient() as client:
        # 向GitHub请求访问令牌
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI
            },
            headers={"Accept": "application/json"}
        )
        
        # 检查响应状态
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="获取访问令牌失败")
        
        # 解析响应
        token_data = token_response.json()
        
        # 检查是否包含访问令牌
        if "access_token" not in token_data:
            raise HTTPException(status_code=400, detail="获取访问令牌失败")
        
        # 获取用户信息
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {token_data['access_token']}",
                "Accept": "application/json"
            }
        )
        
        # 检查响应状态
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="获取用户信息失败")
        
        # 解析用户信息
        user_info = user_response.json()
        
        # 生成会话ID
        session_id = secrets.token_urlsafe(32)
        
        # 存储访问令牌和用户信息
        tokens[session_id] = {
            "access_token": token_data["access_token"],
            "token_type": token_data.get("token_type", "bearer"),
            "user_info": {
                "id": user_info.get("id"),
                "login": user_info.get("login"),
                "name": user_info.get("name"),
                "avatar_url": user_info.get("avatar_url")
            },
            "created_at": datetime.now().isoformat()
        }
        
        # 重定向到前端，并附带会话ID
        redirect_url = f"{FRONTEND_URL}/auth-callback?session_id={session_id}"
        return RedirectResponse(url=redirect_url)

@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    获取会话信息，包括用户信息和令牌类型
    """
    # 检查会话ID是否存在
    if session_id not in tokens:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 获取会话信息
    session_data = tokens[session_id]
    
    # 返回会话信息，但不包括访问令牌
    return {
        "user_info": session_data["user_info"],
        "token_type": session_data["token_type"]
    }

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话，用于用户登出
    """
    # 检查会话ID是否存在
    if session_id not in tokens:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 删除会话
    del tokens[session_id]
    
    return {"message": "会话已删除"}

# PROMPT_SEGMENT_2_COMPLETE
