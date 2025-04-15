from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import uvicorn
from app.auth import router as auth_router
from app.repository import router as repository_router

# 创建FastAPI应用实例
app = FastAPI(
    title="CodeInterpreter AI",
    description="一个智能代码解释器API，能够分析、解释和执行GitHub仓库代码",
    version="0.1.0"
)

# 配置CORS中间件，允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(repository_router)

# 定义请求模型
class GitHubRepoRequest(BaseModel):
    repo_url: HttpUrl

# 定义响应模型
class AuthorizationResponse(BaseModel):
    auth_url: str
    session_id: str

# 路由：健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 路由：连接GitHub仓库
@app.post("/api/connect-github", response_model=AuthorizationResponse)
async def connect_github(request: GitHubRepoRequest):
    try:
        # 这里只是一个示例实现，实际应用中需要实现GitHub OAuth流程
        repo_url = str(request.repo_url)
        
        # 生成一个模拟的授权URL和会话ID
        auth_url = f"https://github.com/login/oauth/authorize?client_id=example_client_id&redirect_uri=http://localhost:3000/callback&state=example_state"
        session_id = "example_session_id"
        
        return AuthorizationResponse(auth_url=auth_url, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 主函数
if __name__ == "__main__":
    # 启动服务器
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

# PROMPT_SEGMENT_1_COMPLETE
# PROMPT_SEGMENT_2_COMPLETE
# PROMPT_SEGMENT_3_COMPLETE
# PROMPT_SEGMENT_4_COMPLETE
# PROMPT_SEGMENT_5_COMPLETE
# PROMPT_SEGMENT_6_COMPLETE
# PROMPT_SEGMENT_7_COMPLETE
