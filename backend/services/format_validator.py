"""
格式验证服务 - 检查论文格式是否符合期刊要求，包括摘要结构、IMRAD格式、
参考文献格式（GB/T 7714）、图表编号、医学术语拼写等。
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def validate_format(
    paper_text: str,
    journal_name: str = "",
) -> list[dict]:
    """
    验证论文格式是否符合期刊要求。

    检查项目：
    - 摘要结构（目的、方法、结果、结论四要素）
    - IMRAD格式（引言、方法、结果、讨论）
    - 参考文献格式（GB/T 7714标准）
    - 图表编号连续性
    - 关键词设置

    Args:
        paper_text: 论文全文文本
        journal_name: 目标期刊名称（用于特定格式检查）

    Returns:
        问题列表，每条包含 severity（info/warning/error）、category、message 字段
    """
    if not paper_text or not paper_text.strip():
        return [{
            "severity": "error",
            "category": "整体",
            "message": "论文内容为空",
        }]

    issues: list[dict] = []
    text_lower = paper_text.lower()

    # 1. 检查IMRAD结构
    issues.extend(_check_imrad_structure(text_lower))

    # 2. 检查摘要结构
    issues.extend(_check_abstract_structure(paper_text))

    # 3. 检查参考文献格式
    issues.extend(_check_references_format(paper_text))

    # 4. 检查图表编号
    issues.extend(_check_figure_table_numbering(paper_text))

    # 5. 检查关键词
    issues.extend(_check_keywords(paper_text))

    # 6. 检查标题层级
    issues.extend(_check_heading_levels(paper_text))

    logger.info(
        f"格式验证完成: journal='{journal_name}', "
        f"发现 {len(issues)} 个问题"
    )
    return issues


def validate_medical_terms(text: str) -> list[dict]:
    """
    检查常见医学术语拼写是否正确。

    内置常见医学术语词典，包括疾病名、药物名、解剖学术语等。
    检查常见拼写错误和术语不规范用法。

    Args:
        text: 论文文本

    Returns:
        术语问题列表，每条包含 severity、term、suggestion 字段
    """
    if not text:
        return []

    issues: list[dict] = []

    # 常见医学拼写错误映射表
    common_errors: dict[str, str] = {
        "阿斯匹林": "阿司匹林",
        "抗菌素": "抗生素",
        "心肌梗塞": "心肌梗死",
        "适应征": "适应证",
        "禁忌征": "禁忌证",
        "体征症": "体征和症状",
        "综合症": "综合征",
        "合并症": "并发症",
        "座疮": "痤疮",
        "皮层": "皮质",
        "脑皮层": "大脑皮质",
        "颅脑": "颅内",  # 注意：某些上下文中颅脑是正确的
        "机理": "机制",
        "机理学": "机制",
        "副作用": "不良反应",
        "激紊": "激素",
        "卵磷酯": "卵磷脂",
        "兰尾": "阑尾",
        "树枝状": "树突状",
        "心率不齐": "心律不齐",
        "心率失常": "心律失常",
        "心律不齐": "心律不齐",  # 部分文献仍用此说法
        "颈项强直": "颈强直",
        "症侯群": "症候群",
        "颈动脉狭窄": "颈动脉狭窄",  # 正确
        "颈动脉硬化": "颈动脉粥样硬化",
        "脑梗塞": "脑梗死",
        "中风": "脑卒中",  # 建议使用规范术语
        "冠心病": "冠状动脉粥样硬化性心脏病",  # 缩写可接受，但初次出现应写全称
        "高血压病": "高血压",  # 建议去掉"病"字
        "糖尿病病": "糖尿病",  # 去掉重复
        "霉菌": "真菌",
        "霉菌感染": "真菌感染",
        "抗菌素治疗": "抗菌药物治疗",
        "何杰金": "霍奇金",
        "何杰金病": "霍奇金病",
        "非何杰金": "非霍奇金",
        "革兰氏": "革兰",  # 建议去掉"氏"
        "美尼尔": "梅尼埃",
        "美尼尔病": "梅尼埃病",
        "雷诺氏": "雷诺",
        "巴彬斯基": "巴宾斯基",
        "柯兴氏": "库欣",
    }

    for wrong, correct in common_errors.items():
        if wrong in text:
            # 检查是否已经是正确写法（避免误报）
            if correct not in text or text.count(wrong) > text.count(correct):
                issues.append({
                    "severity": "warning",
                    "term": wrong,
                    "message": f"术语不规范: '{wrong}' 建议改为 '{correct}'",
                    "suggestion": correct,
                })

    # 检查英文医学术语拼写（常见错误）
    english_errors: dict[str, str] = {
        "alzheimer's": "Alzheimer's",
        "parkinson's": "Parkinson's",
        "hippocampus": "hippocampus",  # 正确
        "hippocampal": "hippocampal",  # 正确
        "hippocampius": "hippocampus",
        "acetylcholinesterase": "acetylcholinesterase",  # 正确
        "acetylcholinesterse": "acetylcholinesterase",
    }

    for wrong, correct in english_errors.items():
        if wrong in text.lower() and wrong != correct.lower():
            issues.append({
                "severity": "warning",
                "term": wrong,
                "message": f"英文术语可能拼写错误: '{wrong}' 建议改为 '{correct}'",
                "suggestion": correct,
            })

    logger.info(f"医学术语检查完成: 发现 {len(issues)} 个问题")
    return issues


def _check_imrad_structure(text: str) -> list[dict]:
    """
    检查IMRAD（引言、方法、结果、讨论）结构是否完整。

    Args:
        text: 论文全文（小写）

    Returns:
        问题列表
    """
    issues: list[dict] = []

    imrad_sections = {
        "引言": ["引言", "introduction", "前言", "背景"],
        "方法": ["方法", "materials and methods", "资料与方法", "材料与方法"],
        "结果": ["结果", "results", "结  果"],
        "讨论": ["讨论", "discussion", "讨  论"],
    }

    missing_sections = []
    for section_name, patterns in imrad_sections.items():
        found = False
        for pattern in patterns:
            if pattern in text:
                found = True
                break
        if not found:
            missing_sections.append(section_name)

    if missing_sections:
        issues.append({
            "severity": "error",
            "category": "IMRAD结构",
            "message": f"缺少IMRAD结构章节: {', '.join(missing_sections)}",
        })

    # 检查是否有结论部分
    conclusion_patterns = ["结论", "conclusion", "conclusions"]
    has_conclusion = any(cp in text for cp in conclusion_patterns)
    if not has_conclusion:
        issues.append({
            "severity": "warning",
            "category": "IMRAD结构",
            "message": "建议在讨论末尾添加简明结论",
        })

    return issues


def _check_abstract_structure(paper_text: str) -> list[dict]:
    """
    检查摘要结构是否包含目的、方法、结果、结论四要素。

    Args:
        paper_text: 论文全文

    Returns:
        问题列表
    """
    issues: list[dict] = []

    # 查找摘要部分
    abstract_match = re.search(
        r"摘\s*要[：:]", paper_text, re.IGNORECASE
    ) or re.search(
        r"abstract", paper_text, re.IGNORECASE
    )

    if not abstract_match:
        issues.append({
            "severity": "warning",
            "category": "摘要",
            "message": "未找到摘要部分，请确认是否包含结构化摘要",
        })
        return issues

    # 提取摘要文本（从摘要标记到下一个章节标记）
    abstract_start = abstract_match.end()
    next_section = re.search(
        r"\n\s*(引言|关键词|方法|1\s|introduction|keywords)",
        paper_text[abstract_start:],
        re.IGNORECASE,
    )
    if next_section:
        abstract_text = paper_text[abstract_start:abstract_start + next_section.start()]
    else:
        abstract_text = paper_text[abstract_start:abstract_start + 1000]

    abstract_lower = abstract_text.lower()

    # 检查四要素
    abstract_elements = {
        "目的": ["目的", "objective", "aim", "背景与目的"],
        "方法": ["方法", "methods", "method"],
        "结果": ["结果", "results", "result"],
        "结论": ["结论", "conclusion", "conclusions"],
    }

    missing_elements = []
    for element_name, patterns in abstract_elements.items():
        if not any(p in abstract_lower for p in patterns):
            missing_elements.append(element_name)

    if missing_elements:
        issues.append({
            "severity": "warning",
            "category": "摘要结构",
            "message": f"摘要缺少以下要素: {', '.join(missing_elements)}。建议采用结构化摘要格式（目的、方法、结果、结论）",
        })

    # 检查摘要字数（一般200-400字）
    abstract_word_count = len(abstract_text.replace(" ", "").replace("\n", ""))
    if abstract_word_count < 150:
        issues.append({
            "severity": "warning",
            "category": "摘要字数",
            "message": f"摘要字数偏少（约{abstract_word_count}字），建议200-400字",
        })
    elif abstract_word_count > 500:
        issues.append({
            "severity": "info",
            "category": "摘要字数",
            "message": f"摘要字数偏多（约{abstract_word_count}字），建议控制在200-400字以内",
        })

    return issues


def _check_references_format(paper_text: str) -> list[dict]:
    """
    检查参考文献格式是否符合GB/T 7714标准。

    Args:
        paper_text: 论文全文

    Returns:
        问题列表
    """
    issues: list[dict] = []

    # 查找参考文献部分
    ref_match = re.search(
        r"参\s*考\s*文\s*献|references",
        paper_text,
        re.IGNORECASE,
    )

    if not ref_match:
        issues.append({
            "severity": "warning",
            "category": "参考文献",
            "message": "未找到参考文献部分",
        })
        return issues

    ref_text = paper_text[ref_match.start():]

    # 检查引用编号格式 [1], [2] 等
    ref_numbers = re.findall(r"\[(\d+)\]", ref_text)
    if not ref_numbers:
        issues.append({
            "severity": "warning",
            "category": "参考文献格式",
            "message": "参考文献未使用编号格式，建议使用 [1], [2] 格式",
        })
    else:
        # 检查编号是否连续
        numbers = sorted(int(n) for n in ref_numbers)
        expected = list(range(1, max(numbers) + 1)) if numbers else []
        missing = set(expected) - set(numbers)
        if missing:
            issues.append({
                "severity": "warning",
                "category": "参考文献格式",
                "message": f"参考文献编号不连续，缺失: {sorted(missing)}",
            })

    # 检查GB/T 7714基本格式要素
    # 期刊论文应包含：作者. 标题[J]. 刊名, 年, 卷(期): 起止页码.
    if ref_text:
        # 检查是否有文献类型标识
        doc_type_marks = ["[J]", "[M]", "[D]", "[C]", "[R]", "[S]", "[P]", "[DB]", "[EB]"]
        has_type_mark = any(mark in ref_text for mark in doc_type_marks)

        if not has_type_mark:
            issues.append({
                "severity": "info",
                "category": "参考文献格式",
                "message": "参考文献未标注文献类型标识（如[J]期刊、[M]专著），建议按GB/T 7714标准添加",
            })

    return issues


def _check_figure_table_numbering(paper_text: str) -> list[dict]:
    """
    检查图表编号是否连续。

    Args:
        paper_text: 论文全文

    Returns:
        问题列表
    """
    issues: list[dict] = []

    # 检查图编号
    figure_numbers = re.findall(r"图\s*(\d+)", paper_text)
    if figure_numbers:
        fig_nums = sorted(int(n) for n in set(figure_numbers))
        expected_figs = list(range(1, max(fig_nums) + 1)) if fig_nums else []
        missing_figs = set(expected_figs) - set(fig_nums)
        if missing_figs:
            issues.append({
                "severity": "warning",
                "category": "图表编号",
                "message": f"图编号不连续，缺失: 图{sorted(missing_figs)}",
            })

    # 检查表编号
    table_numbers = re.findall(r"表\s*(\d+)", paper_text)
    if table_numbers:
        tbl_nums = sorted(int(n) for n in set(table_numbers))
        expected_tbls = list(range(1, max(tbl_nums) + 1)) if tbl_nums else []
        missing_tbls = set(expected_tbls) - set(tbl_nums)
        if missing_tbls:
            issues.append({
                "severity": "warning",
                "category": "图表编号",
                "message": f"表编号不连续，缺失: 表{sorted(missing_tbls)}",
            })

    # 检查正文中是否引用了所有图表
    figure_refs = re.findall(r"(?:见图|见图\s*|如图\s*\d+|fig\.\s*\d+|figure\s*\d+)", paper_text, re.IGNORECASE)
    table_refs = re.findall(r"(?:见表|见表\s*|如表\s*\d+|table\s*\d+)", paper_text, re.IGNORECASE)

    if len(figure_numbers) > 0 and len(figure_refs) == 0:
        issues.append({
            "severity": "info",
            "category": "图表引用",
            "message": "正文中未引用图表，建议在正文相应位置引用",
        })

    return issues


def _check_keywords(paper_text: str) -> list[dict]:
    """
    检查关键词设置。

    Args:
        paper_text: 论文全文

    Returns:
        问题列表
    """
    issues: list[dict] = []

    # 查找关键词部分
    kw_match = re.search(
        r"关键词\s*[：:]", paper_text
    ) or re.search(
        r"key\s*words?\s*[：:]", paper_text, re.IGNORECASE
    )

    if not kw_match:
        issues.append({
            "severity": "warning",
            "category": "关键词",
            "message": "未找到关键词部分，建议设置3-5个关键词",
        })
        return issues

    # 提取关键词
    kw_text = paper_text[kw_match.end():kw_match.end() + 200]
    # 常见分隔符：分号、逗号、空格
    keywords = re.split(r"[；;,，\s]+", kw_text.strip())
    keywords = [kw.strip() for kw in keywords if kw.strip() and len(kw.strip()) > 1]

    # 限制到下一个可能的内容
    actual_keywords = []
    for kw in keywords:
        if re.match(r"^(引言|摘要|方法|结果|讨论|1\s)", kw):
            break
        actual_keywords.append(kw)

    if len(actual_keywords) < 3:
        issues.append({
            "severity": "info",
            "category": "关键词",
            "message": f"关键词数量偏少（{len(actual_keywords)}个），建议设置3-5个",
        })
    elif len(actual_keywords) > 8:
        issues.append({
            "severity": "info",
            "category": "关键词",
            "message": f"关键词数量偏多（{len(actual_keywords)}个），建议控制在3-5个",
        })

    return issues


def _check_heading_levels(paper_text: str) -> list[dict]:
    """
    检查标题层级是否规范。

    Args:
        paper_text: 论文全文

    Returns:
        问题列表
    """
    issues: list[dict] = []

    # 检查是否使用了编号标题（1, 1.1, 1.1.1）
    has_numbered_headings = bool(re.search(r"\n\s*\d+[\.\s]", paper_text))

    if not has_numbered_headings:
        issues.append({
            "severity": "info",
            "category": "标题层级",
            "message": "未检测到编号标题格式，建议使用 '1', '1.1', '1.1.1' 层级编号",
        })

    return issues
