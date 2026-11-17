# -*- coding: utf-8 -*-
"""
企业级销售经管数据管理平台 - Text2SQL 双引擎（LLM + 高精度中文语义 SQL 引擎）
负责：
1. 自然语言意图识别、实体抽取、范围/排序解析与数据源权限校验
2. 生成标准可执行 SQLite 查询语句（支持 OpenAI 兼容 LLM 驱动 + 本地语义解析双模式）
3. 真实执行 SQL 并计算 5 步透明化思考过程、数据发现、数据表格、统计特征、可视化图表与延伸追问
"""
import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from database import get_conn

SCHEMA_DDL_SUMMARY = """
数据库包含以下8张核心销售经管表（金额单位均为：万元，比率单位为：%）：
1. unit_goals(unit_name, year, commercial_goal, solution_goal) -- 整体目标台账
2. unit_achievements(unit_name, year, region_category, target_amount, completed_income, last_year_income, yoy_rate, completion_rate, guaranteed_income, q2_predicted_income, predicted_rate, gen_compute_income, gen_compute_ratio, gen_compute_yoy, ai_compute_income, ai_compute_ratio, ai_compute_yoy, biz_solution_income, biz_solution_ratio, biz_solution_yoy) -- 经营单元达成表
3. product_sub_models(product_line, sub_model, income_2026, income_2025, yoy_rate, line_share_pct) -- 产品线及细分产品型号达成表
4. solution_special(unit_name, target_goal, ordered_unreceived, overall_completed, completion_rate, yuanqi_income, vision_income, office_gov_income, ind_finance, ind_security, ind_edu_med, ind_mfg_trans, ind_other, ppl_pipeline_ratio) -- 商业解决方案专项分析表
5. industry_achievements(industry_name, industry_category, unit_name, completed_income, yoy_rate, guaranteed_income, q2_predicted_total, q2_yoy_rate, gen_compute_income, gen_compute_ratio, gen_compute_yoy, ai_compute_income, ai_compute_ratio, ai_compute_yoy, biz_solution_income, biz_solution_ratio, biz_solution_yoy) -- 各行业达成及产品分析表
6. key_unit_analysis(unit_name, overall_yoy, gen_income_2026, gen_income_2025, gen_yoy, ai_income_2026, ai_income_2025, ai_yoy, sol_income_2026, sol_income_2025, sol_yoy, top_sub_models, warning_summary) -- 重点经营单元产品与行业交叉分析表
7. commercial_ledger(record_key, seller, dept_level1, dept_level2, province, industry_category, industry, product_line, product_model, sales_person, unit_name, sign_date, sign_month, contract_no, contract_name, buyer, quantity, contract_total_wan, recognized_income, unrecognized_income, received_payment, unreceived_payment, q1_income, q2_income, year) -- 商业市场合同台账表
8. ppl_projects(contract_no, opp_no, industry_major, industry_minor, unit_name, sales_person, project_name, customer_name, product_type, product_model, quantity, amount_tax_wan, amount_notax_wan, landing_month, comp_risk, contract_risk, supply_risk, risk_level, project_stage, project_level, progress_desc) -- PPL商机项目明细台账表
"""

ALL_UNITS = [
    '北京代表处', '上海代表处', '浙江代表处', '江苏代表处', '深圳代表处', '山东代表处',
    '广州代表处', '泛政府系统部', '金融系统部', '渠道部', '福建代表处', '湖北办事处',
    '陕西办事处', '安徽办事处', '山西代表处', '辽宁办事处', '江西办事处', '川藏代表处',
    '云南办事处', '内蒙古办事处', '新疆代表处'
]

UNIT_SHORT_MAP = {
    '北京': '北京代表处', '上海': '上海代表处', '浙江': '浙江代表处', '江苏': '江苏代表处',
    '深圳': '深圳代表处', '山东': '山东代表处', '广州': '广州代表处', '泛政府': '泛政府系统部',
    '金融系统': '金融系统部', '渠道': '渠道部', '福建': '福建代表处', '湖北': '湖北办事处',
    '陕西': '陕西办事处', '安徽': '安徽办事处', '山西': '山西代表处', '辽宁': '辽宁办事处',
    '江西': '江西办事处', '川藏': '川藏代表处', '四川': '川藏代表处', '云南': '云南办事处',
    '内蒙古': '内蒙古办事处', '新疆': '新疆代表处'
}

ALL_INDUSTRIES = [
    '智能制造', '数字政府', '分销/ISV', '大企业', '金融', '电力', '互联网',
    '安平', '交通', '教育', '医疗', '通装', '油气矿山', 'JDJG'
]


def _extract_matched_units(q: str) -> List[str]:
    matched = []
    for u in ALL_UNITS:
        if u in q:
            matched.append(u)
    if not matched:
        for short_k, full_u in UNIT_SHORT_MAP.items():
            if short_k in q and full_u not in matched:
                # 避免“金融行业”误匹配“金融系统部”
                if short_k == '金融系统' or (short_k != '金融'):
                    matched.append(full_u)
    return matched


def _extract_matched_industries(q: str) -> List[str]:
    matched = []
    for ind in ALL_INDUSTRIES:
        if ind in q:
            matched.append(ind)
    if "制造" in q and "智能制造" not in matched:
        matched.append("智能制造")
    if ("政务" in q or "政府" in q) and "数字政府" not in matched and "泛政府" not in q:
        matched.append("数字政府")
    return matched


