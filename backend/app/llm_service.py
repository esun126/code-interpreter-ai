import os
import logging
import json
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI
import tiktoken

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 从环境变量获取OpenAI API密钥
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# 默认使用的模型
DEFAULT_MODEL = "gpt-3.5-turbo"
# 最大上下文长度
MAX_CONTEXT_LENGTH = 4000
# 最大响应长度
MAX_RESPONSE_LENGTH = 1000

class LLMService:
    """
    LLM服务，用于调用大型语言模型进行代码问答
    """
    
    def __init__(self, api_key: str = OPENAI_API_KEY, model: str = DEFAULT_MODEL):
        """
        初始化LLM服务
        
        Args:
            api_key: OpenAI API密钥
            model: 使用的模型名称
        """
        self.api_key = api_key
        self.model = model
        self.client = None
        
        # 如果没有提供API密钥，记录警告
        if not self.api_key:
            logger.warning("未提供OpenAI API密钥，将使用模拟模式")
        else:
            # 初始化OpenAI客户端
            self.client = OpenAI(api_key=self.api_key)
        
        # 初始化tokenizer
        self.tokenizer = tiktoken.encoding_for_model(model) if model.startswith("gpt") else None
        
        logger.info(f"LLM服务初始化完成，使用模型: {model}")
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 输入文本
            
        Returns:
            token数量
        """
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # 如果没有tokenizer，使用简单的估算
            return len(text) // 4
    
    def truncate_text(self, text: str, max_tokens: int) -> str:
        """
        截断文本，使其不超过最大token数量
        
        Args:
            text: 输入文本
            max_tokens: 最大token数量
            
        Returns:
            截断后的文本
        """
        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            if len(tokens) <= max_tokens:
                return text
            
            truncated_tokens = tokens[:max_tokens]
            return self.tokenizer.decode(truncated_tokens)
        else:
            # 如果没有tokenizer，使用简单的估算
            if len(text) // 4 <= max_tokens:
                return text
            
            return text[:max_tokens * 4]
    
    def build_prompt(self, question: str, code_chunks: List[Dict[str, Any]], max_tokens: int = MAX_CONTEXT_LENGTH) -> str:
        """
        构建提示词
        
        Args:
            question: 用户问题
            code_chunks: 代码块列表
            max_tokens: 最大token数量
            
        Returns:
            构建的提示词
        """
        # 基本提示词模板
        prompt_template = """你是一个专业的代码解释器，擅长分析和解释代码。请根据以下代码片段回答用户的问题。

用户问题："{question}"

以下是可能相关的代码片段：

{code_chunks}

请根据以上代码片段回答用户的问题。如果代码片段中没有足够的信息来回答问题，请明确指出，并尽可能根据已有信息提供有用的见解。
回答应该清晰、准确、专业，并直接针对用户的问题。
"""
        
        # 格式化代码块
        formatted_chunks = []
        for i, chunk in enumerate(code_chunks, 1):
            content = chunk.get("content", "")
            metadata = chunk.get("metadata", {})
            file_path = metadata.get("file_path", "未知文件")
            start_line = metadata.get("start_line", 1)
            language = metadata.get("language", "未知语言")
            
            formatted_chunk = f"片段 {i} (来自 {file_path} L{start_line}, 语言: {language}):\n```\n{content}\n```\n"
            formatted_chunks.append(formatted_chunk)
        
        # 合并代码块
        all_chunks_text = "\n".join(formatted_chunks)
        
        # 填充提示词模板
        prompt = prompt_template.format(
            question=question,
            code_chunks=all_chunks_text
        )
        
        # 计算提示词的token数量
        prompt_tokens = self.count_tokens(prompt)
        
        # 如果提示词超过最大token数量，需要截断代码块
        if prompt_tokens > max_tokens:
            # 计算需要保留的token数量
            remaining_tokens = max_tokens - self.count_tokens(prompt_template.format(
                question=question,
                code_chunks=""
            ))
            
            # 截断代码块
            truncated_chunks = []
            current_tokens = 0
            
            for chunk in formatted_chunks:
                chunk_tokens = self.count_tokens(chunk)
                
                if current_tokens + chunk_tokens <= remaining_tokens:
                    truncated_chunks.append(chunk)
                    current_tokens += chunk_tokens
                else:
                    # 尝试截断当前代码块
                    available_tokens = remaining_tokens - current_tokens
                    if available_tokens > 100:  # 确保至少有100个token可用
                        truncated_chunk = self.truncate_text(chunk, available_tokens)
                        truncated_chunks.append(truncated_chunk)
                    
                    break
            
            # 重新构建提示词
            prompt = prompt_template.format(
                question=question,
                code_chunks="\n".join(truncated_chunks)
            )
        
        return prompt
    
    def query(self, question: str, code_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        查询LLM
        
        Args:
            question: 用户问题
            code_chunks: 代码块列表
            
        Returns:
            LLM响应
        """
        # 构建提示词
        prompt = self.build_prompt(question, code_chunks)
        
        # 如果没有API密钥，使用模拟模式
        if not self.api_key or not self.client:
            logger.warning("使用模拟模式，无法调用真实的LLM API")
            return {
                "answer": "这是一个模拟的LLM响应。要获取真实的回答，请配置OpenAI API密钥。",
                "model": "模拟模式",
                "prompt_tokens": self.count_tokens(prompt),
                "completion_tokens": 0,
                "total_tokens": self.count_tokens(prompt)
            }
        
        try:
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的代码解释器，擅长分析和解释代码。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=MAX_RESPONSE_LENGTH,
                temperature=0.3,  # 使用较低的温度以获得更确定性的回答
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # 提取回答
            answer = response.choices[0].message.content
            
            # 返回结果
            return {
                "answer": answer,
                "model": self.model,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        except Exception as e:
            logger.error(f"调用LLM API时发生错误: {str(e)}")
            return {
                "answer": f"调用LLM API时发生错误: {str(e)}",
                "model": self.model,
                "prompt_tokens": self.count_tokens(prompt),
                "completion_tokens": 0,
                "total_tokens": self.count_tokens(prompt),
                "error": str(e)
            }

# 创建全局LLM服务实例
llm_service = LLMService()

# PROMPT_SEGMENT_7_COMPLETE
