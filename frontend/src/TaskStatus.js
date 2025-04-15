import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function TaskStatus({ taskId, onClose }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);

  // 获取任务状态
  const fetchTaskStatus = async () => {
    try {
      const sessionId = localStorage.getItem('session_id');
      if (!sessionId) {
        throw new Error('未找到会话ID');
      }

      const response = await axios.get(`/api/repository/status/${taskId}`);
      setStatus(response.data);
      
      // 如果任务已完成或失败，停止轮询
      if (
        response.data.status === 'completed' || 
        response.data.status === 'failed'
      ) {
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
      }
      
      setLoading(false);
    } catch (err) {
      setError(err.message || '获取任务状态失败');
      setLoading(false);
      
      // 发生错误时停止轮询
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
      }
    }
  };

  // 组件挂载时开始轮询任务状态
  useEffect(() => {
    // 立即获取一次状态
    fetchTaskStatus();
    
    // 设置轮询间隔（每3秒）
    const interval = setInterval(fetchTaskStatus, 3000);
    setPollingInterval(interval);
    
    // 组件卸载时清除轮询
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [taskId]);

  // 获取状态类名
  const getStatusClassName = () => {
    if (!status) return '';
    
    switch (status.status) {
      case 'pending':
      case 'downloading':
      case 'processing':
        return 'status-info';
      case 'completed':
        return 'status-success';
      case 'failed':
        return 'status-error';
      default:
        return '';
    }
  };

  // 获取状态图标
  const getStatusIcon = () => {
    if (!status) return null;
    
    switch (status.status) {
      case 'pending':
        return '⏳';
      case 'downloading':
        return '⬇️';
      case 'processing':
        return '🔄';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      default:
        return '❓';
    }
  };

  if (loading) {
    return (
      <div className="task-status-modal">
        <div className="task-status-content">
          <h3>任务状态</h3>
          <div className="loading-spinner"></div>
          <p>正在获取任务状态...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="task-status-modal">
        <div className="task-status-content error">
          <h3>获取任务状态失败</h3>
          <p>{error}</p>
          <button className="form-button" onClick={onClose}>关闭</button>
        </div>
      </div>
    );
  }

  return (
    <div className="task-status-modal">
      <div className="task-status-content">
        <h3>仓库处理状态 {getStatusIcon()}</h3>
        
        <div className={`task-status-details ${getStatusClassName()}`}>
          <p><strong>状态:</strong> {status.status}</p>
          <p><strong>消息:</strong> {status.message}</p>
          <p><strong>仓库:</strong> {status.repo_url}</p>
          <p><strong>任务ID:</strong> {status.task_id}</p>
          <p><strong>创建时间:</strong> {new Date(status.created_at).toLocaleString()}</p>
          <p><strong>更新时间:</strong> {new Date(status.updated_at).toLocaleString()}</p>
          
          {status.error && (
            <div className="task-error">
              <p><strong>错误:</strong> {status.error}</p>
            </div>
          )}
        </div>
        
        <div className="task-status-actions">
          <button className="form-button" onClick={onClose}>关闭</button>
          
          {(status.status === 'completed' || status.status === 'failed') && (
            <button 
              className="form-button"
              onClick={fetchTaskStatus}
              style={{ marginLeft: '10px' }}
            >
              刷新
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default TaskStatus;
