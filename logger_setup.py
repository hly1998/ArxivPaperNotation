"""
日志设置模块 - 统一的日志配置
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

# 全局日志实例
_logger: Optional[logging.Logger] = None


def setup_logger(
    name: str = "arxiv_notifier",
    log_file: Optional[str] = None,
    level: str = "INFO",
    enable_rotation: bool = True,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志名称
        log_file: 日志文件路径
        level: 日志级别
        enable_rotation: 是否启用日志轮转
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的日志备份数量
    
    Returns:
        配置好的Logger对象
    """
    global _logger
    
    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件handler
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        if enable_rotation:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
        else:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """
    获取当前日志记录器
    
    Returns:
        Logger对象，如果未设置则返回默认logger
    """
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger

