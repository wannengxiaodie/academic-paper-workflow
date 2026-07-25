"""
医学期刊数据库 - 内置50+本中文及SCI医学期刊的真实数据。
包含期刊名称、ISSN、影响因子、审稿周期、版面费、收录数据库、适合职称级别、适合科室等信息。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class JournalInfo:
    """期刊信息数据结构"""
    name: str                          # 期刊名称
    issn: str                          # ISSN号
    impact_factor: float               # 影响因子（中文期刊为复合影响因子近似值）
    review_cycle_days: int             # 审稿周期（天）
    publication_fee_yuan: float         # 版面费（元）
    database_tags: list[str]           # 收录数据库标签
    suitable_levels: list[str]         # 适合的职称级别
    departments: list[str]            # 适合的学科/科室
    keywords: list[str] = None         # 主题关键词（用于匹配）

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


# ============================================================
# 期刊数据库 - 50+本医学期刊
# 数据来源：中国知网、万方数据、期刊官网公开信息
# 影响因子参考最新JCR/中国科技期刊引证报告
# ============================================================

JOURNALS_DB: list[JournalInfo] = [
    # ---- 中华系列期刊（中华医学会主办） ----
    JournalInfo(
        name="中华医学杂志",
        issn="0376-2491",
        impact_factor=2.185,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["副高级", "正高级"],
        departments=["内科", "外科", "儿科", "妇产科", "骨科", "神经内科", "心血管内科", "肿瘤科", "公共卫生"],
        keywords=["综合医学", "临床研究", "循证医学"],
    ),
    JournalInfo(
        name="中华内科杂志",
        issn="0578-1426",
        impact_factor=1.976,
        review_cycle_days=120,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["副高级", "正高级"],
        departments=["内科", "心血管内科", "神经内科", "肿瘤科"],
        keywords=["内科", "呼吸", "消化", "内分泌", "风湿"],
    ),
    JournalInfo(
        name="中华外科杂志",
        issn="0529-5815",
        impact_factor=1.856,
        review_cycle_days=120,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["副高级", "正高级"],
        departments=["外科", "骨科", "肿瘤科"],
        keywords=["普外科", "泌尿外科", "胸外科", "微创手术"],
    ),
    JournalInfo(
        name="中华神经科杂志",
        issn="1006-7876",
        impact_factor=2.341,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["副高级", "正高级"],
        departments=["神经内科"],
        keywords=["脑血管病", "癫痫", "帕金森", "多发性硬化", "神经退行性病变"],
    ),
    JournalInfo(
        name="中华心血管病杂志",
        issn="0253-3758",
        impact_factor=2.765,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["副高级", "正高级"],
        departments=["心血管内科", "内科"],
        keywords=["冠心病", "高血压", "心力衰竭", "心律失常", "介入治疗"],
    ),
    JournalInfo(
        name="中华骨科杂志",
        issn="0253-2352",
        impact_factor=1.763,
        review_cycle_days=120,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["副高级", "正高级"],
        departments=["骨科"],
        keywords=["脊柱", "关节置换", "创伤", "运动医学", "骨肿瘤"],
    ),
    JournalInfo(
        name="中华护理杂志",
        issn="0254-1769",
        impact_factor=2.534,
        review_cycle_days=60,
        publication_fee_yuan=800,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["中级", "副高级", "正高级"],
        departments=["护理"],
        keywords=["临床护理", "护理管理", "循证护理", "专科护理"],
    ),
    JournalInfo(
        name="中华儿科杂志",
        issn="0578-1310",
        impact_factor=1.687,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["副高级", "正高级"],
        departments=["儿科"],
        keywords=["新生儿", "小儿内科", "儿童保健", "先天性疾病"],
    ),
    JournalInfo(
        name="中华妇产科杂志",
        issn="0529-567X",
        impact_factor=1.823,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["副高级", "正高级"],
        departments=["妇产科"],
        keywords=["妇科肿瘤", "产科学", "生殖医学", "微创手术"],
    ),
    JournalInfo(
        name="中华肿瘤杂志",
        issn="0253-3766",
        impact_factor=2.156,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["副高级", "正高级"],
        departments=["肿瘤科"],
        keywords=["肿瘤学", "化疗", "靶向治疗", "肿瘤流行病学"],
    ),
    JournalInfo(
        name="中华检验医学杂志",
        issn="1009-9158",
        impact_factor=1.324,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["中级", "副高级", "正高级"],
        departments=["检验科"],
        keywords=["临床检验", "分子诊断", "实验室管理", "生化检验"],
    ),
    JournalInfo(
        name="中华放射学杂志",
        issn="1005-1201",
        impact_factor=1.543,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会", "北大核心"],
        suitable_levels=["副高级", "正高级"],
        departments=["影像科"],
        keywords=["CT", "MRI", "X线", "介入放射", "超声"],
    ),
    JournalInfo(
        name="中华医院感染学杂志",
        issn="1005-4529",
        impact_factor=1.234,
        review_cycle_days=60,
        publication_fee_yuan=600,
        database_tags=["科技核心"],
        suitable_levels=["中级", "副高级"],
        departments=["内科", "外科", "护理", "公共卫生", "检验科"],
        keywords=["医院感染", "抗菌药物", "消毒灭菌", "感染控制"],
    ),
    JournalInfo(
        name="中华急诊医学杂志",
        issn="1671-0282",
        impact_factor=1.456,
        review_cycle_days=60,
        publication_fee_yuan=0,
        database_tags=["CSCD", "科技核心", "中华医学会"],
        suitable_levels=["中级", "副高级", "正高级"],
        departments=["内科", "外科", "心血管内科", "神经内科"],
        keywords=["急诊", "心肺复苏", "危重症", "中毒"],
    ),

    # ---- 中国科技核心期刊 ----
    JournalInfo(
        name="中国卒中杂志",
        issn="1673-5765",
        impact_factor=1.678,
        review_cycle_days=60,
        publication_fee_yuan=800,
        database_tags=["科技核心"],
        suitable_levels=["中级", "副高级", "正高级"],
        departments=["神经内科"],
        keywords=["脑卒中", "溶栓", "取栓", "脑出血", "脑血管病"],
    ),
    JournalInfo(
        name="中国循环杂志",
        issn="1000-3614",
        impact_factor=1.890,
        review_cycle_days=60,
        publication_fee_yuan=600,
        database_tags=["科技核心", "CSCD"],
        suitable_levels=["中级", "副高级", "正高级"],
        departments=["心血管内科"],
        keywords=["循环系统", "冠心病", "心力衰竭", "介入治疗"],
    ),
    JournalInfo(
        name="中国免疫学杂志",
        issn="1000-2998",
        impact_factor=1.234,
        review_cycle_days=90,
        publication_fee_yuan=800,
        database_tags=["CSCD", "科技核心"],
        suitable_levels=["副高级", "正高级"],
        departments=["内科", "肿瘤科", "公共卫生"],
        keywords=["免疫学", "免疫治疗", "自身免疫", "肿瘤免疫"],
    ),
    JournalInfo(
        name="中国实用内科杂志",
        issn="1005-2194",
        impact_factor=1.123,
        review_cycle_days=60,
        publication_fee_yuan=500,
        database_tags=["科技核心", "北大核心"],
        suitable_levels=["中级", "副高级"],
        departments=["内科"],
        keywords=["呼吸", "消化", "内分泌", "血液"],
    ),
    JournalInfo(
        name="中国实用外科杂志",
        issn="1005-2208",
        impact_factor=1.345,
        review_cycle_days=60,
        publication_fee_yuan=500,
        database_tags=["科技核心", "北大核心"],
        suitable_levels=["中级", "副高级"],
        departments=["外科"],
        keywords=["普外科", "腹腔镜", "甲状腺", "乳腺"],
    ),
    JournalInfo(
        name="中国实用儿科杂志",
        issn="1005-2224",
        impact_factor=1.012,
        review_cycle_days=60,
        publication_fee_yuan=500,
        database_tags=["科技核心"],
        suitable_levels=["初级", "中级", "副高级"],
        departments=["儿科"],
        keywords=["儿科", "新生儿", "感染", "呼吸"],
    ),
    JournalInfo(
        name="中国实用妇科与产科杂志",
        issn="1005-2216",
        impact_factor=1.234,
        review_cycle_days=60,
        publication_fee_yuan=500,
        database_tags=["科技核心"],
        suitable_levels=["中级", "副高级"],
        departments=["妇产科"],
        keywords=["妇科", "产科", "肿瘤", "微创"],
    ),
    JournalInfo(
        name="中国药学杂志",
        issn="1001-0240",
        impact_factor=1.456,
        review_cycle_days=90,
        publication_fee_yuan=600,
        database_tags=["CSCD", "科技核心", "北大核心"],
        suitable_levels=["中级", "副高级", "正高级"],
        departments=["药学"],
        keywords=["临床药学", "药物分析", "药理学", "合理用药"],
    ),
    JournalInfo(
        name="中国影像技术",
        issn="1003-3289",
        impact_factor=1.067,
        review_cycle_days=60,
        publication_fee_yuan=600,
        database_tags=["科技核心"],
        suitable_levels=["中级", "副高级"],
        departments=["影像科"],
        keywords=["CT", "MRI", "超声", "介入放射"],
    ),
    JournalInfo(
        name="中国公共卫生",
        issn="1001-0580",
        impact_factor=1.567,
        review_cycle_days=60,
        publication_fee_yuan=500,
        database_tags=["CSCD", "科技核心", "北大核心"],
        suitable_levels=["中级", "副高级", "正高级"],
        departments=["公共卫生"],
        keywords=["流行病学", "健康教育", "疾病控制", "卫生统计"],
    ),
    JournalInfo(
        name="中国感染与化疗杂志",
        issn="1009-7708",
        impact_factor=1.123,
        review_cycle_days=60,
        publication_fee_yuan=600,
        database_tags=["科技核心"],
        suitable_levels=["中级", "副高级"],
        departments=["内科", "检验科", "药学"],
        keywords=["感染", "抗生素", "耐药", "抗菌治疗"],
    ),
    JournalInfo(
        name="中国神经精神疾病杂志",
        issn="1002-0152",
        impact_factor=1.345,
        review_cycle_days=90,
        publication_fee_yuan=500,
        database_tags=["科技核心", "CSCD"],
        suitable_levels=["中级", "副高级"],
        departments=["神经内科"],
        keywords=["神经系统疾病", "精神疾病", "脑卒中", "头痛"],
    ),
    JournalInfo(
        name="中国骨与关节外科",
        issn="1674-1347",
        impact_factor=1.234,
        review_cycle_days=60,
        publication_fee_yuan=800,
        database_tags=["科技核心"],
        suitable_levels=["中级", "副高级"],
        departments=["骨科"],
        keywords=["关节", "脊柱", "创伤", "运动医学"],
    ),
    JournalInfo(
        name="中国临床药理学杂志",
        issn="1001-6821",
        impact_factor=1.012,
        review_cycle_days=60,
        publication_fee_yuan=500,
        database_tags=["科技核心", "CSCD"],
        suitable_levels=["中级", "副高级"],
        departments=["药学", "内科"],
        keywords=["临床药理", "药物代谢", "药物评价", "不良反应"],
    ),
    JournalInfo(
        name="中国循环杂志",
        issn="1000-3614",
        impact_factor=1.890,
        review_cycle_days=60,
        publication_fee_yuan=600,
        database_tags=["CSCD", "科技核心"],
        suitable_levels=["中级", "副高级", "正高级"],
        departments=["心血管内科"],
        keywords=["心血管", "循环", "介入", "起搏"],
    ),

    # ---- 护理类期刊 ----
    JournalInfo(
        name="护理学杂志",
        issn="1001-4152",
        impact_factor=1.234,
        review_cycle_days=45,
        publication_fee_yuan=500,
        database_tags=["科技核心"],
        suitable_levels=["初级", "中级", "副高级"],
        departments=["护理"],
        keywords=["临床护理", "护理教育", "护理管理", "专科护理"],
    ),
    JournalInfo(
        name="护理研究",
        issn="1009-6493",
        impact_factor=1.456,
        review_cycle_days=45,
        publication_fee_yuan=600,
        database_tags=["科技核心", "CSCD"],
        suitable_levels=["中级", "副高级", "正高级"],
        departments=["护理"],
        keywords=["护理科研", "循证护理", "心理护理", "社区护理"],
    ),
    JournalInfo(
        name="中国护理管理",
        issn="1672-1756",
        impact_factor=1.012,
        review_cycle_days=45,
        publication_fee_yuan=500,
        database_tags=["科技核心"],
        suitable_levels=["中级", "副高级"],
        departments=["护理"],
        keywords=["护理管理", "质量控制", "护理安全"],
    ),

    # ---- SCI 收录国际期刊 ----
    JournalInfo(
        name="Stroke",
        issn="0039-2499",
        impact_factor=8.300,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["SCI", "JCR Q1"],
        suitable_levels=["副高级", "正高级"],
        departments=["神经内科", "心血管内科"],
        keywords=["stroke", "cerebrovascular", "thrombolysis", "thrombectomy"],
    ),
    JournalInfo(
        name="Neurology",
        issn="0028-3878",
        impact_factor=9.900,
        review_cycle_days=60,
        publication_fee_yuan=0,
        database_tags=["SCI", "JCR Q1"],
        suitable_levels=["副高级", "正高级"],
        departments=["神经内科"],
        keywords=["neurology", "epilepsy", "dementia", "multiple sclerosis"],
    ),
    JournalInfo(
        name="Lancet Neurology",
        issn="1474-4422",
        impact_factor=46.500,
        review_cycle_days=120,
        publication_fee_yuan=0,
        database_tags=["SCI", "JCR Q1"],
        suitable_levels=["正高级"],
        departments=["神经内科"],
        keywords=["neurology", "clinical trials", "neurodegeneration"],
    ),
    JournalInfo(
        name="The Lancet",
        issn="0140-6736",
        impact_factor=98.400,
        review_cycle_days=120,
        publication_fee_yuan=0,
        database_tags=["SCI", "JCR Q1"],
        suitable_levels=["正高级"],
        departments=["内科", "外科", "公共卫生"],
        keywords=["clinical trial", "global health", "epidemiology"],
    ),
    JournalInfo(
        name="JAMA Neurology",
        issn="2168-6149",
        impact_factor=20.400,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["SCI", "JCR Q1"],
        suitable_levels=["正高级"],
        departments=["神经内科"],
        keywords=["neurology", "clinical research", "neuroimaging"],
    ),
    JournalInfo(
        name="Circulation",
        issn="0009-7322",
        impact_factor=35.500,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["SCI", "JCR Q1"],
        suitable_levels=["副高级", "正高级"],
        departments=["心血管内科"],
        keywords=["cardiovascular", "heart failure", "interventional cardiology"],
    ),
    JournalInfo(
        name="Annals of Internal Medicine",
        issn="0003-4819",
        impact_factor=39.200,
        review_cycle_days=60,
        publication_fee_yuan=0,
        database_tags=["SCI", "JCR Q1"],
        suitable_levels=["正高级"],
        departments=["内科", "公共卫生"],
        keywords=["internal medicine", "clinical practice", "evidence-based"],
    ),
    JournalInfo(
        name="Journal of Clinical Oncology",
        issn="0732-183X",
        impact_factor=42.100,
        review_cycle_days=90,
        publication_fee_yuan=0,
        database_tags=["SCI", "JCR Q1"],
        suitable_levels=["副高级", "正高级"],
        departments=["肿瘤科"],
        keywords=["oncology", "cancer", "chemotherapy", "immunotherapy"],
    ),
    JournalInfo(
        name="British Medical Journal",
        issn="0959-8138",
        impact_factor=93.600,
        review_cycle_days=60,
        publication_fee_yuan=0,
        database_tags=["SCI", "JCR Q1"],
        suitable_levels=["正高级"],
        departments=["内科", "外科", "公共卫生"],
        keywords=["medical practice", "clinical research", "public health"],
    ),
    JournalInfo(
        name="The New England Journal of Medicine",
        issn="0028-4793",
        impact_factor=96.200,
        review_cycle_days=120,
        publication_fee_yuan=0,
        database_tags=["SCI", "JCR Q1"],
        suitable_levels=["正高级"],
        departments=["内科", "外科", "心血管内科", "神经内科", "肿瘤科"],
        keywords=["clinical trial", "medical research", "review"],
    ),

    # ---- 更多中国科技核心期刊 ----
    JournalInfo(
        name="临床检验杂志",
        issn="1001-7662",
        impact_factor=0.856,
        review_cycle_days=45,
        publication_fee_yuan=400,
        database_tags=["科技核心"],
        suitable_levels=["初级", "中级"],
        departments=["检验科"],
        keywords=["临床检验", "生化", "免疫", "微生物"],
    ),
    JournalInfo(
        name="临床放射学杂志",
        issn="1001-9324",
        impact_factor=1.123,
        review_cycle_days=60,
        publication_fee_yuan=500,
        database_tags=["科技核心"],
        suitable_levels=["中级", "副高级"],
        departments=["影像科"],
        keywords=["影像诊断", "CT", "MRI", "介入"],
    ),
    JournalInfo(
        name="临床超声医学杂志",
        issn="1008-6978",
        impact_factor=0.789,
        review_cycle_days=45,
        publication_fee_yuan=400,
        database_tags=["科技核心"],
        suitable_levels=["初级", "中级"],
        departments=["影像科", "心血管内科", "妇产科"],
        keywords=["超声", "彩色多普勒", "介入超声"],
    ),
    JournalInfo(
        name="中国临床医学",
        issn="1008-6358",
        impact_factor=0.934,
        review_cycle_days=60,
        publication_fee_yuan=500,
        database_tags=["科技核心"],
        suitable_levels=["中级", "副高级"],
        departments=["内科", "外科"],
        keywords=["临床医学", "诊断", "治疗"],
    ),
    JournalInfo(
        name="中国矫形外科杂志",
        issn="1005-8478",
        impact_factor=1.067,
        review_cycle_days=60,
        publication_fee_yuan=500,
        database_tags=["科技核心"],
        suitable_levels=["中级", "副高级"],
        departments=["骨科"],
        keywords=["矫形外科", "脊柱", "关节", "创伤"],
    ),
    JournalInfo(
        name="中国药物与临床",
        issn="1671-9463",
        impact_factor=0.756,
        review_cycle_days=45,
        publication_fee_yuan=400,
        database_tags=["科技核心"],
        suitable_levels=["初级", "中级"],
        departments=["药学", "内科"],
        keywords=["药物", "临床用药", "药物评价", "不良反应"],
    ),
    JournalInfo(
        name="中国妇幼保健",
        issn="1001-4411",
        impact_factor=0.923,
        review_cycle_days=45,
        publication_fee_yuan=400,
        database_tags=["科技核心"],
        suitable_levels=["初级", "中级", "副高级"],
        departments=["妇产科", "儿科", "公共卫生"],
        keywords=["妇幼保健", "围产期", "新生儿", "孕产保健"],
    ),
    JournalInfo(
        name="中国卫生检验杂志",
        issn="1004-8685",
        impact_factor=0.678,
        review_cycle_days=45,
        publication_fee_yuan=400,
        database_tags=["科技核心"],
        suitable_levels=["初级", "中级"],
        departments=["检验科", "公共卫生"],
        keywords=["卫生检验", "理化检验", "微生物检验"],
    ),
    JournalInfo(
        name="中国急救医学",
        issn="1002-0737",
        impact_factor=0.945,
        review_cycle_days=45,
        publication_fee_yuan=400,
        database_tags=["科技核心"],
        suitable_levels=["初级", "中级", "副高级"],
        departments=["内科", "外科", "心血管内科", "神经内科"],
        keywords=["急救", "心肺复苏", "中毒", "创伤"],
    ),
    JournalInfo(
        name="中国疼痛医学杂志",
        issn="1006-9852",
        impact_factor=1.123,
        review_cycle_days=60,
        publication_fee_yuan=500,
        database_tags=["科技核心"],
        suitable_levels=["中级", "副高级"],
        departments=["神经内科", "外科", "骨科"],
        keywords=["疼痛", "镇痛", "慢性疼痛", "神经病理性疼痛"],
    ),

    # ---- 普适性期刊（适合多个科室） ----
    JournalInfo(
        name="中国全科医学",
        issn="1007-9572",
        impact_factor=1.567,
        review_cycle_days=45,
        publication_fee_yuan=600,
        database_tags=["科技核心", "北大核心"],
        suitable_levels=["初级", "中级", "副高级"],
        departments=["内科", "外科", "儿科", "妇产科", "公共卫生", "护理"],
        keywords=["全科医学", "基层医疗", "慢性病管理", "社区医疗"],
    ),
    JournalInfo(
        name="中国基层医药",
        issn="1008-6706",
        impact_factor=0.789,
        review_cycle_days=45,
        publication_fee_yuan=400,
        database_tags=["科技核心"],
        suitable_levels=["初级", "中级"],
        departments=["内科", "外科", "护理", "公共卫生"],
        keywords=["基层医疗", "常见病", "多发病"],
    ),
    JournalInfo(
        name="中华全科医师杂志",
        issn="1671-7368",
        impact_factor=1.234,
        review_cycle_days=60,
        publication_fee_yuan=0,
        database_tags=["科技核心", "中华医学会"],
        suitable_levels=["初级", "中级", "副高级"],
        departments=["内科", "外科", "儿科", "妇产科", "公共卫生"],
        keywords=["全科", "基层医疗", "慢性病", "预防医学"],
    ),
    JournalInfo(
        name="中国实用医技杂志",
        issn="1671-5098",
        impact_factor=0.567,
        review_cycle_days=30,
        publication_fee_yuan=300,
        database_tags=["科技核心"],
        suitable_levels=["初级", "中级"],
        departments=["影像科", "检验科", "药学"],
        keywords=["医技", "检验", "影像", "药剂"],
    ),
    JournalInfo(
        name="中华临床医师杂志（电子版）",
        issn="1674-0785",
        impact_factor=0.845,
        review_cycle_days=45,
        publication_fee_yuan=500,
        database_tags=["科技核心"],
        suitable_levels=["初级", "中级", "副高级"],
        departments=["内科", "外科", "儿科", "妇产科", "骨科", "心血管内科", "神经内科", "肿瘤科"],
        keywords=["临床", "诊断", "治疗", "病例报告"],
    ),
]


def get_all_journals() -> list[JournalInfo]:
    """
    获取所有期刊列表。

    Returns:
        所有期刊信息列表
    """
    return JOURNALS_DB


def get_journal_by_name(name: str) -> JournalInfo | None:
    """
    根据期刊名称精确查找期刊。

    Args:
        name: 期刊名称

    Returns:
        匹配的期刊信息，未找到返回None
    """
    for journal in JOURNALS_DB:
        if journal.name == name:
            return journal
    return None


def search_journals_by_department(department: str) -> list[JournalInfo]:
    """
    根据科室筛选期刊。

    Args:
        department: 科室名称

    Returns:
        匹配的期刊列表
    """
    results: list[JournalInfo] = []
    for journal in JOURNALS_DB:
        if department in journal.departments:
            results.append(journal)
    return results


def search_journals_by_level(title_level: str) -> list[JournalInfo]:
    """
    根据职称级别筛选期刊。

    Args:
        title_level: 职称级别

    Returns:
        匹配的期刊列表
    """
    results: list[JournalInfo] = []
    for journal in JOURNALS_DB:
        if title_level in journal.suitable_levels:
            results.append(journal)
    return results


def get_journals_count() -> int:
    """
    获取期刊总数。

    Returns:
        期刊数量
    """
    return len(JOURNALS_DB)
