import os
import re
from typing import List, Dict, Generator, Tuple, Set, Optional
import logging
from dataclasses import dataclass
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CodeChunk:
    """
    代码块数据类，包含代码内容和元数据
    """
    content: str  # 代码块内容
    file_path: str  # 文件路径
    start_line: int  # 起始行号
    end_line: int  # 结束行号
    language: str  # 编程语言
    chunk_id: str  # 块ID

class CodeChunker:
    """
    代码分块器，用于将代码仓库分割成小块
    """
    # 支持的编程语言及其文件扩展名
    SUPPORTED_LANGUAGES = {
        'python': ['.py', '.pyx', '.pyi', '.pyw'],
        'javascript': ['.js', '.jsx', '.ts', '.tsx'],
        'java': ['.java'],
        'c': ['.c', '.h'],
        'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.hh', '.hxx'],
        'csharp': ['.cs'],
        'go': ['.go'],
        'ruby': ['.rb'],
        'php': ['.php'],
        'swift': ['.swift'],
        'rust': ['.rs'],
        'kotlin': ['.kt', '.kts'],
        'scala': ['.scala'],
        'html': ['.html', '.htm'],
        'css': ['.css', '.scss', '.sass', '.less'],
        'json': ['.json'],
        'yaml': ['.yaml', '.yml'],
        'xml': ['.xml'],
        'markdown': ['.md', '.markdown'],
        'shell': ['.sh', '.bash', '.zsh'],
        'sql': ['.sql'],
    }
    
    # 要忽略的目录
    IGNORED_DIRS = {
        '.git', 'node_modules', 'venv', 'env', '.env', '__pycache__', 
        'dist', 'build', 'target', 'out', 'bin', 'obj', '.idea', '.vscode',
        'coverage', '.nyc_output', '.pytest_cache', '.mypy_cache', '.tox',
        'vendor', 'bower_components', 'jspm_packages', 'packages'
    }
    
    # 要忽略的文件
    IGNORED_FILES = {
        'LICENSE', 'LICENCE', 'NOTICE', 'PATENTS', 'AUTHORS', 'CONTRIBUTORS',
        'COPYING', 'INSTALL', 'CHANGELOG', 'CHANGES', 'NEWS', 'HISTORY',
        '.gitignore', '.gitattributes', '.gitmodules', '.editorconfig',
        '.travis.yml', '.gitlab-ci.yml', 'appveyor.yml', 'circle.yml',
        'Dockerfile', 'docker-compose.yml', 'Makefile', 'CMakeLists.txt',
        'package-lock.json', 'yarn.lock', 'Pipfile.lock', 'poetry.lock',
        '.DS_Store', 'Thumbs.db'
    }
    
    # 要忽略的文件扩展名
    IGNORED_EXTENSIONS = {
        # 图片
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp',
        # 音频
        '.mp3', '.wav', '.ogg', '.flac', '.aac',
        # 视频
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv',
        # 压缩文件
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
        # 二进制文件
        '.exe', '.dll', '.so', '.dylib', '.class', '.pyc', '.pyd',
        # 其他
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.ttf', '.otf', '.woff', '.woff2', '.eot'
    }
    
    def __init__(self, 
                 repo_dir: str, 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 100,
                 max_file_size: int = 1024 * 1024,  # 1MB
                 ignored_dirs: Optional[Set[str]] = None,
                 ignored_files: Optional[Set[str]] = None,
                 ignored_extensions: Optional[Set[str]] = None):
        """
        初始化代码分块器
        
        Args:
            repo_dir: 代码仓库目录
            chunk_size: 块大小（字符数）
            chunk_overlap: 块重叠大小（字符数）
            max_file_size: 最大文件大小（字节）
            ignored_dirs: 要忽略的目录集合
            ignored_files: 要忽略的文件集合
            ignored_extensions: 要忽略的文件扩展名集合
        """
        self.repo_dir = os.path.abspath(repo_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_file_size = max_file_size
        
        # 合并默认忽略列表和用户提供的忽略列表
        self.ignored_dirs = self.IGNORED_DIRS.copy()
        if ignored_dirs:
            self.ignored_dirs.update(ignored_dirs)
            
        self.ignored_files = self.IGNORED_FILES.copy()
        if ignored_files:
            self.ignored_files.update(ignored_files)
            
        self.ignored_extensions = self.IGNORED_EXTENSIONS.copy()
        if ignored_extensions:
            self.ignored_extensions.update(ignored_extensions)
        
        # 创建扩展名到语言的映射
        self.ext_to_lang = {}
        for lang, extensions in self.SUPPORTED_LANGUAGES.items():
            for ext in extensions:
                self.ext_to_lang[ext] = lang
    
    def get_file_language(self, file_path: str) -> Optional[str]:
        """
        根据文件扩展名获取编程语言
        
        Args:
            file_path: 文件路径
            
        Returns:
            语言名称，如果不支持则返回None
        """
        ext = os.path.splitext(file_path)[1].lower()
        return self.ext_to_lang.get(ext)
    
    def should_process_file(self, file_path: str) -> bool:
        """
        判断是否应该处理该文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否应该处理
        """
        # 检查文件大小
        try:
            if os.path.getsize(file_path) > self.max_file_size:
                logger.info(f"跳过大文件: {file_path}")
                return False
        except OSError:
            logger.warning(f"无法获取文件大小: {file_path}")
            return False
        
        # 检查文件名
        file_name = os.path.basename(file_path)
        if file_name in self.ignored_files:
            return False
        
        # 检查文件扩展名
        ext = os.path.splitext(file_name)[1].lower()
        if ext in self.ignored_extensions:
            return False
        
        # 检查是否是支持的语言
        return self.get_file_language(file_path) is not None
    
    def should_process_dir(self, dir_path: str) -> bool:
        """
        判断是否应该处理该目录
        
        Args:
            dir_path: 目录路径
            
        Returns:
            是否应该处理
        """
        dir_name = os.path.basename(dir_path)
        return dir_name not in self.ignored_dirs
    
    def find_code_files(self) -> Generator[str, None, None]:
        """
        遍历仓库目录，找出所有应该处理的代码文件
        
        Returns:
            文件路径生成器
        """
        for root, dirs, files in os.walk(self.repo_dir):
            # 过滤掉要忽略的目录
            dirs[:] = [d for d in dirs if self.should_process_dir(os.path.join(root, d))]
            
            for file in files:
                file_path = os.path.join(root, file)
                if self.should_process_file(file_path):
                    yield file_path
    
    def chunk_file_by_size(self, file_path: str) -> List[CodeChunk]:
        """
        按固定大小+重叠策略分割文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            代码块列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"无法以UTF-8编码读取文件: {file_path}")
            try:
                # 尝试使用Latin-1编码
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"读取文件失败: {file_path}, 错误: {str(e)}")
                return []
        except Exception as e:
            logger.error(f"读取文件失败: {file_path}, 错误: {str(e)}")
            return []
        
        # 如果文件为空，返回空列表
        if not content.strip():
            return []
        
        # 获取文件相对于仓库根目录的路径
        rel_path = os.path.relpath(file_path, self.repo_dir)
        
        # 获取文件语言
        language = self.get_file_language(file_path)
        
        # 分割文件内容
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_chunk_size = 0
        start_line = 1
        
        for i, line in enumerate(lines, 1):
            line_with_newline = line + '\n'
            line_size = len(line_with_newline)
            
            # 如果当前行加上当前块大小超过了块大小，并且当前块不为空，则创建新块
            if current_chunk_size + line_size > self.chunk_size and current_chunk:
                # 创建代码块
                chunk_content = ''.join(current_chunk)
                chunk_id = f"{rel_path}:{start_line}-{i-1}"
                chunk = CodeChunk(
                    content=chunk_content,
                    file_path=rel_path,
                    start_line=start_line,
                    end_line=i-1,
                    language=language,
                    chunk_id=chunk_id
                )
                chunks.append(chunk)
                
                # 计算重叠部分
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                current_chunk = current_chunk[overlap_start:]
                current_chunk_size = sum(len(c) for c in current_chunk)
                
                # 更新起始行号
                overlap_lines = len(current_chunk)
                start_line = i - overlap_lines
            
            current_chunk.append(line_with_newline)
            current_chunk_size += line_size
        
        # 处理最后一个块
        if current_chunk:
            chunk_content = ''.join(current_chunk)
            chunk_id = f"{rel_path}:{start_line}-{len(lines)}"
            chunk = CodeChunk(
                content=chunk_content,
                file_path=rel_path,
                start_line=start_line,
                end_line=len(lines),
                language=language,
                chunk_id=chunk_id
            )
            chunks.append(chunk)
        
        return chunks
    
    def chunk_file_by_file(self, file_path: str) -> List[CodeChunk]:
        """
        按文件分割，每个文件作为一个块
        
        Args:
            file_path: 文件路径
            
        Returns:
            代码块列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"无法以UTF-8编码读取文件: {file_path}")
            try:
                # 尝试使用Latin-1编码
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"读取文件失败: {file_path}, 错误: {str(e)}")
                return []
        except Exception as e:
            logger.error(f"读取文件失败: {file_path}, 错误: {str(e)}")
            return []
        
        # 如果文件为空，返回空列表
        if not content.strip():
            return []
        
        # 获取文件相对于仓库根目录的路径
        rel_path = os.path.relpath(file_path, self.repo_dir)
        
        # 获取文件语言
        language = self.get_file_language(file_path)
        
        # 计算行数
        line_count = content.count('\n') + 1
        
        # 创建代码块
        chunk_id = f"{rel_path}:1-{line_count}"
        chunk = CodeChunk(
            content=content,
            file_path=rel_path,
            start_line=1,
            end_line=line_count,
            language=language,
            chunk_id=chunk_id
        )
        
        return [chunk]
    
    def chunk_repository(self, by_file: bool = False) -> List[CodeChunk]:
        """
        分割整个代码仓库
        
        Args:
            by_file: 是否按文件分割，如果为False则按固定大小+重叠分割
            
        Returns:
            代码块列表
        """
        all_chunks = []
        
        for file_path in self.find_code_files():
            try:
                if by_file:
                    chunks = self.chunk_file_by_file(file_path)
                else:
                    chunks = self.chunk_file_by_size(file_path)
                
                all_chunks.extend(chunks)
                logger.info(f"处理文件: {file_path}, 生成 {len(chunks)} 个代码块")
            except Exception as e:
                logger.error(f"处理文件失败: {file_path}, 错误: {str(e)}")
        
        logger.info(f"总共生成 {len(all_chunks)} 个代码块")
        return all_chunks

# PROMPT_SEGMENT_5_COMPLETE
