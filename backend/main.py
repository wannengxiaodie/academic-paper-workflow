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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import config
from models.schemas import (
    ApiResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatSession,
    GateCheckRequest,
    GenerateTemplateRequest,
    JournalMatchRequest,
    LiteratureSearchRequest,
    OutlineEvaluateRequest,
    PolishSubmitRequest,
    TaskDefinition,
    TaskStatus,
    TaskUpdateRequest,
    WriteChapterRequest,
)
import uuid
from datetime import datetime

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

# 会话存储（内存存储，生产环境应使用数据库）
_sessions: dict[str, ChatSession] = {}


def _update_state(key: str, value: object) -> None:
    """更新项目状态。"""
    _project_state[key] = value


def _get_state(key: str, default=None):
    """获取项目状态。"""
    return _project_state.get(key, default)


def _get_or_create_session(session_id: str = "") -> ChatSession:
    """获取或创建会话。"""
    now = datetime.now().isoformat()
    if session_id and session_id in _sessions:
        session = _sessions[session_id]
        session.updated_at = now
        return session
    
    new_id = session_id or str(uuid.uuid4())
    session = ChatSession(
        session_id=new_id,
        title="新对话",
        created_at=now,
        updated_at=now,
    )
    _sessions[new_id] = session
    return session


def _add_message(session: ChatSession, role: str, content: str, metadata: dict = None) -> None:
    """向会话添加消息。"""
    message = ChatMessage(
        role=role,
        content=content,
        timestamp=datetime.now().isoformat(),
        metadata=metadata or {},
    )
    session.messages.append(message)
    session.updated_at = datetime.now().isoformat()
    
    if role == "user" and session.title == "新对话" and content:
        session.title = content[:20] + ("..." if len(content) > 20 else "")


# ============================================================
# FastAPI 应用初始化
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    logger.info("医学职称论文写作自动化平台启动中...")
    logger.info(f"期刊数据库: {_get_journals_count()} 本期刊")
    logger.info(f"AI增强模式: {'已启用' if (config.API_KEY_OPENAI or config.API_KEY_ANTHROPIC) else '未启用'}")

    from services.task_scheduler import set_base_url, start_scheduler, stop_scheduler
    set_base_url("http://localhost:8000")
    start_scheduler()
    logger.info("任务调度器已启动")

    logger.info("服务就绪")
    yield
    stop_scheduler()
    logger.info("任务调度器已停止")
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

# 静态文件服务 - 前端页面
_PAGES_DIR = Path(__file__).resolve().parent.parent / "pages"
if _PAGES_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_PAGES_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(str(_PAGES_DIR / "index.html"))


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
        "version": "2.0.0",
        "journals_loaded": _get_journals_count(),
    }


# ============================================================
# 对话式聊天 API（Agent 架构）
# ============================================================

@app.post("/api/chat", response_model=ApiResponse)
async def chat_endpoint(request: ChatRequest) -> ApiResponse:
    """
    对话式聊天接口 - 基于 Agent 架构的智能交互。
    
    支持自然语言交互，自动识别用户意图并执行相应任务：
    - 文献检索
    - 大纲生成
    - 章节写作
    - 润色投稿
    """
    from agents.strategist import StrategistAgent
    from agents.composer import ComposerAgent
    
    session = _get_or_create_session(request.session_id)
    _add_message(session, "user", request.message)
    
    user_msg = request.message.strip()
    steps = []
    literature = []
    response_text = ""
    
    try:
        # 步骤1：理解需求
        steps.append({"label": "理解需求", "status": "done"})
        
        # 步骤2：根据意图执行任务
        if _is_literature_search_request(user_msg):
            # 文献检索
            steps.append({"label": "文献检索", "status": "active"})
            
            agent = StrategistAgent()
            result = agent.review_literature(user_msg, max_results=10)
            
            literature = result.get("pubmed_results", [])
            research_gaps = result.get("research_gaps", [])
            
            steps.append({"label": "文献检索", "status": "done"})
            steps.append({"label": "分析整理", "status": "active"})
            
            response_text = _build_literature_response(user_msg, literature, research_gaps)
            session.project_data["last_search"] = result
            
        elif _is_outline_request(user_msg):
            # 大纲生成
            steps.append({"label": "大纲生成", "status": "active"})
            
            agent = ComposerAgent()
            topic = _extract_topic(user_msg)
            result = agent.generate_template(
                journal_name="中华医学杂志",
                topic=topic,
                study_type="临床试验",
                title_level="副高级",
            )
            
            steps.append({"label": "大纲生成", "status": "done"})
            steps.append({"label": "整理输出", "status": "active"})
            
            response_text = _build_outline_response(topic, result)
            session.project_data["outline"] = result
            
        elif _is_writing_request(user_msg):
            # 论文写作
            steps.append({"label": "内容生成", "status": "active"})
            
            response_text = _build_writing_response(user_msg)
            
        elif _is_polish_request(user_msg):
            # 润色投稿
            steps.append({"label": "润色检查", "status": "active"})
            
            response_text = _build_polish_response(user_msg)
            
        else:
            # 通用对话
            steps.append({"label": "分析回答", "status": "active"})
            response_text = _build_general_response(user_msg)
        
        steps.append({"label": "生成结果", "status": "done"})
        
        # 更新会话
        _add_message(session, "assistant", response_text, {
            "steps": steps,
            "literature_count": len(literature),
        })
        
        return ApiResponse(
            success=True,
            message="对话完成",
            data={
                "session_id": session.session_id,
                "title": session.title,
                "message": response_text,
                "steps": steps,
                "literature": literature,
            },
        )
        
    except Exception as e:
        logger.error(f"对话处理失败: {e}")
        error_msg = f"抱歉，处理您的请求时出现了错误：{str(e)}"
        _add_message(session, "assistant", error_msg)
        return ApiResponse(
            success=False,
            message=error_msg,
            data={
                "session_id": session.session_id,
            },
        )


