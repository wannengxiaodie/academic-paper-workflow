"""
配置文件 - 集中管理API密钥、数据库路径、常量等配置信息。
所有敏感信息从环境变量中读取，避免硬编码。
"""

import os
from pathlib import Path


# ============================================================
# API 密钥配置（从环境变量读取）
# ============================================================
API_KEY_OPENAI: str = os.getenv("API_KEY_OPENAI", "")
API_KEY_ANTHROPIC: str = os.getenv("API_KEY_ANTHROPIC", "")

# OpenAI API 配置
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "4096"))

# Anthropic API 配置
ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_MAX_TOKENS: int = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096"))

# ============================================================
# PubMed / 文献检索接口配置
# ============================================================
PUBMED_EUTILS_BASE: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_API_KEY: str = os.getenv("PUBMED_API_KEY", "")  # 可选，有key可提高请求速率
PUBMED_DEFAULT_RETMAX: int = 20
PUBMED_REQUEST_TIMEOUT: int = 30  # 秒

# CNKI 接口配置（预留，待正式对接）
CNKI_SEARCH_URL: str = os.getenv("CNKI_SEARCH_URL", "https://api.cnki.net/search")
CNKI_API_KEY: str = os.getenv("CNKI_API_KEY", "")

# ============================================================
# 支持的职称级别
# ============================================================
SUPPORTED_TITLE_LEVELS: list[str] = ["初级", "中级", "副高级", "正高级"]

# 职称级别权重映射（用于期刊匹配评分）
TITLE_LEVEL_WEIGHTS: dict[str, float] = {
    "初级": 1.0,
    "中级": 2.0,
    "副高级": 3.0,
    "正高级": 4.0,
}

# ============================================================
# 支持的学科/科室列表
# ============================================================
SUPPORTED_DEPARTMENTS: list[str] = [
    "内科",
    "外科",
    "儿科",
    "妇产科",
    "骨科",
    "神经内科",
    "心血管内科",
    "肿瘤科",
    "护理",
    "药学",
    "影像科",
    "检验科",
    "公共卫生",
]

# ============================================================
# 支持的研究类型
# ============================================================
SUPPORTED_STUDY_TYPES: list[str] = [
    "RCT",
    "队列研究",
    "病例对照",
    "横断面",
    "病例系列",
    "病例报告",
    "系统综述",
    "Meta分析",
]

# ============================================================
# 质量门控阈值配置
# ============================================================
GATE_PASS_THRESHOLD: float = 3.5  # 每维度平均分 >= 3.5 通过
GATE_MIN_DIMENSION_SCORE: int = 2  # 每维度最低分 >= 2

# 评分维度
REVIEW_DIMENSIONS: list[str] = [
    "临床价值",
    "科学性",
    "创新性",
    "文献覆盖",
    "统计方法",
    "伦理合规",
    "写作规范",
]

# ============================================================
# 论文字数配置（按职称级别）
# ============================================================
WORD_COUNT_TARGETS: dict[str, dict[str, int]] = {
    "初级": {"min": 2000, "max": 3000},
    "中级": {"min": 3000, "max": 5000},
    "副高级": {"min": 4000, "max": 6000},
    "正高级": {"min": 5000, "max": 8000},
}

# ============================================================
# 项目路径配置
# ============================================================
BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR / "data"

# ============================================================
# AI 调用降级策略配置
# ============================================================
AI_FALLBACK_ENABLED: bool = True  # 当AI API不可用时是否使用降级策略
AI_REQUEST_TIMEOUT: int = 60  # 秒
AI_MAX_RETRIES: int = 3
AI_RETRY_DELAY: float = 1.0  # 秒
