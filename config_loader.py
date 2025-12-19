"""
配置加载器 - 从YAML文件和环境变量加载配置

环境变量优先级高于配置文件，支持以下环境变量：
- ARXIV_CATEGORIES: arXiv分类，JSON格式，如 '["cs.CV", "cs.CL"]'
- MATCHING_KEYWORDS: 关键词，JSON格式，如 '{"rag": 2.0, "agent": 1.0}'
- MATCHING_THRESHOLD: BM25阈值
- MATCHING_TOP_K: 最大论文数量
- LLM_MODEL: 模型名称
- LLM_BASE_URL: API基础URL
- LLM_API_KEY: API密钥
- LLM_BATCH_SIZE: 批量处理大小
- EMAIL_SMTP_SERVER: SMTP服务器
- EMAIL_SMTP_PORT: SMTP端口
- EMAIL_SENDER: 发送方邮箱
- EMAIL_PASSWORD: 邮箱密码/授权码
- EMAIL_RECIPIENTS: 收件人，JSON格式，如 '["a@b.com", "c@d.com"]'
"""
import os
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict


def _parse_json_env(env_name: str, default=None):
    """
    解析环境变量，支持多种格式：
    - JSON格式: '["a", "b"]' 或 '{"a": 1.0, "b": 2.0}'
    - 逗号分隔: 'a, b, c'
    - 单个值: 'a'
    """
    value = os.environ.get(env_name, '').strip()
    if not value:
        return default
    
    # 尝试 JSON 解析
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass
    
    # 尝试逗号分隔的列表
    if ',' in value:
        return [item.strip() for item in value.split(',') if item.strip()]
    
    # 单个值作为列表返回
    if default is not None and isinstance(default, list):
        return [value]
    
    return value if value else default