@app.get("/api/sessions", response_model=ApiResponse)
async def list_sessions() -> ApiResponse:
    """获取会话列表。"""
    sessions_list = sorted(
        _sessions.values(),
        key=lambda s: s.updated_at,
        reverse=True,
    )
    return ApiResponse(
        success=True,
        message=f"共 {len(sessions_list)} 个会话",
        data={
            "sessions": [
                {
                    "session_id": s.session_id,
                    "title": s.title,
                    "updated_at": s.updated_at,
                    "message_count": len(s.messages),
                }
                for s in sessions_list
            ],
        },
    )


@app.get("/api/sessions/{session_id}", response_model=ApiResponse)
async def get_session(session_id: str) -> ApiResponse:
    """获取单个会话详情。"""
    session = _sessions.get(session_id)
    if not session:
        return ApiResponse(success=False, message="会话不存在")
    return ApiResponse(
        success=True,
        message="查询成功",
        data=session.model_dump(),
    )


@app.delete("/api/sessions/{session_id}", response_model=ApiResponse)
async def delete_session(session_id: str) -> ApiResponse:
    """删除会话。"""
    if session_id in _sessions:
        del _sessions[session_id]
        return ApiResponse(success=True, message="会话已删除")
    return ApiResponse(success=False, message="会话不存在")


def _is_literature_search_request(msg: str) -> bool:
    """判断是否为文献检索请求。"""
    keywords = ["检索", "搜索", "文献", "研究进展", "综述", "找一下", "查一下",
                "literature", "search", "paper", "研究", "最新"]
    return any(kw in msg for kw in keywords)


def _is_outline_request(msg: str) -> bool:
    """判断是否为大纲生成请求。"""
    keywords = ["大纲", "提纲", "结构", "目录", "框架", "outline", "生成论文"]
    return any(kw in msg for kw in keywords) and not _is_writing_request(msg)


def _is_writing_request(msg: str) -> bool:
    """判断是否为论文写作请求。"""
    keywords = ["写一篇", "写作", "生成论文", "撰写", "帮我写", "写论文",
                "字左右", "字的论文", "完整论文"]
    return any(kw in msg for kw in keywords)


def _is_polish_request(msg: str) -> bool:
    """判断是否为润色投稿请求。"""
    keywords = ["润色", "修改", "检查", "投稿", "格式", "polish", "proofread"]
    return any(kw in msg for kw in keywords)


