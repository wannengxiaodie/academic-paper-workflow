"""
工具函数 - 提供项目中通用的辅助函数。
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)


def count_chinese_words(text: str) -> int:
    """
    统计文本中的中文字数（不含空格和标点）。

    Args:
        text: 待统计文本

    Returns:
        中文字数
    """
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    return len(chinese_chars)


def count_total_words(text: str) -> int:
    """
    统计文本总字数（中文字 + 英文单词），不含空白字符。

    Args:
        text: 待统计文本

    Returns:
        总字数
    """
    # 移除空白
    cleaned = re.sub(r"\s+", "", text)
    return len(cleaned)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本到指定长度。

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后添加的后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_duration(seconds: float) -> str:
    """
    将秒数格式化为可读的时间字符串。

    Args:
        seconds: 秒数

    Returns:
        格式化的时间字符串（如 "1分30秒"）
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}分{secs:.0f}秒"
    hours = int(minutes // 60)
    mins = minutes % 60
    return f"{hours}小时{mins}分{secs:.0f}秒"


def safe_dict_get(data: dict, key: str, default: Any = None) -> Any:
    """
    安全地从嵌套字典中获取值。

    Args:
        data: 字典
        key: 键名（支持点号分隔的嵌套路径，如 "a.b.c"）
        default: 默认值

    Returns:
        找到的值或默认值
    """
    if not data or not isinstance(data, dict):
        return default

    keys = key.split(".")
    current = data
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return default
    return current


def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
):
    """
    带指数退避的重试装饰器。

    Args:
        func: 需要重试的函数
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）

    Returns:
        装饰后的函数
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"{func.__name__} 第{attempt + 1}次调用失败: {e}, "
                        f"{delay:.1f}秒后重试..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"{func.__name__} 重试{max_retries}次后仍然失败: {e}"
                    )
        raise last_error

    return wrapper


def validate_title_level(level: str) -> bool:
    """
    验证职称级别是否合法。

    Args:
        level: 职称级别

    Returns:
        是否合法
    """
    import config
    return level in config.SUPPORTED_TITLE_LEVELS


def validate_department(department: str) -> bool:
    """
    验证科室是否合法。

    Args:
        department: 科室名称

    Returns:
        是否合法
    """
    import config
    return department in config.SUPPORTED_DEPARTMENTS


def validate_study_type(study_type: str) -> bool:
    """
    验证研究类型是否合法。

    Args:
        study_type: 研究类型

    Returns:
        是否合法
    """
    import config
    return study_type in config.SUPPORTED_STUDY_TYPES


def build_pubmed_query(topic: str, filters: dict | None = None) -> str:
    """
    构建PubMed检索查询字符串。

    将中文主题转换为英文PubMed检索语法。

    Args:
        topic: 研究主题（中英文均可）
        filters: 额外的筛选条件（如年份范围等）

    Returns:
        PubMed检索查询字符串
    """
    # 基础查询
    query = topic

    # 添加常见医学检索限定
    if filters:
        if filters.get("min_year"):
            query += f' AND ("{filters["min_year"]}"[PDAT] : "3000"[PDAT])'
        if filters.get("max_year"):
            query += f' AND ("1900"[PDAT] : "{filters["max_year"]}"[PDAT])'
        if filters.get("article_type"):
            query += f' AND {filters["article_type"]}[pt]'
        if filters.get("language") == "English":
            query += ' AND English[lang]'

    return query


def merge_paper_sections(sections: list[dict]) -> str:
    """
    将多个章节合并为完整论文文本。

    Args:
        sections: 章节列表，每条包含 title 和 content

    Returns:
        合并后的完整文本
    """
    parts: list[str] = []
    for section in sections:
        title = section.get("title", "")
        content = section.get("content", "")
        if content:
            if title:
                parts.append(f"\n{title}\n\n{content}")
            else:
                parts.append(content)

    return "\n\n".join(parts).strip()
