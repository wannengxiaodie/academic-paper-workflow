"""
大纲生成服务 - 根据研究主题、目标期刊和研究类型生成IMRAD结构的论文大纲。
包含每个章节的字数目标和关键要点。
"""

from __future__ import annotations

import logging

import config
from models.schemas import OutlineSection, OutlineSubSection

logger = logging.getLogger(__name__)


# 默认论文字数分配（按总字数比例）
_DEFAULT_WORD_ALLOCATION: dict[str, dict[str, int]] = {
    "title": {"min_ratio": 0.01, "max_ratio": 0.02},
    "abstract": {"min_ratio": 0.05, "max_ratio": 0.08},
    "introduction": {"min_ratio": 0.12, "max_ratio": 0.18},
    "methods": {"min_ratio": 0.20, "max_ratio": 0.30},
    "results": {"min_ratio": 0.25, "max_ratio": 0.35},
    "discussion": {"min_ratio": 0.15, "max_ratio": 0.22},
    "conclusion": {"min_ratio": 0.03, "max_ratio": 0.05},
    "references": {"min_ratio": 0.05, "max_ratio": 0.10},
}


def generate_outline(
    topic: str,
    journal: str,
    study_type: str = "RCT",
    title_level: str = "副高级",
) -> list[OutlineSection]:
    """
    根据研究主题、目标期刊和研究类型生成IMRAD结构大纲。

    Args:
        topic: 研究主题
        journal: 目标期刊名称
        study_type: 研究类型（RCT/队列研究/病例对照/横断面/病例系列/病例报告/系统综述/Meta分析）
        title_level: 目标职称级别

    Returns:
        完整的IMRAD大纲结构列表
    """
    # 获取目标字数
    word_config = config.WORD_COUNT_TARGETS.get(title_level, {"min": 4000, "max": 6000})
    target_total = (word_config["min"] + word_config["max"]) // 2

    # 根据研究类型生成对应的大纲
    if study_type in ("系统综述", "Meta分析"):
        outline = _generate_review_outline(topic, target_total)
    elif study_type in ("病例报告", "病例系列"):
        outline = _generate_case_outline(topic, target_total)
    else:
        outline = _generate_imrad_outline(topic, study_type, target_total)

    logger.info(
        f"大纲生成完成: topic='{topic}', journal='{journal}', "
        f"study_type='{study_type}', 总目标字数={target_total}, "
        f"章节数={len(outline)}"
    )
    return outline