def _extract_topic(msg: str) -> str:
    """从用户消息中提取研究主题。"""
    import re
    patterns = [
        r"关于[「\"'](.+?)[」\"']",
        r"「(.+?)」",
        r"['\"](.+?)['\"]",
        r"(?:主题|题目|研究)(?:是|为)?(.+?)(?:的|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, msg)
        if match:
            return match.group(1).strip()
    
    cleaned = re.sub(r"^(帮我|请|给我|生成|写|检索|搜索|查一下|找一下)", "", msg)
    cleaned = re.sub(r"(的大纲|的论文|的文献|的研究进展|的最新进展)$", "", cleaned)
    cleaned = re.sub(r"\d+字左右", "", cleaned)
    return cleaned.strip() or "医学研究"


def _build_literature_response(query: str, papers: list, gaps: list) -> str:
    """构建文献检索响应。"""
    response = f"根据您的研究主题「{query}」，我已完成文献检索和分析。\n\n"
    
    response += f"**📚 检索结果概览**\n"
    response += f"共检索到 {len(papers)} 篇相关文献，识别到 {len(gaps)} 个潜在研究空白。\n\n"
    
    if gaps:
        response += f"**💡 研究空白识别**\n"
        for i, gap in enumerate(gaps[:3], 1):
            desc = gap.get("gap_description", gap.get("description", "研究空白"))
            direction = gap.get("research_direction", "")
            response += f"{i}. {desc}\n"
            if direction:
                response += f"   建议方向：{direction}\n"
            response += "\n"
    
    response += "**🔬 下一步建议**\n"
    response += "1. 查看下方文献详情，了解当前研究现状\n"
    response += "2. 基于研究空白确定您的创新点\n"
    response += "3. 需要我帮您生成论文大纲吗？直接告诉我即可\n"
    
    return response


def _build_outline_response(topic: str, result: dict) -> str:
    """构建大纲生成响应。"""
    outline = result.get("outline", [])
    total_words = result.get("total_word_target", 0)
    
    response = f"已为您生成关于「{topic}」的论文大纲。\n\n"
    response += f"**📋 大纲概览**\n"
    response += f"共 {len(outline)} 个章节，目标字数约 {total_words} 字。\n\n"
    
    response += "**📑 论文章节结构**\n"
    for i, section in enumerate(outline, 1):
        title = section.get("title", f"第{i}章")
        word_count = section.get("word_count_target", 0)
        response += f"{i}. **{title}**（约 {word_count} 字）\n"
        
        subsections = section.get("subsections", [])
        for j, sub in enumerate(subsections, 1):
            sub_title = sub.get("title", "")
            if sub_title:
                response += f"   {i}.{j} {sub_title}\n"
        response += "\n"
    
    response += "**✍️ 下一步**\n"
    response += "- 需要我开始撰写某个章节吗？请告诉我章节名称\n"
    response += "- 或者直接说「开始写作」，我将按顺序完成全文\n"
    
    return response


def _build_writing_response(msg: str) -> str:
    """构建写作响应。"""
    return (
        f"好的，我将为您撰写论文。\n\n"
        f"**📝 写作说明**\n"
        f"由于当前为演示模式，我将为您生成模板化的论文框架。"
        f"如需 AI 生成高质量内容，请配置 API 密钥。\n\n"
        f"**📋 论文结构**\n"
        f"1. 摘要（约300字）\n"
        f"2. 引言（约800字）\n"
        f"3. 资料与方法（约1200字）\n"
        f"4. 结果（约1000字）\n"
        f"5. 讨论（约1000字）\n"
        f"6. 结论（约300字）\n\n"
        f"**💡 提示**\n"
        f"您可以说「写摘要」或「写引言」来生成特定章节，"
        f"或者说「继续」来按顺序写作。"
    )


def _build_polish_response(msg: str) -> str:
    """构建润色响应。"""
    return (
        f"好的，我可以帮您润色论文。\n\n"
        f"**✨ 润色服务包括**\n"
        f"- 语言润色：优化表达、修正语法\n"
        f"- 术语规范：统一医学术语使用\n"
        f"- 格式检查：核对期刊投稿格式要求\n"
        f"- 查重检测：初步相似度检测\n\n"
        f"**📋 使用方法**\n"
        f"请将您的论文内容粘贴到对话框中，"
        f"我会为您进行全面的润色和检查。\n\n"
        f"**💡 提示**\n"
        f"如果您有目标期刊，也请告诉我，我会按照该期刊的要求进行格式调整。"
    )


def _build_general_response(msg: str) -> str:
    """构建通用响应。"""
    return (
        f"您好！我是 MedPaper AI，您的医学论文写作助手。\n\n"
        f"我可以帮您完成以下任务：\n\n"
        f"🔬 **文献检索** - 检索 PubMed、OpenAlex 等数据库的最新文献\n"
        f"📋 **大纲生成** - 根据研究主题智能生成论文结构\n"
        f"✍️ **论文写作** - 自动生成完整的医学论文内容\n"
        f"✨ **润色投稿** - 论文润色、术语修正、格式检查\n\n"
        f"您可以直接告诉我您的需求，例如：\n"
        f"- 「帮我检索一下糖尿病治疗的最新进展」\n"
        f"- 「生成一篇关于肺癌靶向治疗的论文大纲」\n"
        f"- 「写一篇3000字的高血压综述」\n\n"
        f"请问有什么我可以帮您的吗？"
    )


# ============================================================
# 任务调度 API
# ============================================================

@app.post("/api/tasks", response_model=ApiResponse)
async def create_task_endpoint(request: TaskDefinition) -> ApiResponse:
    """创建定时任务。"""
    from services.task_scheduler import create_scheduled_task

    if request.task_type.value == "cron" and not request.cron_expression:
        return ApiResponse(success=False, message="cron类型任务必须提供cron表达式")
    if request.task_type.value == "once" and not request.run_at:
        return ApiResponse(success=False, message="一次性任务必须提供执行时间run_at")

    try:
        task = create_scheduled_task(request)
        return ApiResponse(
            success=True,
            message=f"任务创建成功: {task.name}",
            data={"task": task.model_dump()},
        )
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        return ApiResponse(success=False, message=f"创建任务失败: {str(e)}")


@app.get("/api/tasks", response_model=ApiResponse)
async def list_tasks_endpoint(status: str | None = None) -> ApiResponse:
    """获取任务列表，可按状态筛选。"""
    from data.task_store import list_tasks

    status_enum = None
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            return ApiResponse(success=False, message=f"无效的任务状态: {status}")

    tasks = list_tasks(status_enum)
    return ApiResponse(
        success=True,
        message=f"查询到 {len(tasks)} 个任务",
        data={"tasks": [t.model_dump() for t in tasks]},
    )


@app.get("/api/tasks/{task_id}", response_model=ApiResponse)
async def get_task_endpoint(task_id: str) -> ApiResponse:
    """获取单个任务详情。"""
    from data.task_store import get_task

    task = get_task(task_id)
    if not task:
        return ApiResponse(success=False, message=f"任务不存在: {task_id}")
    return ApiResponse(success=True, message="查询成功", data={"task": task.model_dump()})


@app.put("/api/tasks/{task_id}", response_model=ApiResponse)
async def update_task_endpoint(task_id: str, request: TaskUpdateRequest) -> ApiResponse:
    """更新任务配置。"""
    from data.task_store import get_task, update_task
    from services.task_scheduler import _schedule_next_cron_run

    task = get_task(task_id)
    if not task:
        return ApiResponse(success=False, message=f"任务不存在: {task_id}")

    update_data = request.model_dump(exclude_none=True)
    if not update_data:
        return ApiResponse(success=False, message="没有提供要更新的字段")

    updated = update_task(task_id, **update_data)

    if updated and updated.task_type.value == "cron" and "cron_expression" in update_data:
        _schedule_next_cron_run(task_id)

    return ApiResponse(
        success=True,
        message="任务更新成功",
        data={"task": updated.model_dump() if updated else None},
    )


@app.delete("/api/tasks/{task_id}", response_model=ApiResponse)
async def delete_task_endpoint(task_id: str) -> ApiResponse:
    """删除任务。"""
    from services.task_scheduler import remove_task

    success = remove_task(task_id)
    if not success:
        return ApiResponse(success=False, message=f"任务不存在: {task_id}")
    return ApiResponse(success=True, message="任务删除成功")


@app.post("/api/tasks/{task_id}/trigger", response_model=ApiResponse)
async def trigger_task_endpoint(task_id: str) -> ApiResponse:
    """立即触发任务执行。"""
    from services.task_scheduler import trigger_task

    task = trigger_task(task_id)
    if not task:
        return ApiResponse(success=False, message=f"任务不存在: {task_id}")
    return ApiResponse(success=True, message=f"任务已触发: {task.name}")


@app.post("/api/tasks/{task_id}/pause", response_model=ApiResponse)
async def pause_task_endpoint(task_id: str) -> ApiResponse:
    """暂停任务。"""
    from services.task_scheduler import pause_task

    task = pause_task(task_id)
    if not task:
        return ApiResponse(success=False, message=f"任务不存在: {task_id}")
    return ApiResponse(
        success=True,
        message=f"任务已暂停: {task.name}",
        data={"task": task.model_dump()},
    )


@app.post("/api/tasks/{task_id}/resume", response_model=ApiResponse)
async def resume_task_endpoint(task_id: str) -> ApiResponse:
    """恢复任务。"""
    from services.task_scheduler import resume_task

    task = resume_task(task_id)
    if not task:
        return ApiResponse(success=False, message=f"任务不存在: {task_id}")
    return ApiResponse(
        success=True,
        message=f"任务已恢复: {task.name}",
        data={"task": task.model_dump()},
    )


@app.get("/api/scheduler/status", response_model=ApiResponse)
async def scheduler_status_endpoint() -> ApiResponse:
    """获取调度器状态。"""
    from services.task_scheduler import get_scheduler_status

    status = get_scheduler_status()
    return ApiResponse(success=True, message="调度器状态查询成功", data=status)


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
