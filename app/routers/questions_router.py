from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import json
from app.database import get_db
from app.models import CustomQuestion, EventType
from app.auth import get_current_user

router = APIRouter(prefix="/admin/questions")
templates = Jinja2Templates(directory="app/templates")


def require_auth(request, db):
    from app.routers.admin_router import require_auth as ra
    return ra(request, db)


@router.get("/{event_type_id}", response_class=HTMLResponse)
async def questions_page(request: Request, event_type_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    et = db.query(EventType).filter(EventType.id == event_type_id, EventType.user_id == user.id).first()
    if not et:
        raise HTTPException(status_code=404)

    questions = db.query(CustomQuestion).filter(
        CustomQuestion.event_type_id == event_type_id
    ).order_by(CustomQuestion.display_order).all()

    # Parse options_json for each question
    for q in questions:
        try:
            q.parsed_options = json.loads(q.options_json) if q.options_json else []
        except json.JSONDecodeError:
            q.parsed_options = []

    return templates.TemplateResponse("admin/questions.html", {
        "request": request, "user": user, "event_type": et,
        "questions": questions, "active_page": "event_types"
    })


@router.post("/{event_type_id}/add")
async def add_question(request: Request, event_type_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    form = await request.form()
    question_text = form.get("question_text", "")
    question_type = form.get("question_type", "text")
    options_raw = form.get("options", "")
    is_required = form.get("is_required") == "on"

    # Parse options for types that need them
    options = []
    if question_type in ("radio", "checkbox", "dropdown") and options_raw:
        options = [o.strip() for o in options_raw.split("\n") if o.strip()]

    max_order = db.query(CustomQuestion).filter(
        CustomQuestion.event_type_id == event_type_id
    ).count()

    q = CustomQuestion(
        event_type_id=event_type_id,
        question_text=question_text,
        question_type=question_type,
        options_json=json.dumps(options),
        is_required=is_required,
        is_enabled=True,
        display_order=max_order
    )
    db.add(q)
    db.commit()
    return RedirectResponse(url=f"/admin/questions/{event_type_id}", status_code=303)


@router.post("/{event_type_id}/{question_id}/edit")
async def edit_question(request: Request, event_type_id: int, question_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    q = db.query(CustomQuestion).filter(CustomQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404)

    form = await request.form()
    q.question_text = form.get("question_text", q.question_text)
    q.question_type = form.get("question_type", q.question_type)
    q.is_required = form.get("is_required") == "on"

    options_raw = form.get("options", "")
    if q.question_type in ("radio", "checkbox", "dropdown") and options_raw:
        q.options_json = json.dumps([o.strip() for o in options_raw.split("\n") if o.strip()])

    db.commit()
    return RedirectResponse(url=f"/admin/questions/{event_type_id}", status_code=303)


@router.post("/{event_type_id}/{question_id}/delete")
async def delete_question(request: Request, event_type_id: int, question_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    q = db.query(CustomQuestion).filter(CustomQuestion.id == question_id).first()
    if q:
        db.delete(q)
        db.commit()
    return RedirectResponse(url=f"/admin/questions/{event_type_id}", status_code=303)


@router.post("/{event_type_id}/{question_id}/toggle")
async def toggle_question(request: Request, event_type_id: int, question_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    q = db.query(CustomQuestion).filter(CustomQuestion.id == question_id).first()
    if not q:
        return JSONResponse({"error": "not found"}, status_code=404)
    q.is_enabled = not q.is_enabled
    db.commit()
    return JSONResponse({"is_enabled": q.is_enabled})


@router.post("/{event_type_id}/reorder")
async def reorder_questions(request: Request, event_type_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    body = await request.json()
    order = body.get("order", [])
    for idx, qid in enumerate(order):
        q = db.query(CustomQuestion).filter(CustomQuestion.id == int(qid)).first()
        if q:
            q.display_order = idx
    db.commit()
    return JSONResponse({"success": True})
