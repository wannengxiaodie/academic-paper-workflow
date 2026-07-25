"""
FastAPI 主入口 - 医学职称论文写作自动化平台的后端API服务。
提供从期刊匹配、文献检索、大纲评审到章节写作、润色投稿的完整API。
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import config
from models.schemas import (
    ApiResponse,
    GateCheckRequest,
    GenerateTemplateRequest,
    JournalMatchRequest,
    LiteratureSearchRequest,
    OutlineEvaluateRequest,
    PolishSubmitRequest,
    WriteChapterRequest,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# 全局状态管理（简单内存存储，生产环境应使用数据库）
# ============================================================
_project_state: dict = {
    "current_step": 0,
    "topic": "",
    "title_level": "",
    "department": "",
    "target_journal": "",
    "journal_recommendations": [],
    "literature_results": [],
    "research_gaps": [],
    "outline": [],
    "scores": {},
    "chapters": [],
    "final_paper": "",
}


def _update_state(key: str, value: object) -> None:
    """更新项目状态。"""
    _project_state[key] = value


def _get_state(key: str, default=None):
    """获取项目状态。"""
    return _project_state.get(key, default)


# ============================================================
# FastAPI 应用初始化
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    logger.info("医学职称论文写作自动化平台启动中...")
    logger.info(f"期刊数据库: {_get_journals_count()} 本期刊")
    logger.info(f"AI增强模式: {'已启用' if (config.API_KEY_OPENAI or config.API_KEY_ANTHROPIC) else '未启用'}")
    logger.info("服务就绪")
    yield
    logger.info("服务关闭")


app = FastAPI(
    title="医学职称论文写作自动化平台",
    description=(
        "提供从期刊匹配、文献检索、大纲评审到章节写作、润色投稿的完整API服务。"
        "支持多种职称级别和科室的论文写作需求。"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 工具函数
# ============================================================

def _get_journals_count() -> int:
    """获取期刊数据库中的期刊数量。"""
    from data.journals_db import get_journals_count
    return get_journals_count()


def _safe_call(func, *args, **kwargs):
    """
    安全调用服务函数，捕获异常并返回友好错误信息。

    Args:
        func: 服务函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        (success, result_or_error) 元组
    """
    try:
        result = func(*args, **kwargs)
        return True, result
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        logger.error(f"服务调用异常: {func.__name__}, 错误: {e}")
        return False, f"服务内部错误: {str(e)}"


# ============================================================
# API 端点
# ============================================================

# ---- Step 1: 期刊匹配 ----

@app.post("/api/step1/journal-match", response_model=ApiResponse)
async def step1_journal_match(request: JournalMatchRequest) -> ApiResponse:
    """
    Step 1: 期刊匹配 - 根据研究主题、职称级别和科室推荐适合投稿的期刊。
    """
    from agents.strategist import StrategistAgent
    from services.journal_matcher import match_journals

    # 参数校验
    if request.title_level not in config.SUPPORTED_TITLE_LEVELS:
        return ApiResponse(
            success=False,
            message=f"不支持的职称级别: '{request.title_level}'。支持: {', '.join(config.SUPPORTED_TITLE_LEVELS)}",
        )

    if request.department not in config.SUPPORTED_DEPARTMENTS:
        return ApiResponse(
            success=False,
            message=f"不支持的科室: '{request.department}'。支持: {', '.join(config.SUPPORTED_DEPARTMENTS)}",
        )

    success, result = _safe_call(match_journals, request.topic, request.title_level, request.department)

    if not success:
        return ApiResponse(success=False, message=result)

    # 更新状态
    _update_state("current_step", 1)
    _update_state("topic", request.topic)
    _update_state("title_level", request.title_level)
    _update_state("department", request.department)
    _update_state("journal_recommendations", [r.model_dump() for r in result])

    return ApiResponse(
        success=True,
        message=f"期刊匹配完成，共推荐 {len(result)} 本期刊",
        data={
            "recommendations": [r.model_dump() for r in result],
            "total_journals_scanned": _get_journals_count(),
        },
    )


# ---- Step 2: 文献检索 ----

@app.post("/api/step2/literature-search", response_model=ApiResponse)
async def step2_literature_search(request: LiteratureSearchRequest) -> ApiResponse:
    """
    Step 2: 文献检索 - 通过PubMed检索英文文献，识别研究空白。
    """
    from agents.strategist import StrategistAgent

    agent = StrategistAgent()
    success, result = _safe_call(
        agent.review_literature,
        request.query,
        request.max_results,
    )

    if not success:
        return ApiResponse(success=False, message=result)

    # 更新状态
    _update_state("current_step", 2)
    _update_state("literature_results", result.get("pubmed_results", []))
    _update_state("research_gaps", result.get("research_gaps", []))

    return ApiResponse(
        success=True,
        message=f"文献检索完成，PubMed {len(result.get('pubmed_results', []))} 篇，识别到 {len(result.get('research_gaps', []))} 个研究空白",
        data=result,
    )


# ---- Step 3: 大纲评审 ----

@app.post("/api/step3/outline-evaluate", response_model=ApiResponse)
async def step3_outline_evaluate(request: OutlineEvaluateRequest) -> ApiResponse:
    """
    Step 3: 大纲评审 - 从7个维度对论文大纲进行评分。
    """
    from agents.strategist import StrategistAgent

    agent = StrategistAgent()
    success, result = _safe_call(
        agent.evaluate_outline,
        request.topic,
        request.outline,
    )

    if not success:
        return ApiResponse(success=False, message=result)

    # 更新状态
    _update_state("current_step", 3)
    _update_state("outline", [s.model_dump() for s in request.outline])
    _update_state("scores", result.get("scores", {}))

    return ApiResponse(
        success=True,
        message=f"大纲评审完成，总分 {result.get('total_score', 0)}/35，均分 {result.get('average_score', 0)}/5",
        data=result,
    )


# ---- Step 4: 质量门控 ----

@app.post("/api/step4/gate-check", response_model=ApiResponse)
async def step4_gate_check(request: GateCheckRequest) -> ApiResponse:
    """
    Step 4: 质量门控 - 判断策略阶段结果是否达到写作阶段的准入标准。
    """
    from agents.reviewer import ReviewerAgent

    agent = ReviewerAgent()

    # 构建策略结果（模拟从前面步骤收集）
    strategy_result = {
        "scores": request.scores,
        "topic": request.topic,
        "title_level": _get_state("title_level", "副高级"),
        "word_count": 0,
        "section_titles": [s.get("title", "") for s in _get_state("outline", [])],
        "reference_count": 0,
    }

    success, result = _safe_call(agent.check_gate, strategy_result)

    if not success:
        return ApiResponse(success=False, message=result)

    # 更新状态
    _update_state("current_step", 4)

    if result.get("passed"):
        return ApiResponse(
            success=True,
            message="质量门控通过，可以进入写作阶段",
            data=result,
        )
    else:
        return ApiResponse(
            success=False,
            message="质量门控未通过",
            data=result,
        )


# ---- Step 5: 模板生成 ----

@app.post("/api/step5/generate-template", response_model=ApiResponse)
async def step5_generate_template(request: GenerateTemplateRequest) -> ApiResponse:
    """
    Step 5: 模板生成 - 基于目标期刊和研究类型生成论文大纲和写作模板。
    """
    from agents.composer import ComposerAgent

    agent = ComposerAgent()
    title_level = _get_state("title_level", "副高级")

    success, result = _safe_call(
        agent.generate_template,
        request.journal_name,
        request.topic,
        request.study_type,
        title_level,
    )

    if not success:
        return ApiResponse(success=False, message=result)

    # 更新状态
    _update_state("current_step", 5)
    _update_state("target_journal", request.journal_name)
    _update_state("outline", result.get("outline", []))

    return ApiResponse(
        success=True,
        message=f"模板生成完成，包含 {len(result.get('outline', []))} 个章节",
        data=result,
    )


# ---- Step 6: 章节写作 ----

@app.post("/api/step6/write-chapter", response_model=ApiResponse)
async def step6_write_chapter(request: WriteChapterRequest) -> ApiResponse:
    """
    Step 6: 章节写作 - 根据大纲和上下文生成单个章节的内容。
    """
    from agents.composer import ComposerAgent

    agent = ComposerAgent()

    # 从状态获取大纲
    outline_data = _get_state("outline", [])
    from models.schemas import OutlineSection, OutlineSubSection
    outline = []
    for section_data in outline_data:
        subsections = [
            OutlineSubSection(**sub)
            for sub in section_data.get("subsections", [])
        ]
        outline.append(OutlineSection(
            title=section_data.get("title", ""),
            subsections=subsections,
            word_count_target=section_data.get("word_count_target", 500),
            key_points=section_data.get("key_points", []),
        ))

    success, result = _safe_call(
        agent.write_chapter,
        request.chapter_key,
        outline,
        request.context,
        request.topic,
    )

    if not success:
        return ApiResponse(success=False, message=result)

    # 更新状态
    _update_state("current_step", 6)
    chapters = _get_state("chapters", [])
    if result.get("chapter"):
        chapters.append(result["chapter"])
        _update_state("chapters", chapters)

    return ApiResponse(
        success=True,
        message=f"章节写作完成: {request.chapter_key}",
        data=result,
    )


# ---- Step 7: 润色投稿 ----

@app.post("/api/step7/polish-submit", response_model=ApiResponse)
async def step7_polish_submit(request: PolishSubmitRequest) -> ApiResponse:
    """
    Step 7: 润色投稿 - 对论文全文进行润色、术语修正、格式验证和查重检测。
    """
    from agents.composer import ComposerAgent

    agent = ComposerAgent()
    journal_name = request.journal_name or _get_state("target_journal", "")

    success, result = _safe_call(
        agent.polish_paper,
        request.paper_text,
        journal_name,
    )

    if not success:
        return ApiResponse(success=False, message=result)

    # 更新状态
    _update_state("current_step", 7)
    _update_state("final_paper", result.get("polished_text", ""))

    submission_ready = result.get("submission_ready", False)
    message = "论文润色完成，可以投稿" if submission_ready else "论文润色完成，但仍有需要修正的问题"

    return ApiResponse(
        success=submission_ready,
        message=message,
        data=result,
    )


# ---- 项目状态查询 ----

@app.get("/api/status", response_model=ApiResponse)
async def get_status() -> ApiResponse:
    """
    获取当前项目的整体状态。
    """
    return ApiResponse(
        success=True,
        message="项目状态查询成功",
        data={
            "current_step": _get_state("current_step", 0),
            "topic": _get_state("topic", ""),
            "title_level": _get_state("title_level", ""),
            "department": _get_state("department", ""),
            "target_journal": _get_state("target_journal", ""),
            "journal_recommendations_count": len(_get_state("journal_recommendations", [])),
            "literature_results_count": len(_get_state("literature_results", [])),
            "research_gaps_count": len(_get_state("research_gaps", [])),
            "outline_sections_count": len(_get_state("outline", [])),
            "chapters_written": len(_get_state("chapters", [])),
            "final_paper_length": len(_get_state("final_paper", "")),
            "step_descriptions": {
                0: "未开始",
                1: "期刊匹配完成",
                2: "文献检索完成",
                3: "大纲评审完成",
                4: "质量门控检查完成",
                5: "模板生成完成",
                6: "章节写作中",
                7: "润色投稿完成",
            },
            "supported_title_levels": config.SUPPORTED_TITLE_LEVELS,
            "supported_departments": config.SUPPORTED_DEPARTMENTS,
            "supported_study_types": config.SUPPORTED_STUDY_TYPES,
            "journals_count": _get_journals_count(),
            "ai_enhanced": bool(config.API_KEY_OPENAI or config.API_KEY_ANTHROPIC),
        },
    )


# ---- 健康检查 ----

@app.get("/api/health")
async def health_check() -> dict:
    """健康检查端点。"""
    return {
        "status": "healthy",
        "service": "医学职称论文写作自动化平台",
        "version": "1.0.0",
        "journals_loaded": _get_journals_count(),
    }


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
