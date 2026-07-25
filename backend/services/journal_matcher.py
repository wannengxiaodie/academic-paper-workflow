"""
期刊匹配服务 - 根据研究主题、职称级别、科室匹配最适合投稿的医学期刊。
"""

from __future__ import annotations

import logging
from typing import Optional

from data.journals_db import JournalInfo, get_all_journals
from models.schemas import JournalRecommendation

logger = logging.getLogger(__name__)


def _calculate_match_score(
    journal: JournalInfo,
    topic: str,
    title_level: str,
    department: str,
) -> float:
    """
    计算期刊与需求的综合匹配度评分。

    评分算法：
    - 科室匹配（40%权重）：科室是否在期刊的适合科室列表中
    - 级别匹配（30%权重）：职称级别是否在期刊的适合级别列表中
    - 关键词匹配（20%权重）：主题关键词与期刊关键词的重叠度
    - 期刊质量（10%权重）：影响因子归一化评分

    Args:
        journal: 期刊信息
        topic: 研究主题
        title_level: 职称级别
        department: 科室

    Returns:
        匹配度评分（0-100）
    """
    score: float = 0.0
    topic_lower = topic.lower()

    # 1. 科室匹配（40分）
    if department in journal.departments:
        # 科室完全匹配
        dept_score = 40.0
        # 如果科室是期刊的主打科室（排在第一），额外加分
        if journal.departments[0] == department:
            dept_score = 45.0
    else:
        # 科室不匹配，但检查主题关键词是否与期刊相关
        dept_overlap = 0
        for kw in journal.keywords:
            if kw.lower() in topic_lower:
                dept_overlap += 1
        dept_score = min(20.0, dept_overlap * 5.0)

    # 2. 级别匹配（30分）
    if title_level in journal.suitable_levels:
        level_score = 30.0
    else:
        # 级别不匹配，根据差距扣分
        level_order = ["初级", "中级", "副高级", "正高级"]
        try:
            journal_levels = [level_order.index(l) for l in journal.suitable_levels if l in level_order]
            user_level = level_order.index(title_level) if title_level in level_order else 2
            if journal_levels:
                min_distance = min(abs(l - user_level) for l in journal_levels)
                level_score = max(0, 30.0 - min_distance * 10.0)
            else:
                level_score = 10.0
        except (ValueError, IndexError):
            level_score = 10.0

    # 3. 关键词匹配（20分）
    topic_keywords = set(topic_lower.split())
    journal_keywords = set(kw.lower() for kw in journal.keywords)
    # 扩展主题关键词（按常见医学词汇拆分）
    expanded_topic = set()
    for char in ["病", "炎", "瘤", "癌", "症", "术", "治疗", "研究", "分析", "临床"]:
        if char in topic:
            expanded_topic.add(char)
    topic_keywords.update(expanded_topic)

    if journal_keywords and topic_keywords:
        overlap = len(journal_keywords & topic_keywords)
        keyword_score = min(20.0, overlap / max(len(journal_keywords), 1) * 20.0)
    else:
        keyword_score = 5.0

    # 4. 期刊质量（10分）
    if journal.impact_factor > 5.0:
        quality_score = 10.0
    elif journal.impact_factor > 2.0:
        quality_score = 8.0
    elif journal.impact_factor > 1.0:
        quality_score = 6.0
    else:
        quality_score = 4.0

    score = dept_score + level_score + keyword_score + quality_score
    return round(min(100.0, score), 1)


def match_journals(
    topic: str,
    title_level: str,
    department: str,
    top_n: int = 10,
) -> list[JournalRecommendation]:
    """
    根据研究主题、职称级别、科室匹配推荐期刊。

    Args:
        topic: 研究主题/论文题目关键词
        title_level: 目标职称级别（初级/中级/副高级/正高级）
        department: 所属科室
        top_n: 返回前N个推荐结果，默认10

    Returns:
        按匹配度降序排列的期刊推荐列表

    Raises:
        ValueError: 当输入参数不合法时
    """
    # 参数校验
    if not topic or not topic.strip():
        raise ValueError("研究主题不能为空")
    if not title_level:
        raise ValueError("职称级别不能为空")
    if not department:
        raise ValueError("科室不能为空")

    topic = topic.strip()
    title_level = title_level.strip()
    department = department.strip()

    all_journals = get_all_journals()
    scored_journals: list[tuple[float, JournalInfo]] = []

    for journal in all_journals:
        match_score = _calculate_match_score(journal, topic, title_level, department)
        if match_score > 0:
            scored_journals.append((match_score, journal))

    # 按匹配度降序排序
    scored_journals.sort(key=lambda x: x[0], reverse=True)

    # 取前N个结果
    results: list[JournalRecommendation] = []
    for score, journal in scored_journals[:top_n]:
        recommendation = JournalRecommendation(
            name=journal.name,
            issn=journal.issn,
            impact_factor=journal.impact_factor,
            review_cycle=journal.review_cycle_days,
            publication_fee=journal.publication_fee_yuan,
            database_tags=journal.database_tags,
            match_score=score,
        )
        results.append(recommendation)

    logger.info(
        f"期刊匹配完成: topic='{topic}', department='{department}', "
        f"level='{title_level}', 匹配到 {len(results)} 本期刊"
    )
    return results
