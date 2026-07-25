"""
查重检测服务 - 对论文进行查重检测。
当前版本使用本地文本比对算法进行模拟检测，支持后续接入专业查重API。
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def check_plagiarism(
    paper_text: str,
    reference_texts: list[dict] | None = None,
) -> dict:
    """
    对论文进行查重检测。

    当前版本使用基于N-gram的文本相似度算法进行本地检测。
    后续可接入知网查重、PaperPass等专业查重API。

    Args:
        paper_text: 待检测论文全文
        reference_texts: 参考文献文本列表（可选），每条包含 title 和 content 字段

    Returns:
        查重结果字典，包含：
        - similarity_rate: 总体相似率（0-100）
        - matched_sources: 匹配来源列表
        - total_words: 检测总字数
        - note: 说明信息（如使用模拟检测）
    """
    if not paper_text or not paper_text.strip():
        return {
            "similarity_rate": 0.0,
            "matched_sources": [],
            "total_words": 0,
            "note": "论文内容为空，无法进行查重检测",
        }

    total_words = len(paper_text.replace(" ", "").replace("\n", ""))
    matched_sources: list[dict] = []

    if reference_texts:
        # 如果有参考文献文本，进行逐篇比对
        for ref in reference_texts:
            ref_content = ref.get("content", "")
            ref_title = ref.get("title", "未知来源")
            if not ref_content:
                continue

            similarity = _calculate_text_similarity(paper_text, ref_content)

            if similarity > 5.0:  # 只报告相似度超过5%的来源
                # 找到相似片段
                similar_segments = _find_similar_segments(
                    paper_text, ref_content, threshold=0.7
                )
                matched_sources.append({
                    "source_title": ref_title,
                    "matched_text": similar_segments[:3] if similar_segments else [],
                    "similarity_percent": round(similarity, 1),
                })
    else:
        # 无参考文献时，进行自重复率检测和常见医学短语检测
        matched_sources = _check_common_phrases(paper_text)

    # 计算总体相似率
    if matched_sources:
        similarity_rate = min(
            100.0,
            max(source["similarity_percent"] for source in matched_sources)
        )
    else:
        similarity_rate = 0.0

    result = {
        "similarity_rate": round(similarity_rate, 1),
        "matched_sources": matched_sources,
        "total_words": total_words,
        "note": "本地模拟检测。正式使用建议接入专业查重系统（如知网查重、PaperPass等）以获得更准确的结果。",
    }

    logger.info(
        f"查重检测完成: 总字数={total_words}, "
        f"相似率={similarity_rate}%, 匹配来源数={len(matched_sources)}"
    )
    return result


def _calculate_text_similarity(text1: str, text2: str, n: int = 3) -> float:
    """
    使用N-gram方法计算两段文本的相似度。

    Args:
        text1: 文本1
        text2: 文本2
        n: N-gram的N值，默认3

    Returns:
        相似度百分比（0-100）
    """
    def get_ngrams(text: str) -> set:
        """获取文本的N-gram集合"""
        # 清理文本
        cleaned = re.sub(r"\s+", "", text.lower())
        cleaned = re.sub(r"[^\w\u4e00-\u9fff]", "", cleaned)
        if len(cleaned) < n:
            return set()
        return set(cleaned[i:i+n] for i in range(len(cleaned) - n + 1))

    ngrams1 = get_ngrams(text1)
    ngrams2 = get_ngrams(text2)

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = ngrams1 & ngrams2
    union = ngrams1 | ngrams2

    # Jaccard相似度
    jaccard = len(intersection) / len(union) if union else 0.0

    return round(jaccard * 100, 2)


def _find_similar_segments(
    text: str,
    ref_text: str,
    threshold: float = 0.7,
    min_length: int = 20,
) -> list[str]:
    """
    在两段文本中找出相似度超过阈值的片段。

    Args:
        text: 论文文本
        ref_text: 参考文本
        threshold: 相似度阈值
        min_length: 最小片段长度

    Returns:
        相似片段列表
    """
    segments: list[str] = []
    text_clean = re.sub(r"\s+", "", text)
    ref_clean = re.sub(r"\s+", "", ref_text)

    # 简化的滑动窗口比对
    window_size = min_length
    step = min_length // 2

    for i in range(0, max(0, len(text_clean) - window_size), step):
        window = text_clean[i:i + window_size]
        if len(window) < min_length:
            continue

        if window in ref_clean:
            # 精确匹配
            segments.append(window[:50] + "..." if len(window) > 50 else window)
            if len(segments) >= 5:  # 最多返回5个片段
                break

    return segments


def _check_common_phrases(paper_text: str) -> list[dict]:
    """
    检查论文中是否包含常见的医学论文模板化表达。

    Args:
        paper_text: 论文全文

    Returns:
        匹配来源列表（基于常见模板短语）
    """
    # 常见的医学论文模板化表达
    template_phrases = [
        "目的：探讨",
        "方法：回顾性分析",
        "方法：前瞻性研究",
        "结果：共纳入",
        "结论：",
        "本研究存在以下局限性",
        "差异无统计学意义（P>0.05）",
        "差异有统计学意义（P<0.05）",
        "综上所述",
        "为临床治疗提供参考",
        "具有临床指导意义",
        "有待进一步研究",
    ]

    matched_count = 0
    for phrase in template_phrases:
        if phrase in paper_text:
            matched_count += 1

    # 模板化表达比例
    total_chars = len(paper_text.replace(" ", "").replace("\n", ""))
    template_rate = (matched_count / max(len(template_phrases), 1)) * 100

    if matched_count > 0:
        return [{
            "source_title": "常见医学论文模板表达",
            "matched_text": template_phrases,
            "similarity_percent": round(template_rate * 0.3, 1),  # 加权计算
        }]

    return []
