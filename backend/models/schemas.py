"""
Pydantic 数据模型定义 - 定义所有API输入输出的数据结构。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ============================================================
# 期刊推荐相关模型
# ============================================================

class JournalRecommendation(BaseModel):
    """期刊推荐结果"""
    name: str = Field(..., description="期刊名称")
    issn: str = Field(..., description="ISSN号")
    impact_factor: float = Field(..., description="影响因子")
    review_cycle: int = Field(..., description="审稿周期（天）")
    publication_fee: float = Field(..., description="版面费（元）")
    database_tags: list[str] = Field(default_factory=list, description="收录数据库标签")
    match_score: float = Field(..., ge=0, le=100, description="匹配度评分（0-100）")


# ============================================================
# 文献检索相关模型
# ============================================================

class LiteratureGap(BaseModel):
    """研究空白/缺口"""
    gap_description: str = Field(..., description="研究空白描述")
    supporting_papers: list[str] = Field(default_factory=list, description="支持该空白的文献标题")
    evidence_level: str = Field(..., description="证据等级")
    research_direction: str = Field(..., description="建议研究方向")


class LiteratureSearchResult(BaseModel):
    """单条文献检索结果"""
    title: str = Field(..., description="文献标题")
    authors: list[str] = Field(default_factory=list, description="作者列表")
    abstract: str = Field(default="", description="摘要")
    pmid: str = Field(default="", description="PubMed ID")
    year: int = Field(default=0, description="发表年份")
    source: str = Field(default="pubmed", description="来源：pubmed/cnki")


# ============================================================
# 评审评分相关模型
# ============================================================

class ReviewScore(BaseModel):
    """评审评分 - 7个维度评分"""
    clinical_value: int = Field(..., ge=1, le=5, description="临床价值评分（1-5）")
    scientific_rigor: int = Field(..., ge=1, le=5, description="科学性评分（1-5）")
    innovation: int = Field(..., ge=1, le=5, description="创新性评分（1-5）")
    literature_coverage: int = Field(..., ge=1, le=5, description="文献覆盖评分（1-5）")
    statistical_method: int = Field(..., ge=1, le=5, description="统计方法评分（1-5）")
    ethics_compliance: int = Field(..., ge=1, le=5, description="伦理合规评分（1-5）")
    writing_standard: int = Field(..., ge=1, le=5, description="写作规范评分（1-5）")

    @property
    def total_score(self) -> float:
        """计算总分（满分35分）"""
        return float(
            self.clinical_value
            + self.scientific_rigor
            + self.innovation
            + self.literature_coverage
            + self.statistical_method
            + self.ethics_compliance
            + self.writing_standard
        )

    @property
    def average_score(self) -> float:
        """计算平均分（满分5分）"""
        return round(self.total_score / 7, 2)

    def to_dict(self) -> dict[str, int]:
        """转换为字典形式"""
        return {
            "临床价值": self.clinical_value,
            "科学性": self.scientific_rigor,
            "创新性": self.innovation,
            "文献覆盖": self.literature_coverage,
            "统计方法": self.statistical_method,
            "伦理合规": self.ethics_compliance,
            "写作规范": self.writing_standard,
        }


# ============================================================
# 大纲相关模型
# ============================================================

class OutlineSubSection(BaseModel):
    """大纲子章节"""
    title: str = Field(..., description="子章节标题")
    key_points: list[str] = Field(default_factory=list, description="关键要点")


class OutlineSection(BaseModel):
    """大纲章节"""
    title: str = Field(..., description="章节标题")
    subsections: list[OutlineSubSection] = Field(default_factory=list, description="子章节列表")
    word_count_target: int = Field(..., description="目标字数")
    key_points: list[str] = Field(default_factory=list, description="关键要点")


# ============================================================
# 写作相关模型
# ============================================================

class WritingChapter(BaseModel):
    """论文章节"""
    chapter_key: str = Field(..., description="章节标识")
    title: str = Field(..., description="章节标题")
    content: str = Field(default="", description="章节内容")
    word_count: int = Field(default=0, description="实际字数")
    term_check_passed: bool = Field(default=False, description="术语检查是否通过")
    format_check_passed: bool = Field(default=False, description="格式检查是否通过")


# ============================================================
# 查重相关模型
# ============================================================

class PlagiarismMatchedSource(BaseModel):
    """查重匹配来源"""
    source_title: str = Field(..., description="匹配来源标题")
    matched_text: str = Field(default="", description="匹配的文本片段")
    similarity_percent: float = Field(default=0.0, description="与该来源的相似度百分比")


class PlagiarismResult(BaseModel):
    """查重检测结果"""
    similarity_rate: float = Field(..., ge=0, le=100, description="总体相似率（%）")
    matched_sources: list[PlagiarismMatchedSource] = Field(default_factory=list, description="匹配来源列表")
    total_words: int = Field(default=0, description="检测总字数")


# ============================================================
# 质量门控相关模型
# ============================================================

class GateCheckItem(BaseModel):
    """质量门控检查项"""
    name: str = Field(..., description="检查项名称")
    passed: bool = Field(..., description="是否通过")
    description: str = Field(default="", description="检查描述")


class GateResult(BaseModel):
    """质量门控结果"""
    passed: bool = Field(..., description="是否通过质量门控")
    checks: list[GateCheckItem] = Field(default_factory=list, description="检查项列表")
    total_score: float = Field(default=0.0, description="总分")


# ============================================================
# 论文项目模型
# ============================================================

class PaperProject(BaseModel):
    """论文项目 - 贯穿整个写作流程的完整数据结构"""
    topic: str = Field(..., description="研究主题")
    title_level: str = Field(..., description="目标职称级别")
    department: str = Field(..., description="所属学科/科室")
    target_journal: str = Field(default="", description="目标投稿期刊")
    outline: list[OutlineSection] = Field(default_factory=list, description="论文大纲")
    chapters: list[WritingChapter] = Field(default_factory=list, description="各章节内容")
    final_paper: str = Field(default="", description="最终论文全文")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "急性脑卒中静脉溶栓治疗的时间窗优化研究",
                "title_level": "副高级",
                "department": "神经内科",
                "target_journal": "中华神经科杂志",
            }
        }


# ============================================================
# API 请求/响应模型
# ============================================================

class JournalMatchRequest(BaseModel):
    """期刊匹配请求"""
    topic: str = Field(..., description="研究主题")
    title_level: str = Field(..., description="职称级别")
    department: str = Field(..., description="科室")


class LiteratureSearchRequest(BaseModel):
    """文献检索请求"""
    query: str = Field(..., description="检索关键词")
    max_results: int = Field(default=20, ge=1, le=100, description="最大返回数量")


class OutlineEvaluateRequest(BaseModel):
    """大纲评审请求"""
    topic: str = Field(..., description="研究主题")
    outline: list[OutlineSection] = Field(..., description="论文大纲")


class GateCheckRequest(BaseModel):
    """质量门控请求"""
    topic: str = Field(..., description="研究主题")
    scores: dict[str, int] = Field(..., description="7维度评分")


class GenerateTemplateRequest(BaseModel):
    """模板生成请求"""
    journal_name: str = Field(..., description="目标期刊名称")
    topic: str = Field(..., description="研究主题")
    study_type: str = Field(default="RCT", description="研究类型")


class WriteChapterRequest(BaseModel):
    """章节写作请求"""
    chapter_key: str = Field(..., description="章节标识")
    outline: list[OutlineSection] = Field(..., description="论文大纲")
    context: str = Field(default="", description="上下文/已有内容")
    topic: str = Field(..., description="研究主题")


class PolishSubmitRequest(BaseModel):
    """润色投稿请求"""
    paper_text: str = Field(..., description="论文全文")
    journal_name: str = Field(default="", description="目标期刊名称")


class ApiResponse(BaseModel):
    """统一API响应格式"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="", description="响应消息")
    data: dict | list | None = Field(default=None, description="响应数据")


