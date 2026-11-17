# -*- coding: utf-8 -*-
"""
企业级销售经管数据管理平台 - SQLite 数据库与种子数据初始化模块
从原型 Data/index.html 提炼全部业务台账、统计报表与系统状态表
"""
import json
import os
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sales_data.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    # ==================== 1. 业务数据表（Text2SQL 目标库表） ====================

    # 表1: 整体目标台账 (unit_goals)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS unit_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_name TEXT NOT NULL,           -- 经营单元
        year INTEGER NOT NULL,             -- 年度 (2025/2026)
        commercial_goal REAL NOT NULL,     -- 商业目标(万元)
        solution_goal REAL NOT NULL        -- 商解目标(万元)
    )
    """)

    # 表2: 经营单元达成表 (unit_achievements - 对应 rpt1 & 驾驶舱经营单元达成)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS unit_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_name TEXT NOT NULL,           -- 经营单元
        year INTEGER NOT NULL,             -- 年度
        region_category TEXT NOT NULL,     -- 所属大区/类别
        target_amount REAL NOT NULL,       -- 不含税目标(万元)
        completed_income REAL NOT NULL,    -- 已完成收入额(万元)
        last_year_income REAL NOT NULL,    -- 去年同期收入额(万元)
        yoy_rate REAL NOT NULL,            -- 收入同比(%)
        completion_rate REAL NOT NULL,     -- 完成率(%)
        guaranteed_income REAL NOT NULL,   -- Q2保底收入(万元)
        q2_predicted_income REAL NOT NULL, -- Q2预测完成(万元)
        predicted_rate REAL NOT NULL,      -- 预测完成率(%)
        gen_compute_income REAL NOT NULL,  -- 通用计算完成收入(万元)
        gen_compute_ratio REAL NOT NULL,   -- 通用计算占比(%)
        gen_compute_yoy REAL NOT NULL,     -- 通用计算同比(%)
        ai_compute_income REAL NOT NULL,   -- 智能计算完成收入(万元)
        ai_compute_ratio REAL NOT NULL,    -- 智能计算占比(%)
        ai_compute_yoy REAL NOT NULL,      -- 智能计算同比(%)
        biz_solution_income REAL NOT NULL, -- 商业解决方案完成收入(万元)
        biz_solution_ratio REAL NOT NULL,  -- 商业解决方案占比(%)
        biz_solution_yoy REAL NOT NULL     -- 商业解决方案同比(%)
    )
    """)

    # 表3: 产品线及细分产品分析表 (product_sub_models - 对应 rpt2)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS product_sub_models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_line TEXT NOT NULL,        -- 产品线 (通用计算/智能计算/商业解决方案)
        sub_model TEXT NOT NULL,           -- 细分产品型号 (920/920X/天擎/液冷/卡多多/AT3500 G3等)
        income_2026 REAL NOT NULL,         -- 2026年已完成收入(万元)
        income_2025 REAL NOT NULL,         -- 2025年同期收入(万元)
        yoy_rate REAL NOT NULL,            -- 同比增长率(%)
        line_share_pct REAL NOT NULL       -- 占所属产品线比例(%)
    )
    """)

    # 表4: 商业解决方案专项分析表 (solution_special - 对应 rpt3)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS solution_special (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_name TEXT NOT NULL,           -- 经营单元
        target_goal REAL NOT NULL,         -- 整体收入目标(万元)
        ordered_unreceived REAL NOT NULL,  -- 订未收金额(万元)
        overall_completed REAL NOT NULL,   -- 整体完成收入(万元)
        completion_rate REAL NOT NULL,     -- 完成率(%)
        yuanqi_income REAL NOT NULL,       -- 元启解决方案收入(万元)
        vision_income REAL NOT NULL,       -- 视觉解决方案收入(万元)
        office_gov_income REAL NOT NULL,   -- 办公及政务导办收入(万元)
        ind_finance REAL NOT NULL,         -- 金融行业收入(万元)
        ind_security REAL NOT NULL,        -- 安平行业收入(万元)
        ind_edu_med REAL NOT NULL,         -- 教医行业收入(万元)
        ind_mfg_trans REAL NOT NULL,       -- 制造&交通&大企业收入(万元)
        ind_other REAL NOT NULL,           -- 其他行业收入(万元)
        ppl_pipeline_ratio REAL NOT NULL   -- PPL管道比
    )
    """)

    # 表5: 各行业达成及产品分析表 (industry_achievements - 对应 rpt4)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS industry_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        industry_name TEXT NOT NULL,       -- 行业名称 (大企业/安平/金融/数字政府/互联网/智能制造等14个行业)
        industry_category TEXT NOT NULL,   -- 行业大类 (政企/商业市场/运营商/渠道部)
        unit_name TEXT NOT NULL,           -- 主力经营单元
        completed_income REAL NOT NULL,    -- 已完成收入额(万元)
        yoy_rate REAL NOT NULL,            -- 收入同比(%)
        guaranteed_income REAL NOT NULL,   -- 保底收入(万元)
        q2_predicted_total REAL NOT NULL,  -- Q2预测总计(万元)
        q2_yoy_rate REAL NOT NULL,         -- Q2预测同比(%)
        gen_compute_income REAL NOT NULL,  -- 通用计算完成(万元)
        gen_compute_ratio REAL NOT NULL,   -- 通用计算占比(%)
        gen_compute_yoy REAL NOT NULL,     -- 通用计算同比(%)
        ai_compute_income REAL NOT NULL,   -- 智能计算完成(万元)
        ai_compute_ratio REAL NOT NULL,    -- 智能计算占比(%)
        ai_compute_yoy REAL NOT NULL,      -- 智能计算同比(%)
        biz_solution_income REAL NOT NULL, -- 商业解决方案完成(万元)
        biz_solution_ratio REAL NOT NULL,  -- 商业解决方案占比(%)
        biz_solution_yoy REAL NOT NULL     -- 商业解决方案同比(%)
    )
    """)

    # 表6: 重点经营单元产品与行业分析表 (key_unit_analysis - 对应 rpt5)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS key_unit_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_name TEXT NOT NULL,           -- 重点经营单元
        overall_yoy REAL NOT NULL,         -- 整体同比(%)
        gen_income_2026 REAL NOT NULL,     -- 通用计算2026收入(万元)
        gen_income_2025 REAL NOT NULL,     -- 通用计算2025收入(万元)
        gen_yoy REAL NOT NULL,             -- 通用计算同比(%)
        ai_income_2026 REAL NOT NULL,      -- 智能计算2026收入(万元)
        ai_income_2025 REAL NOT NULL,      -- 智能计算2025收入(万元)
        ai_yoy REAL NOT NULL,              -- 智能计算同比(%)
        sol_income_2026 REAL NOT NULL,     -- 商业解决方案2026收入(万元)
        sol_income_2025 REAL NOT NULL,     -- 商业解决方案2025收入(万元)
        sol_yoy REAL NOT NULL,             -- 商业解决方案同比(%)
        top_sub_models TEXT NOT NULL,      -- 核心细分产品JSON摘要
        warning_summary TEXT NOT NULL      -- 重点单元分析预警文案
    )
    """)

    # 表7: 商业市场合同台账表 (commercial_ledger - 对应 fields2026)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS commercial_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_key TEXT NOT NULL,          -- 主键
        seller TEXT NOT NULL,              -- 卖方
        dept_level1 TEXT NOT NULL,         -- 一级部门
        dept_level2 TEXT NOT NULL,         -- 业绩二级部门
        province TEXT NOT NULL,            -- 省份
        industry_category TEXT NOT NULL,   -- 行业大类 (政企/运营商/商业市场/渠道部)
        industry TEXT NOT NULL,            -- 行业
        product_line TEXT NOT NULL,        -- 产品线 (通用计算/智能计算/商业解决方案)
        product_model TEXT NOT NULL,       -- 产品型号 (R5300 G5/R5500 G5/920/AT3500 G3等)
        sales_person TEXT NOT NULL,        -- 业绩销售
        unit_name TEXT NOT NULL,           -- 经营单元
        sign_date TEXT NOT NULL,           -- 签订日期 (YYYY-MM-DD)
        sign_month INTEGER NOT NULL,       -- 签订月份 (1-12)
        contract_no TEXT NOT NULL,         -- 合同编号
        contract_name TEXT NOT NULL,       -- 合同名称
        buyer TEXT NOT NULL,               -- 买方/客户名称
        quantity INTEGER NOT NULL,         -- 台套数
        contract_total_wan REAL NOT NULL,  -- 合同总价(万元)
        recognized_income REAL NOT NULL,   -- 本年度已计收金额(万元)
        unrecognized_income REAL NOT NULL, -- 未计收金额(万元)
        received_payment REAL NOT NULL,    -- 本年度已回款金额(万元)
        unreceived_payment REAL NOT NULL,  -- 未回款金额(万元)
        q1_income REAL NOT NULL,           -- Q1收入(万元)
        q2_income REAL NOT NULL,           -- Q2收入(万元)
        year INTEGER NOT NULL              -- 年度
    )
    """)

    # 表8: PPL商机项目明细台账表 (ppl_projects - 对应 fieldsPPL)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ppl_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contract_no TEXT NOT NULL,         -- 合同编号
        opp_no TEXT NOT NULL,              -- 预销售/机会点编号
        industry_major TEXT NOT NULL,      -- 行业大类
        industry_minor TEXT NOT NULL,      -- 行业小类
        unit_name TEXT NOT NULL,           -- 经营单元
        sales_person TEXT NOT NULL,        -- 销售
        project_name TEXT NOT NULL,        -- 项目名称
        customer_name TEXT NOT NULL,       -- 最终客户(全称)
        product_type TEXT NOT NULL,        -- 产品类型 (服务器/存储/智算设备/商业解决方案)
        product_model TEXT NOT NULL,       -- 产品型号
        quantity INTEGER NOT NULL,         -- 台套数
        amount_tax_wan REAL NOT NULL,      -- 含税金额(万元)
        amount_notax_wan REAL NOT NULL,    -- 不含税金额(万元)
        landing_month TEXT NOT NULL,       -- 预计落地月份 (2026-01 ~ 2026-12)
        comp_risk TEXT NOT NULL,           -- 项目竞争风险 (低风险/中风险/高风险)
        contract_risk TEXT NOT NULL,       -- 合同签订风险 (低风险/中风险/高风险)
        supply_risk TEXT NOT NULL,         -- 供应&交付风险 (低风险/中风险/高风险)
        risk_level TEXT NOT NULL,          -- 项目风险等级 (低风险/中风险/高风险)
        project_stage TEXT NOT NULL,       -- 项目阶段 (商机/方案/投标/商务/签约/交付)
        project_level TEXT NOT NULL,       -- 立项级别 (集团级/公司级/部门级)
        progress_desc TEXT NOT NULL        -- 项目进展及风险说明
    )
    """)

    # ==================== 2. 系统状态与配置表 ====================

    cur.execute("""
    CREATE TABLE IF NOT EXISTS app_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        greeting INTEGER NOT NULL DEFAULT 1,
        suggestions INTEGER NOT NULL DEFAULT 1,
        tts INTEGER NOT NULL DEFAULT 0,
        stt INTEGER NOT NULL DEFAULT 0,
        hot_recommend INTEGER NOT NULL DEFAULT 1,
        model_config INTEGER NOT NULL DEFAULT 1,
        greeting_text TEXT NOT NULL,
        greeting_questions TEXT NOT NULL,
        hot_threshold INTEGER NOT NULL DEFAULT 3
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS llm_models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        base_url TEXT NOT NULL,
        model_name TEXT NOT NULL,
        api_key TEXT NOT NULL DEFAULT '',
        is_active INTEGER NOT NULL DEFAULT 0,
        is_builtin INTEGER NOT NULL DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS data_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT NOT NULL,
        name TEXT NOT NULL UNIQUE,
        label TEXT NOT NULL,
        table_name TEXT NOT NULL,
        checked INTEGER NOT NULL DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS qa_sessions (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        pinned INTEGER NOT NULL DEFAULT 0,
        user_name TEXT NOT NULL DEFAULT '管理员',
        user_role TEXT NOT NULL DEFAULT 'admin',
        model_used TEXT NOT NULL DEFAULT 'GPT-4o',
        user_feedback TEXT NOT NULL DEFAULT '',
        admin_feedback TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS qa_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        role TEXT NOT NULL,                -- 'user' or 'ai'
        text TEXT NOT NULL,                -- 用户问题 或 AI 总结纯文本
        favorited INTEGER NOT NULL DEFAULT 0,
        payload_json TEXT NOT NULL DEFAULT '{}', -- AI 结构化模块数据(steps, discovery, table, stats, chart, followups, sql, metrics)
        created_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES qa_sessions(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS qa_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS qa_question_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL UNIQUE,
        ask_count INTEGER NOT NULL DEFAULT 1,
        last_asked_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS qa_feedbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        question TEXT NOT NULL,
        user_name TEXT NOT NULL,
        msg TEXT NOT NULL,
        ai_reply TEXT NOT NULL,
        sql_text TEXT NOT NULL DEFAULT '',
        time_str TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT '待处理',
        remark TEXT NOT NULL DEFAULT ''
    )
    """)

    conn.commit()

    # 检查是否已灌入种子数据
    cur.execute("SELECT COUNT(*) as cnt FROM unit_achievements")
    if cur.fetchone()["cnt"] == 0:
        _seed_business_data(conn)

    cur.execute("SELECT COUNT(*) as cnt FROM app_config")
    if cur.fetchone()["cnt"] == 0:
        _seed_system_data(conn)

    conn.close()