def _generate_imrad_outline(
    topic: str,
    study_type: str,
    total_words: int,
) -> list[OutlineSection]:
    """
    生成标准IMRAD结构大纲（适用于RCT、队列研究、病例对照、横断面等）。

    Args:
        topic: 研究主题
        study_type: 研究类型
        total_words: 目标总字数

    Returns:
        大纲章节列表
    """
    sections: list[OutlineSection] = []

    # ---- 摘要 ----
    abstract_words = max(200, int(total_words * 0.06))
    sections.append(OutlineSection(
        title="摘要",
        subsections=[
            OutlineSubSection(
                title="目的",
                key_points=[f"简要说明研究{topic}的临床背景和目的"],
            ),
            OutlineSubSection(
                title="方法",
                key_points=[
                    f"说明研究类型（{study_type}）",
                    "研究对象及纳入排除标准",
                    "主要观察指标和统计方法",
                ],
            ),
            OutlineSubSection(
                title="结果",
                key_points=["主要研究结果和数据摘要"],
            ),
            OutlineSubSection(
                title="结论",
                key_points=["研究结论及临床意义"],
            ),
        ],
        word_count_target=abstract_words,
        key_points=["结构化摘要：目的-方法-结果-结论", "200-400字", "不引用参考文献"],
    ))

    # ---- 引言 ----
    intro_words = max(300, int(total_words * 0.15))
    sections.append(OutlineSection(
        title="引言",
        subsections=[
            OutlineSubSection(
                title="研究背景",
                key_points=[
                    f"{topic}的流行病学现状",
                    "国内外研究进展",
                    "当前存在的问题和争议",
                ],
            ),
            OutlineSubSection(
                title="研究目的与假设",
                key_points=[
                    "明确研究目的",
                    f"提出关于{topic}的研究假设",
                    "说明研究的临床意义",
                ],
            ),
        ],
        word_count_target=intro_words,
        key_points=["由宽到窄的逻辑递进", "引用最新文献（近5年优先）", "引出研究假设"],
    ))

    # ---- 资料与方法 ----
    methods_words = max(500, int(total_words * 0.25))
    sections.append(OutlineSection(
        title="资料与方法",
        subsections=[
            OutlineSubSection(
                title="一般资料",
                key_points=[
                    "研究对象来源",
                    "纳入标准和排除标准",
                    "样本量计算依据",
                ],
            ),
            OutlineSubSection(
                title="研究方法",
                key_points=[
                    f"研究设计类型：{study_type}",
                    "随机化方法（RCT适用）",
                    "分组方法",
                    "干预措施",
                ],
            ),
            OutlineSubSection(
                title="观察指标",
                key_points=[
                    "主要终点指标",
                    "次要终点指标",
                    "安全性指标",
                ],
            ),
            OutlineSubSection(
                title="统计学方法",
                key_points=[
                    "统计软件及版本",
                    "描述性统计方法",
                    "推断性统计方法",
                    "显著性水平设定",
                ],
            ),
            OutlineSubSection(
                title="伦理学声明",
                key_points=[
                    "伦理委员会审批情况",
                    "知情同意书签署",
                    "临床试验注册号（RCT适用）",
                ],
            ),
        ],
        word_count_target=methods_words,
        key_points=["可重复性原则", "详细描述研究流程", "明确统计方法"],
    ))

    # ---- 结果 ----
    results_words = max(500, int(total_words * 0.30))
    sections.append(OutlineSection(
        title="结果",
        subsections=[
            OutlineSubSection(
                title="基线资料比较",
                key_points=[
                    "研究对象的基线特征表",
                    "组间均衡性分析",
                ],
            ),
            OutlineSubSection(
                title="主要结果",
                key_points=[
                    "主要终点指标的分析结果",
                    "统计学检验结果（P值、95%CI）",
                    "关键图表展示",
                ],
            ),
            OutlineSubSection(
                title="次要结果",
                key_points=[
                    "次要终点指标的分析结果",
                    "亚组分析（如适用）",
                ],
            ),
            OutlineSubSection(
                title="安全性/不良反应",
                key_points=[
                    "不良事件发生率",
                    "严重不良事件报告",
                ],
            ),
        ],
        word_count_target=results_words,
        key_points=[
            "仅报告结果，不做解释讨论",
            "数据与图表配合",
            "报告效应量和置信区间",
        ],
    ))

    # ---- 讨论 ----
    discussion_words = max(400, int(total_words * 0.18))
    sections.append(OutlineSection(
        title="讨论",
        subsections=[
            OutlineSubSection(
                title="主要发现总结",
                key_points=[
                    "简明总结本研究的主要发现",
                    "与预期假设的一致性",
                ],
            ),
            OutlineSubSection(
                title="与既往研究的比较",
                key_points=[
                    "与国内外同类研究的对比",
                    "结果一致和差异的分析",
                    "可能的解释",
                ],
            ),
            OutlineSubSection(
                title="临床意义",
                key_points=[
                    "研究结果对临床实践的指导意义",
                    "可能的影响和应用前景",
                ],
            ),
            OutlineSubSection(
                title="研究局限性",
                key_points=[
                    "样本量限制",
                    "单中心/回顾性设计的局限",
                    "未控制的因素",
                    "对未来研究的建议",
                ],
            ),
        ],
        word_count_target=discussion_words,
        key_points=["不要重复结果中的数据", "围绕研究目的展开", "客观评价研究局限"],
    ))

    # ---- 结论 ----
    conclusion_words = max(100, int(total_words * 0.04))
    sections.append(OutlineSection(
        title="结论",
        subsections=[],
        word_count_target=conclusion_words,
        key_points=["简明扼要", "基于研究数据的客观结论", "一至两句话"],
    ))

    return sections