# ============================================================
# 任务调度相关模型
# ============================================================

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskType(str, Enum):
    """任务类型枚举"""
    ONCE = "once"
    CRON = "cron"


class TaskDefinition(BaseModel):
    """任务定义 - 创建任务时的输入"""
    name: str = Field(..., description="任务名称")
    task_type: TaskType = Field(default=TaskType.ONCE, description="任务类型：once/cron")
    cron_expression: str = Field(default="", description="cron表达式（cron类型必填）")
    run_at: str = Field(default="", description="一次性任务的执行时间（ISO格式，如 2026-07-25T10:00:00）")
    target_endpoint: str = Field(..., description="目标API端点路径，如 /api/step1/journal-match")
    payload: dict = Field(default_factory=dict, description="任务执行时的请求体")
    description: str = Field(default="", description="任务描述")


class TaskRecord(BaseModel):
    """任务记录 - 任务的完整信息"""
    task_id: str = Field(..., description="任务ID")
    name: str = Field(..., description="任务名称")
    task_type: TaskType = Field(..., description="任务类型")
    cron_expression: str = Field(default="", description="cron表达式")
    run_at: str = Field(default="", description="计划执行时间")
    target_endpoint: str = Field(..., description="目标API端点")
    payload: dict = Field(default_factory=dict, description="请求体")
    description: str = Field(default="", description="任务描述")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    last_run_at: str = Field(default="", description="上次执行时间")
    next_run_at: str = Field(default="", description="下次执行时间")
    run_count: int = Field(default=0, description="执行次数")
    last_result: dict | None = Field(default=None, description="上次执行结果")
    last_error: str = Field(default="", description="上次错误信息")


class TaskUpdateRequest(BaseModel):
    """任务更新请求"""
    name: str | None = Field(default=None, description="任务名称")
    cron_expression: str | None = Field(default=None, description="cron表达式")
    run_at: str | None = Field(default=None, description="执行时间")
    target_endpoint: str | None = Field(default=None, description="目标端点")
    payload: dict | None = Field(default=None, description="请求体")
    description: str | None = Field(default=None, description="任务描述")


# ============================================================
# 会话/对话相关模型
# ============================================================

class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色：user/assistant")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(default="", description="时间戳")
    metadata: dict = Field(default_factory=dict, description="元数据")


class ChatSession(BaseModel):
    """聊天会话"""
    session_id: str = Field(..., description="会话ID")
    title: str = Field(default="新对话", description="会话标题")
    messages: list[ChatMessage] = Field(default_factory=list, description="消息列表")
    created_at: str = Field(default="", description="创建时间")
    updated_at: str = Field(default="", description="更新时间")
    project_data: dict = Field(default_factory=dict, description="项目相关数据")


class ChatRequest(BaseModel):
    """聊天请求"""
    session_id: str = Field(default="", description="会话ID（新建则为空）")
    message: str = Field(..., description="用户消息")
    stream: bool = Field(default=False, description="是否流式响应")


class ChatResponse(BaseModel):
    """聊天响应"""
    session_id: str = Field(..., description="会话ID")
    message: str = Field(..., description="助手回复")
    steps: list[dict] = Field(default_factory=list, description="执行步骤")
    literature: list[dict] = Field(default_factory=list, description="文献结果")
    metadata: dict = Field(default_factory=dict, description="元数据")