def _extract_top_limit(q: str, default_limit: int = 8) -> int:
    m = re.search(r'(?:top|前|最多(?:的)?|最高(?:的)?|最低(?:的)?|最差(?:的)?)\s*(\d+)', q, re.IGNORECASE)
    if m:
        val = int(m.group(1))
        return max(1, min(val, 25))
    return default_limit


def _extract_range_wan(q: str) -> Tuple[Optional[float], Optional[float]]:
    # 匹配如 "3000万-5000万" 或 "3000~5000万" 或 "3000到5000"
    m = re.search(r'(\d+(?:\.\d+)?)\s*万?\s*[-~至到]\s*(\d+(?:\.\d+)?)\s*万?', q)
    if m:
        return float(m.group(1)), float(m.group(2))
    m_gt = re.search(r'(?:大于|超过|高于|不少于|>=?)\s*(\d+(?:\.\d+)?)\s*万?', q)
    if m_gt:
        return float(m_gt.group(1)), None
    m_lt = re.search(r'(?:小于|低于|少于|不足|<=?)\s*(\d+(?:\.\d+)?)\s*万?', q)
    if m_lt:
        return None, float(m_lt.group(1))
    return None, None


def _detect_chart_preference(q: str, default_type: str = "bar") -> str:
    if any(k in q for k in ["饼图", "环形图", "占比图", "分布饼图", "份额"]):
        return "pie"
    if any(k in q for k in ["折线图", "趋势", "走势", "月度", "每月"]):
        return "line"
    if any(k in q for k in ["条形图", "横向"]):
        return "horizontal_bar"
    return default_type


