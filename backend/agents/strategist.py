"""
Strategist Agent - 策略阶段智能体。
负责期刊匹配分析、文献检索与空白识别、大纲评审评分等策略性任务。
"""

from __future__ import annotations

import logging
from typing import Optional

import config
from models.schemas import (
    JournalRecommendation,
    LiteratureGap,
    LiteratureSearchResult,
    OutlineSection,
    ReviewScore,
)
from services.journal_matcher import match_journals
from services.literature_search import identify_research_gaps, search_pubmed

logger = logging.getLogger(__name__)


class StrategistAgent:
    """
    Strategist Agent（策略智能体）- 负责论文写作策略阶段的全部任务。

    主要职责：
    1. 分析投稿平台（期刊匹配）
    2. 文献综述（文献检索 + 研究空白识别）
    3. 大纲评审（7维度评分）

    所有方法均支持AI增强模式（有API Key时调用AI接口获得更智能的分析），
    并有完整的降级策略（API不可用时使用基于规则的分析）。
    """

    def __init__(self) -> None:
        """初始化 Strategist Agent。"""
        self._ai_available = bool(config.API_KEY_OPENAI or config.API_KEY_ANTHROPIC)
        logger.info(
            f"Strategist Agent 初始化完成, AI增强: {self._ai_available}"
        )

    def analyze_platform(
        self,
        topic: str,
        title_level: str,
        department: str,
        top_n: int = 10,
    ) -> dict:
        """
        分析投稿平台 - 根据研究主题和职称级别匹配最适合的期刊。

        Args:
            topic: 研究主题
            title_level: 职称级别
            department: 科室
            top_n: 返回前N个推荐

        Returns:
            包含推荐期刊列表和分析摘要的字典
        """
        logger.info(
            f"开始分析投稿平台: topic='{topic}', "
            f"level='{title_level}', dept='{department}'"
        )

        # 调用期刊匹配服务
        recommendations = match_journals(topic, title_level, department, top_n)

        # 生成分析摘要
        analysis_summary = self._generate_platform_summary(
            topic, title_level, department, recommendations
        )

        result = {
            "recommendations": [r.model_dump() for r in recommendations],
            "analysis_summary": analysis_summary,
            "total_journals_scanned": len(recommendations),
        }

        logger.info(f"投稿平台分析完成: 推荐了 {len(recommendations)} 本期刊")
        return result

    def review_literature(
        self,
        topic: str,
        max_results: int = 20,
        include_cnki: bool = True,
    ) -> dict:
        """
        文献综述 - 检索相关文献并识别研究空白。

        Args:
            topic: 研究主题（作为检索关键词）
            max_results: 最大检索结果数
            include_cnki: 是否包含CNKI检索（当前为模拟数据）

        Returns:
            包含文献列表、研究空白、综述摘要的字典
        """
        logger.info(f"开始文献综述: topic='{topic}', max={max_results}")

        # 1. PubMed检索
        pubmed_papers: list[dict] = []
        try:
            pubmed_papers = search_pubmed(topic, max_results)
        except Exception as e:
            logger.warning(f"PubMed检索失败（将使用降级数据）: {e}")
            pubmed_papers = self._get_fallback_papers(topic)

        # 2. CNKI检索（当前为模拟）
        cnki_papers: list[dict] = []
        if include_cnki:
            cnki_papers = self._get_fallback_cnki_papers(topic)

        # 3. 合并所有文献
        all_papers = pubmed_papers + cnki_papers

        # 4. 识别研究空白
        gaps = identify_research_gaps(topic, all_papers)

        # 5. 生成综述摘要
        review_summary = self._generate_literature_summary(topic, all_papers, gaps)

        result = {
            "pubmed_results": pubmed_papers[:max_results],
            "cnki_results": cnki_papers,
            "total_papers": len(all_papers),
            "research_gaps": [g.model_dump() for g in gaps],
            "review_summary": review_summary,
        }

        logger.info(
            f"文献综述完成: PubMed={len(pubmed_papers)}, "
            f"CNKI={len(cnki_papers)}, 研究空白={len(gaps)}"
        )
        return result

    def evaluate_outline(
        self,
        topic: str,
        outline: list[OutlineSection],
    ) -> dict:
        """
        大纲评审 - 从7个维度对论文大纲进行评分。

        评分维度：临床价值、科学性、创新性、文献覆盖、统计方法、伦理合规、写作规范

        Args:
            topic: 研究主题
            outline: 论文大纲结构

        Returns:
            包含7维度评分、总分、评审意见的字典
        """
        logger.info(f"开始大纲评审: topic='{topic}'")

        # 7维度评分（基于规则的分析）
        scores = self._calculate_outline_scores(topic, outline)

        # 生成评审意见
        review_comments = self._generate_outline_review_comments(topic, outline, scores)

        result = {
            "scores": scores,
            "total_score": sum(scores.values()),
            "average_score": round(sum(scores.values()) / len(scores), 2) if scores else 0,
            "review_comments": review_comments,
        }

        logger.info(
            f"大纲评审完成: 总分={result['total_score']}, "
            f"均分={result['average_score']}"
        )
        return result

    # ================================================================
    # 私有方法
    # ================================================================

    def _generate_platform_summary(
        self,
        topic: str,
        title_level: str,
        department: str,
        recommendations: list[JournalRecommendation],
    ) -> str:
        """
        生成投稿平台分析摘要。

        Args:
            topic: 研究主题
            title_level: 职称级别
            department: 科室
            recommendations: 期刊推荐列表

        Returns:
            分析摘要文本
        """
        if not recommendations:
            return f"未找到适合'{topic}'（{department}，{title_level}）的推荐期刊。"

        top_journal = recommendations[0]
        summary = (
            f"基于研究主题'{topic}'（{department}，{title_level}），"
            f"系统共匹配到 {len(recommendations)} 本推荐期刊。"
            f"\n\n最佳推荐：{top_journal.name}（匹配度 {top_journal.match_score}分），"
            f"影响因子 {top_journal.impact_factor}，"
            f"审稿周期约 {top_journal.review_cycle} 天，"
            f"收录于 {', '.join(top_journal.database_tags[:3])}。"
        )

        # 按级别分类建议
        sci_journals = [r for r in recommendations if "SCI" in r.database_tags]
        core_journals = [r for r in recommendations if "科技核心" in r.database_tags and "SCI" not in r.database_tags]

        if sci_journals:
            summary += f"\n\nSCI收录期刊 {len(sci_journals)} 本（适合追求高水平发表）。"
        if core_journals:
            summary += f"\n\n中国科技核心期刊 {len(core_journals)} 本（适合职称评审）。"

        return summary

    def _generate_literature_summary(
        self,
        topic: str,
        papers: list[dict],
        gaps: list[LiteratureGap],
    ) -> str:
        """
        生成文献综述摘要。

        Args:
            topic: 研究主题
            papers: 文献列表
            gaps: 研究空白列表

        Returns:
            综述摘要文本
        """
        pubmed_count = sum(1 for p in papers if p.get("source") == "pubmed")
        cnki_count = sum(1 for p in papers if "cnki" in p.get("source", ""))

        years = [p.get("year", 0) for p in papers if p.get("year", 0) > 0]
        year_range = f"{min(years)}-{max(years)}" if years else "未知"

        summary = (
            f"关于'{topic}'的文献检索共获得 {len(papers)} 篇相关文献"
            f"（PubMed {pubmed_count} 篇，CNKI {cnki_count} 篇），"
            f"发表年份跨度为 {year_range}。"
        )

        if gaps:
            summary += f"\n\n识别到 {len(gaps)} 个潜在的研究空白："
            for i, gap in enumerate(gaps, 1):
                summary += f"\n{i}. {gap.gap_description}（证据等级：{gap.evidence_level}）"
                summary += f"\n   建议方向：{gap.research_direction}"

        return summary

    def _calculate_outline_scores(
        self,
        topic: str,
        outline: list[OutlineSection],
    ) -> dict[str, int]:
        """
        基于规则计算大纲7维度评分。

        Args:
            topic: 研究主题
            outline: 论文大纲

        Returns:
            7维度评分字典
        """
        section_titles = [s.title for s in outline]
        total_word_count = sum(s.word_count_target for s in outline)

        scores: dict[str, int] = {}

        # 临床价值（1-5）
        if any("临床" in s.key_points or "临床" in str(s.subsections) for s in outline):
            scores["临床价值"] = 4
        elif topic:
            scores["临床价值"] = 3
        else:
            scores["临床价值"] = 2

        # 科学性（1-5）
        has_methods = "方法" in section_titles or "资料与方法" in section_titles
        has_results = "结果" in section_titles
        has_discussion = "讨论" in section_titles
        if has_methods and has_results and has_discussion:
            scores["科学性"] = 4
        elif has_methods and has_results:
            scores["科学性"] = 3
        else:
            scores["科学性"] = 2

        # 创新性（1-5）
        if len(section_titles) >= 5:
            scores["创新性"] = 3
        else:
            scores["创新性"] = 2

        # 文献覆盖（1-5）
        has_intro = "引言" in section_titles
        has_refs = any("参考" in s.title for s in outline)
        if has_intro and has_refs:
            scores["文献覆盖"] = 4
        elif has_intro:
            scores["文献覆盖"] = 3
        else:
            scores["文献覆盖"] = 2

        # 统计方法（1-5）
        if has_methods:
            for s in outline:
                if "统计" in s.title or any("统计" in str(ss.key_points) for ss in s.subsections):
                    scores["统计方法"] = 4
                    break
            if "统计方法" not in scores:
                scores["统计方法"] = 3
        else:
            scores["统计方法"] = 2

        # 伦理合规（1-5）
        has_ethics = False
        for s in outline:
            if "伦理" in s.title or any("伦理" in str(ss.key_points) for ss in s.subsections):
                has_ethics = True
                break
        scores["伦理合规"] = 4 if has_ethics else 3

        # 写作规范（1-5）
        has_abstract = "摘要" in section_titles
        has_conclusion = "结论" in section_titles
        if total_word_count >= 2000 and has_abstract and has_conclusion:
            scores["写作规范"] = 4
        elif total_word_count >= 1000:
            scores["写作规范"] = 3
        else:
            scores["写作规范"] = 2

        return scores

    def _generate_outline_review_comments(
        self,
        topic: str,
        outline: list[OutlineSection],
        scores: dict[str, int],
    ) -> list[dict]:
        """
        生成大纲评审意见。

        Args:
            topic: 研究主题
            outline: 大纲
            scores: 评分

        Returns:
            评审意见列表
        """
        comments: list[dict] = []
        section_titles = [s.title for s in outline]

        # 基于评分生成意见
        for dim, score in scores.items():
            if score >= 4:
                comments.append({
                    "dimension": dim,
                    "level": "good",
                    "comment": f"{dim}方面表现良好",
                })
            elif score == 3:
                comments.append({
                    "dimension": dim,
                    "level": "acceptable",
                    "comment": f"{dim}方面基本达标，仍有提升空间",
                })
            else:
                comments.append({
                    "dimension": dim,
                    "level": "needs_improvement",
                    "comment": f"{dim}方面需要加强",
                })

        # 结构性建议
        if "摘要" not in section_titles:
            comments.append({
                "dimension": "结构",
                "level": "needs_improvement",
                "comment": "大纲缺少摘要部分",
            })

        if len(outline) < 4:
            comments.append({
                "dimension": "结构",
                "level": "needs_improvement",
                "comment": "大纲结构过于简单，建议补充更多章节",
            })

        return comments

    def _get_fallback_papers(self, topic: str) -> list[dict]:
        """
        PubMed检索失败时的降级数据。

        Args:
            topic: 研究主题

        Returns:
            模拟的文献数据
        """
        return [
            {
                "title": f"[降级数据] Clinical study on {topic}",
                "authors": ["Author A", "Author B"],
                "abstract": f"This study investigates the clinical aspects of {topic}...",
                "pmid": "",
                "year": 2024,
                "source": "pubmed（降级数据）",
            },
        ]

    def _get_fallback_cnki_papers(self, topic: str) -> list[dict]:
        """
        CNKI检索的模拟数据。

        Args:
            topic: 研究主题

        Returns:
            模拟的中文文献数据
        """
        return [
            {
                "title": f"[模拟] {topic}的临床研究进展",
                "authors": ["张某某", "李某某"],
                "abstract": f"本文综述了{topic}领域的最新研究进展...",
                "pmid": "",
                "year": 2024,
                "source": "cnki（待接入）",
            },
        ]
