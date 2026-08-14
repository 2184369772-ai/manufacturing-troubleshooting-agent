from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.agent import build_result, next_follow_up
from app.db import (
    append_message,
    create_case_record,
    create_session,
    finalize_session,
    get_session,
    init_db,
    list_case_records,
    list_session_messages,
    list_sessions,
    list_test_cases,
    update_session_progress,
)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Manufacturing Troubleshooting Agent Demo")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

STATUS_LABELS = {
    "collecting": "追问中",
    "resolved": "已完成",
    "escalated": "待人工升级",
}
URGENCY_LABELS = {
    "Low": "低",
    "Medium": "中",
    "High": "高",
}
RISK_LEVEL_LABELS = {
    "Low": "低",
    "Medium": "中",
    "High": "高",
}
ROLE_LABELS = {
    "agent": "AI Agent",
    "operator": "用户输入",
}


@app.on_event("startup")
def startup() -> None:
    init_db()


def render(request: Request, template_name: str, context: dict) -> HTMLResponse:
    base = {
        "request": request,
        "sessions": list_sessions()[:6],
        "case_records": list_case_records()[:6],
        "status_labels": STATUS_LABELS,
        "urgency_labels": URGENCY_LABELS,
        "risk_level_labels": RISK_LEVEL_LABELS,
        "role_labels": ROLE_LABELS,
    }
    base.update(context)
    return templates.TemplateResponse(template_name, base)


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return render(request, "home.html", {"test_cases": list_test_cases()})


@app.post("/sessions/new")
def session_new(
    question_text: str = Form(...),
    line_name: str = Form(""),
    impact_scope: str = Form(""),
    urgency: str = Form("Medium"),
) -> RedirectResponse:
    title = question_text.strip()[:100] or "Synthetic Data 诊断会话"
    session_id = create_session(title=title, question_text=question_text.strip(), line_name=line_name.strip(), impact_scope=impact_scope.strip(), urgency=urgency.strip())
    session = get_session(session_id)
    follow_up = next_follow_up(session["question_text"], session["answers_json"], session["asked_questions_json"])
    if follow_up:
        append_message(session_id, "agent", follow_up["question"])
        asked = session["asked_questions_json"] + [follow_up["key"]]
        update_session_progress(session_id, "collecting", session["answers_json"], asked, len(asked))
    else:
        finalize(request_session_id=session_id)
    return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)


def finalize(request_session_id: int) -> None:
    session = get_session(request_session_id)
    result = build_result(
        question_text=session["question_text"],
        line_name=session["line_name"] or "",
        impact_scope=session["impact_scope"] or "",
        urgency=session["urgency"] or "Medium",
        answers=session["answers_json"],
    )
    status = "escalated" if result["human_escalation"]["required"] else "resolved"
    finalize_session(request_session_id, status, result)
    append_message(request_session_id, "agent", "结构化结果已生成。请查看下方的可能原因、建议检查项、风险等级与人工升级说明。")
    create_case_record(
        session_id=request_session_id,
        title=session["title"],
        status=status,
        risk_level=result["risk_level"],
        escalation_required=result["human_escalation"]["required"],
        summary_text=result["risk_warning"],
        result=result,
    )


@app.get("/sessions/{session_id}", response_class=HTMLResponse)
def session_detail(request: Request, session_id: int) -> HTMLResponse:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="未找到对应会话")
    return render(
        request,
        "session_detail.html",
        {
            "session": session,
            "messages": list_session_messages(session_id),
            "test_cases": list_test_cases(),
        },
    )


@app.post("/sessions/{session_id}/reply")
def session_reply(session_id: int, answer_text: str = Form(...)) -> RedirectResponse:
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="未找到对应会话")
    if session["status"] not in {"collecting"}:
        return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)

    append_message(session_id, "operator", answer_text.strip())
    asked = session["asked_questions_json"]
    answers = dict(session["answers_json"])
    if asked:
        answers[asked[-1]] = answer_text.strip()
    update_session_progress(session_id, "collecting", answers, asked, len(asked))

    follow_up = next_follow_up(session["question_text"], answers, asked)
    if follow_up:
        append_message(session_id, "agent", follow_up["question"])
        asked = asked + [follow_up["key"]]
        update_session_progress(session_id, "collecting", answers, asked, len(asked))
    else:
        finalize(session_id)

    return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)


@app.get("/cases", response_class=HTMLResponse)
def case_index(request: Request) -> HTMLResponse:
    return render(request, "cases.html", {"all_cases": list_case_records()})


@app.get("/knowledge", response_class=HTMLResponse)
def knowledge_index(request: Request) -> HTMLResponse:
    from app.db import list_knowledge_items

    return render(request, "knowledge.html", {"knowledge_items": list_knowledge_items(), "test_cases": list_test_cases()})
