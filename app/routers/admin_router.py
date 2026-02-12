from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database import get_db
from app.models import User, EventType, Booking, Setting
from app.auth import get_current_user, COOKIE_NAME

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def require_auth(request: Request, db: Session):
    from app.auth import COOKIE_NAME, _decode_token
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    payload = _decode_token(token)
    if not payload:
        return None
    user_id = payload.get("user_id")
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Stats
    total_event_types = db.query(EventType).filter(EventType.user_id == user.id).count()
    total_bookings = db.query(Booking).join(EventType).filter(EventType.user_id == user.id).count()

    upcoming_bookings = db.query(Booking).join(EventType).filter(
        EventType.user_id == user.id,
        Booking.start_time >= datetime.utcnow(),
        Booking.status == "confirmed"
    ).order_by(Booking.start_time).limit(10).all()

    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())
    bookings_this_week = db.query(Booking).join(EventType).filter(
        EventType.user_id == user.id,
        Booking.start_time >= datetime.combine(week_start, datetime.min.time()),
        Booking.status == "confirmed"
    ).count()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user,
        "total_event_types": total_event_types,
        "total_bookings": total_bookings,
        "upcoming_bookings": upcoming_bookings,
        "bookings_this_week": bookings_this_week,
        "active_page": "dashboard"
    })


@router.get("/bookings", response_class=HTMLResponse)
async def bookings_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    status_filter = request.query_params.get("status", "all")
    search = request.query_params.get("search", "")

    query = db.query(Booking).join(EventType).filter(EventType.user_id == user.id)

    if status_filter != "all":
        query = query.filter(Booking.status == status_filter)
    if search:
        query = query.filter(
            (Booking.invitee_name.ilike(f"%{search}%")) |
            (Booking.invitee_email.ilike(f"%{search}%"))
        )

    bookings = query.order_by(Booking.start_time.desc()).all()

    return templates.TemplateResponse("admin/bookings.html", {
        "request": request,
        "user": user,
        "bookings": bookings,
        "status_filter": status_filter,
        "search": search,
        "active_page": "bookings"
    })


@router.get("/bookings/{booking_id}", response_class=HTMLResponse)
async def booking_detail(request: Request, booking_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    booking = db.query(Booking).join(EventType).filter(
        Booking.id == booking_id,
        EventType.user_id == user.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    import json
    answers = json.loads(booking.answers_json) if booking.answers_json else {}

    return templates.TemplateResponse("admin/booking_detail.html", {
        "request": request,
        "user": user,
        "booking": booking,
        "answers": answers,
        "active_page": "bookings"
    })


@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    booking = db.query(Booking).join(EventType).filter(
        Booking.id == booking_id,
        EventType.user_id == user.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = "cancelled"
    db.commit()

    from app.mock_services import delete_calendar_event, send_cancellation_email
    if booking.google_event_id:
        delete_calendar_event(booking.google_event_id)
    send_cancellation_email(booking.invitee_email, {
        "event_name": booking.event_type.name,
        "start_time": booking.start_time.isoformat()
    })

    return RedirectResponse(url=f"/admin/bookings/{booking_id}", status_code=303)