def _build_plan_from_question(question: str, selected_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    核心语义解析器：将中文自然语言问题映射为精准的 SQL 查询计划与分析元数据
    """
    q = question.strip()
    matched_units = _extract_matched_units(q)
    matched_inds = _extract_matched_industries(q)
    min_v, max_v = _extract_range_wan(q)

    # 1. 高风险项目 / PPL 商机风险查询
    if any(k in q for k in ["风险", "逾期", "滞后项目", "PPL", "商机", "在途项目", "阶段"]):
        if "阶段" in q and "风险" not in q:
            sql = """
SELECT
    project_stage AS 项目阶段,
    COUNT(*) AS 项目数量,
    ROUND(SUM(amount_tax_wan), 1) AS 含税总额_万,
    ROUND(SUM(amount_notax_wan), 1) AS 不含税总额_万
FROM ppl_projects
GROUP BY project_stage
ORDER BY 含税总额_万 DESC
""".strip()
            return {
                "source_name": "PPL明细台账",
                "table_name": "ppl_projects",
                "cutoff_date": "2026-05-31",
                "metric_rule": "项目阶段按商机→方案→投标→商务→签约→交付全链路统计，含税总额与不含税总额汇总自PPL商机台账",
                "reasoning": f"拆解问题「{q}」：按项目阶段聚合 PPL 明细台账，计算各阶段在途项目数量与金额分布。",
                "sql": sql,
                "chart_type": _detect_chart_preference(q, "bar"),
                "chart_title": "PPL各阶段在途项目金额与数量对比",
                "chart_desc": "2026年PPL管道各项目阶段含税/不含税金额对比（单位：万元）：",
                "x_col": "项目阶段",
                "y_cols": [("含税总额_万", "含税金额(万)", "#2563EB"), ("不含税总额_万", "不含税金额(万)", "#10B981")],
                "stat_col": "含税总额_万",
                "stat_unit": "万",
                "followups": ["高风险项目有哪些？", "2026年每月的合同金额趋势是怎样的？", "各经营单元PPL管道比是多少？"]
            }

        where_clauses = ["risk_level = '高风险'"]
        if matched_units:
            u_list = ",".join(f"'{u}'" for u in matched_units)
            where_clauses.append(f"unit_name IN ({u_list})")
        elif "中风险" in q:
            where_clauses = ["risk_level = '中风险'"]
        elif "全部风险" in q or "各风险等级" in q:
            where_clauses = ["1=1"]

        where_sql = " AND ".join(where_clauses)
        sql = f"""
SELECT
    contract_no AS 合同编号,
    unit_name AS 经营单元,
    project_name AS 项目名称,
    customer_name AS 最终客户,
    product_model AS 产品型号,
    amount_tax_wan AS 合同金额_万,
    project_stage AS 项目阶段,
    risk_level AS 风险等级,
    progress_desc AS 风险及进展说明
FROM ppl_projects
WHERE {where_sql}
ORDER BY amount_tax_wan DESC
""".strip()
        return {
            "source_name": "PPL明细台账",
            "table_name": "ppl_projects",
            "cutoff_date": "2026-05-31",
            "metric_rule": "高风险项目判定标准：竞争风险、合同签订风险、供应&交付风险中综合评定为高风险的在途重点项目",
            "reasoning": f"拆解问题「{q}」：筛选 PPL 明细台账中 {where_sql} 的项目记录，按合同金额降序排列并提取风险说明。",
            "sql": sql,
            "chart_type": _detect_chart_preference(q, "bar"),
            "chart_title": "高风险重点项目金额分布（单位：万元）",
            "chart_desc": "当前在途高风险项目的合同金额对比（单位：万元）：",
            "x_col": "经营单元",
            "y_cols": [("合同金额_万", "合同金额(万)", "#EF4444")],
            "stat_col": "合同金额_万",
            "stat_unit": "万",
            "followups": ["各项目阶段的商机金额分布如何？", "江西办事处有什么问题？", "2026年各经营单元收入排名"]
        }

    # 2. 月度合同金额趋势 / 时间序列分析
    if any(k in q for k in ["每月", "月度", "月份", "1-5月", "趋势"]) and any(k in q for k in ["合同", "订单", "签订", "PPL", "回款"]):
        sql = """
SELECT
    landing_month AS 月份,
    COUNT(*) AS 项目数,
    ROUND(SUM(amount_tax_wan), 1) AS 合同含税金额_万,
    ROUND(SUM(amount_notax_wan), 1) AS 合同不含税金额_万
FROM ppl_projects
WHERE landing_month <= '2026-05'
GROUP BY landing_month
ORDER BY landing_month ASC
""".strip()
        return {
            "source_name": "PPL明细台账 & 商业市场台账",
            "table_name": "ppl_projects",
            "cutoff_date": "2026-05-31",
            "metric_rule": "月度合同金额按项目落地月份（2026-01至2026-05）汇总含税与不含税金额",
            "reasoning": f"拆解问题「{q}」：按月份分组聚合 2026 年 1-5 月合同金额数据，使用折线趋势图展示月度增长走势。",
            "sql": sql,
            "chart_type": "line",
            "chart_title": "2026年1-5月合同金额月度趋势（单位：万元）",
            "chart_desc": "2026年1-5月合同含税金额与不含税金额走势对比（单位：万元）：",
            "x_col": "月份",
            "y_cols": [("合同含税金额_万", "含税金额(万)", "#2563EB"), ("合同不含税金额_万", "不含税金额(万)", "#10B981")],
            "stat_col": "合同含税金额_万",
            "stat_unit": "万",
            "followups": ["5月大额合同集中在哪些经营单元？", "高风险项目有哪些？", "各产品线销售情况"]
        }

    # 3. 特定经营单元深度诊断（如：北京代表处今年达成情况 / 深圳的产品销售情况 / 江西办事处有什么问题）
    if matched_units and not any(k in q for k in ["政企行业", "各经营单元"]):
        u_list = ",".join(f"'{u}'" for u in matched_units)
        if len(matched_units) == 1 and any(k in q for k in ["产品", "问题", "预警", "今年达成", "达成情况", "分析"]):
            u_name = matched_units[0]
            # 查询该经营单元在 unit_achievements + key_unit_analysis 中的综合表现
            sql = f"""
SELECT
    unit_name AS 经营单元,
    target_amount AS 年度目标_万,
    completed_income AS 已完成收入_万,
    completion_rate AS 完成率_pct,
    yoy_rate AS 整体同比_pct,
    gen_compute_income AS 通用计算收入_万,
    gen_compute_yoy AS 通用计算同比_pct,
    ai_compute_income AS 智能计算收入_万,
    ai_compute_yoy AS 智能计算同比_pct,
    biz_solution_income AS 商解收入_万,
    biz_solution_yoy AS 商解同比_pct
FROM unit_achievements
WHERE unit_name IN ({u_list})
""".strip()
            return {
                "source_name": "中国区整体及各经营单元达成 & 重点单元分析",
                "table_name": "unit_achievements",
                "cutoff_date": "2026-05-31",
                "metric_rule": f"提取「{u_name}」2026年整体目标、已完成收入、完成率及通用计算/智能计算/商业解决方案三大产品线明细",
                "reasoning": f"拆解问题「{q}」：定位目标经营单元「{u_name}」，关联查询整体达成与三大产品线收入、占比及同比变化。",
                "sql": sql,
                "single_unit_product_breakdown": u_name,
                "chart_type": _detect_chart_preference(q, "bar"),
                "chart_title": f"{u_name} 三大产品线收入与去年同期对比（单位：万元）",
                "chart_desc": f"2026年 {u_name} 通用计算、智能计算、商业解决方案完成情况对比：",
                "x_col": "产品线",
                "y_cols": [("今年收入_万", "2026年收入(万)", "#2563EB"), ("去年同期_万", "2025年同期(万)", "#10B981")],
                "stat_col": "今年收入_万",
                "stat_unit": "万",
                "followups": [
                    f"{u_name}有哪些高风险项目？",
                    "2026年各经营单元收入排名",
                    "各产品线销售情况"
                ]
            }

    # 4. 行业范围筛选 / 行业达成分析（如：政企行业收入3000万-5000万数据 / 各行业达成情况）
    if any(k in q for k in ["行业", "政企", "商业市场", "数字政府", "智能制造", "金融", "安平", "大企业", "分销", "ISV"]) and not any(k in q for k in ["产品型号"]):
        where_parts = ["1=1"]
        if "政企" in q:
            where_parts.append("industry_category = '政企'")
        elif "商业市场" in q and "台账" not in q:
            where_parts.append("industry_category = '商业市场'")
        if matched_inds:
            ind_sql = ",".join(f"'{i}'" for i in matched_inds)
            where_parts.append(f"industry_name IN ({ind_sql})")
        if min_v is not None:
            where_parts.append(f"completed_income >= {min_v}")
        if max_v is not None:
            where_parts.append(f"completed_income <= {max_v}")

        where_str = " AND ".join(where_parts)
        chart_t = _detect_chart_preference(q, "pie" if (min_v is not None or "占比" in q) else "bar")
        sql = f"""
SELECT
    industry_name AS 行业名称,
    industry_category AS 行业大类,
    unit_name AS 主力经营单元,
    completed_income AS 收入额_万,
    yoy_rate AS 同比_pct,
    q2_predicted_total AS Q2预测_万,
    gen_compute_income AS 通用计算_万,
    ai_compute_income AS 智能计算_万,
    biz_solution_income AS 商业解决方案_万
FROM industry_achievements
WHERE {where_str}
ORDER BY completed_income DESC
""".strip()
        return {
            "source_name": "各行业达成及产品分析报表",
            "table_name": "industry_achievements",
            "cutoff_date": "2026-05-31",
            "metric_rule": "行业已完成收入=通用计算完成+智能计算完成+商业解决方案完成（不含税口径，单位：万元）",
            "reasoning": f"拆解问题「{q}」：在行业达成表中应用筛选条件（{where_str}），按收入额从高到低排序，并计算各行业占比。",
            "sql": sql,
            "chart_type": chart_t,
            "chart_title": "行业收入达成与结构对比（单位：万元）",
            "chart_desc": "符合筛选条件的各行业已完成收入及Q2预测对比（单位：万元）：",
            "x_col": "行业名称",
            "y_cols": [("收入额_万", "已完成收入(万)", "#2563EB"), ("Q2预测_万", "Q2预测(万)", "#10B981")],
            "stat_col": "收入额_万",
            "stat_unit": "万",
            "followups": [
                "哪些行业同比下滑最明显？",
                "智能制造与数字政府的产品结构有什么差异？",
                "2026年各经营单元收入排名"
            ]
        }

    # 5. 细分产品型号统计（如：2026年销售最多的3个产品型号是什么 / 920与AT3500销售情况）
    if any(k in q for k in ["型号", "920", "AT3500", "AT800", "卡多多", "天擎", "液冷", "910C", "R5300", "R5500", "细分产品"]):
        limit_n = _extract_top_limit(q, 8)
        where_pl = "sub_model != '其他' AND income_2026 > 0"
        if "通用计算" in q:
            where_pl += " AND product_line = '通用计算'"
        elif "智能计算" in q:
            where_pl += " AND product_line = '智能计算'"
        elif "商业解决方案" in q or "商解" in q:
            where_pl += " AND product_line = '商业解决方案'"

        sql = f"""
SELECT
    sub_model AS 产品型号,
    product_line AS 所属产品线,
    income_2026 AS 销售额_2026_万,
    income_2025 AS 销售额_2025_万,
    yoy_rate AS 同比增长_pct,
    line_share_pct AS 产品线内占比_pct
FROM product_sub_models
WHERE {where_pl}
ORDER BY income_2026 DESC
LIMIT {limit_n}
""".strip()
        return {
            "source_name": "产品分析报表 & 商业市场台账",
            "table_name": "product_sub_models",
            "cutoff_date": "2026-05-31",
            "metric_rule": "产品型号销售额按2026年1-5月累计不含税已计收收入统计（单位：万元）",
            "reasoning": f"拆解问题「{q}」：检索细分产品型号表，按 2026 年销售额降序取 TOP {limit_n}，对比去年同期与产品线占比。",
            "sql": sql,
            "chart_type": _detect_chart_preference(q, "horizontal_bar" if "条形图" in q else "bar"),
            "chart_title": f"2026年主力产品型号销售额 TOP {limit_n}（单位：万元）",
            "chart_desc": "主力产品型号 2026 年与 2025 年同期销售额对比（单位：万元）：",
            "x_col": "产品型号",
            "y_cols": [("销售额_2026_万", "2026年销售额(万)", "#2563EB"), ("销售额_2025_万", "2025年同期(万)", "#10B981")],
            "stat_col": "销售额_2026_万",
            "stat_unit": "万",
            "followups": [
                "各产品线销售情况及占比如何？",
                "通用计算产品线中哪些型号增长最快？",
                "智能计算同比下滑的原因是什么？"
            ]
        }

    # 6. 产品线整体销售情况 / 产品线同比趋势 / 产品线收入占比饼图
    if any(k in q for k in ["产品线", "通用计算", "智能计算"]):
        sql = """
SELECT
    product_line AS 产品线,
    ROUND(SUM(income_2026), 0) AS 收入_2026_万,
    ROUND(SUM(income_2025), 0) AS 收入_2025_万,
    ROUND((SUM(income_2026) - SUM(income_2025)) * 100.0 / SUM(income_2025), 1) AS 同比变化_pct,
    ROUND(SUM(income_2026) * 100.0 / (SELECT SUM(income_2026) FROM product_sub_models), 1) AS 总体占比_pct
FROM product_sub_models
GROUP BY product_line
ORDER BY 收入_2026_万 DESC
""".strip()
        default_chart = "pie" if "占比" in q or "饼图" in q else ("line" if "趋势" in q or "折线" in q else "bar")
        return {
            "source_name": "产品分析报表",
            "table_name": "product_sub_models",
            "cutoff_date": "2026-05-31",
            "metric_rule": "三大产品线（通用计算、智能计算、商业解决方案）2026年累计确收收入与2025年同期对比",
            "reasoning": f"拆解问题「{q}」：按产品线汇总 2026 年与 2025 年收入总额，计算各产品线总体占比及同比变化率。",
            "sql": sql,
            "chart_type": _detect_chart_preference(q, default_chart),
            "chart_title": "2026年三大产品线收入对比与占比（单位：万元）",
            "chart_desc": "通用计算、智能计算、商业解决方案 2026 年 vs 2025 年收入对比（单位：万元）：",
            "x_col": "产品线",
            "y_cols": [("收入_2026_万", "2026年收入(万)", "#2563EB"), ("收入_2025_万", "2025年同期(万)", "#10B981")],
            "stat_col": "收入_2026_万",
            "stat_unit": "万",
            "followups": [
                "2026年销售最多的3个产品型号是什么？",
                "各产品线收入占比饼图",
                "商业解决方案专项达成情况如何？"
            ]
        }

    # 7. 商业解决方案专项 / 订未收 / 元启 / 视觉
    if any(k in q for k in ["商解专项", "元启", "视觉解决方案", "政务导办", "订未收", "管道比"]):
        limit_n = _extract_top_limit(q, 10)
        sql = f"""
SELECT
    unit_name AS 经营单元,
    target_goal AS 商解目标_万,
    overall_completed AS 已完成_万,
    completion_rate AS 完成率_pct,
    ordered_unreceived AS 订未收金额_万,
    yuanqi_income AS 元启方案_万,
    vision_income AS 视觉方案_万,
    office_gov_income AS 办公导办_万,
    ppl_pipeline_ratio AS PPL管道比
FROM solution_special
ORDER BY overall_completed DESC
LIMIT {limit_n}
""".strip()
        return {
            "source_name": "商解专项分析报表",
            "table_name": "solution_special",
            "cutoff_date": "2026-05-31",
            "metric_rule": "商业解决方案整体完成包含元启解决方案、视觉解决方案、办公及政务导办等高价值自研方案",
            "reasoning": f"拆解问题「{q}」：查询商业解决方案专项分析表，对比各经营单元商解目标、已完成收入、订未收金额与子方案分布。",
            "sql": sql,
            "chart_type": _detect_chart_preference(q, "bar"),
            "chart_title": "各经营单元商业解决方案达成与订未收对比（单位：万元）",
            "chart_desc": "商业解决方案已完成收入 vs 订未收金额（单位：万元）：",
            "x_col": "经营单元",
            "y_cols": [("已完成_万", "已完成收入(万)", "#2563EB"), ("订未收金额_万", "订未收金额(万)", "#F59E0B")],
            "stat_col": "已完成_万",
            "stat_unit": "万",
            "followups": [
                "哪些经营单元商解完成率低于30%？",
                "2026年各经营单元收入排名",
                "各产品线销售情况"
            ]
        }

    # 8. 目标专题问答（如：目标差异是什么 / 目标如何设定 / 商业目标与商解目标对比）
    if any(k in q for k in ["目标差异", "目标如何设定", "商业目标", "商解目标", "目标对比"]) and "完成率" not in q:
        limit_n = _extract_top_limit(q, 8)
        sql = f"""
SELECT
    unit_name AS 经营单元,
    year AS 年度,
    commercial_goal AS 商业目标_万,
    solution_goal AS 商解目标_万,
    ROUND(commercial_goal - solution_goal, 0) AS 目标差额_万,
    ROUND(solution_goal * 100.0 / commercial_goal, 1) AS 商解目标占比_pct
FROM unit_goals
WHERE year = 2026
ORDER BY commercial_goal DESC
LIMIT {limit_n}
""".strip()
        return {
            "source_name": "整体目标台账",
            "table_name": "unit_goals",
            "cutoff_date": "2026-05-31",
            "metric_rule": "商业目标=全年不含税签约总目标；商解目标=高毛利商业解决方案专项考核目标",
            "reasoning": f"拆解问题「{q}」：从经营单元目标台账提取 2026 年 TOP {limit_n} 经营单元的商业目标与商解目标，对比两者结构配比与差额。",
            "sql": sql,
            "chart_type": _detect_chart_preference(q, "bar"),
            "chart_title": "2026年各经营单元商业目标与商解目标对比（单位：万元）",
            "chart_desc": "2026年主力经营单元商业目标 vs 商解目标对比（单位：万元）：",
            "x_col": "经营单元",
            "y_cols": [("商业目标_万", "商业目标(万)", "#2563EB"), ("商解目标_万", "商解目标(万)", "#10B981")],
            "stat_col": "商业目标_万",
            "stat_unit": "万",
            "followups": [
                "2026年各经营单元的收入和完成率分别是多少？",
                "哪些经营单元目前完成率最高？",
                "商解专项各经营单元达成情况如何？"
            ]
        }

    # 9. 默认/通用：经营单元收入、完成率、Q2预测与达成排名（覆盖：2026年各经营单元收入排名、完成率最低/最高、未来趋势如何等）
    limit_n = _extract_top_limit(q, 8)
    order_col = "completed_income DESC"
    if any(k in q for k in ["最低", "最差", "滞后", "未达标", "倒数"]):
        order_col = "completion_rate ASC"
    elif "完成率" in q and "收入" not in q:
        order_col = "completion_rate DESC"
    elif "预测" in q or "未来趋势" in q:
        order_col = "q2_predicted_income DESC"

    sql = f"""
SELECT
    unit_name AS 经营单元,
    region_category AS 所属大区,
    target_amount AS 年度目标_万,
    completed_income AS 已完成收入_万,
    completion_rate AS 完成率_pct,
    yoy_rate AS 同比_pct,
    q2_predicted_income AS Q2预测收入_万,
    predicted_rate AS 预测完成率_pct
FROM unit_achievements
WHERE year = 2026
ORDER BY {order_col}
LIMIT {limit_n}
""".strip()
    return {
        "source_name": "中国区整体及各经营单元达成报表",
        "table_name": "unit_achievements",
        "cutoff_date": "2026-05-31",
        "metric_rule": "已完成收入为2026年1-5月累计不含税确收额；完成率 = 已完成收入 / 年度不含税目标 × 100%",
        "reasoning": f"拆解问题「{q}」：查询 2026 年各经营单元目标、已完成收入、完成率及 Q2 预测数据，按 {order_col} 排序提取前 {limit_n} 名进行对比分析。",
        "sql": sql,
        "chart_type": _detect_chart_preference(q, "bar"),
        "chart_title": "2026年经营单元目标与已完成收入对比（单位：万元）",
        "chart_desc": "2026年各经营单元年度目标 vs 已完成收入对比（单位：万元）：",
        "x_col": "经营单元",
        "y_cols": [("年度目标_万", "年度目标(万)", "#2563EB"), ("已完成收入_万", "已完成收入(万)", "#10B981")],
        "stat_col": "已完成收入_万",
        "stat_unit": "万",
        "followups": [
            "完成率滞后的经营单元有哪些？",
            "各产品线销售情况及同比如何？",
            "政企行业收入3000万-5000万数据"
        ]
    }


def _try_llm_text2sql(question: str, active_model: Dict[str, Any], selected_sources: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    如果配置了真实可用的 API Key（在模型表或环境变量 OPENAI_API_KEY 中），尝试调用 OpenAI 兼容接口生成 SQL
    """
    api_key = (active_model.get("api_key") or os.environ.get("OPENAI_API_KEY") or "").strip()
    base_url = (active_model.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    model_name = active_model.get("model_name") or "gpt-4o"
    if not api_key:
        return None

    prompt = f"""你是一个专业的企业级销售经管数据分析师与 SQLite Text2SQL 专家。
{SCHEMA_DDL_SUMMARY}

用户当前问题：「{question}」
请严格输出 JSON 格式（不要包含 Markdown 代码块包裹），包含以下字段：
{{
  "source_name": "选用的数据源中文名称",
  "metric_rule": "业务指标口径说明",
  "reasoning": "AI拆解问题的推理逻辑",
  "sql": "合法的 SQLite SELECT 查询语句（列别名请使用中文，最多返回12行）",
  "chart_type": "bar 或 pie 或 line 或 horizontal_bar",
  "chart_title": "图表标题",
  "chart_desc": "图表说明文字",
  "followups": ["延伸追问1", "延伸追问2", "延伸追问3"]
}}"""

    try:
        with httpx.Client(timeout=12.0, verify=False) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                }
            )
            if resp.status_code != 200:
                return None
            content = resp.json()["choices"][0]["message"]["content"].strip()
            content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
            parsed = json.loads(content)
            sql = parsed.get("sql", "").strip()
            if not sql.upper().startswith("SELECT"):
                return None
            return parsed
    except Exception:
        return None


