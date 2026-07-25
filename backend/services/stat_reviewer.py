"""
统计方法审查服务 - 检查论文中使用的统计方法是否适合研究类型，
并给出样本量、校正方法等方面的审查意见。
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


# 支持的研究类型列表
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

# 各研究类型推荐的统计方法
_STUDY_TYPE_METHODS: dict[str, dict] = {
    "RCT": {
        "recommended": [
            "意向性分析（ITT）",
            "卡方检验",
            "t检验",
            "方差分析（ANOVA）",
            "Kaplan-Meier生存分析",
            "Cox比例风险回归",
            "Logistic回归",
            "重复测量方差分析",
        ],
        "required": [
            "随机化方法描述",
            "样本量计算/功效分析",
            "盲法说明",
        ],
        "inappropriate": [
            "简单描述性统计（作为主要分析方法）",
        ],
    },
    "队列研究": {
        "recommended": [
            "生存分析（Kaplan-Meier, Cox回归）",
            "Logistic回归",
            "人年计算",
            "发病率/死亡率计算",
            "多因素Cox回归",
            "倾向性评分匹配",
        ],
        "required": [
            "失访率报告",
            "混杂因素调整",
            "随访时间描述",
        ],
        "inappropriate": [
            "因果推断（队列研究只能得出关联）",
        ],
    },
    "病例对照": {
        "recommended": [
            "Odds Ratio计算",
            "条件Logistic回归",
            "卡方检验",
            "分层分析",
            "多因素Logistic回归",
        ],
        "required": [
            "匹配方式说明",
            "OR值及95%CI",
            "选择偏倚讨论",
        ],
        "inappropriate": [
            "相对危险度（RR）计算（病例对照研究应使用OR）",
        ],
    },
    "横断面": {
        "recommended": [
            "卡方检验",
            "t检验",
            "Logistic回归",
            "线性回归",
            "描述性统计",
            "多因素回归分析",
        ],
        "required": [
            "抽样方法描述",
            "应答率报告",
            "代表性讨论",
        ],
        "inappropriate": [
            "因果推断",
            "生存分析",
        ],
    },
    "病例系列": {
        "recommended": [
            "描述性统计",
            "频率/百分比",
            "中位数/四分位数",
        ],
        "required": [
            "病例定义标准",
            "连续入组时间",
        ],
        "inappropriate": [
            "统计推断（p值、置信区间不适用于无对照的病例系列）",
        ],
    },
    "病例报告": {
        "recommended": [
            "描述性报告",
        ],
        "required": [
            "详细病例描述",
            "文献复习",
        ],
        "inappropriate": [
            "统计推断",
        ],
    },
    "系统综述": {
        "recommended": [
            "PRISMA流程图",
            "GRADE证据分级",
            "NOS量表质量评价",
            "异质性检验（I²统计量）",
        ],
        "required": [
            "系统检索策略描述",
            "纳入排除标准",
            "质量评价",
        ],
        "inappropriate": [
            "原始数据统计分析",
        ],
    },
    "Meta分析": {
        "recommended": [
            "固定效应模型",
            "随机效应模型",
            "异质性检验（I², Q检验）",
            "发表偏倚检验（Egger's检验, 漏斗图）",
            "亚组分析",
            "敏感性分析",
            "GRADE证据分级",
        ],
        "required": [
            "效应量合并（OR, RR, MD, SMD等）",
            "95%置信区间",
            "异质性评估",
            "发表偏倚评估",
        ],
        "inappropriate": [
            "仅使用固定效应模型（不报告随机效应模型结果）",
        ],
    },
}


def review_statistics(
    method_description: str,
    study_type: str,
) -> list[dict]:
    """
    审查统计方法是否适合研究类型。

    Args:
        method_description: 论文中描述的统计方法文本
        study_type: 研究类型（RCT/队列研究/病例对照/横断面/病例系列/病例报告/系统综述/Meta分析）

    Returns:
        审查意见列表，每条包含 severity（info/warning/error）、message 字段

    Raises:
        ValueError: 研究类型不在支持列表中时
    """
    if study_type not in SUPPORTED_STUDY_TYPES:
        raise ValueError(
            f"不支持的研究类型: '{study_type}'。"
            f"支持的研究类型: {', '.join(SUPPORTED_STUDY_TYPES)}"
        )

    if not method_description or not method_description.strip():
        return [{
            "severity": "error",
            "message": "未找到统计方法描述，请补充统计方法部分",
        }]

    method_lower = method_description.lower()
    opinions: list[dict] = []
    config = _STUDY_TYPE_METHODS[study_type]

    # 1. 检查推荐方法是否被使用
    used_recommended = []
    missing_recommended = []
    for method in config["recommended"]:
        # 提取关键短语进行匹配
        keywords = _extract_keywords(method)
        if any(kw in method_lower for kw in keywords):
            used_recommended.append(method)
        else:
            missing_recommended.append(method)

    if used_recommended:
        opinions.append({
            "severity": "info",
            "message": f"已使用的推荐统计方法: {', '.join(used_recommended)}",
        })

    # 2. 检查必需项
    for required in config["required"]:
        keywords = _extract_keywords(required)
        if not any(kw in method_lower for kw in keywords):
            opinions.append({
                "severity": "warning",
                "message": f"建议补充: {required}",
            })

    # 3. 检查不适当的方法
    for inappropriate in config["inappropriate"]:
        keywords = _extract_keywords(inappropriate)
        if any(kw in method_lower for kw in keywords):
            opinions.append({
                "severity": "error",
                "message": f"对于{study_type}，不推荐使用: {inappropriate}",
            })

    # 4. 通用统计检查
    opinions.extend(_general_stat_checks(method_lower, study_type))

    # 5. 样本量检查
    opinions.extend(_check_sample_size(method_lower))

    # 如果没有任何意见，给出正面评价
    if not opinions:
        opinions.append({
            "severity": "info",
            "message": f"统计方法选择合理，适合{study_type}研究设计",
        })

    logger.info(
        f"统计方法审查完成: study_type='{study_type}', "
        f"生成 {len(opinions)} 条意见"
    )
    return opinions


def _extract_keywords(text: str) -> list[str]:
    """
    从中文统计方法名称中提取关键匹配词。

    Args:
        text: 统计方法名称

    Returns:
        关键词列表
    """
    # 常见统计学方法中英文关键词映射
    keyword_map = {
        "t检验": ["t检验", "t-test", "student's t"],
        "卡方检验": ["卡方", "chi-square", "chi2", "χ2"],
        "方差分析": ["方差分析", "anova"],
        "Logistic回归": ["logistic回归", "logistic regression", "logit"],
        "Cox回归": ["cox回归", "cox proportional", "cox模型"],
        "Kaplan-Meier": ["kaplan-meier", "kaplan meier", "km曲线", "生存曲线"],
        "意向性分析": ["意向性分析", "itt", "intention-to-treat"],
        "样本量": ["样本量", "样本大小", "sample size", "功效分析", "power analysis"],
        "随机化": ["随机", "random", "randomization"],
        "盲法": ["盲法", "blind", "双盲", "单盲", "double-blind", "single-blind"],
        "倾向性评分": ["倾向性评分", "propensity score", "psm"],
        "异质性": ["异质性", "heterogeneity", "i²", "i2", "q检验"],
        "发表偏倚": ["发表偏倚", "publication bias", "egger", "漏斗图", "funnel"],
        "GRADE": ["grade", "证据分级"],
        "PRISMA": ["prisma"],
        "NOS": ["nos量表", "newcastle"],
        "固定效应": ["固定效应", "fixed effect", "fixed-effect"],
        "随机效应": ["随机效应", "random effect", "random-effect"],
        "Meta": ["meta分析", "meta-analysis", "meta regression", "meta回归"],
        "系统综述": ["系统综述", "systematic review"],
    }

    matched = []
    for key, aliases in keyword_map.items():
        if key in text or any(alias in text.lower() for alias in aliases):
            matched.extend(aliases)

    # 如果没有映射到，直接返回原文中的分词结果
    if not matched:
        # 按标点或空格分割
        parts = re.split(r"[，,、()（）\[\]]+", text)
        matched = [p.strip().lower() for p in parts if len(p.strip()) >= 2]

    return matched


def _general_stat_checks(method_text: str, study_type: str) -> list[dict]:
    """
    通用统计方法检查。

    Args:
        method_text: 统计方法描述文本（小写）
        study_type: 研究类型

    Returns:
        检查意见列表
    """
    opinions: list[dict] = []

    # 检查是否提及显著性水平
    p_value_patterns = ["p<0.05", "p < 0.05", "p<0.01", "p < 0.01", "显著性水平", "alpha"]
    if not any(pv in method_text for pv in p_value_patterns):
        opinions.append({
            "severity": "info",
            "message": "建议明确说明显著性水平（如α=0.05）",
        })

    # 检查是否使用统计软件
    software_patterns = [
        "spss", "sas", "r语言", "r software", "stata", "python",
        "graphpad", "medcalc", "revman",
    ]
    if not any(sw in method_text for sw in software_patterns):
        opinions.append({
            "severity": "info",
            "message": "建议说明所使用的统计软件及版本号",
        })

    # 检查是否提及置信区间
    if "95%ci" not in method_text and "95% ci" not in method_text and "置信区间" not in method_text:
        if study_type not in ["病例报告", "病例系列"]:
            opinions.append({
                "severity": "info",
                "message": "建议在结果中报告95%置信区间",
            })

    return opinions


def _check_sample_size(method_text: str) -> list[dict]:
    """
    检查样本量相关描述。

    Args:
        method_text: 统计方法描述文本（小写）

    Returns:
        检查意见列表
    """
    opinions: list[dict] = []

    sample_patterns = [
        "样本量", "sample size", "n=", "n =", "例",
        "功效分析", "power analysis", "power calculation",
    ]

    has_sample_info = any(sp in method_text for sp in sample_patterns)

    if not has_sample_info:
        opinions.append({
            "severity": "warning",
            "message": "统计方法部分未提及样本量信息，建议补充样本量计算方法或至少报告纳入分析的样本数",
        })

    return opinions
