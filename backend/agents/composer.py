"""
Composer Agent - 写作阶段智能体。
负责论文模板生成、章节内容写作、论文润色等写作阶段任务。
支持接入AI API进行智能内容生成，有完整的降级策略。
"""

from __future__ import annotations

import logging
import time

import config
from models.schemas import OutlineSection, WritingChapter
from services.outline_generator import generate_outline
from services.format_validator import validate_format, validate_medical_terms

logger = logging.getLogger(__name__)


class ComposerAgent:
    """
    Composer Agent（写作智能体）- 负责论文写作阶段的全部任务。

    主要职责：
    1. 生成论文模板/大纲
    2. 逐章节写作
    3. 全文润色

    写作能力：
    - 有AI API Key时：调用大模型生成高质量医学论文内容
    - 无AI API时：基于模板和规则生成框架性内容（降级策略）
    """

    def __init__(self) -> None:
        """初始化 Composer Agent。"""
        self._ai_available = bool(config.API_KEY_OPENAI or config.API_KEY_ANTHROPIC)
        self._chapters_cache: list[WritingChapter] = []
        logger.info(
            f"Composer Agent 初始化完成, AI增强: {self._ai_available}"
        )

    def generate_template(
        self,
        journal_name: str,
        topic: str,
        study_type: str = "RCT",
        title_level: str = "副高级",
    ) -> dict:
        """
        生成论文模板 - 基于目标期刊和研究类型生成完整的论文大纲。

        Args:
            journal_name: 目标期刊名称
            topic: 研究主题
            study_type: 研究类型
            title_level: 职称级别

        Returns:
            包含大纲结构和模板说明的字典
        """
        logger.info(
            f"开始生成模板: journal='{journal_name}', "
            f"topic='{topic}', type='{study_type}'"
        )

        # 调用大纲生成服务
        outline = generate_outline(topic, journal_name, study_type, title_level)

        # 初始化章节缓存
        self._chapters_cache = [
            WritingChapter(
                chapter_key=f"section_{i}",
                title=section.title,
                content="",
                word_count=0,
                term_check_passed=False,
                format_check_passed=False,
            )
            for i, section in enumerate(outline)
        ]

        # 计算总字数目标
        total_words = sum(s.word_count_target for s in outline)

        # 生成模板说明
        template_notes = self._generate_template_notes(
            journal_name, topic, study_type, outline
        )

        result = {
            "journal": journal_name,
            "topic": topic,
            "study_type": study_type,
            "outline": [s.model_dump() for s in outline],
            "total_word_target": total_words,
            "template_notes": template_notes,
            "chapter_keys": [f"section_{i}" for i in range(len(outline))],
        }

        logger.info(
            f"模板生成完成: {len(outline)} 个章节, "
            f"总字数目标={total_words}"
        )
        return result

    def write_chapter(
        self,
        chapter_key: str,
        outline: list[OutlineSection],
        context: str = "",
        topic: str = "",
        study_type: str = "RCT",
    ) -> dict:
        """
        写作单个章节 - 根据大纲和上下文生成章节内容。

        支持AI增强写作（有API Key时）和模板化降级写作。

        Args:
            chapter_key: 章节标识（如 section_0, section_1 等）
            outline: 论文大纲
            context: 上下文/已有内容
            topic: 研究主题
            study_type: 研究类型

        Returns:
            包含章节内容的字典
        """
        # 解析章节索引
        try:
            chapter_idx = int(chapter_key.split("_")[1])
        except (IndexError, ValueError):
            return {
                "success": False,
                "message": f"无效的章节标识: '{chapter_key}'",
                "chapter": None,
            }

        if chapter_idx >= len(outline):
            return {
                "success": False,
                "message": f"章节索引越界: {chapter_idx} >= {len(outline)}",
                "chapter": None,
            }

        section = outline[chapter_idx]
        logger.info(f"开始写作章节: {section.title}（{chapter_key}）")

        # 尝试AI写作
        content = ""
        if self._ai_available:
            try:
                content = self._write_with_ai(
                    topic, section, context, study_type
                )
                if content:
                    logger.info(f"AI写作成功: {section.title}")
                else:
                    logger.warning("AI写作返回空内容，使用降级写作")
            except Exception as e:
                logger.warning(f"AI写作失败，使用降级策略: {e}")

        # 降级写作（基于模板）
        if not content:
            content = self._write_with_template(section, topic, study_type)

        # 创建章节对象
        chapter = WritingChapter(
            chapter_key=chapter_key,
            title=section.title,
            content=content,
            word_count=len(content.replace(" ", "").replace("\n", "")),
        )

        # 术语检查
        term_issues = validate_medical_terms(content)
        chapter.term_check_passed = len(term_issues) == 0

        # 格式检查
        format_issues = validate_format(content, "")
        error_count = sum(1 for i in format_issues if i.get("severity") == "error")
        chapter.format_check_passed = error_count == 0

        # 更新缓存
        self._update_chapter_cache(chapter)

        result = {
            "success": True,
            "message": f"章节'{section.title}'写作完成",
            "chapter": chapter.model_dump(),
            "term_check_issues": term_issues,
            "format_check_issues": format_issues,
        }

        logger.info(
            f"章节写作完成: {section.title}, "
            f"字数={chapter.word_count}, "
            f"术语通过={chapter.term_check_passed}, "
            f"格式通过={chapter.format_check_passed}"
        )
        return result

    def polish_paper(
        self,
        paper_text: str,
        journal_name: str = "",
    ) -> dict:
        """
        润色论文 - 对论文全文进行语言润色和规范检查。

        Args:
            paper_text: 论文全文
            journal_name: 目标期刊名称（用于特定格式调整）

        Returns:
            包含润色结果和检查报告的字典
        """
        logger.info(f"开始润色论文: 总字数={len(paper_text)}")

        polished_text = paper_text

        # 1. AI润色（如果可用）
        if self._ai_available:
            try:
                polished_text = self._polish_with_ai(paper_text, journal_name)
            except Exception as e:
                logger.warning(f"AI润色失败，使用基础润色: {e}")
                polished_text = self._basic_polish(paper_text)
        else:
            polished_text = self._basic_polish(paper_text)

        # 2. 术语修正
        term_issues = validate_medical_terms(polished_text)
        term_corrections = []
        for issue in term_issues:
            if issue.get("suggestion"):
                polished_text = polished_text.replace(
                    issue["term"], issue["suggestion"]
                )
                term_corrections.append({
                    "original": issue["term"],
                    "correction": issue["suggestion"],
                })

        # 3. 格式验证
        format_issues = validate_format(polished_text, journal_name)

        # 4. 查重检测（模拟）
        from services.plagiarism_check import check_plagiarism
        plagiarism_result = check_plagiarism(polished_text)

        result = {
            "polished_text": polished_text,
            "original_length": len(paper_text),
            "polished_length": len(polished_text),
            "term_corrections": term_corrections,
            "format_issues": format_issues,
            "plagiarism_check": plagiarism_result,
            "submission_ready": (
                len(term_corrections) == 0
                and all(i.get("severity") != "error" for i in format_issues)
            ),
        }

        logger.info(
            f"润色完成: 术语修正={len(term_corrections)}, "
            f"格式问题={len(format_issues)}, "
            f"投稿就绪={result['submission_ready']}"
        )
        return result

    def get_current_paper(self) -> str:
        """
        获取当前已写作的所有章节合并后的论文全文。

        Returns:
            合并后的论文全文
        """
        if not self._chapters_cache:
            return ""

        full_text_parts = []
        for chapter in self._chapters_cache:
            if chapter.content:
                full_text_parts.append(f"\n{chapter.title}\n{chapter.content}")

        return "\n".join(full_text_parts)

    # ================================================================
    # 私有方法
    # ================================================================

    def _write_with_ai(
        self,
        topic: str,
        section: OutlineSection,
        context: str,
        study_type: str,
    ) -> str:
        """
        使用AI API生成章节内容。

        Args:
            topic: 研究主题
            section: 大纲章节
            context: 上下文
            study_type: 研究类型

        Returns:
            AI生成的文本

        Raises:
            Exception: AI调用失败时
        """
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=config.API_KEY_OPENAI,
                base_url=config.OPENAI_BASE_URL,
                timeout=config.AI_REQUEST_TIMEOUT,
            )

            prompt = self._build_writing_prompt(topic, section, context, study_type)

            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一位经验丰富的医学论文写作专家。"
                            "请根据提供的大纲和要求，撰写学术论文章节内容。"
                            "内容应当：\n"
                            "1. 严谨、专业、符合医学论文写作规范\n"
                            "2. 使用规范的医学术语\n"
                            "3. 逻辑清晰、数据准确\n"
                            "4. 符合目标章节的字数要求\n"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=config.OPENAI_MAX_TOKENS,
                temperature=0.7,
            )

            content = response.choices[0].message.content or ""
            return content.strip()

        except ImportError:
            raise RuntimeError("openai 包未安装，请执行: pip install openai")
        except Exception as e:
            raise RuntimeError(f"AI API调用失败: {e}")

    def _build_writing_prompt(
        self,
        topic: str,
        section: OutlineSection,
        context: str,
        study_type: str,
    ) -> str:
        """
        构建AI写作的提示词。

        Args:
            topic: 研究主题
            section: 大纲章节
            context: 上下文
            study_type: 研究类型

        Returns:
            提示词文本
        """
        subsections_text = "\n".join(
            f"  - {sub.title}: {', '.join(sub.key_points)}"
            for sub in section.subsections
        )

        prompt = (
            f"请为以下医学论文撰写章节内容：\n\n"
            f"研究主题：{topic}\n"
            f"研究类型：{study_type}\n"
            f"当前章节：{section.title}\n"
            f"目标字数：约{section.word_count_target}字\n"
        )

        if subsections_text:
            prompt += f"\n子章节要求：\n{subsections_text}"

        if section.key_points:
            prompt += f"\n关键要点：{', '.join(section.key_points)}"

        if context:
            prompt += f"\n\n上下文/已有内容：\n{context[:500]}"

        return prompt

    def _write_with_template(
        self,
        section: OutlineSection,
        topic: str,
        study_type: str,
    ) -> str:
        """
        使用模板生成章节内容（降级策略）。

        生成框架性内容，标注为模板生成，提示用户需要补充具体数据。

        Args:
            section: 大纲章节
            topic: 研究主题
            study_type: 研究类型

        Returns:
            模板生成的文本
        """
        templates: dict[str, str] = {
            "摘要": (
                f"[模板内容 - 请补充具体数据]\n\n"
                f"目的：探讨{topic}的临床效果及相关因素。\n\n"
                f"方法：采用{study_type}设计，[请补充研究对象数量和纳入排除标准]。"
                f"主要观察指标包括[请补充具体指标]。\n\n"
                f"结果：[请补充主要研究结果数据]。\n\n"
                f"结论：[请补充研究结论]。\n"
            ),
            "引言": (
                f"[模板内容 - 请补充具体数据和引用]\n\n"
                f"[请在此介绍{topic}的流行病学背景]\n\n"
                f"[请介绍国内外研究现状]\n\n"
                f"[请说明当前研究存在的问题和争议]\n\n"
                f"本研究旨在[请补充研究目的]，以期为临床实践提供参考。\n"
            ),
            "资料与方法": (
                f"[模板内容 - 请补充具体数据]\n\n"
                f"1.1 一般资料\n"
                f"选取[请补充时间段]于我院收治的[请补充疾病名称]患者[请补充数量]例。"
                f"纳入标准：（1）[请补充]；（2）[请补充]。"
                f"排除标准：（1）[请补充]；（2）[请补充]。\n\n"
                f"1.2 研究方法\n"
                f"[请描述{study_type}的具体实施方案]\n\n"
                f"1.3 观察指标\n"
                f"主要终点指标：[请补充]。\n"
                f"次要终点指标：[请补充]。\n\n"
                f"1.4 统计学方法\n"
                f"采用SPSS [版本]统计学软件进行数据分析。计量资料以均数+-标准差表示，"
                f"组间比较采用t检验；计数资料以例数（百分比）表示，"
                f"组间比较采用卡方检验。P<0.05为差异有统计学意义。\n\n"
                f"1.5 伦理学声明\n"
                f"本研究经医院伦理委员会审批（批号：[请补充]），所有患者均签署知情同意书。\n"
            ),
            "结果": (
                f"[模板内容 - 请补充具体数据]\n\n"
                f"2.1 基线资料比较\n"
                f"两组患者在年龄、性别、病程等基线资料方面比较，差异无统计学意义（P>0.05），具有可比性。\n\n"
                f"[请补充表1：两组基线资料比较]\n\n"
                f"2.2 主要结果\n"
                f"[请补充主要观察指标的分析结果]\n\n"
                f"[请补充表2/图1：主要结果]\n\n"
                f"2.3 次要结果\n"
                f"[请补充次要观察指标的分析结果]\n\n"
                f"2.4 安全性/不良反应\n"
                f"[请补充不良事件发生情况]\n"
            ),
            "讨论": (
                f"[模板内容 - 请补充具体分析和引用]\n\n"
                f"本研究结果显示[请补充主要发现]。这与[请补充参考文献]的研究结果一致/不一致。\n\n"
                f"[请分析可能的原因和机制]\n\n"
                f"本研究的临床意义在于[请补充]。\n\n"
                f"本研究的局限性：（1）[请补充样本量限制]；"
                f"（2）[请补充单中心/回顾性设计的局限]；"
                f"（3）[请补充其他局限]。\n\n"
                f"未来研究方向：[请补充对后续研究的建议]。\n"
            ),
            "结论": (
                f"[模板内容 - 请补充具体结论]\n\n"
                f"[请用一到两句话概括本研究的主要结论及临床意义]。\n"
            ),
        }

        # 查找匹配的模板
        content = templates.get(section.title, "")

        if not content:
            # 通用模板
            content = (
                f"[模板内容 - 请补充具体内容]\n\n"
                f"章节标题：{section.title}\n"
                f"目标字数：{section.word_count_target}字\n\n"
            )
            if section.key_points:
                content += f"关键要点：{', '.join(section.key_points)}\n\n"
            content += "[请根据以上要点撰写具体内容]\n"

        return content

    def _polish_with_ai(self, paper_text: str, journal_name: str) -> str:
        """
        使用AI API润色论文。

        Args:
            paper_text: 论文全文
            journal_name: 目标期刊名称

        Returns:
            润色后的文本

        Raises:
            Exception: AI调用失败时
        """
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=config.API_KEY_OPENAI,
                base_url=config.OPENAI_BASE_URL,
                timeout=config.AI_REQUEST_TIMEOUT,
            )

            # 截取过长的文本（AI有token限制）
            max_chars = 8000
            text_to_polish = paper_text[:max_chars]

            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一位资深医学编辑。请对以下论文进行润色，"
                            "修正语法错误、规范术语使用、改善表达流畅度。"
                            "保持学术风格，不要改变原文的核心内容和数据。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"请润色以下论文内容（目标期刊：{journal_name}）：\n\n{text_to_polish}",
                    },
                ],
                max_tokens=config.OPENAI_MAX_TOKENS,
                temperature=0.3,
            )

            polished = response.choices[0].message.content or ""
            # 保留未润色的部分
            if len(paper_text) > max_chars:
                return polished.strip() + "\n\n[以下内容未润色]\n" + paper_text[max_chars:]
            return polished.strip()

        except ImportError:
            raise RuntimeError("openai 包未安装")
        except Exception as e:
            raise RuntimeError(f"AI润色调用失败: {e}")

    def _basic_polish(self, paper_text: str) -> str:
        """
        基础润色（不依赖AI）- 执行简单的文本规范化处理。

        Args:
            paper_text: 论文全文

        Returns:
            基础润色后的文本
        """
        import re

        text = paper_text

        # 统一全角/半角标点
        text = text.replace(",", "，").replace(";", "；")
        text = text.replace(":", "：").replace("!", "！")
        text = text.replace("?", "？")
        text = text.replace("(", "（").replace(")", "）")

        # 去除多余空行
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 去除行首行尾空格
        lines = text.split("\n")
        lines = [line.strip() for line in lines]
        text = "\n".join(lines)

        return text

    def _update_chapter_cache(self, chapter: WritingChapter) -> None:
        """
        更新章节缓存。

        Args:
            chapter: 最新写作的章节
        """
        for i, cached in enumerate(self._chapters_cache):
            if cached.chapter_key == chapter.chapter_key:
                self._chapters_cache[i] = chapter
                return
        self._chapters_cache.append(chapter)

    def _generate_template_notes(
        self,
        journal_name: str,
        topic: str,
        study_type: str,
        outline: list[OutlineSection],
    ) -> str:
        """
        生成模板使用说明。

        Args:
            journal_name: 期刊名称
            topic: 主题
            study_type: 研究类型
            outline: 大纲

        Returns:
            说明文本
        """
        total_words = sum(s.word_count_target for s in outline)
        notes = (
            f"论文模板已根据'{journal_name}'的要求生成。\n"
            f"研究主题：{topic}\n"
            f"研究类型：{study_type}\n"
            f"总目标字数：约{total_words}字\n\n"
            f"写作流程：\n"
            f"1. 按章节顺序依次写作（摘要 -> 引言 -> 方法 -> 结果 -> 讨论 -> 结论）\n"
            f"2. 每个章节写作时会自动进行术语和格式检查\n"
            f"3. 全部章节完成后进行全文润色\n"
        )

        if not self._ai_available:
            notes += (
                "\n\n注意：当前未配置AI API密钥，将生成模板化内容。"
                "如需AI辅助写作，请配置 API_KEY_OPENAI 环境变量。"
            )

        return notes