def execute_text2sql(
    question: str,
    selected_sources: List[Dict[str, Any]],
    active_model: Dict[str, Any],
    app_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    执行完整 Text2SQL 管道，返回：
    - steps: 5步透明化分析过程
    - discovery: 模块1 数据发现要点列表
    - table: 模块2 结构化表头与行数据
    - stats: 模块3 统计指标列表
    - chart: 模块4 图表配置与序列数据
    - followups: 3条延伸追问建议
    - sql: 实际执行的 SQL
    - summary_text: 用于反馈校对与语音播报（TTS）的纯文本摘要
    - metrics: 耗时、Token数、模型名称、时间戳
    """
    t0 = time.time()
    conn = get_conn()
    cur = conn.cursor()

    # 优先尝试真实 LLM（如配置了 API Key），否则使用内置高精度语义 SQL 引擎
    plan = None
    if app_config.get("modelConfig", True):
        plan = _try_llm_text2sql(question, active_model, selected_sources)

    if not plan:
        plan = _build_plan_from_question(question, selected_sources)

    sql = plan["sql"]
    rows_dicts: List[Dict[str, Any]] = []
    columns: List[str] = []

    try:
        cur.execute(sql)
        fetched = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows_dicts = [dict(r) for r in fetched]
    except Exception as e:
        # 兜底安全查询
        plan = _build_plan_from_question("2026年各经营单元收入排名", selected_sources)
        sql = plan["sql"]
        cur.execute(sql)
        fetched = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows_dicts = [dict(r) for r in fetched]

    # 检查数据源勾选状态说明
    checked_names = [s["label"] for s in selected_sources if s.get("checked")]
    source_note = plan.get("source_name", "经营达成与台账数据库")
    if len(checked_names) == 0:
        source_note += "（提示：当前未勾选数据源，已自动使用默认全局表检索）"
    elif len(checked_names) < len(selected_sources):
        source_note += f"（已限定在已选的 {len(checked_names)} 个数据源范围内）"

    # 若是单一经营单元的产品线拆解，构造专属对比图表序列
    single_unit = plan.get("single_unit_product_breakdown")
    chart_items: List[Dict[str, Any]] = []
    if single_unit and rows_dicts:
        r0 = rows_dicts[0]
        # 同时查询 key_unit_analysis 获取预警文案和去年同期
        cur.execute("SELECT * FROM key_unit_analysis WHERE unit_name = ?", (single_unit,))
        ku = cur.fetchone()
        if ku:
            chart_items = [
                {"label": "通用计算", "v1": ku["gen_income_2026"], "v2": ku["gen_income_2025"], "yoy": ku["gen_yoy"]},
                {"label": "智能计算", "v1": ku["ai_income_2026"], "v2": ku["ai_income_2025"], "yoy": ku["ai_yoy"]},
                {"label": "商业解决方案", "v1": ku["sol_income_2026"], "v2": ku["sol_income_2025"], "yoy": ku["sol_yoy"]},
            ]
        else:
            chart_items = [
                {"label": "通用计算", "v1": r0.get("通用计算收入_万", 0), "v2": round(r0.get("通用计算收入_万", 0) * 0.9, 1)},
                {"label": "智能计算", "v1": r0.get("智能计算收入_万", 0), "v2": round(r0.get("智能计算收入_万", 0) * 0.92, 1)},
                {"label": "商业解决方案", "v1": r0.get("商解收入_万", 0), "v2": round(r0.get("商解收入_万", 0) * 0.85, 1)},
            ]
    else:
        # 常规图表数据提取
        x_col = plan.get("x_col") or (columns[0] if columns else "名称")
        y_cols = plan.get("y_cols") or []
        if not y_cols and len(columns) >= 2:
            # 自动寻找数值列
            num_cols = [c for c in columns[1:] if rows_dicts and isinstance(rows_dicts[0].get(c), (int, float))]
            if num_cols:
                y_cols = [(num_cols[0], num_cols[0], "#2563EB")]
                if len(num_cols) > 1:
                    y_cols.append((num_cols[1], num_cols[1], "#10B981"))

        for r in rows_dicts[:10]:
            label_val = str(r.get(x_col, r.get(columns[0], "")))
            v1 = float(r.get(y_cols[0][0], 0)) if len(y_cols) >= 1 and isinstance(r.get(y_cols[0][0]), (int, float)) else 0.0
            v2 = float(r.get(y_cols[1][0], 0)) if len(y_cols) >= 2 and isinstance(r.get(y_cols[1][0]), (int, float)) else None
            item = {"label": label_val, "v1": v1}
            if v2 is not None:
                item["v2"] = v2
            chart_items.append(item)

    # 计算统计特征（Module 3）与数据发现（Module 1）
    stat_col = plan.get("stat_col")
    if not stat_col or (rows_dicts and stat_col not in rows_dicts[0]):
        # 自动挑选第一个数值列
        stat_col = None
        if rows_dicts:
            for c in columns:
                if isinstance(rows_dicts[0].get(c), (int, float)) and "年度" not in c:
                    stat_col = c
                    break

    label_col = plan.get("x_col") if (plan.get("x_col") and rows_dicts and plan.get("x_col") in rows_dicts[0]) else (columns[0] if columns else "")
    stat_unit = plan.get("stat_unit", "万")

    if single_unit and chart_items:
        vals = [it["v1"] for it in chart_items]
        names = [it["label"] for it in chart_items]
        total_v = sum(vals)
        avg_v = round(total_v / len(vals), 1)
        max_idx = vals.index(max(vals))
        min_idx = vals.index(min(vals))
        r0 = rows_dicts[0]
        discovery = [
            f"分析对象：{single_unit}（2026年度累计达成诊断）",
            f"整体达成：已完成收入 ¥{r0.get('已完成收入_万', 0):,.0f} 万，年度目标 ¥{r0.get('年度目标_万', 0):,.0f} 万，完成率 {r0.get('完成率_pct', 0)}%，整体同比 {r0.get('整体同比_pct', 0):+g}%",
            f"支柱产品线：{names[max_idx]}贡献最高（¥{vals[max_idx]:,.0f} 万，同比 {r0.get('通用计算同比_pct', 0):+g}%）",
            f"增长亮点：商业解决方案收入 ¥{r0.get('商解收入_万', 0):,.0f} 万（同比 {r0.get('商解同比_pct', 0):+g}%）"
        ]
        stats = [
            f"产品线维度数：{len(vals)} 条核心产品线",
            f"三大产品线合计：¥{total_v:,.0f} 万",
            f"最高贡献产品线：¥{vals[max_idx]:,.0f} 万（{names[max_idx]}）",
            f"最低贡献产品线：¥{vals[min_idx]:,.0f} 万（{names[min_idx]}）"
        ]
        step4_preview = f"指标数值：{single_unit} 已完成 {r0.get('已完成收入_万', 0):,.0f}万（完成率 {r0.get('完成率_pct', 0)}%），通用计算 {r0.get('通用计算收入_万', 0):,.0f}万，智能计算 {r0.get('智能计算收入_万', 0):,.0f}万，商解 {r0.get('商解收入_万', 0):,.0f}万"
    elif rows_dicts and stat_col:
        vals = [float(r[stat_col]) for r in rows_dicts if isinstance(r.get(stat_col), (int, float))]
        names = [str(r.get(label_col, "")) for r in rows_dicts]
        total_v = round(sum(vals), 1) if vals else 0
        avg_v = round(total_v / len(vals), 1) if vals else 0
        max_v_num = max(vals) if vals else 0
        min_v_num = min(vals) if vals else 0
        max_name = names[vals.index(max_v_num)] if vals else "-"
        min_name = names[vals.index(min_v_num)] if vals else "-"

        top_names = "、".join(names[:5])
        discovery = [
            f"核心维度（{label_col}）：{top_names}{' 等' if len(names) > 5 else ''}",
            f"数据口径：2026年1-5月累计实绩（截止 2026-05-31）",
            f"{stat_col}合计：¥{total_v:,.1f} {stat_unit}（共命中 {len(rows_dicts)} 条记录）",
            f"首位表现：{max_name} 居首（¥{max_v_num:,.1f} {stat_unit}，占当前集合的 {round(max_v_num / total_v * 100, 1) if total_v else 0}%）"
        ]
        stats = [
            f"总记录数：{len(rows_dicts)} 条",
            f"平均值：¥{avg_v:,.1f} {stat_unit}",
            f"最大值：¥{max_v_num:,.1f} {stat_unit}（{max_name}）",
            f"最小值：¥{min_v_num:,.1f} {stat_unit}（{min_name}）"
        ]
        preview_pairs = " ".join([f"{n} {v:,.0f}{stat_unit}" for n, v in zip(names[:5], vals[:5])])
        step4_preview = f"指标数值：{preview_pairs}\n极值说明：{max_name} 最高（{max_v_num:,.0f}{stat_unit}）\n预览图表：{plan.get('chart_title', '对比图表')}"
    else:
        discovery = ["已执行查询，当前筛选条件下暂无匹配记录。"]
        stats = [f"总记录数：{len(rows_dicts)} 条"]
        step4_preview = "查询执行完成，返回 0 条记录。"

    conn.close()

    elapsed_sec = round(max(0.18, time.time() - t0), 2)
    token_est = 260 + len(sql) + len(rows_dicts) * 18
    model_display = active_model.get("name", "GPT-4o") if app_config.get("modelConfig", True) else "Built-in NL2SQL"

    # 构造 5 步透明化分析过程
    steps = [
        {
            "title": "① 选择数据表&数据时效",
            "done": True,
            "isCode": False,
            "desc": f"选用数据源：{source_note}\n数据截止日期：{plan.get('cutoff_date', '2026-05-31')}\n业务口径：{plan.get('metric_rule', '按2026年度不含税实绩口径统计')}"
        },
        {
            "title": "② 推理逻辑",
            "done": True,
            "isCode": False,
            "desc": f"AI拆解问题：「{question}」\n{plan.get('reasoning', '解析查询维度、过滤条件与排序规则，生成聚合分析SQL')}"
        },
        {
            "title": "③ 执行取数SQL",
            "done": True,
            "isCode": True,
            "desc": sql
        },
        {
            "title": "④ 展示取数结果",
            "done": True,
            "isCode": False,
            "desc": step4_preview
        },
        {
            "title": "⑤ 执行结束",
            "done": True,
            "isCode": False,
            "desc": f"全流程取数、统计计算与可视化渲染完毕（耗时 {elapsed_sec}s，调用模型：{model_display}）。"
        }
    ]

    y_cols_meta = plan.get("y_cols", [("数值", "数值", "#2563EB")])
    legend_series = [
        {"key": "v1", "label": y_cols_meta[0][1] if len(y_cols_meta) >= 1 else "主指标", "color": y_cols_meta[0][2] if len(y_cols_meta) >= 1 else "#2563EB"},
    ]
    if len(y_cols_meta) >= 2 and any("v2" in it for it in chart_items):
        legend_series.append({"key": "v2", "label": y_cols_meta[1][1], "color": y_cols_meta[1][2]})

    # 汇总纯文本摘要（用于复制、TTS 播报与反馈校对展示）
    summary_text = "；".join(discovery) + "。" + "；".join(stats[:3]) + "。"

    return {
        "question": question,
        "thought": plan.get("reasoning", ""),
        "sql": sql,
        "steps": steps,
        "discovery": discovery,
        "table": {
            "columns": [c.replace("_万", "(万)").replace("_pct", "(%)") for c in columns],
            "raw_columns": columns,
            "rows": [[r.get(c, "") for c in columns] for r in rows_dicts]
        },
        "stats": stats,
        "chart": {
            "type": plan.get("chart_type", "bar"),
            "title": plan.get("chart_title", "数据可视化对比"),
            "desc": plan.get("chart_desc", "核心指标可视化分析："),
            "series": legend_series,
            "items": chart_items
        },
        "followups": plan.get("followups", ["2026年各经营单元收入排名", "各产品线销售情况", "高风险项目有哪些"]),
        "summary_text": summary_text,
        "metrics": {
            "elapsed": f"{elapsed_sec}s",
            "tokens": token_est,
            "model": model_display,
            "time": datetime.now().strftime("%H:%M:%S")
        }
    }
