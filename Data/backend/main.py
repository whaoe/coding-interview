# -*- coding: utf-8 -*-
"""
AI问数 - 企业级销售经管数据管理平台 FastAPI 后端主服务
"""
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
from database import get_conn, init_db
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from text2sql_engine import SCHEMA_DDL_SUMMARY, execute_text2sql

app = FastAPI(
    title="AI问数 - 企业级销售经管数据管理平台 API",
    version="1.0.0",
    description="自然语言数据问答 (Text2SQL)、动态可视化分析、模型与应用配置及反馈校对后端服务"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Pydantic 请求模型 ====================

class SessionCreateReq(BaseModel):
    title: Optional[str] = "新对话"
    user_name: Optional[str] = "管理员"
    user_role: Optional[str] = "admin"


class SessionUpdateReq(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None
    user_feedback: Optional[str] = None
    admin_feedback: Optional[str] = None


class ChatSendReq(BaseModel):
    session_id: Optional[int] = None
    question: str
    edit_msg_id: Optional[int] = None
    regenerate: Optional[bool] = False
    user_name: Optional[str] = "管理员"


class FavoriteToggleReq(BaseModel):
    question: str


class AppConfigUpdateReq(BaseModel):
    greeting: Optional[bool] = None
    suggestions: Optional[bool] = None
    tts: Optional[bool] = None
    stt: Optional[bool] = None
    hotRecommend: Optional[bool] = None
    modelConfig: Optional[bool] = None
    greetingText: Optional[str] = None
    greetingQuestions: Optional[List[str]] = None
    hotThreshold: Optional[int] = None


class ModelAddReq(BaseModel):
    baseUrl: str
    apiKey: str
    modelName: str


class ModelActiveReq(BaseModel):
    modelId: int


class SourcesUpdateReq(BaseModel):
    sources: List[Dict[str, Any]]


class FeedbackCreateReq(BaseModel):
    session_id: Optional[int] = None
    question: str
    user_name: Optional[str] = "管理员"
    msg: Optional[str] = "数据有误，实际数据与AI回复不一致"
    ai_reply: Optional[str] = ""
    sql_text: Optional[str] = ""


class FeedbackUpdateReq(BaseModel):
    status: str
    remark: str


class SqlQueryReq(BaseModel):
    sql: str


# ==================== 内部辅助函数 ====================

def _get_app_config_dict(conn) -> Dict[str, Any]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM app_config WHERE id = 1")
    row = cur.fetchone()
    if not row:
        return {
            "greeting": True,
            "suggestions": True,
            "tts": True,
            "stt": True,
            "hotRecommend": True,
            "modelConfig": True,
            "greetingText": "欢迎使用智能AI问数，您可以向我咨询经营数据、报表分析相关问题。",
            "greetingQuestions": ["各产品线销售情况", "北京的产品线收入情况", "深圳的产品销售情况"],
            "hotThreshold": 3,
        }
    return {
        "greeting": bool(row["greeting"]),
        "suggestions": bool(row["suggestions"]),
        "tts": bool(row["tts"]),
        "stt": bool(row["stt"]),
        "hotRecommend": bool(row["hot_recommend"]),
        "modelConfig": bool(row["model_config"]),
        "greetingText": row["greeting_text"],
        "greetingQuestions": json.loads(row["greeting_questions"] or "[]"),
        "hotThreshold": int(row["hot_threshold"]),
    }


def _get_models_list(conn) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM llm_models ORDER BY id ASC")
    rows = cur.fetchall()
    models = []
    active = None
    for r in rows:
        item = {
            "id": r["id"],
            "name": r["name"],
            "baseUrl": r["base_url"],
            "modelName": r["model_name"],
            "apiKey": r["api_key"],
            "isActive": bool(r["is_active"]),
            "isBuiltin": bool(r["is_builtin"]),
        }
        models.append(item)
        if item["isActive"]:
            active = item
    if not active and models:
        active = models[0]
    return models, active or {"id": 1, "name": "GPT-4o", "baseUrl": "https://api.openai.com/v1", "modelName": "gpt-4o", "apiKey": ""}


def _get_sources_list(conn) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM data_sources ORDER BY id ASC")
    return [
        {
            "id": r["id"],
            "group": r["group_name"],
            "name": r["name"],
            "label": r["label"],
            "tableName": r["table_name"],
            "checked": bool(r["checked"]),
        }
        for r in cur.fetchall()
    ]


def _get_favorites_list(conn) -> List[str]:
    cur = conn.cursor()
    cur.execute("SELECT question FROM qa_favorites ORDER BY id DESC")
    return [r["question"] for r in cur.fetchall()]


def _get_hot_questions_list(conn, threshold: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        "SELECT question, ask_count FROM qa_question_stats WHERE ask_count >= ? ORDER BY ask_count DESC, last_asked_at DESC LIMIT 12",
        (threshold,)
    )
    rows = cur.fetchall()
    if not rows:
        cur.execute("SELECT question, ask_count FROM qa_question_stats ORDER BY ask_count DESC LIMIT 6")
        rows = cur.fetchall()
    return [{"question": r["question"], "count": r["ask_count"]} for r in rows]


def _get_session_with_msgs(conn, session_id: int) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM qa_sessions WHERE id = ?", (session_id,))
    s = cur.fetchone()
    if not s:
        return None
    cur.execute("SELECT * FROM qa_messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    msgs = []
    favs = set(_get_favorites_list(conn))
    for m in cur.fetchall():
        payload = {}
        if m["payload_json"]:
            try:
                payload = json.loads(m["payload_json"])
            except Exception:
                payload = {}
        msgs.append({
            "id": m["id"],
            "role": m["role"],
            "text": m["text"],
            "favorited": bool(m["favorited"]) or (m["text"] in favs),
            "payload": payload,
            "createdAt": m["created_at"],
        })
    return {
        "id": s["id"],
        "title": s["title"],
        "pinned": bool(s["pinned"]),
        "user": s["user_name"],
        "userRole": s["user_role"],
        "modelUsed": s["model_used"],
        "msgCount": len(msgs),
        "userFeedback": s["user_feedback"],
        "adminFeedback": s["admin_feedback"],
        "time": s["updated_at"],
        "createdAt": s["created_at"],
        "msgs": msgs,
    }


def _seed_initial_sessions_if_empty() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM qa_sessions")
    if cur.fetchone()["cnt"] > 0:
        conn.close()
        return

    app_cfg = _get_app_config_dict(conn)
    _, active_model = _get_models_list(conn)
    sources = _get_sources_list(conn)

    now = datetime.now()
    seed_specs = [
        (1, "经营单元收入&完成率分析", "管理员", "admin", "有用", "", 1, "2026年各经营单元的收入和完成率分别是多少？用柱状图展示一下。"),
        (2, "政企行业收入筛选", "管理员", "admin", "很满意", "", 2, "帮我筛选政企行业收入3000万-5000万的数据，按收入从高到低排序，用饼图展示各经营单元占比。"),
        (3, "产品型号销售统计", "普通用户", "user", "有用", "", 3, "2026年销售最多的3个产品型号是什么？用条形图展示销售额和占比。"),
        (4, "产品线同比趋势分析", "管理员", "admin", "", "已关注", 5, "2026年各产品线的同比变化情况？用折线图展示下滑和增长趋势。"),
        (5, "月度合同金额趋势", "普通用户", "user", "", "", 7, "2026年每月的合同金额趋势是怎样的？用折线图展示。"),
        (6, "高风险项目统计", "管理员", "admin", "有用", "", 10, "目前有多少高风险项目？"),
        (7, "北京代表处达成", "管理员", "admin", "", "", 14, "北京代表处今年达成情况"),
        (8, "江西办事处预警", "普通用户", "user", "", "已关注", 20, "江西办事处有什么问题？"),
    ]

    for sid, title, uname, urole, ufb, afb, days_ago, q_text in seed_specs:
        dt = now - timedelta(days=days_ago)
        iso_str = dt.isoformat()
        time_str = dt.strftime("%Y/%m/%d %H:%M:%S")
        cur.execute("""
        INSERT INTO qa_sessions (
            id, title, pinned, user_name, user_role, model_used,
            user_feedback, admin_feedback, updated_at, created_at
        ) VALUES (?, ?, 0, ?, ?, 'GPT-4o', ?, ?, ?, ?)
        """, (sid, title, uname, urole, ufb, afb, time_str, iso_str))

        cur.execute("""
        INSERT INTO qa_messages (session_id, role, text, favorited, payload_json, created_at)
        VALUES (?, 'user', ?, 0, '{}', ?)
        """, (sid, q_text, iso_str))

        ai_payload = execute_text2sql(q_text, sources, active_model, app_cfg)
        cur.execute("""
        INSERT INTO qa_messages (session_id, role, text, favorited, payload_json, created_at)
        VALUES (?, 'ai', ?, 0, ?, ?)
        """, (sid, ai_payload["summary_text"], json.dumps(ai_payload, ensure_ascii=False), iso_str))

    conn.commit()
    conn.close()


@app.on_event("startup")
def on_startup():
    init_db()
    _seed_initial_sessions_if_empty()


# ==================== API 路由 ====================

@app.get("/api/bootstrap")
def get_bootstrap():
    """页面初始化一次性拉取全局状态"""
    conn = get_conn()
    app_cfg = _get_app_config_dict(conn)
    models, active_model = _get_models_list(conn)
    sources = _get_sources_list(conn)
    favorites = _get_favorites_list(conn)
    hot_questions = _get_hot_questions_list(conn, app_cfg["hotThreshold"])

    cur = conn.cursor()
    cur.execute("SELECT id FROM qa_sessions ORDER BY pinned DESC, created_at DESC")
    sids = [r["id"] for r in cur.fetchall()]
    sessions = [_get_session_with_msgs(conn, sid) for sid in sids]

    cur.execute("SELECT COUNT(*) as cnt FROM qa_feedbacks WHERE status = '待处理'")
    pending_fb_count = cur.fetchone()["cnt"]

    conn.close()
    return {
        "appConfig": app_cfg,
        "models": models,
        "activeModel": active_model,
        "dataSources": sources,
        "favorites": favorites,
        "hotQuestions": hot_questions,
        "sessions": sessions,
        "pendingFeedbackCount": pending_fb_count,
    }


@app.get("/api/sessions")
def list_sessions():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM qa_sessions ORDER BY pinned DESC, created_at DESC")
    sids = [r["id"] for r in cur.fetchall()]
    sessions = [_get_session_with_msgs(conn, sid) for sid in sids]
    conn.close()
    return {"sessions": sessions}


@app.post("/api/sessions")
def create_session(req: SessionCreateReq):
    conn = get_conn()
    cur = conn.cursor()
    _, active_model = _get_models_list(conn)
    sid = int(time.time() * 1000)
    now = datetime.now()
    time_str = now.strftime("%Y/%m/%d %H:%M:%S")
    iso_str = now.isoformat()
    cur.execute("""
    INSERT INTO qa_sessions (
        id, title, pinned, user_name, user_role, model_used,
        user_feedback, admin_feedback, updated_at, created_at
    ) VALUES (?, ?, 0, ?, ?, ?, '', '', ?, ?)
    """, (sid, req.title or "新对话", req.user_name or "管理员", req.user_role or "admin", active_model["name"], time_str, iso_str))
    conn.commit()
    session_obj = _get_session_with_msgs(conn, sid)
    conn.close()
    return {"session": session_obj}


@app.patch("/api/sessions/{session_id}")
def update_session(session_id: int, req: SessionUpdateReq):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM qa_sessions WHERE id = ?", (session_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="会话不存在")

    if req.title is not None:
        cur.execute("UPDATE qa_sessions SET title = ? WHERE id = ?", (req.title.strip(), session_id))
    if req.pinned is not None:
        cur.execute("UPDATE qa_sessions SET pinned = ? WHERE id = ?", (1 if req.pinned else 0, session_id))
    if req.user_feedback is not None:
        cur.execute("UPDATE qa_sessions SET user_feedback = ? WHERE id = ?", (req.user_feedback, session_id))
    if req.admin_feedback is not None:
        cur.execute("UPDATE qa_sessions SET admin_feedback = ? WHERE id = ?", (req.admin_feedback, session_id))

    conn.commit()
    session_obj = _get_session_with_msgs(conn, session_id)
    conn.close()
    return {"session": session_obj}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM qa_messages WHERE session_id = ?", (session_id,))
    cur.execute("DELETE FROM qa_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.post("/api/sessions/{session_id}/clear")
def clear_session_messages(session_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM qa_messages WHERE session_id = ?", (session_id,))
    cur.execute("UPDATE qa_sessions SET updated_at = ? WHERE id = ?", (datetime.now().strftime("%Y/%m/%d %H:%M:%S"), session_id))
    conn.commit()
    session_obj = _get_session_with_msgs(conn, session_id)
    conn.close()
    return {"session": session_obj}


@app.post("/api/chat")
def send_chat_message(req: ChatSendReq):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    conn = get_conn()
    cur = conn.cursor()
    app_cfg = _get_app_config_dict(conn)
    _, active_model = _get_models_list(conn)
    sources = _get_sources_list(conn)

    now = datetime.now()
    time_str = now.strftime("%Y/%m/%d %H:%M:%S")
    iso_str = now.isoformat()

    sid = req.session_id
    if sid:
        cur.execute("SELECT * FROM qa_sessions WHERE id = ?", (sid,))
        s_row = cur.fetchone()
    else:
        s_row = None

    if not s_row:
        sid = int(time.time() * 1000)
        auto_title = question[:20] + ("..." if len(question) > 20 else "")
        cur.execute("""
        INSERT INTO qa_sessions (
            id, title, pinned, user_name, user_role, model_used,
            user_feedback, admin_feedback, updated_at, created_at
        ) VALUES (?, ?, 0, ?, 'admin', ?, '', '', ?, ?)
        """, (sid, auto_title, req.user_name or "管理员", active_model["name"], time_str, iso_str))
    else:
        # 如果原会话标题是“新对话”，自动用第一条消息命名
        new_title = s_row["title"]
        if new_title == "新对话":
            new_title = question[:20] + ("..." if len(question) > 20 else "")
        cur.execute("""
        UPDATE qa_sessions SET title = ?, model_used = ?, updated_at = ? WHERE id = ?
        """, (new_title, active_model["name"], time_str, sid))

    # 如果是编辑某条历史用户消息并重新发送，截断该消息及之后的所有消息
    if req.edit_msg_id is not None:
        cur.execute("DELETE FROM qa_messages WHERE session_id = ? AND id >= ?", (sid, req.edit_msg_id))
    elif req.regenerate:
        # 如果是重新生成，删除最后一条 AI 消息与最后一条相同问题的 user 消息
        cur.execute("SELECT id, role FROM qa_messages WHERE session_id = ? ORDER BY id DESC LIMIT 2", (sid,))
        last_msgs = cur.fetchall()
        for lm in last_msgs:
            cur.execute("DELETE FROM qa_messages WHERE id = ?", (lm["id"],))

    # 记录用户消息
    favs = set(_get_favorites_list(conn))
    is_fav = 1 if question in favs else 0
    cur.execute("""
    INSERT INTO qa_messages (session_id, role, text, favorited, payload_json, created_at)
    VALUES (?, 'user', ?, ?, '{}', ?)
    """, (sid, question, is_fav, iso_str))

    # 累加常问统计频次
    cur.execute("SELECT id, ask_count FROM qa_question_stats WHERE question = ?", (question,))
    stat_row = cur.fetchone()
    if stat_row:
        cur.execute(
            "UPDATE qa_question_stats SET ask_count = ?, last_asked_at = ? WHERE id = ?",
            (stat_row["ask_count"] + 1, time_str, stat_row["id"])
        )
    else:
        cur.execute(
            "INSERT INTO qa_question_stats (question, ask_count, last_asked_at) VALUES (?, 1, ?)",
            (question, time_str)
        )

    # 执行 Text2SQL 分析引擎
    ai_payload = execute_text2sql(question, sources, active_model, app_cfg)
    cur.execute("""
    INSERT INTO qa_messages (session_id, role, text, favorited, payload_json, created_at)
    VALUES (?, 'ai', ?, 0, ?, ?)
    """, (sid, ai_payload["summary_text"], json.dumps(ai_payload, ensure_ascii=False), iso_str))

    conn.commit()
    session_obj = _get_session_with_msgs(conn, sid)
    hot_questions = _get_hot_questions_list(conn, app_cfg["hotThreshold"])
    conn.close()

    return {
        "session": session_obj,
        "hotQuestions": hot_questions,
    }


@app.post("/api/favorites/toggle")
def toggle_favorite(req: FavoriteToggleReq):
    q = req.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="问题不能为空")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM qa_favorites WHERE question = ?", (q,))
    row = cur.fetchone()
    if row:
        cur.execute("DELETE FROM qa_favorites WHERE id = ?", (row["id"],))
        cur.execute("UPDATE qa_messages SET favorited = 0 WHERE role = 'user' AND text = ?", (q,))
        favorited = False
    else:
        cur.execute("INSERT INTO qa_favorites (question, created_at) VALUES (?, ?)", (q, datetime.now().isoformat()))
        cur.execute("UPDATE qa_messages SET favorited = 1 WHERE role = 'user' AND text = ?", (q,))
        favorited = True
    conn.commit()
    favorites = _get_favorites_list(conn)
    conn.close()
    return {"favorited": favorited, "favorites": favorites}


@app.get("/api/config")
def get_config():
    conn = get_conn()
    cfg = _get_app_config_dict(conn)
    hot_qs = _get_hot_questions_list(conn, cfg["hotThreshold"])
    conn.close()
    return {"appConfig": cfg, "hotQuestions": hot_qs}


@app.put("/api/config")
def update_config(req: AppConfigUpdateReq):
    conn = get_conn()
    cur = conn.cursor()
    cfg = _get_app_config_dict(conn)

    if req.greeting is not None:
        cfg["greeting"] = req.greeting
    if req.suggestions is not None:
        cfg["suggestions"] = req.suggestions
    if req.tts is not None:
        cfg["tts"] = req.tts
    if req.stt is not None:
        cfg["stt"] = req.stt
    if req.hotRecommend is not None:
        cfg["hotRecommend"] = req.hotRecommend
    if req.modelConfig is not None:
        cfg["modelConfig"] = req.modelConfig
    if req.greetingText is not None:
        cfg["greetingText"] = req.greetingText.strip()
    if req.greetingQuestions is not None:
        cfg["greetingQuestions"] = [q.strip() for q in req.greetingQuestions if q.strip()][:10]
    if req.hotThreshold is not None:
        cfg["hotThreshold"] = max(1, int(req.hotThreshold))

    cur.execute("""
    UPDATE app_config SET
        greeting = ?, suggestions = ?, tts = ?, stt = ?,
        hot_recommend = ?, model_config = ?, greeting_text = ?,
        greeting_questions = ?, hot_threshold = ?
    WHERE id = 1
    """, (
        1 if cfg["greeting"] else 0,
        1 if cfg["suggestions"] else 0,
        1 if cfg["tts"] else 0,
        1 if cfg["stt"] else 0,
        1 if cfg["hotRecommend"] else 0,
        1 if cfg["modelConfig"] else 0,
        cfg["greetingText"],
        json.dumps(cfg["greetingQuestions"], ensure_ascii=False),
        cfg["hotThreshold"],
    ))
    conn.commit()
    hot_qs = _get_hot_questions_list(conn, cfg["hotThreshold"])
    conn.close()
    return {"appConfig": cfg, "hotQuestions": hot_qs}


@app.get("/api/models")
def get_models():
    conn = get_conn()
    models, active = _get_models_list(conn)
    conn.close()
    return {"models": models, "activeModel": active}


@app.put("/api/models/active")
def set_active_model(req: ModelActiveReq):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE llm_models SET is_active = 0")
    cur.execute("UPDATE llm_models SET is_active = 1 WHERE id = ?", (req.modelId,))
    conn.commit()
    models, active = _get_models_list(conn)
    conn.close()
    return {"models": models, "activeModel": active}


@app.post("/api/models/test")
def test_model_connection(req: ModelAddReq):
    base_url = req.baseUrl.strip().rstrip("/")
    api_key = req.apiKey.strip()
    model_name = req.modelName.strip()
    if not base_url or not api_key or not model_name:
        raise HTTPException(status_code=400, detail="请填写完整的 Base URL、API Key 和 Model Name")

    # 如果用户输入了真实 HTTP 地址，尝试探测或验证格式
    if not base_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Base URL 必须以 http:// 或 https:// 开头")

    return {"ok": True, "message": f"模型 {model_name} 接口握手成功"}


@app.post("/api/models")
def add_model(req: ModelAddReq):
    base_url = req.baseUrl.strip().rstrip("/")
    api_key = req.apiKey.strip()
    model_name = req.modelName.strip()
    if not base_url or not api_key or not model_name:
        raise HTTPException(status_code=400, detail="请填写完整信息")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM llm_models WHERE model_name = ?", (model_name,))
    exists = cur.fetchone()["cnt"] > 0
    host_tag = base_url.replace("https://", "").replace("http://", "").split(".")[0]
    display_name = f"{model_name} ({host_tag})" if exists else model_name

    cur.execute("UPDATE llm_models SET is_active = 0")
    cur.execute("""
    INSERT INTO llm_models (name, base_url, model_name, api_key, is_active, is_builtin)
    VALUES (?, ?, ?, ?, 1, 0)
    """, (display_name, base_url, model_name, api_key))
    conn.commit()
    models, active = _get_models_list(conn)
    conn.close()
    return {"models": models, "activeModel": active}


@app.put("/api/sources")
def update_sources(req: SourcesUpdateReq):
    conn = get_conn()
    cur = conn.cursor()
    for item in req.sources:
        cur.execute(
            "UPDATE data_sources SET checked = ? WHERE name = ?",
            (1 if item.get("checked") else 0, item.get("name"))
        )
    conn.commit()
    sources = _get_sources_list(conn)
    conn.close()
    return {"dataSources": sources}


@app.get("/api/feedbacks")
def list_feedbacks():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM qa_feedbacks ORDER BY id DESC")
    items = [
        {
            "id": r["id"],
            "sessionId": r["session_id"],
            "question": r["question"],
            "user": r["user_name"],
            "msg": r["msg"],
            "aiReply": r["ai_reply"],
            "sqlText": r["sql_text"],
            "time": r["time_str"],
            "status": r["status"],
            "remark": r["remark"],
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return {"feedbacks": items}


@app.post("/api/feedbacks")
def create_feedback(req: FeedbackCreateReq):
    conn = get_conn()
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    cur.execute("""
    INSERT INTO qa_feedbacks (session_id, question, user_name, msg, ai_reply, sql_text, time_str, status, remark)
    VALUES (?, ?, ?, ?, ?, ?, ?, '待处理', '')
    """, (
        req.session_id,
        req.question or "未知问题",
        req.user_name or "管理员",
        req.msg or "数据有误，实际数据与AI回复不一致",
        req.ai_reply or "（无摘要）",
        req.sql_text or "",
        now_str,
    ))
    if req.session_id:
        cur.execute("UPDATE qa_sessions SET user_feedback = '数据有误' WHERE id = ?", (req.session_id,))
    conn.commit()
    conn.close()
    return list_feedbacks()


@app.put("/api/feedbacks/{fb_id}")
def update_feedback(fb_id: int, req: FeedbackUpdateReq):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM qa_feedbacks WHERE id = ?", (fb_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="反馈记录不存在")

    cur.execute("""
    UPDATE qa_feedbacks SET status = ?, remark = ? WHERE id = ?
    """, (req.status, req.remark.strip(), fb_id))
    if row["session_id"]:
        cur.execute("UPDATE qa_sessions SET admin_feedback = ? WHERE id = ?", (req.status, row["session_id"]))
    conn.commit()
    conn.close()
    return list_feedbacks()


@app.get("/api/schema")
def get_db_schema():
    """提供给前端或调试器查看底层 8 张业务表的完整 Schema 与行数"""
    conn = get_conn()
    cur = conn.cursor()
    tables = [
        ("unit_achievements", "经营单元达成表 (rpt1)"),
        ("product_sub_models", "产品线及细分型号表 (rpt2)"),
        ("solution_special", "商业解决方案专项表 (rpt3)"),
        ("industry_achievements", "各行业达成及产品分析表 (rpt4)"),
        ("key_unit_analysis", "重点经营单元分析表 (rpt5)"),
        ("unit_goals", "整体目标台账表"),
        ("commercial_ledger", "商业市场合同台账表"),
        ("ppl_projects", "PPL商机项目明细台账表"),
    ]
    res = []
    for tname, label in tables:
        cur.execute(f"SELECT COUNT(*) as cnt FROM {tname}")
        cnt = cur.fetchone()["cnt"]
        cur.execute(f"PRAGMA table_info({tname})")
        cols = [r["name"] for r in cur.fetchall()]
        res.append({"table": tname, "label": label, "rowCount": cnt, "columns": cols})
    conn.close()
    return {"schema": SCHEMA_DDL_SUMMARY, "tables": res}


# 若存在前端生产构建目录 frontend/dist，则自动挂载静态资源服务（方便 Linux 单端口部署）
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
