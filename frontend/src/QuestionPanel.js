import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function QuestionPanel({ repoUrl, onError }) {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);

  // 处理输入变化
  const handleInputChange = (e) => {
    setQuestion(e.target.value);
    // 清除之前的错误
    if (error) {
      setError(null);
    }
  };

  // 处理提问
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // 验证输入
    if (!question.trim()) {
      setError('请输入问题');
      return;
    }

    // 验证仓库URL
    if (!repoUrl) {
      setError('请先提交GitHub仓库URL');
      if (onError) {
        onError('请先提交GitHub仓库URL');
      }
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      // 获取会话ID
      const sessionId = localStorage.getItem('session_id');
      if (!sessionId) {
        throw new Error('未找到会话ID，请重新登录');
      }
      
      // 调用后端API
      const response = await axios.post(
        '/api/repository/question',
        {
          question: question,
          repo_url: repoUrl,
          n_results: 5
        },
        {
          headers: { 'session_id': sessionId }
        }
      );
      
      // 处理响应
      const result = response.data;
      
      // 更新答案
      setAnswer(result);
      
      // 添加到历史记录
      setHistory(prevHistory => [
        ...prevHistory,
        {
          id: Date.now(),
          question: question,
          answer: result
        }
      ]);
      
      // 清空输入框
      setQuestion('');
    } catch (err) {
      console.error('提问时发生错误:', err);
      setError(err.response?.data?.detail || err.message || '提问失败，请稍后重试');
      if (onError) {
        onError(err.response?.data?.detail || err.message || '提问失败，请稍后重试');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // 渲染代码块
  const renderCodeChunks = (chunks) => {
    if (!chunks || chunks.length === 0) {
      return <p>未找到相关代码块</p>;
    }

    return (
      <div className="code-chunks">
        <h4>相关代码块：</h4>
        {chunks.map((chunk, index) => (
          <div key={index} className="code-chunk">
            <div className="code-chunk-header">
              <span className="code-chunk-file">{chunk.metadata.file_path}</span>
              <span className="code-chunk-lines">行 {chunk.metadata.start_line}-{chunk.metadata.end_line}</span>
              <span className="code-chunk-language">{chunk.metadata.language}</span>
            </div>
            <pre className="code-chunk-content">
              <code>{chunk.content}</code>
            </pre>
          </div>
        ))}
      </div>
    );
  };

  // 渲染历史记录
  const renderHistory = () => {
    if (history.length === 0) {
      return null;
    }

    return (
      <div className="question-history">
        <h3>对话历史</h3>
        {history.map((item) => (
          <div key={item.id} className="history-item">
            <div className="history-question">
              <strong>问题：</strong> {item.question}
            </div>
            <div className="history-answer">
              <strong>回答：</strong>
              <div className="answer-content">{item.answer.answer}</div>
              <div className="answer-meta">
                <small>模型：{item.answer.model} | Token使用：{item.answer.total_tokens}</small>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="question-panel">
      <h2>代码问答</h2>
      <p className="panel-description">
        向仓库提问，AI将基于代码内容回答您的问题。
      </p>
      
      <form onSubmit={handleSubmit} className="question-form">
        <div className="form-group">
          <label htmlFor="question-input" className="form-label">
            您的问题
          </label>
          <textarea
            id="question-input"
            className="form-input question-input"
            value={question}
            onChange={handleInputChange}
            placeholder="例如：这个仓库的主要功能是什么？或 请解释一下 XYZ 函数的作用..."
            rows={3}
            disabled={isLoading}
          />
        </div>
        
        <button 
          type="submit" 
          className="form-button"
          disabled={isLoading || !question.trim()}
        >
          {isLoading ? '正在思考...' : '提问'}
        </button>
      </form>
      
      {error && (
        <div className="status-area status-error">
          <p>{error}</p>
        </div>
      )}
      
      {isLoading && (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>AI正在思考您的问题，请稍候...</p>
        </div>
      )}
      
      {answer && !isLoading && (
        <div className="answer-container">
          <h3>回答</h3>
          <div className="answer-content">
            {answer.answer.split('\n').map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </div>
          
          <div className="answer-meta">
            <p>
              <small>模型：{answer.model} | 提示词Token：{answer.prompt_tokens} | 
              完成Token：{answer.completion_tokens} | 总Token：{answer.total_tokens}</small>
            </p>
          </div>
          
          {renderCodeChunks(answer.chunks)}
        </div>
      )}
      
      {renderHistory()}
    </div>
  );
}

export default QuestionPanel;

// PROMPT_SEGMENT_8_COMPLETE
