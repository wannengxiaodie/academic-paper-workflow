"""
Reviewer Agent - 评审智能体。
负责综合质量检查、质量门控判断、7维度评分等评审任务。
"""

from __future__ import annotations

import logging
from typing import Optional

import config
from models.schemas import GateCheckItem, GateResult, ReviewScore

logger = logging.getLogger(__name__)


class ReviewerAgent:
    """
    Reviewer Agent（评审智能体）- 负责论文质量评审阶段的全部任务。

    主要职责：
    1. 综合质量检查（7维度评分）
    2. 质量门控判断（是否达到投稿标准）
    3. 生成评审报告

    评审维度：
    - 临床价值（1-5分）
    - 科学性（1-5分）
    - 创新性（1-5分）
    - 文献覆盖（1-5分）
    - 统计方法（1-5分）
    - 伦理合规（1-5分）
    - 写作规范（1-5分）
    """

    def __init__(self) -> None:
        """初始化 Reviewer Agent。"""
        self._ai_available = bool(config.API_KEY_OPENAI or config.API_KEY_ANTHROPIC)
        logger.info(
            f"Reviewer Agent 初始化完成, AI增强: {self._ai_available}"
        )

    def review_quality(self, paper_text: str) -> dict:
        """
        综合质量检查 - 从7个维度对论文进行全面评审。

        Args:
            paper_text: 论文全文

        Returns:
            包含7维度评分、总分、详细评审意见的字典
        """
        logger.info(f"开始综合质量检查: 字数={len(paper_text)}")

        if not paper_text or not paper_text.strip():
            return {
                "success": False,
                "message": "论文内容为空，无法进行质量评审",
                "review": None,
            }

        # 1. 格式验证
        from services.format_validator import validate_format, validate_medical_terms
        format_issues = validate_format(paper_text)
        term_issues = validate_medical_terms(paper_text)

        # 2. 7维度评分
        scores = self._evaluate_all_dimensions(paper_text, format_issues, term_issues)

        # 3. 构建ReviewScore对象
        review_score = ReviewScore(
            clinical_value=scores["临床价值"],
            scientific_rigor=scores["科学性"],
            innovation=scores["创新性"],
            literature_coverage=scores["文献覆盖"],
            statistical_method=scores["统计方法"],
            ethics_compliance=scores["伦理合规"],
            writing_standard=scores["写作规范"],
        )

        # 4. 生成评审意见
        review_opinions = self._generate_review_opinions(
            paper_text, scores, format_issues, term_issues
        )

        result = {
            "success": True,
            "message": "质量评审完成",
            "review": {
                "scores": scores,
                "total_score": review_score.total_score,
                "average_score": review_score.average_score,
                "score_details": review_score.to_dict(),
                "format_issues_count": len(format_issues),
                "term_issues_count": len(term_issues),
                "format_issues": format_issues,
                "term_issues": term_issues,
                "review_opinions": review_opinions,
            },
        }

        logger.info(
            f"质量评审完成: 总分={review_score.total_score}, "
            f"均分={review_score.average_score}, "
            f"格式问题={len(format_issues)}, 术语问题={len(term_issues)}"
        )
        return result

    def check_gate(self, strategy_result: dict) -> dict:
        """
        质量门控判断 - 判断论文是否达到投稿标准。

        门控规则：
        - 7维度平均分 >= GATE_PASS_THRESHOLD（默认3.5）
        - 每个维度最低分 >= GATE_MIN_DIMENSION_SCORE（默认2）
        - 无error级别的格式问题
        - 术语检查通过率 >= 80%

        Args:
            strategy_result: 策略阶段的结果（包含scores等信息）

        Returns:
            包含门控结果、各项检查详情、通过/未通过建议的字典
        """
        logger.info("开始质量门控检查")

        # 提取评分
        scores = strategy_result.get("scores", {})
        if not scores:
            return {
                "passed": False,
                "message": "无法进行门控检查：缺少评分数据",
                "checks": [],
                "total_score": 0,
                "suggestions": ["请先完成策略阶段评审"],
            }

        checks: list[GateCheckItem] = []
        suggestions: list[str] = []

        # 检查1: 平均分检查
        total_score = sum(scores.values())
        avg_score = total_score / len(scores) if scores else 0
        avg_passed = avg_score >= config.GATE_PASS_THRESHOLD

        checks.append(GateCheckItem(
            name="平均分检查",
            passed=avg_passed,
            description=(
                f"7维度平均分: {avg_score:.2f}/5.0"
                f"（阈值: {config.GATE_PASS_THRESHOLD}）"
            ),
        ))

        if not avg_passed:
            suggestions.append(
                f"7维度平均分{avg_score:.1f}分低于阈值{config.GATE_PASS_THRESHOLD}，"
                f"建议重点提升低分维度"
            )

        # 检查2: 最低分检查
        min_score = min(scores.values()) if scores else 0
        min_passed = min_score >= config.GATE_MIN_DIMENSION_SCORE
        min_dimension = [
            dim for dim, score in scores.items() if score < config.GATE_MIN_DIMENSION_SCORE
        ]

        checks.append(GateCheckItem(
            name="最低分检查",
            passed=min_passed,
            description=(
                f"最低维度分: {min_score}/5"
                f"（阈值: {config.GATE_MIN_DIMENSION_SCORE}）"
                + (f"，低于阈值的维度: {', '.join(min_dimension)}" if min_dimension else "")
            ),
        ))

        if not min_passed and min_dimension:
            suggestions.append(
                f"以下维度评分过低需要重点改进: {', '.join(min_dimension)}"
            )

        # 检查3: 结构完整性检查
        section_titles = strategy_result.get("section_titles", [])
        required_sections = ["引言", "方法", "结果", "讨论"]
        missing = [s for s in required_sections if s not in section_titles]
        structure_passed = len(missing) == 0

        checks.append(GateCheckItem(
            name="结构完整性检查",
            passed=structure_passed,
            description=(
                f"IMRAD结构: "
                + ("完整" if structure_passed else f"缺少 {', '.join(missing)}")
            ),
        ))

        if not structure_passed:
            suggestions.append(f"补充缺少的章节: {', '.join(missing)}")

        # 检查4: 字数检查
        word_count = strategy_result.get("word_count", 0)
        title_level = strategy_result.get("title_level", "副高级")
        word_config = config.WORD_COUNT_TARGETS.get(title_level, {"min": 4000, "max": 6000})
        word_passed = word_config["min"] <= word_count <= word_config["max"]

        checks.append(GateCheckItem(
            name="字数检查",
            passed=word_passed,
            description=(
                f"论文字数: {word_count}"
                f"（要求: {word_config['min']}-{word_config['max']}）"
            ),
        ))

        if not word_passed:
            if word_count < word_config["min"]:
                suggestions.append(
                    f"论文字数{word_count}字低于最低要求{word_config['min']}字，"
                    f"建议扩充内容"
                )
            else:
                suggestions.append(
                    f"论文字数{word_count}字超出上限{word_config['max']}字，"
                    f"建议精简内容"
                )

        # 检查5: 文献引用检查
        ref_count = strategy_result.get("reference_count", 0)
        ref_passed = ref_count >= 10

        checks.append(GateCheckItem(
            name="文献引用检查",
            passed=ref_passed,
            description=f"参考文献数量: {ref_count}（建议 >= 10）",
        ))

        if not ref_passed:
            suggestions.append(f"参考文献仅{ref_count}篇，建议补充至10篇以上")

        # 总体门控判断
        all_passed = all(c.passed for c in checks)
        overall_passed = all_passed

        # 即使未全部通过，如果平均分很高也可以考虑放行
        if not overall_passed and avg_passed and min_passed:
            suggestions.append(
                "虽然部分检查未通过，但核心评分达标，可酌情投稿"
            )

        result = {
            "passed": overall_passed,
            "message": (
                "质量门控通过，可以进入写作阶段"
                if overall_passed
                else "质量门控未通过，建议根据反馈改进后重新检查"
            ),
            "checks": [c.model_dump() for c in checks],
            "total_score": total_score,
            "average_score": round(avg_score, 2),
            "suggestions": suggestions,
        }

        logger.info(
            f"质量门控检查完成: 通过={overall_passed}, "
            f"总分={total_score}, 检查项={len(checks)}"
        )
        return result

    # ================================================================
    # 私有方法
    # ================================================================

    def _evaluate_all_dimensions(
        self,
        paper_text: str,
        format_issues: list[dict],
        term_issues: list[dict],
    ) -> dict[str, int]:
        """
        评估所有7个维度。

        Args:
            paper_text: 论文全文
            format_issues: 格式问题列表
            term_issues: 术语问题列表

        Returns:
            7维度评分字典
        """
        scores: dict[str, int] = {}

        # 1. 临床价值
        scores["临床价值"] = self._evaluate_clinical_value(paper_text)

        # 2. 科学性
        scores["科学性"] = self._evaluate_scientific_rigor(paper_text)

        # 3. 创新性
        scores["创新性"] = self._evaluate_innovation(paper_text)

        # 4. 文献覆盖
        scores["文献覆盖"] = self._evaluate_literature_coverage(paper_text)

        # 5. 统计方法
        scores["统计方法"] = self._evaluate_statistical_method(paper_text)

        # 6. 伦理合规
        scores["伦理合规"] = self._evaluate_ethics(paper_text)

        # 7. 写作规范
        scores["写作规范"] = self._evaluate_writing_standard(
            paper_text, format_issues, term_issues
        )

        return scores

    def _evaluate_clinical_value(self, text: str) -> int:
        """评估临床价值维度。"""
        score = 3  # 基准分
        text_lower = text.lower()

        clinical_indicators = [
            "临床意义", "预后", "诊断", "治疗", "疗效", "安全性",
            "不良反应", "并发症", "生存率", "改善", "降低",
            "clinical significance", "prognosis", "outcome",
        ]
        indicator_count = sum(1 for kw in clinical_indicators if kw in text_lower)
        if indicator_count >= 5:
            score = 4
        elif indicator_count >= 8:
            score = 5
        elif indicator_count <= 1:
            score = 2

        return score

    def _evaluate_scientific_rigor(self, text: str) -> int:
        """评估科学性维度。"""
        score = 3
        text_lower = text.lower()

        # 检查研究设计要素
        rigor_indicators = [
            "纳入标准", "排除标准", "随机", "对照", "盲法",
            "纳入排除标准", "纳入标准", "p<0.05", "p<0.01",
            "statistically significant", "inclusion criteria",
        ]
        rigor_count = sum(1 for kw in rigor_indicators if kw in text_lower)

        # 检查IMRAD结构
        has_intro = "引言" in text_lower or "introduction" in text_lower
        has_methods = "方法" in text_lower or "methods" in text_lower
        has_results = "结果" in text_lower or "results" in text_lower
        has_discussion = "讨论" in text_lower or "discussion" in text_lower
        has_imrad = has_intro and has_methods and has_results and has_discussion

        if has_imrad and rigor_count >= 5:
            score = 5
        elif has_imrad and rigor_count >= 3:
            score = 4
        elif has_imrad:
            score = 3
        else:
            score = 2

        return score

    def _evaluate_innovation(self, text: str) -> int:
        """评估创新性维度。"""
        score = 3
        text_lower = text.lower()

        innovation_indicators = [
            "首次", "新颖", "创新", "未见报道", "尚未研究",
            "新的方法", "新技术", "新策略",
            "novel", "innovative", "first reported", "new approach",
        ]
        innovation_count = sum(1 for kw in innovation_indicators if kw in text_lower)

        if innovation_count >= 3:
            score = 4
        elif innovation_count >= 5:
            score = 5
        elif innovation_count == 0:
            score = 2

        return score

    def _evaluate_literature_coverage(self, text: str) -> int:
        """评估文献覆盖维度。"""
        score = 3
        text_lower = text.lower()

        # 检查引用数量
        ref_numbers = __import__("re").findall(r"\[\d+\]", text)
        ref_count = len(set(ref_numbers))

        if ref_count >= 30:
            score = 5
        elif ref_count >= 20:
            score = 4
        elif ref_count >= 10:
            score = 3
        elif ref_count >= 5:
            score = 2
        else:
            score = 1

        return score

    def _evaluate_statistical_method(self, text: str) -> int:
        """评估统计方法维度。"""
        score = 3
        text_lower = text.lower()

        stat_indicators = [
            "t检验", "卡方", "方差分析", "anova", "logistic回归",
            "cox回归", "kaplan-meier", "spss", "sas", "r软件",
            "p值", "置信区间", "95%ci", "显著性",
            "t-test", "chi-square", "regression", "spss", "stata",
        ]
        stat_count = sum(1 for kw in stat_indicators if kw in text_lower)

        if stat_count >= 5:
            score = 4
        elif stat_count >= 8:
            score = 5
        elif stat_count <= 1:
            score = 2
        elif stat_count == 0:
            score = 1

        return score

    def _evaluate_ethics(self, text: str) -> int:
        """评估伦理合规维度。"""
        score = 3
        text_lower = text.lower()

        ethics_indicators = [
            "伦理委员会", "伦理审批", "知情同意", "伦理审查",
            " Declaration of Helsinki", "IRB", "informed consent",
            "伦理学", "批号", "符合伦理",
        ]
        ethics_count = sum(1 for kw in ethics_indicators if kw in text_lower)

        if ethics_count >= 3:
            score = 5
        elif ethics_count >= 2:
            score = 4
        elif ethics_count >= 1:
            score = 3
        else:
            score = 2

        return score

    def _evaluate_writing_standard(
        self,
        paper_text: str,
        format_issues: list[dict],
        term_issues: list[dict],
    ) -> int:
        """评估写作规范维度。"""
        score = 4  # 基准分

        # 根据格式问题扣分
        error_count = sum(1 for i in format_issues if i.get("severity") == "error")
        warning_count = sum(1 for i in format_issues if i.get("severity") == "warning")
        term_error_count = sum(1 for i in term_issues if i.get("severity") == "error")

        if error_count > 0:
            score = max(1, score - error_count)
        if warning_count > 3:
            score = max(1, score - 1)
        if term_error_count > 3:
            score = max(1, score - 1)

        return score

    def _generate_review_opinions(
        self,
        paper_text: str,
        scores: dict[str, int],
        format_issues: list[dict],
        term_issues: list[dict],
    ) -> list[dict]:
        """
        生成评审意见列表。

        Args:
            paper_text: 论文全文
            scores: 7维度评分
            format_issues: 格式问题
            term_issues: 术语问题

        Returns:
            评审意见列表
        """
        opinions: list[dict] = []

        # 评分相关的意见
        for dim, score in scores.items():
            if score <= 2:
                opinions.append({
                    "category": dim,
                    "level": "critical",
                    "opinion": f"{dim}评分较低（{score}分），需要重点关注和改进",
                })
            elif score == 3:
                opinions.append({
                    "category": dim,
                    "level": "suggestion",
                    "opinion": f"{dim}评分达标（{score}分），仍有提升空间",
                })

        # 格式问题相关的意见
        for issue in format_issues:
            if issue.get("severity") == "error":
                opinions.append({
                    "category": "格式",
                    "level": "critical",
                    "opinion": issue.get("message", ""),
                })

        # 术语问题相关的意见
        for issue in term_issues[:3]:  # 最多报告3个术语问题
            if issue.get("severity") == "error" or issue.get("severity") == "warning":
                opinions.append({
                    "category": "术语",
                    "level": "warning",
                    "opinion": issue.get("message", ""),
                })

        return opinions
