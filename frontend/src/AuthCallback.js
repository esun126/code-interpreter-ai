import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './App.css';

function AuthCallback() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userInfo, setUserInfo] = useState(null);

  useEffect(() => {
    const fetchSessionData = async () => {
      try {
        // 从URL获取会话ID
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = urlParams.get('session_id');

        if (!sessionId) {
          throw new Error('未找到会话ID');
        }

        // 获取会话信息
        const response = await axios.get(`/auth/session/${sessionId}`);
        setUserInfo(response.data.user_info);
        
        // 将会话ID存储在localStorage中，以便后续使用
        localStorage.setItem('session_id', sessionId);
        
        // 设置已认证状态
        localStorage.setItem('is_authenticated', 'true');
        
        setLoading(false);
        
        // 3秒后重定向到主页
        setTimeout(() => {
          window.location.href = '/';
        }, 3000);
      } catch (err) {
        setError(err.message || '认证过程中发生错误');
        setLoading(false);
      }
    };

    fetchSessionData();
  }, []);

  if (loading) {
    return (
      <div className="App">
        <header className="App-header">
          <h1 className="App-title">CodeInterpreter AI</h1>
          <p className="App-subtitle">正在处理GitHub认证...</p>
        </header>
        <div className="auth-callback-container">
          <div className="loading-spinner"></div>
          <p>正在处理您的GitHub认证，请稍候...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="App">
        <header className="App-header">
          <h1 className="App-title">CodeInterpreter AI</h1>
          <p className="App-subtitle">认证错误</p>
        </header>
        <div className="auth-callback-container error">
          <p>认证过程中发生错误：{error}</p>
          <button 
            className="form-button" 
            onClick={() => window.location.href = '/'}
          >
            返回首页
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1 className="App-title">CodeInterpreter AI</h1>
        <p className="App-subtitle">认证成功</p>
      </header>
      <div className="auth-callback-container success">
        <div className="user-info">
          {userInfo?.avatar_url && (
            <img 
              src={userInfo.avatar_url} 
              alt="GitHub头像" 
              className="github-avatar" 
            />
          )}
          <h2>欢迎，{userInfo?.name || userInfo?.login || '用户'}！</h2>
        </div>
        <p>您已成功通过GitHub认证。</p>
        <p>正在返回首页...</p>
      </div>
    </div>
  );
}

export default AuthCallback;

// PROMPT_SEGMENT_2_COMPLETE