def _generate_review_outline(
    topic: str,
    total_words: int,
) -> list[OutlineSection]:
    """
    生成系统综述/Meta分析大纲。

    Args:
        topic: 研究主题
        total_words: 目标总字数

    Returns:
        大纲章节列表
    """
    sections: list[OutlineSection] = []

    # 摘要
    sections.append(OutlineSection(
        title="摘要",
        subsections=[
            OutlineSubSection(title="目的", key_points=["系统综述/Meta分析目的"]),
            OutlineSubSection(title="方法", key_points=["检索策略、纳入标准、统计方法"]),
            OutlineSubSection(title="结果", key_points=["纳入研究数量、主要效应量"]),
            OutlineSubSection(title="结论", key_points=["主要结论和证据等级"]),
        ],
        word_count_target=300,
        key_points=["结构化摘要", "250-400字"],
    ))

    # 引言
    sections.append(OutlineSection(
        title="引言",
        subsections=[
            OutlineSubSection(
                title="背景",
                key_points=[f"{topic}的临床背景", "已有研究的不足"],
            ),
            OutlineSubSection(
                title="目的",
                key_points=["系统综述/Meta分析的具体目的"],
            ),
        ],
        word_count_target=int(total_words * 0.12),
        key_points=["说明进行系统综述的必要性"],
    ))

    # 资料与方法
    sections.append(OutlineSection(
        title="资料与方法",
        subsections=[
            OutlineSubSection(
                title="检索策略",
                key_points=["数据库选择", "检索词和时间范围", "检索式"],
            ),
            OutlineSubSection(
                title="纳入排除标准",
                key_points=["PICOS原则", "研究类型", "人群", "干预", "结局"],
            ),
            OutlineSubSection(
                title="文献筛选与数据提取",
                key_points=["筛选流程", "数据提取表"],
            ),
            OutlineSubSection(
                title="质量评价",
                key_points=["偏倚风险评估工具", "GRADE证据分级"],
            ),
            OutlineSubSection(
                title="统计分析",
                key_points=["效应量合并方法", "异质性检验", "发表偏倚"],
            ),
        ],
        word_count_target=int(total_words * 0.22),
        key_points=["遵循PRISMA指南"],
    ))

    # 结果
    sections.append(OutlineSection(
        title="结果",
        subsections=[
            OutlineSubSection(
                title="文献检索结果",
                key_points=["PRISMA流程图", "纳入研究基本特征表"],
            ),
            OutlineSubSection(
                title="纳入研究质量评价",
                key_points=["偏倚风险评估结果", "GRADE证据分级"],
            ),
            OutlineSubSection(
                title="Meta分析结果",
                key_points=["主要结局合并结果", "森林图", "亚组分析"],
            ),
            OutlineSubSection(
                title="发表偏倚评估",
                key_points=["漏斗图", "Egger's检验"],
            ),
        ],
        word_count_target=int(total_words * 0.30),
        key_points=["客观报告数据"],
    ))

    # 讨论
    sections.append(OutlineSection(
        title="讨论",
        subsections=[
            OutlineSubSection(title="主要发现", key_points=["核心结果总结"]),
            OutlineSubSection(title="证据质量评价", key_points=["GRADE分级解读"]),
            OutlineSubSection(title="临床实践意义", key_points=["对临床的指导价值"]),
            OutlineSubSection(title="研究局限性", key_points=["系统综述的局限性", "对未来研究的建议"]),
        ],
        word_count_target=int(total_words * 0.18),
        key_points=["客观评价证据质量"],
    ))

    # 结论
    sections.append(OutlineSection(
        title="结论",
        subsections=[],
        word_count_target=int(total_words * 0.04),
        key_points=["简明结论"],
    ))

    return sections


def _generate_case_outline(
    topic: str,
    total_words: int,
) -> list[OutlineSection]:
    """
    生成病例报告/病例系列大纲。

    Args:
        topic: 研究主题
        total_words: 目标总字数

    Returns:
        大纲章节列表
    """
    sections: list[OutlineSection] = []

    # 摘要
    sections.append(OutlineSection(
        title="摘要",
        subsections=[],
        word_count_target=200,
        key_points=["非结构化摘要或简短摘要", "150-250字"],
    ))

    # 引言
    sections.append(OutlineSection(
        title="引言",
        subsections=[
            OutlineSubSection(
                title="疾病背景",
                key_points=[f"{topic}的概述", "罕见性或临床重要性"],
            ),
        ],
        word_count_target=int(total_words * 0.15),
        key_points=["简洁说明为何值得报告"],
    ))

    # 病例报告
    sections.append(OutlineSection(
        title="病例报告",
        subsections=[
            OutlineSubSection(
                title="一般资料",
                key_points=["年龄、性别、主诉", "现病史、既往史"],
            ),
            OutlineSubSection(
                title="体格检查与辅助检查",
                key_points=["阳性体征", "影像学/实验室检查结果"],
            ),
            OutlineSubSection(
                title="诊断与治疗经过",
                key_points=["诊断依据", "治疗方案", "疗效评估"],
            ),
            OutlineSubSection(
                title="随访结果",
                key_points=["随访时间", "预后情况", "不良反应"],
            ),
        ],
        word_count_target=int(total_words * 0.50),
        key_points=["按时间顺序描述", "重要的阴性结果也应报告"],
    ))

    # 讨论
    sections.append(OutlineSection(
        title="讨论",
        subsections=[
            OutlineSubSection(
                title="病例分析",
                key_points=["诊治特点总结", "与文献报道的对比"],
            ),
            OutlineSubSection(
                title="经验教训",
                key_points=["对临床实践的启示", "诊治要点"],
            ),
        ],
        word_count_target=int(total_words * 0.25),
        key_points=["结合文献讨论"],
    ))

    return sections
