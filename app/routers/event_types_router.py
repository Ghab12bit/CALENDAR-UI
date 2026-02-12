from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import re
from app.database import get_db
from app.models import EventType, User
from app.auth import get_current_user

router = APIRouter(prefix="/admin/event-types")
templates = Jinja2Templates(directory="app/templates")


def require_auth(request, db):
    from app.routers.admin_router import require_auth as ra
    return ra(request, db)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


@router.get("", response_class=HTMLResponse)
async def list_event_types(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    event_types = db.query(EventType).filter(EventType.user_id == user.id).order_by(EventType.created_at.desc()).all()
    return templates.TemplateResponse("admin/event_types.html", {
        "request": request, "user": user, "event_types": event_types, "active_page": "event_types"
    })


@router.get("/new", response_class=HTMLResponse)
async def new_event_type(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("admin/event_type_form.html", {
        "request": request, "user": user, "event_type": None, "active_page": "event_types", "error": None
    })


@router.post("/new")
async def create_event_type(
    request: Request,
    name: str = Form(...),
    slug: str = Form(""),
    duration_minutes: int = Form(30),
    buffer_before: int = Form(0),
    buffer_after: int = Form(0),
    location_type: str = Form("video"),
    location_value: str = Form(""),
    description: str = Form(""),
    color: str = Form("#0069ff"),
    max_per_day: int = Form(10),
    db: Session = Depends(get_db)
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if not slug:
        slug = slugify(name)

    # Ensure unique slug
    existing = db.query(EventType).filter(EventType.slug == slug).first()
    if existing:
        slug = f"{slug}-{user.id}"

    et = EventType(
        user_id=user.id, name=name, slug=slug,
        duration_minutes=duration_minutes,
        buffer_before=buffer_before, buffer_after=buffer_after,
        location_type=location_type, location_value=location_value,
        description=description, color=color, max_per_day=max_per_day
    )
    db.add(et)
    db.commit()
    return RedirectResponse(url="/admin/event-types", status_code=303)


@router.get("/{event_type_id}/edit", response_class=HTMLResponse)
async def edit_event_type(request: Request, event_type_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    et = db.query(EventType).filter(EventType.id == event_type_id, EventType.user_id == user.id).first()
    if not et:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("admin/event_type_form.html", {
        "request": request, "user": user, "event_type": et, "active_page": "event_types", "error": None
    })


@router.post("/{event_type_id}/edit")
async def update_event_type(
    request: Request,
    event_type_id: int,
    name: str = Form(...),
    slug: str = Form(""),
    duration_minutes: int = Form(30),
    buffer_before: int = Form(0),
    buffer_after: int = Form(0),
    location_type: str = Form("video"),
    location_value: str = Form(""),
    description: str = Form(""),
    color: str = Form("#0069ff"),
    max_per_day: int = Form(10),
    is_active: bool = Form(True),
    db: Session = Depends(get_db)
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    et = db.query(EventType).filter(EventType.id == event_type_id, EventType.user_id == user.id).first()
    if not et:
        raise HTTPException(status_code=404)

    if not slug:
        slug = slugify(name)

    et.name = name
    et.slug = slug
    et.duration_minutes = duration_minutes
    et.buffer_before = buffer_before
    et.buffer_after = buffer_after
    et.location_type = location_type
    et.location_value = location_value
    et.description = description
    et.color = color
    et.max_per_day = max_per_day
    et.is_active = is_active
    db.commit()
    return RedirectResponse(url="/admin/event-types", status_code=303)


@router.post("/{event_type_id}/delete")
async def delete_event_type(request: Request, event_type_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    et = db.query(EventType).filter(EventType.id == event_type_id, EventType.user_id == user.id).first()
    if not et:
        raise HTTPException(status_code=404)
    db.delete(et)
    db.commit()
    return RedirectResponse(url="/admin/event-types", status_code=303)


@router.post("/{event_type_id}/toggle")
async def toggle_event_type(request: Request, event_type_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    et = db.query(EventType).filter(EventType.id == event_type_id, EventType.user_id == user.id).first()
    if not et:
        return JSONResponse({"error": "not found"}, status_code=404)
    et.is_active = not et.is_active
    db.commit()
    return JSONResponse({"is_active": et.is_active})