def _seed_business_data(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    random.seed(202605)

    # 1. 经营单元达成数据 (21个经营单元，与原型完全对齐并赋予真实感指标)
    unit_records = [
        # (unit_name, region_category, target, income, old_income, yoy, rate, baodi, q2_pred, pred_rate, gc_inc, gc_yoy, ai_inc, ai_yoy, bs_inc, bs_yoy, sol_goal)
        ("北京代表处", "华北大区", 7950, 6200, 6392, -3.0, 78.0, 5565, 6820, 85.8, 3600, -5.0, 2100, 7.0, 500, 33.0, 1800),
        ("上海代表处", "华东大区", 7070, 5800, 5273, 10.0, 82.0, 4949, 6380, 90.2, 3200, 12.0, 2100, 6.0, 500, 25.0, 1500),
        ("浙江代表处", "华东大区", 6460, 4200, 3889, 8.0, 65.0, 4522, 5120, 79.3, 2100, 9.0, 1500, 11.0, 600, 20.0, 1300),
        ("江苏代表处", "华东大区", 5560, 3800, 3304, 15.0, 68.3, 3892, 4650, 83.6, 1800, 17.0, 1500, 9.0, 500, 20.0, 1400),
        ("深圳代表处", "华南大区", 4820, 4200, 4421, -5.0, 87.1, 3374, 4580, 95.0, 2200, 11.0, 1500, -12.0, 500, 33.0, 1600),
        ("山东代表处", "华东大区", 4090, 3200, 3019, 6.0, 78.2, 2863, 3750, 91.7, 1600, 7.0, 1200, 6.0, 400, 25.0, 1100),
        ("广州代表处", "华南大区", 3290, 2450, 2268, 8.0, 74.5, 2303, 2890, 87.8, 1220, 10.0, 910, 5.0, 320, 15.0, 1200),
        ("泛政府系统部", "行业系统部", 3800, 2920, 2630, 11.0, 76.8, 2660, 3420, 90.0, 1580, 14.0, 980, 8.0, 360, 12.0, 650),
        ("金融系统部", "行业系统部", 4500, 3680, 3200, 15.0, 81.8, 3150, 4150, 92.2, 1840, 18.0, 1280, 10.0, 560, 20.0, 950),
        ("渠道部", "渠道体系", 5200, 3960, 3168, 25.0, 76.2, 3640, 4680, 90.0, 1980, 28.0, 1320, 22.0, 660, 24.0, 2000),
        ("福建代表处", "华东大区", 2950, 1850, 2011, -8.0, 62.7, 2065, 2320, 78.6, 980, -12.0, 650, -12.0, 220, 25.0, 900),
        ("湖北办事处", "华中大区", 2600, 1920, 1810, 6.1, 73.8, 1820, 2280, 87.7, 1020, 8.0, 660, 4.0, 240, 6.0, 450),
        ("陕西办事处", "西北大区", 2400, 1760, 1692, 4.0, 73.3, 1680, 2100, 87.5, 920, 5.0, 620, 3.0, 220, 4.0, 550),
        ("安徽办事处", "华东大区", 2300, 1620, 1543, 5.0, 70.4, 1610, 1980, 86.1, 860, 6.0, 560, 4.0, 200, 5.0, 500),
        ("山西代表处", "华北大区", 2150, 1380, 1500, -8.0, 64.2, 1505, 1720, 80.0, 740, -9.0, 480, -8.0, 160, -3.0, 600),
        ("辽宁办事处", "东北大区", 2050, 1460, 1390, 5.0, 71.2, 1435, 1780, 86.8, 780, 6.0, 510, 4.0, 170, 5.0, 420),
        ("江西办事处", "华中大区", 2750, 1650, 1875, -12.0, 60.0, 1925, 2080, 75.6, 900, -18.0, 600, -20.0, 150, 20.0, 380),
        ("川藏代表处", "西南大区", 2800, 1540, 1791, -14.0, 55.0, 1960, 1950, 69.6, 820, -15.0, 520, -16.0, 200, -5.0, 800),
        ("云南办事处", "西南大区", 1850, 1280, 1231, 4.0, 69.2, 1295, 1560, 84.3, 680, 5.0, 440, 3.0, 160, 3.0, 350),
        ("内蒙古办事处", "华北大区", 1750, 1190, 1266, -6.0, 68.0, 1225, 1480, 84.6, 640, -7.0, 410, -5.0, 140, -4.0, 400),
        ("新疆代表处", "西北大区", 2200, 1180, 1494, -21.0, 53.6, 1540, 1520, 69.1, 620, -22.0, 410, -21.0, 150, -16.0, 700),
    ]

    for row in unit_records:
        (uname, reg, target, inc, old_inc, yoy, rate, baodi, q2_pred, pred_rate,
         gc_inc, gc_yoy, ai_inc, ai_yoy, bs_inc, bs_yoy, sol_goal) = row
        gc_ratio = round(gc_inc / inc * 100, 1)
        ai_ratio = round(ai_inc / inc * 100, 1)
        bs_ratio = round(bs_inc / inc * 100, 1)

        cur.execute("""
        INSERT INTO unit_achievements (
            unit_name, year, region_category, target_amount, completed_income, last_year_income,
            yoy_rate, completion_rate, guaranteed_income, q2_predicted_income, predicted_rate,
            gen_compute_income, gen_compute_ratio, gen_compute_yoy,
            ai_compute_income, ai_compute_ratio, ai_compute_yoy,
            biz_solution_income, biz_solution_ratio, biz_solution_yoy
        ) VALUES (?, 2026, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uname, reg, target, inc, old_inc, yoy, rate, baodi, q2_pred, pred_rate,
            gc_inc, gc_ratio, gc_yoy, ai_inc, ai_ratio, ai_yoy, bs_inc, bs_ratio, bs_yoy
        ))

        # 2026 & 2025 目标台账
        cur.execute("""
        INSERT INTO unit_goals (unit_name, year, commercial_goal, solution_goal)
        VALUES (?, 2026, ?, ?)
        """, (uname, target, sol_goal))
        cur.execute("""
        INSERT INTO unit_goals (unit_name, year, commercial_goal, solution_goal)
        VALUES (?, 2025, ?, ?)
        """, (uname, round(target * 0.88), round(sol_goal * 0.82)))

    # 2. 产品线及细分型号表 (product_sub_models - 对应 rpt2 数据)
    sub_models_data = [
        # 通用计算 (2026合计: 28830万, 2025合计: 15429万, 同比 +87%)
        ("通用计算", "920", 14364, 11961),
        ("通用计算", "920X", 8303, 713),
        ("通用计算", "天擎", 3690, 2362),
        ("通用计算", "液冷", 1201, 27),
        ("通用计算", "其他", 1272, 366),
        # 智能计算 (2026合计: 21365万, 2025合计: 24268万, 同比 -12%)
        ("智能计算", "AT3500 G3", 8873, 14458),
        ("智能计算", "其他", 5748, 0),
        ("智能计算", "AT800 3000", 2140, 1222),
        ("智能计算", "卡多多", 1830, 1692),
        ("智能计算", "910C", 1648, 0),
        ("智能计算", "训练", 1100, 6895),
        ("智能计算", "天巡", 27, 0),
        # 商业解决方案 (2026合计: 2570万, 2025合计: 1778万, 同比 +45%)
        ("商业解决方案", "AT3500 G3", 1548, 1058),
        ("商业解决方案", "920", 748, 80),
        ("商业解决方案", "天擎", 124, 0),
        ("商业解决方案", "AT800 3000", 59, 12),
        ("商业解决方案", "软件", 53, 409),
        ("商业解决方案", "卡多多", 35, 0),
        ("商业解决方案", "天巡", 3, 80),
        ("商业解决方案", "920X", 0, 135),
        ("商业解决方案", "昇腾其它", 0, 3),
    ]
    line_totals = {}
    for pl, _, v26, _ in sub_models_data:
        line_totals[pl] = line_totals.get(pl, 0) + v26

    for pl, sm, v26, v25 in sub_models_data:
        yoy = round((v26 - v25) / v25 * 100, 1) if v25 > 0 else (100.0 if v26 > 0 else 0.0)
        share = round(v26 / line_totals[pl] * 100, 1) if line_totals[pl] > 0 else 0.0
        cur.execute("""
        INSERT INTO product_sub_models (product_line, sub_model, income_2026, income_2025, yoy_rate, line_share_pct)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (pl, sm, v26, v25, yoy, share))

    # 3. 商业解决方案专项分析表 (solution_special - 对应 rpt3)
    rpt3_units = [
        '北京代表处', '上海代表处', '广州代表处', '深圳代表处', '川藏代表处',
        '江苏代表处', '山东代表处', '福建代表处', '山西代表处', '渠道部',
        '安徽办事处', '内蒙古办事处', '陕西办事处', '湖北办事处', '云南办事处',
        '新疆代表处', '江西办事处', '辽宁办事处', '泛政府系统部'
    ]
    rpt3_data = [
        [1800, 272, 315, 85, 120, 60, 40, 180, 120, 90, 65, 55, 0.45],
        [1500, 483, 210, 55, 80, 35, 30, 110, 85, 60, 45, 40, 0.32],
        [1200, 189, 165, 42, 68, 28, 22, 95, 60, 50, 38, 30, 0.51],
        [1600, 312, 245, 63, 98, 42, 33, 135, 88, 72, 50, 42, 0.28],
        [800, 96, 72, 18, 28, 12, 10, 38, 25, 20, 15, 12, 0.63],
        [1400, 235, 620, 155, 240, 110, 85, 320, 180, 140, 110, 95, 0.41],
        [1100, 168, 440, 105, 175, 78, 62, 225, 130, 100, 85, 70, 0.37],
        [900, 145, 385, 92, 150, 68, 55, 200, 115, 88, 72, 58, 0.52],
        [600, 78, 52, 12, 18, 8, 6, 26, 18, 14, 10, 8, 0.19],
        [2000, 530, 445, 108, 175, 78, 62, 240, 130, 100, 85, 75, 0.44],
        [500, 59, 55, 13, 20, 10, 8, 28, 18, 14, 12, 10, 0.55],
        [400, 42, 38, 9, 14, 6, 5, 18, 12, 10, 8, 6, 0.71],
        [550, 68, 62, 15, 24, 10, 8, 30, 20, 16, 14, 10, 0.38],
        [450, 55, 48, 11, 18, 8, 6, 22, 16, 12, 10, 8, 0.42],
        [350, 38, 32, 7, 12, 5, 4, 16, 10, 8, 6, 5, 0.58],
        [700, 102, 85, 22, 32, 14, 12, 42, 28, 22, 18, 15, 0.35],
        [380, 45, 40, 9, 15, 6, 5, 18, 12, 10, 8, 6, 0.62],
        [420, 52, 45, 10, 17, 7, 6, 20, 14, 12, 10, 8, 0.46],
        [650, 88, 70, 16, 26, 12, 10, 36, 22, 18, 14, 12, 0.39],
    ]
    for u, d in zip(rpt3_units, rpt3_data):
        rate = round(d[2] / d[0] * 100, 1) if d[0] else 0.0
        cur.execute("""
        INSERT INTO solution_special (
            unit_name, target_goal, ordered_unreceived, overall_completed, completion_rate,
            yuanqi_income, vision_income, office_gov_income,
            ind_finance, ind_security, ind_edu_med, ind_mfg_trans, ind_other, ppl_pipeline_ratio
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (u, d[0], d[1], d[2], rate, d[4], d[5], d[6], d[7], d[8], d[9], d[10], d[11], d[12]))

    # 4. 各行业达成及产品分析表 (industry_achievements - 对应 rpt4)
    ind_names = ['大企业', '安平', '金融', '数字政府', '互联网', '智能制造', '交通', '医疗', '通装', '教育', '油气矿山', '电力', '分销/ISV', 'JDJG']
    ind_cats = ['政企', '政企', '政企', '政企', '商业市场', '政企', '政企', '商业市场', '政企', '商业市场', '政企', '政企', '渠道部', '政企']
    ind_units = ['北京代表处', '深圳代表处', '金融系统部', '泛政府系统部', '上海代表处', '江苏代表处', '山东代表处', '浙江代表处', '陕西办事处', '江西办事处', '新疆代表处', '福建代表处', '渠道部', '北京代表处']
    rpt4_data = [
        [6520, 8, 4564, 7820, 6, 3580, 10, 2210, 5, 730, 8],
        [4130, -3, 2891, 4950, -5, 1650, -8, 1980, 2, 500, -10],
        [7280, 15, 5096, 8740, 12, 3640, 18, 2550, 10, 1090, 20],
        [12350, -5, 8645, 14200, -3, 4940, -8, 6690, 3, 720, 10],
        [4580, 22, 3206, 5500, 18, 2750, 25, 1460, 18, 370, 15],
        [15680, 12, 10976, 18800, 8, 8620, 5, 6080, -2, 980, -15],
        [3850, 6, 2695, 4620, 4, 1850, 8, 1380, 3, 620, 10],
        [2960, 18, 2072, 3550, 15, 1180, 22, 1060, 15, 720, 20],
        [2240, -8, 1568, 2690, -10, 1080, -12, 810, -5, 350, -8],
        [3180, 10, 2226, 3820, 8, 1590, 12, 1140, 8, 450, 10],
        [1870, 5, 1309, 2240, 3, 860, 8, 670, 2, 340, 5],
        [4950, 2, 3465, 5940, 0, 2230, 5, 1980, -2, 740, 3],
        [6720, 30, 4704, 8060, 25, 2350, 35, 2020, 28, 2350, 25],
        [1560, 15, 1092, 1870, 12, 620, 18, 560, 12, 380, 15],
    ]
    for name, cat, u, d in zip(ind_names, ind_cats, ind_units, rpt4_data):
        inc = d[0]
        gc_r = round(d[5] / inc * 100, 1)
        ai_r = round(d[7] / inc * 100, 1)
        bs_r = round(d[9] / inc * 100, 1)
        cur.execute("""
        INSERT INTO industry_achievements (
            industry_name, industry_category, unit_name, completed_income, yoy_rate,
            guaranteed_income, q2_predicted_total, q2_yoy_rate,
            gen_compute_income, gen_compute_ratio, gen_compute_yoy,
            ai_compute_income, ai_compute_ratio, ai_compute_yoy,
            biz_solution_income, biz_solution_ratio, biz_solution_yoy
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, cat, u, inc, d[1], d[2], d[3], d[4], d[5], gc_r, d[6], d[7], ai_r, d[8], d[9], bs_r, d[10]))

    # 5. 重点经营单元产品与行业交叉分析表 (key_unit_analysis - 对应 rpt5)
    rpt5_unit_data = {
        '深圳代表处': (-5, (4200, 3800, 11), (3500, 4000, -12), (800, 600, 33), "通用计算: 920(2100万)、920X(1200万)；智能计算: AT3500 G3(1500万)、卡多多(800万)"),
        '浙江代表处': (8, (3800, 3500, 9), (4200, 3800, 11), (600, 500, 20), "通用计算: 920(1900万)、920X(1100万)；智能计算: AT3500 G3(1800万)、卡多多(1000万)"),
        '北京代表处': (-3, (6200, 6500, -5), (4800, 4500, 7), (1200, 900, 33), "通用计算: 920(3100万)、920X(1800万)；智能计算: AT3500 G3(2000万)、卡多多(1200万)"),
        '江苏代表处': (15, (5600, 4800, 17), (3500, 3200, 9), (1800, 1500, 20), "通用计算: 920(2800万)、920X(1500万)；智能计算: AT3500 G3(1400万)、卡多多(900万)"),
        '江西办事处': (-12, (1800, 2200, -18), (1200, 1500, -20), (300, 250, 20), "通用计算: 920(900万)、920X(500万)；智能计算: AT3500 G3(500万)、卡多多(300万)"),
        '山东代表处': (6, (4500, 4200, 7), (3800, 3600, 6), (1000, 800, 25), "通用计算: 920(2250万)、920X(1300万)；智能计算: AT3500 G3(1600万)、卡多多(1000万)"),
        '上海代表处': (10, (5800, 5200, 12), (5100, 4800, 6), (1500, 1200, 25), "通用计算: 920(2900万)、920X(1600万)；智能计算: AT3500 G3(2200万)、卡多多(1300万)"),
        '福建代表处': (-8, (2800, 3200, -12), (2200, 2500, -12), (500, 400, 25), "通用计算: 920(1400万)、920X(800万)；智能计算: AT3500 G3(900万)、卡多多(550万)"),
    }
    for uname, (ov_yoy, gc, ai, sol, top_subs) in rpt5_unit_data.items():
        warn = (
            f"{uname}：整体{'同比上升' if ov_yoy >= 0 else '同比下降'}{abs(ov_yoy)}%，"
            f"其中通用计算{'增长' if gc[2] >= 0 else '下降'}{abs(gc[2])}%，"
            f"智能计算{'增长' if ai[2] >= 0 else '下降'}{abs(ai[2])}%，"
            f"商业解决方案{'增长' if sol[2] >= 0 else '下降'}{abs(sol[2])}%。"
            f"{'需重点关注！' if abs(ov_yoy) >= 8 else '整体运行平稳。'}"
        )
        cur.execute("""
        INSERT INTO key_unit_analysis (
            unit_name, overall_yoy,
            gen_income_2026, gen_income_2025, gen_yoy,
            ai_income_2026, ai_income_2025, ai_yoy,
            sol_income_2026, sol_income_2025, sol_yoy,
            top_sub_models, warning_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uname, ov_yoy, gc[0], gc[1], gc[2], ai[0], ai[1], ai[2], sol[0], sol[1], sol[2], top_subs, warn))

    # 6. 商业市场合同台账表 (commercial_ledger - 200条代表性合同台账)
    models = ['R5300 G5', 'R5500 G5', 'R5900 G5', '920', '920X', 'AT3500 G3', 'AT800 3000', '卡多多', '天擎', '液冷']
    prod_lines_map = {
        'R5300 G5': '通用计算', 'R5500 G5': '通用计算', 'R5900 G5': '通用计算',
        '920': '通用计算', '920X': '通用计算', '天擎': '通用计算', '液冷': '通用计算',
        'AT3500 G3': '智能计算', 'AT800 3000': '智能计算', '卡多多': '商业解决方案'
    }
    customers = ['中国银行', '工商银行', '建设银行', '阿里巴巴', '腾讯科技', '国家电网', '中国移动', '中国联通', '平安集团', '字节跳动', '中石化', '南方电网']
    sellers = ['北京华鲲振宇智能科技有限责任公司', '四川华鲲振宇智能科技有限责任公司', '江苏华鲲振宇智能科技有限责任公司']
    depts1 = ['系统部', '华北', '华东', '华南', '渠道部', '西南', '西北']
    provs = ['北京', '上海', '浙江', '江苏', '广东', '山东', '四川', '福建', '江西', '湖北']
    ind_cats_list = ['政企', '运营商', '商业市场', '渠道部']
    inds_list = ['智能制造', '数字政府', '金融', '大企业', '互联网', '电力', '医疗', '教育', '交通', '安平']
    units_list = [r[0] for r in unit_records]

    for i in range(200):
        m = models[i % len(models)]
        pl = prod_lines_map[m]
        cust = customers[i % len(customers)]
        unit = units_list[i % len(units_list)]
        month = (i % 5) + 1  # 1-5月为主
        day = (i % 27) + 1
        sign_date = f"2026-{month:02d}-{day:02d}"
        total_wan = round(random.uniform(80, 680), 2)
        rec_inc = round(total_wan * random.uniform(0.55, 0.95), 2)
        unrec_inc = round(total_wan - rec_inc, 2)
        rec_pay = round(rec_inc * random.uniform(0.5, 0.9), 2)
        unrec_pay = round(total_wan - rec_pay, 2)
        q1_inc = round(rec_inc * 0.6, 2) if month <= 3 else round(rec_inc * 0.25, 2)
        q2_inc = round(rec_inc - q1_inc, 2)

        cur.execute("""
        INSERT INTO commercial_ledger (
            record_key, seller, dept_level1, dept_level2, province,
            industry_category, industry, product_line, product_model,
            sales_person, unit_name, sign_date, sign_month, contract_no,
            contract_name, buyer, quantity, contract_total_wan,
            recognized_income, unrecognized_income, received_payment, unreceived_payment,
            q1_income, q2_income, year
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 2026)
        """, (
            f"CK-{10001 + i}",
            sellers[i % len(sellers)],
            depts1[i % len(depts1)],
            inds_list[i % len(inds_list)],
            provs[i % len(provs)],
            ind_cats_list[i % len(ind_cats_list)],
            inds_list[i % len(inds_list)],
            pl,
            m,
            f"销售专员{(i % 25) + 1}",
            unit,
            sign_date,
            month,
            f"HS2026{month:02d}{100 + i}",
            f"2026年{cust}{m}算力服务器采购合同",
            cust,
            (i % 40) + 2,
            total_wan,
            rec_inc,
            unrec_inc,
            rec_pay,
            unrec_pay,
            q1_inc,
            q2_inc,
        ))

    # 7. PPL 商机项目明细台账表 (ppl_projects - 包含明确的高风险项目以对齐原型问答)
    stages = ['商机', '方案', '投标', '商务', '签约', '交付']
    high_risk_projects = [
        ("HT-2026-2001", "YS-4001", "政企", "政务云", "江西办事处", "陈建国", "省级政务智算中心二期扩容项目", "江西省大数据中心", "智算设备", "AT3500 G3", 32, 680.0, 601.8, "2026-05", "高风险", "高风险", "中风险", "高风险", "商务", "集团级", "交付排期紧张，客户预算审批延迟，存在回款逾期风险"),
        ("HT-2026-2002", "YS-4002", "政企", "智慧城市", "新疆代表处", "王海涛", "智慧园区AI视觉底座建设项目", "乌鲁木齐城投集团", "商业解决方案", "卡多多", 18, 520.0, 460.2, "2026-05", "高风险", "中风险", "高风险", "高风险", "投标", "公司级", "竞争对手低价竞标，关键GPU组件供应周期拉长"),
        ("HT-2026-2003", "YS-4003", "金融", "国有银行", "北京代表处", "张明远", "总行核心交易系统信创服务器替换", "中国农业银行总行", "服务器", "920X", 64, 1280.0, 1132.7, "2026-05", "中风险", "高风险", "高风险", "高风险", "签约", "集团级", "合同商务条款审核滞后，首批液冷机柜交付延迟"),
        ("HT-2026-2004", "YS-4004", "政企", "数字政府", "川藏代表处", "刘伟东", "区域智算调度平台一期采购", "成都市数据集团", "智算设备", "AT800 3000", 24, 590.0, 522.1, "2026-06", "高风险", "高风险", "中风险", "高风险", "方案", "公司级", "客户技术指标变更频繁，项目进度落后计划3周"),
        ("HT-2026-2005", "YS-4005", "制造", "智能制造", "福建代表处", "林志强", "新能源产线工业质检AI集群项目", "宁德时代新能源", "智算设备", "910C", 16, 460.0, 407.1, "2026-05", "中风险", "中风险", "高风险", "高风险", "交付", "公司级", "现场机房改造未就绪导致设备无法上架验收入账"),
        ("HT-2026-2006", "YS-4006", "互联网", "云计算", "深圳代表处", "周浩然", "华南大区大模型推理算力池采购", "腾讯科技（深圳）", "智算设备", "AT3500 G3", 48, 960.0, 849.6, "2026-05", "高风险", "中风险", "高风险", "高风险", "商务", "集团级", "商务议价分歧较大，交付周期要求极严"),
        ("HT-2026-2007", "YS-4007", "电力", "电网数字化", "山西代表处", "赵鹏飞", "电力调度AI负荷预测平台建设", "国网山西省电力公司", "服务器", "920", 28, 380.0, 336.3, "2026-06", "高风险", "高风险", "低风险", "高风险", "投标", "部门级", "招标挂网时间推迟，竞争风险较高"),
    ]
    for p in high_risk_projects:
        cur.execute("""
        INSERT INTO ppl_projects (
            contract_no, opp_no, industry_major, industry_minor, unit_name,
            sales_person, project_name, customer_name, product_type, product_model,
            quantity, amount_tax_wan, amount_notax_wan, landing_month,
            comp_risk, contract_risk, supply_risk, risk_level,
            project_stage, project_level, progress_desc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, p)

    # 补充常规低/中风险PPL项目（使各月度合同趋势和各阶段分布完整）
    month_targets = {
        "2026-01": 800.0,
        "2026-02": 650.0,
        "2026-03": 900.0,
        "2026-04": 1000.0,
    }
    idx = 8
    for m_str, target_sum in month_targets.items():
        per_proj = round(target_sum / 5, 2)
        for j in range(5):
            u = units_list[(idx + j) % len(units_list)]
            st = stages[(idx + j) % len(stages)]
            rk = "低风险" if j % 2 == 0 else "中风险"
            md = models[(idx + j) % len(models)]
            cur.execute("""
            INSERT INTO ppl_projects (
                contract_no, opp_no, industry_major, industry_minor, unit_name,
                sales_person, project_name, customer_name, product_type, product_model,
                quantity, amount_tax_wan, amount_notax_wan, landing_month,
                comp_risk, contract_risk, supply_risk, risk_level,
                project_stage, project_level, progress_desc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"HT-2026-{2000 + idx}", f"YS-{4000 + idx}",
                ind_cats_list[j % len(ind_cats_list)], inds_list[j % len(inds_list)],
                u, f"销售代表{idx}", f"{u}{inds_list[j % len(inds_list)]}算力底座建设一期",
                customers[(idx + j) % len(customers)], "服务器", md,
                10 + j * 4, per_proj, round(per_proj / 1.13, 2), m_str,
                rk, "低风险", rk, rk, st, "公司级", f"项目处于{st}阶段，整体推进正常"
            ))
            idx += 1

    conn.commit()


def _seed_system_data(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # 1. 默认应用配置
    default_greeting_qs = [
        "各产品线销售情况",
        "北京的产品线收入情况",
        "深圳的产品销售情况",
        "2026年各经营单元收入排名",
        "政企行业收入3000万-5000万数据",
        "高风险项目有哪些"
    ]
    cur.execute("""
    INSERT INTO app_config (
        id, greeting, suggestions, tts, stt, hot_recommend, model_config,
        greeting_text, greeting_questions, hot_threshold
    ) VALUES (1, 1, 1, 1, 1, 1, 1, ?, ?, 3)
    """, (
        "欢迎使用智能AI问数，您可以向我咨询经营数据、报表分析相关问题。",
        json.dumps(default_greeting_qs, ensure_ascii=False)
    ))

    # 2. 预置模型列表
    default_models = [
        ("GPT-4o", "https://api.openai.com/v1", "gpt-4o", "", 1, 1),
        ("GPT-4o-mini", "https://api.openai.com/v1", "gpt-4o-mini", "", 0, 1),
        ("Claude 3.5 Sonnet", "https://api.anthropic.com/v1", "claude-3-5-sonnet-20241022", "", 0, 1),
        ("DeepSeek-V3", "https://api.deepseek.com/v1", "deepseek-chat", "", 0, 1),
        ("Qwen2.5-72B", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen2.5-72b-instruct", "", 0, 1),
        ("GLM-4-Plus", "https://open.bigmodel.cn/api/paas/v4", "glm-4-plus", "", 0, 1),
        ("Moonshot-v1", "https://api.moonshot.cn/v1", "moonshot-v1-8k", "", 0, 1),
    ]
    cur.executemany("""
    INSERT INTO llm_models (name, base_url, model_name, api_key, is_active, is_builtin)
    VALUES (?, ?, ?, ?, ?, ?)
    """, default_models)

    # 3. 数据源列表
    sources = [
        ("台账数据", "商业市场台账", "商业市场台账", "commercial_ledger", 1),
        ("台账数据", "PPL明细台账", "PPL明细台账", "ppl_projects", 1),
        ("台账数据", "整体目标台账", "整体目标台账", "unit_goals", 1),
        ("统计报表", "整体达成", "中国区整体及各经营单元达成", "unit_achievements", 1),
        ("统计报表", "产品分析", "产品分析", "product_sub_models", 1),
        ("统计报表", "商解专项", "商解专项分析", "solution_special", 1),
        ("统计报表", "行业达成", "行业达成分析", "industry_achievements", 1),
        ("统计报表", "重点单元", "重点单元分析", "key_unit_analysis", 1),
    ]
    cur.executemany("""
    INSERT INTO data_sources (group_name, name, label, table_name, checked)
    VALUES (?, ?, ?, ?, ?)
    """, sources)

    # 4. 初始常问问题频次统计
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    initial_hot = [
        ("政企行业收入3000万-5000万数据", 6),
        ("北京代表处今年达成情况", 5),
        ("2026年各经营单元收入排名", 4),
        ("各产品线销售情况", 4),
        ("高风险项目有哪些", 3),
    ]
    for q, cnt in initial_hot:
        cur.execute("""
        INSERT INTO qa_question_stats (question, ask_count, last_asked_at)
        VALUES (?, ?, ?)
        """, (q, cnt, now_str))

    # 5. 初始收藏问题
    cur.execute("""
    INSERT INTO qa_favorites (question, created_at)
    VALUES (?, ?)
    """, ("2026年各经营单元收入排名", now_str))

    # 6. 初始反馈校对列表（来自原型并补全真实 AI 回复上下文）
    now = datetime.now()
    initial_feedbacks = [
        (
            "上季度销售目标达成率",
            "张经理",
            "数据有误，实际达成率应为85%不是90%",
            "上季度销售目标达成率为90%，已超额完成目标。详细数据请参见销售达成率趋势图。",
            "SELECT unit_name, target_amount, completed_income, completion_rate FROM unit_achievements ORDER BY completion_rate DESC",
            (now - timedelta(days=1)).strftime("%Y/%m/%d %H:%M:%S"),
            "待处理",
            ""
        ),
        (
            "本月应收账款账龄",
            "李主管",
            "应收账款金额与报表不一致，差了约200万",
            "本月应收账款账龄主要集中在30-60天，未回款总金额约1200万元。",
            "SELECT unit_name, SUM(unreceived_payment) AS unreceived_wan FROM commercial_ledger GROUP BY unit_name",
            (now - timedelta(days=3)).strftime("%Y/%m/%d %H:%M:%S"),
            "待处理",
            ""
        ),
        (
            "各区域成本对比",
            "王主任",
            "成本数据缺少华东区域",
            "各区域对比显示华北大区收入最高，华南大区次之，西南大区最低。",
            "SELECT region_category, SUM(completed_income) FROM unit_achievements GROUP BY region_category",
            (now - timedelta(days=6)).strftime("%Y/%m/%d %H:%M:%S"),
            "待处理",
            ""
        ),
        (
            "年度预算执行情况",
            "赵专员",
            "预算执行率计算口径不对，应按不含税口径计算",
            "年度目标执行率为75.2%，整体进度符合预期，建议加快重点单元交付确收节奏。",
            "SELECT AVG(completion_rate) AS avg_rate FROM unit_achievements WHERE year = 2026",
            (now - timedelta(days=9)).strftime("%Y/%m/%d %H:%M:%S"),
            "已处理",
            "已修正为不含税目标口径，重新校验一致。"
        ),
    ]
    cur.executemany("""
    INSERT INTO qa_feedbacks (question, user_name, msg, ai_reply, sql_text, time_str, status, remark)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, initial_feedbacks)

    conn.commit()