@dataclass
class Config:
    """配置类"""
    # arXiv分类
    categories: List[str] = field(default_factory=lambda: ["cs.CV", "cs.CL"])
    
    # 数据目录
    base_data_dir: str = "../data"
    
    # PDF下载配置（现在默认禁用）
    download_pdf: bool = False
    pdf_timeout: int = 60
    pdf_max_size_mb: int = 100
    concurrent_downloads: int = 4
    
    # 日志配置
    log_dir: str = "../logs"
    log_level: str = "INFO"
    enable_log_rotation: bool = True
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    # 关键词匹配配置（支持简单列表或带权重字典）
    keywords: Union[List[str], Dict[str, float]] = field(default_factory=dict)
    threshold: float = 0.5  # BM25得分阈值
    top_k: Optional[int] = None  # 最大论文数量限制（None表示不限制）
    
    # LLM批量处理配置
    llm_batch_size: int = 3  # 每次LLM调用处理的论文数量
    
    # LLM配置
    llm_model: str = "deepseek-chat"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    
    # 邮件配置
    email_smtp_server: str = ""
    email_smtp_port: int = 587
    email_sender: str = ""
    email_password: str = ""
    email_recipients: List[str] = field(default_factory=list)
    
    def ensure_directories(self):
        """确保必要目录存在"""
        Path(self.base_data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
    
    def get_log_file(self, name: str) -> str:
        """获取日志文件路径"""
        return os.path.join(self.log_dir, f"{name}.log")


def load_config_from_yaml(yaml_path: str) -> dict:
    """从YAML文件加载配置"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def _resolve_path(path: str, base_dir: str) -> str:
    """将相对路径转换为绝对路径（基于项目根目录）"""
    if os.path.isabs(path):
        return path
    return os.path.abspath(os.path.join(base_dir, path))


def get_config(config_path: Optional[str] = None) -> Config:
    """
    获取配置对象
    
    Args:
        config_path: 配置文件路径，默认为项目根目录的 config.yaml
    
    Returns:
        Config对象
    """
    # 默认配置文件路径（项目根目录）
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    
    # 加载YAML配置（如果存在）
    if os.path.exists(config_path):
        yaml_config = load_config_from_yaml(config_path)
        # 获取项目根目录（配置文件所在目录）
        project_root = os.path.dirname(os.path.abspath(config_path))
    else:
        yaml_config = {}  # 配置文件不存在时使用空配置，但继续处理环境变量
        # 使用当前工作目录作为项目根目录
        project_root = os.getcwd()
    
    # 构建配置对象
    config = Config()
    
    # ==========================================================================
    # arXiv配置 - 环境变量优先
    # ==========================================================================
    arxiv_config = yaml_config.get('arxiv', {})
    env_categories = _parse_json_env('ARXIV_CATEGORIES')
    if env_categories:
        config.categories = env_categories
    elif 'categories' in arxiv_config:
        config.categories = arxiv_config['categories']
    
    # ==========================================================================
    # 数据目录配置（转换为绝对路径）
    # ==========================================================================
    data_config = yaml_config.get('data', {})
    if 'base_dir' in data_config:
        config.base_data_dir = _resolve_path(data_config['base_dir'], project_root)
    else:
        config.base_data_dir = _resolve_path(config.base_data_dir, project_root)
    
    # ==========================================================================
    # PDF配置（默认禁用）
    # ==========================================================================
    pdf_config = yaml_config.get('pdf', {})
    config.download_pdf = pdf_config.get('download', False)
    config.pdf_timeout = pdf_config.get('timeout', 60)
    config.pdf_max_size_mb = pdf_config.get('max_size_mb', 100)
    config.concurrent_downloads = pdf_config.get('concurrent_downloads', 4)
    
    # ==========================================================================
    # 日志配置（转换为绝对路径）
    # ==========================================================================
    log_config = yaml_config.get('logging', {})
    if 'dir' in log_config:
        config.log_dir = _resolve_path(log_config['dir'], project_root)
    else:
        config.log_dir = _resolve_path(config.log_dir, project_root)
    config.log_level = log_config.get('level', 'INFO')
    config.enable_log_rotation = log_config.get('rotation', True)
    config.log_max_bytes = log_config.get('max_bytes', 10 * 1024 * 1024)
    config.log_backup_count = log_config.get('backup_count', 5)
    
    # ==========================================================================
    # 关键词匹配配置 - 环境变量优先
    # ==========================================================================
    match_config = yaml_config.get('matching', {})
    
    # 关键词（环境变量优先）
    env_keywords = _parse_json_env('MATCHING_KEYWORDS')
    if env_keywords:
        raw_keywords = env_keywords
    else:
        raw_keywords = match_config.get('keywords', [])
    
    # 解析关键词格式
    if isinstance(raw_keywords, dict):
        config.keywords = raw_keywords
    elif isinstance(raw_keywords, list):
        keywords_dict = {}
        for item in raw_keywords:
            if isinstance(item, str):
                keywords_dict[item] = 1.0
            elif isinstance(item, dict):
                keywords_dict.update(item)
        config.keywords = keywords_dict
    else:
        config.keywords = {}
    
    # 阈值（环境变量优先）
    env_threshold = os.environ.get('MATCHING_THRESHOLD')
    if env_threshold:
        config.threshold = float(env_threshold)
    else:
        config.threshold = match_config.get('threshold', 0.5)
    
    # Top-K（环境变量优先）
    env_top_k = os.environ.get('MATCHING_TOP_K')
    if env_top_k:
        config.top_k = int(env_top_k) if env_top_k.lower() != 'null' else None
    else:
        config.top_k = match_config.get('top_k', None)
    
    # ==========================================================================
    # LLM配置 - 环境变量优先
    # ==========================================================================
    llm_config = yaml_config.get('llm', {})
    
    # 模型名称
    config.llm_model = os.environ.get('LLM_MODEL') or llm_config.get('model_name', 'deepseek-chat')
    
    # API密钥（仅从环境变量读取，安全考虑）
    config.llm_api_key = os.environ.get('LLM_API_KEY', '') or llm_config.get('api_key', '')
    
    # Base URL
    config.llm_base_url = os.environ.get('LLM_BASE_URL') or llm_config.get('base_url', 'https://api.deepseek.com')
    
    # 批量处理大小
    env_batch_size = os.environ.get('LLM_BATCH_SIZE')
    if env_batch_size:
        config.llm_batch_size = int(env_batch_size)
    else:
        config.llm_batch_size = llm_config.get('batch_size', 3)
    
    # ==========================================================================
    # 邮件配置 - 环境变量优先
    # ==========================================================================
    email_config = yaml_config.get('email', {})
    
    # SMTP服务器
    config.email_smtp_server = os.environ.get('EMAIL_SMTP_SERVER') or email_config.get('smtp_server', '')
    
    # SMTP端口
    env_smtp_port = os.environ.get('EMAIL_SMTP_PORT')
    if env_smtp_port:
        config.email_smtp_port = int(env_smtp_port)
    else:
        config.email_smtp_port = email_config.get('smtp_port', 587)
    
    # 发送方邮箱
    config.email_sender = os.environ.get('EMAIL_SENDER') or email_config.get('sender', '')
    
    # 邮箱密码（仅从环境变量读取，安全考虑）
    config.email_password = os.environ.get('EMAIL_PASSWORD', '') or email_config.get('password', '')
    
    # 收件人列表
    env_recipients = _parse_json_env('EMAIL_RECIPIENTS')
    if env_recipients:
        config.email_recipients = env_recipients
    else:
        config.email_recipients = email_config.get('recipients', [])
    
    return config

