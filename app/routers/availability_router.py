from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date
import json

from app.database import get_db
from app.models import AvailabilitySchedule, AvailabilityOverride, User
from app.auth import get_current_user

router = APIRouter(prefix="/admin/availability")
templates = Jinja2Templates(directory="app/templates")


def require_auth(request, db):
    from app.routers.admin_router import require_auth as ra
    return ra(request, db)


@router.get("", response_class=HTMLResponse)
async def availability_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    schedules = db.query(AvailabilitySchedule).filter(
        AvailabilitySchedule.user_id == user.id
    ).order_by(AvailabilitySchedule.day_of_week).all()

    overrides = db.query(AvailabilityOverride).filter(
        AvailabilityOverride.user_id == user.id,
        AvailabilityOverride.override_date >= date.today()
    ).order_by(AvailabilityOverride.override_date).all()

    # Build schedule map
    schedule_map = {}
    for s in schedules:
        schedule_map[s.day_of_week] = {
            "id": s.id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "is_enabled": s.is_enabled
        }

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    return templates.TemplateResponse("admin/availability.html", {
        "request": request,
        "user": user,
        "schedule_map": schedule_map,
        "overrides": overrides,
        "days": days,
        "active_page": "availability"
    })


@router.post("/schedule")
async def save_schedule(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    form_data = await request.form()
    # Delete existing schedules
    db.query(AvailabilitySchedule).filter(AvailabilitySchedule.user_id == user.id).delete()

    for day in range(7):
        enabled = form_data.get(f"day_{day}_enabled")
        start = form_data.get(f"day_{day}_start", "09:00")
        end = form_data.get(f"day_{day}_end", "17:00")

        schedule = AvailabilitySchedule(
            user_id=user.id,
            day_of_week=day,
            start_time=start,
            end_time=end,
            is_enabled=enabled == "on"
        )
        db.add(schedule)

    db.commit()
    return RedirectResponse(url="/admin/availability", status_code=303)


@router.post("/override")
async def add_override(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    form_data = await request.form()
    override_date_str = form_data.get("override_date")
    is_available = form_data.get("is_available") == "on"
    start_time = form_data.get("start_time", "")
    end_time = form_data.get("end_time", "")

    if not override_date_str:
        return RedirectResponse(url="/admin/availability", status_code=303)

    override_date = date.fromisoformat(override_date_str)

    # Remove existing override for this date
    db.query(AvailabilityOverride).filter(
        AvailabilityOverride.user_id == user.id,
        AvailabilityOverride.override_date == override_date
    ).delete()

    override = AvailabilityOverride(
        user_id=user.id,
        override_date=override_date,
        is_available=is_available,
        start_time=start_time if is_available else None,
        end_time=end_time if is_available else None
    )
    db.add(override)
    db.commit()
    return RedirectResponse(url="/admin/availability", status_code=303)


@router.post("/override/{override_id}/delete")
async def delete_override(request: Request, override_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    override = db.query(AvailabilityOverride).filter(
        AvailabilityOverride.id == override_id,
        AvailabilityOverride.user_id == user.id
    ).first()
    if override:
        db.delete(override)
        db.commit()
    return RedirectResponse(url="/admin/availability", status_code=303)


@router.post("/timezone")
async def update_timezone(request: Request, timezone: str = Form(...), db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    user.timezone = timezone
    db.commit()
    return RedirectResponse(url="/admin/availability", status_code=303)
