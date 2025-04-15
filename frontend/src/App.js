import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import TaskStatus from './TaskStatus';
import QuestionPanel from './QuestionPanel';
import './App.css';

function App() {
  // 状态管理
  const [repoUrl, setRepoUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState({ type: '', message: '' });
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [showTaskStatus, setShowTaskStatus] = useState(false);
  const [taskCompleted, setTaskCompleted] = useState(false);
  
  const navigate = useNavigate();

  // 检查用户是否已认证
  useEffect(() => {
    const checkAuth = async () => {
      const sessionId = localStorage.getItem('session_id');
      const isAuth = localStorage.getItem('is_authenticated');
      
      if (sessionId && isAuth === 'true') {
        setIsAuthenticated(true);
        
        try {
          // 获取用户信息
          const response = await axios.get(`/auth/session/${sessionId}`);
          setUserInfo(response.data.user_info);
        } catch (error) {
          // 如果获取用户信息失败，清除认证状态
          localStorage.removeItem('session_id');
          localStorage.removeItem('is_authenticated');
          setIsAuthenticated(false);
        }
      }
    };
    
    checkAuth();
  }, []);

  // 处理输入变化
  const handleInputChange = (e) => {
    setRepoUrl(e.target.value);
    // 清除之前的状态消息
    if (status.message) {
      setStatus({ type: '', message: '' });
    }
  };

  // 处理表单提交
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // 验证输入
    if (!repoUrl) {
      setStatus({ type: 'error', message: '请输入GitHub仓库URL' });
      return;
    }

    // 验证URL格式
    try {
      new URL(repoUrl);
    } catch (error) {
      setStatus({ type: 'error', message: '请输入有效的URL' });
      return;
    }

    // 如果用户未认证，先进行GitHub认证
    if (!isAuthenticated) {
      handleGitHubAuth();
      return;
    }

    setIsLoading(true);
    setStatus({ type: 'info', message: '正在处理GitHub仓库...' });

    try {
      // 获取会话ID
      const sessionId = localStorage.getItem('session_id');
      
      // 调用后端API处理仓库
      const response = await axios.post('/api/repository', 
        { repo_url: repoUrl },
        { headers: { 'session_id': sessionId } }
      );
      
      // 保存任务ID并显示任务状态
      setTaskId(response.data.task_id);
      setShowTaskStatus(true);
      
      setStatus({ 
        type: 'success', 
        message: response.data.message || '仓库处理已开始！' 
      });
    } catch (error) {
      setStatus({ 
        type: 'error', 
        message: `处理失败: ${error.response?.data?.detail || error.message}` 
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  // 处理GitHub认证
  const handleGitHubAuth = () => {
    setIsLoading(true);
    setStatus({ type: 'info', message: '正在重定向到GitHub授权页面...' });
    
    // 重定向到后端的GitHub认证端点
    window.location.href = '/auth/github';
  };
  
  // 处理登出
  const handleLogout = async () => {
    const sessionId = localStorage.getItem('session_id');
    
    if (sessionId) {
      try {
        // 调用后端API删除会话
        await axios.delete(`/auth/session/${sessionId}`);
      } catch (error) {
        console.error('登出时发生错误:', error);
      }
    }
    
    // 清除本地存储
    localStorage.removeItem('session_id');
    localStorage.removeItem('is_authenticated');
    
    // 更新状态
    setIsAuthenticated(false);
    setUserInfo(null);
    
    setStatus({ type: 'info', message: '您已成功登出' });
  };

  // 关闭任务状态模态框
  const handleCloseTaskStatus = () => {
    setShowTaskStatus(false);
    
    // 检查任务是否已完成
    if (taskId) {
      checkTaskStatus(taskId);
    }
  };
  
  // 检查任务状态
  const checkTaskStatus = async (id) => {
    try {
      const response = await axios.get(`/api/repository/status/${id}`);
      if (response.data.status === 'completed') {
        setTaskCompleted(true);
      }
    } catch (error) {
      console.error('获取任务状态失败:', error);
    }
  };
  
  return (
    <div className="App">
      <header className="App-header">
        <h1 className="App-title">CodeInterpreter AI</h1>
        <p className="App-subtitle">智能代码解释器应用</p>
        
        {isAuthenticated && userInfo && (
          <div className="user-profile">
            {userInfo.avatar_url && (
              <img 
                src={userInfo.avatar_url} 
                alt="GitHub头像" 
                className="user-profile-avatar" 
              />
            )}
            <span className="user-profile-name">
              {userInfo.name || userInfo.login}
            </span>
            <button 
              onClick={handleLogout}
              className="form-button"
              style={{ marginLeft: '10px', padding: '5px 10px', fontSize: '0.8rem' }}
            >
              登出
            </button>
          </div>
        )}
      </header>
      
      <main className="App-form">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="repo-url" className="form-label">
              GitHub仓库URL
            </label>
            <input
              id="repo-url"
              type="text"
              className="form-input"
              value={repoUrl}
              onChange={handleInputChange}
              placeholder="https://github.com/username/repository"
              disabled={isLoading}
            />
          </div>
          
          <button 
            type="submit" 
            className="form-button"
            disabled={isLoading}
          >
            {isLoading ? '处理中...' : isAuthenticated ? '分析仓库' : '连接GitHub并授权'}
          </button>
        </form>
        
        {status.message && (
          <div className={`status-area status-${status.type}`}>
            <p>{status.message}</p>
          </div>
        )}
      </main>
      
      {/* 任务状态模态框 */}
      {showTaskStatus && taskId && (
        <TaskStatus 
          taskId={taskId} 
          onClose={handleCloseTaskStatus} 
        />
      )}
      
      {/* 问答面板 - 仅在任务完成后显示 */}
      {taskCompleted && (
        <QuestionPanel 
          repoUrl={repoUrl}
          onError={(errorMessage) => setStatus({ type: 'error', message: errorMessage })}
        />
      )}
    </div>
  );
}

export default App;

// PROMPT_SEGMENT_1_COMPLETE
// PROMPT_SEGMENT_2_COMPLETE
// PROMPT_SEGMENT_3_COMPLETE
// PROMPT_SEGMENT_4_COMPLETE
// PROMPT_SEGMENT_8_COMPLETE
