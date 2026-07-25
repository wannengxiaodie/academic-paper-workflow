"""
文献检索服务 - 通过PubMed E-utilities API检索英文文献，预留CNKI中文文献检索接口。
使用Bio.Entrez对接PubMed，免费且无需API Key。
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Optional

import httpx

import config
from models.schemas import LiteratureGap

logger = logging.getLogger(__name__)


def search_pubmed(
    query: str,
    max_results: int = 20,
    retstart: int = 0,
) -> list[dict]:
    """
    通过PubMed E-utilities API检索英文文献。

    使用NCBI Entrez Programming Utilities (E-utilities) 的 esearch + efetch 方式。
    该接口免费使用，无需API Key。如有API Key可提高请求速率限制。

    Args:
        query: 检索关键词（支持PubMed检索语法）
        max_results: 最大返回结果数，默认20
        retstart: 起始位置（用于分页），默认0

    Returns:
        文献列表，每条包含 title, authors, abstract, pmid, year, source 字段

    Raises:
        httpx.HTTPError: 网络请求失败时
        ValueError: 查询参数不合法时
    """
    if not query or not query.strip():
        raise ValueError("检索关键词不能为空")

    query = query.strip()
    max_results = min(max(1, max_results), 100)  # 限制在1-100之间

    try:
        # 步骤1: esearch 获取PMID列表
        search_url = f"{config.PUBMED_EUTILS_BASE}/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retstart": retstart,
            "retmode": "json",
            "sort": "relevance",
        }
        if config.PUBMED_API_KEY:
            search_params["api_key"] = config.PUBMED_API_KEY

        with httpx.Client(timeout=config.PUBMED_REQUEST_TIMEOUT) as client:
            search_response = client.get(search_url, params=search_params)
            search_response.raise_for_status()
            search_data = search_response.json()

        id_list = search_data.get("esearchresult", {}).get("idlist", [])

        if not id_list:
            logger.info(f"PubMed检索无结果: query='{query}'")
            return []

        # 步骤2: efetch 获取详细信息
        fetch_url = f"{config.PUBMED_EUTILS_BASE}/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "xml",
            "rettype": "abstract",
        }
        if config.PUBMED_API_KEY:
            fetch_params["api_key"] = config.PUBMED_API_KEY

        with httpx.Client(timeout=config.PUBMED_REQUEST_TIMEOUT) as client:
            fetch_response = client.get(fetch_url, params=fetch_params)
            fetch_response.raise_for_status()

        # 解析XML响应
        results = _parse_pubmed_xml(fetch_response.text)

        logger.info(f"PubMed检索成功: query='{query}', 返回 {len(results)} 条结果")
        return results

    except httpx.HTTPStatusError as e:
        logger.error(f"PubMed API返回HTTP错误: {e.response.status_code}")
        raise
    except httpx.TimeoutException:
        logger.error("PubMed API请求超时")
        raise
    except httpx.RequestError as e:
        logger.error(f"PubMed API请求失败: {e}")
        raise
    except ET.ParseError as e:
        logger.error(f"PubMed XML解析失败: {e}")
        return []


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    """
    解析PubMed efetch返回的XML格式数据。

    Args:
        xml_text: PubMed返回的XML文本

    Returns:
        解析后的文献列表
    """
    results: list[dict] = []

    try:
        root = ET.fromstring(xml_text)

        for article_elem in root.findall(".//PubmedArticle"):
            try:
                # PMID
                pmid = ""
                pmid_elem = article_elem.find(".//PMID")
                if pmid_elem is not None and pmid_elem.text:
                    pmid = pmid_elem.text.strip()

                # 标题
                title = ""
                title_elem = article_elem.find(".//ArticleTitle")
                if title_elem is not None and title_elem.text:
                    title = title_elem.text.strip()

                # 作者
                authors: list[str] = []
                author_list = article_elem.findall(".//Author")
                for author in author_list:
                    last_name = author.findtext("LastName", "")
                    fore_name = author.findtext("ForeName", "")
                    if last_name:
                        if fore_name:
                            authors.append(f"{last_name} {fore_name}")
                        else:
                            authors.append(last_name)

                # 摘要
                abstract = ""
                abstract_elem = article_elem.find(".//Abstract/AbstractText")
                if abstract_elem is not None:
                    # 合并所有AbstractText段
                    abstract_parts = []
                    for at in article_elem.findall(".//Abstract/AbstractText"):
                        label = at.get("Label", "")
                        text = "".join(at.itertext()).strip()
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        elif text:
                            abstract_parts.append(text)
                    abstract = " ".join(abstract_parts)

                # 发表年份
                year = 0
                pub_date = article_elem.find(".//PubDate")
                if pub_date is not None:
                    year_elem = pub_date.find("Year")
                    if year_elem is not None and year_elem.text:
                        year = int(year_elem.text.strip())
                    else:
                        medline_date = pub_date.find("MedlineDate")
                        if medline_date is not None and medline_date.text:
                            year_str = medline_date.text.strip()[:4]
                            if year_str.isdigit():
                                year = int(year_str)

                results.append({
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "pmid": pmid,
                    "year": year,
                    "source": "pubmed",
                })

            except Exception as e:
                logger.warning(f"解析单条PubMed记录失败: {e}")
                continue

    except ET.ParseError as e:
        logger.error(f"PubMed XML根解析失败: {e}")

    return results


def search_cnki(keyword: str, max_results: int = 20) -> list[dict]:
    """
    中国知网（CNKI）文献检索接口（预留，待正式对接）。

    当前返回模拟数据，标注为待接入状态。
    正式接入后需替换为真实的CNKI API调用。

    Args:
        keyword: 检索关键词
        max_results: 最大返回结果数

    Returns:
        模拟的中文文献列表
    """
    logger.warning(
        f"CNKI检索暂未正式接入，返回模拟数据: keyword='{keyword}'"
    )

    # 模拟数据 - 待正式接入CNKI API后替换
    mock_results = [
        {
            "title": f"[模拟] {keyword}的临床应用研究进展",
            "authors": ["张某某", "李某某", "王某某"],
            "abstract": f"本文综述了近年来{keyword}领域的研究进展，包括临床表现、诊断方法和治疗策略等方面的最新成果。",
            "pmid": "",
            "year": 2024,
            "source": "cnki（待接入）",
        },
        {
            "title": f"[模拟] {keyword}相关并发症的危险因素分析",
            "authors": ["赵某某", "钱某某"],
            "abstract": f"目的：探讨{keyword}患者发生并发症的危险因素。方法：回顾性分析我院收治的{keyword}患者临床资料。",
            "pmid": "",
            "year": 2023,
            "source": "cnki（待接入）",
        },
        {
            "title": f"[模拟] {keyword}的预后影响因素及生存分析",
            "authors": ["孙某某", "周某某", "吴某某"],
            "abstract": f"目的：分析影响{keyword}患者预后的相关因素。方法：采用多因素Cox回归模型分析。",
            "pmid": "",
            "year": 2024,
            "source": "cnki（待接入）",
        },
    ]

    return mock_results[:min(max_results, len(mock_results))]


def identify_research_gaps(
    topic: str,
    papers: list[dict],
) -> list[LiteratureGap]:
    """
    基于文献检索结果识别可能的研究空白/缺口。

    通过分析已有文献的研究方向、结论局限性、样本特征等，
    识别尚未充分研究的领域和可能的研究方向。

    Args:
        topic: 研究主题
        papers: 文献检索结果列表（来自search_pubmed或search_cnki）

    Returns:
        研究空白列表
    """
    if not papers:
        return []

    gaps: list[LiteratureGap] = []
    topic_lower = topic.lower()

    # 策略1: 检查文献中的"局限性"提及
    limitation_keywords = [
        "limitation", "局限性", "不足", "future", "未来研究",
        "further study", "进一步", "需要更多", "remain unclear",
    ]
    limitation_papers: list[str] = []
    for paper in papers:
        abstract_lower = paper.get("abstract", "").lower()
        for kw in limitation_keywords:
            if kw in abstract_lower:
                limitation_papers.append(paper.get("title", ""))
                break

    if limitation_papers:
        gaps.append(LiteratureGap(
            gap_description=f"现有文献中多篇明确指出研究局限性，提示'{topic}'领域仍有深入研究的空间",
            supporting_papers=limitation_papers[:5],
            evidence_level="B",
            research_direction="基于已有研究的局限性设计更严谨的临床研究",
        ))

    # 策略2: 检查研究人群覆盖情况
    population_keywords = [
        "elderly", "老年", "pediatric", "儿童", "pregnant", "妊娠",
        "community", "社区", "rural", "农村",
    ]
    underrepresented: list[str] = []
    for paper in papers:
        abstract_lower = paper.get("abstract", "").lower()
        for kw in population_keywords:
            if kw in abstract_lower:
                underrepresented.append(paper.get("title", ""))
                break

    if not underrepresented and len(papers) >= 5:
        gaps.append(LiteratureGap(
            gap_description=f"检索到的文献中缺乏特殊人群（如老年、儿童、妊娠等）的研究数据",
            supporting_papers=[p.get("title", "") for p in papers[:3]],
            evidence_level="C",
            research_direction="针对特殊人群开展专项临床研究",
        ))

    # 策略3: 检查多中心 vs 单中心研究
    multicenter_count = 0
    for paper in papers:
        abstract_lower = paper.get("abstract", "").lower()
        if "multicenter" in abstract_lower or "多中心" in abstract_lower:
            multicenter_count += 1

    if multicenter_count < len(papers) * 0.3 and len(papers) >= 5:
        gaps.append(LiteratureGap(
            gap_description=f"'{topic}'领域缺乏大规模多中心随机对照研究，现有证据级别有待提高",
            supporting_papers=[p.get("title", "") for p in papers[:3]],
            evidence_level="B",
            research_direction="开展多中心随机对照研究以提升证据等级",
        ))

    # 策略4: 检查时间趋势 - 近年研究是否减少
    recent_papers = [p for p in papers if p.get("year", 0) >= 2022]
    if len(papers) > 5 and len(recent_papers) < len(papers) * 0.2:
        gaps.append(LiteratureGap(
            gap_description=f"近年来关于'{topic}'的研究热度有所下降，可能存在未被关注的新方向",
            supporting_papers=[p.get("title", "") for p in recent_papers[:3]] if recent_papers else [],
            evidence_level="C",
            research_direction="探索该领域的新兴研究热点和技术方法",
        ))

    # 策略5: 检查是否缺乏Meta分析/系统综述
    review_count = 0
    for paper in papers:
        abstract_lower = paper.get("abstract", "").lower()
        if "meta-analysis" in abstract_lower or "系统综述" in abstract_lower or "systematic review" in abstract_lower:
            review_count += 1

    if review_count == 0 and len(papers) >= 10:
        gaps.append(LiteratureGap(
            gap_description=f"目前尚无关于'{topic}'的系统综述或Meta分析，存在证据整合的需求",
            supporting_papers=[p.get("title", "") for p in papers[:3]],
            evidence_level="B",
            research_direction="开展系统综述/Meta分析以整合现有证据",
        ))

    # 至少返回一个缺口（如果策略都没触发）
    if not gaps and papers:
        gaps.append(LiteratureGap(
            gap_description=f"基于现有文献分析，'{topic}'领域仍存在待深入研究的方向",
            supporting_papers=[p.get("title", "") for p in papers[:3]],
            evidence_level="C",
            research_direction="结合临床实践中的实际问题设计针对性研究",
        ))

    logger.info(f"识别到 {len(gaps)} 个研究空白: topic='{topic}'")
    return gaps
