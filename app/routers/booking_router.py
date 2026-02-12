from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
import json
import secrets

from app.database import get_db
from app.models import EventType, CustomQuestion, Booking, Setting
from app.availability_engine import get_available_slots, get_available_dates
from app.mock_services import create_calendar_event, send_confirmation_email, send_admin_notification

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/book/{slug}", response_class=HTMLResponse)
async def booking_page(request: Request, slug: str, db: Session = Depends(get_db)):
    et = db.query(EventType).filter(EventType.slug == slug, EventType.is_active == True).first()
    if not et:
        raise HTTPException(status_code=404, detail="Event type not found")

    questions = db.query(CustomQuestion).filter(
        CustomQuestion.event_type_id == et.id,
        CustomQuestion.is_enabled == True
    ).order_by(CustomQuestion.display_order).all()

    for q in questions:
        try:
            q.parsed_options = json.loads(q.options_json) if q.options_json else []
        except json.JSONDecodeError:
            q.parsed_options = []

    # Pre-fill params
    prefill = {
        "name": request.query_params.get("name", ""),
        "email": request.query_params.get("email", ""),
        "phone": request.query_params.get("phone", ""),
    }

    return templates.TemplateResponse("booking/booking_page.html", {
        "request": request,
        "event_type": et,
        "questions": questions,
        "prefill": prefill,
        "host_name": et.user.name or et.user.email
    })


@router.get("/api/available-dates/{event_type_id}")
async def api_available_dates(
    event_type_id: int,
    month: int,
    year: int,
    db: Session = Depends(get_db)
):
    et = db.query(EventType).filter(EventType.id == event_type_id).first()
    if not et:
        return JSONResponse({"dates": []})

    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)

    # Don't show past dates
    today = date.today()
    if start < today:
        start = today

    dates = get_available_dates(db, et.user_id, event_type_id, start, end)
    return JSONResponse({"dates": dates})


@router.get("/api/available-slots/{event_type_id}")
async def api_available_slots(
    event_type_id: int,
    date_str: str,
    tz: str = "UTC",
    db: Session = Depends(get_db)
):
    et = db.query(EventType).filter(EventType.id == event_type_id).first()
    if not et:
        return JSONResponse({"slots": []})

    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return JSONResponse({"slots": []})

    slots = get_available_slots(db, et.user_id, event_type_id, target_date, tz)
    return JSONResponse({"slots": slots})


@router.post("/book/{slug}/submit")
async def submit_booking(request: Request, slug: str, db: Session = Depends(get_db)):
    et = db.query(EventType).filter(EventType.slug == slug, EventType.is_active == True).first()
    if not et:
        raise HTTPException(status_code=404)

    form = await request.form()
    name = form.get("name", "").strip()
    email = form.get("email", "").strip()
    phone = form.get("phone", "")
    timezone = form.get("timezone", "UTC")
    slot_start = form.get("slot_start", "")
    slot_end = form.get("slot_end", "")

    if not name or not email or not slot_start or not slot_end:
        return JSONResponse({"error": "Missing required fields"}, status_code=400)

    try:
        start_dt = datetime.fromisoformat(slot_start)
        end_dt = datetime.fromisoformat(slot_end)
    except ValueError:
        return JSONResponse({"error": "Invalid time format"}, status_code=400)

    # Gather custom question answers
    answers = {}
    questions = db.query(CustomQuestion).filter(
        CustomQuestion.event_type_id == et.id,
        CustomQuestion.is_enabled == True
    ).all()

    for q in questions:
        key = f"question_{q.id}"
        if q.question_type == "checkbox":
            answers[q.question_text] = form.getlist(key)
        else:
            answers[q.question_text] = form.get(key, "")

        # Validate required
        if q.is_required:
            val = answers[q.question_text]
            if not val or (isinstance(val, list) and len(val) == 0):
                return JSONResponse(
                    {"error": f"'{q.question_text}' is required"},
                    status_code=400
                )

    cancel_token = secrets.token_urlsafe(32)

    booking = Booking(
        event_type_id=et.id,
        invitee_name=name,
        invitee_email=email,
        invitee_phone=phone,
        invitee_timezone=timezone,
        start_time=start_dt,
        end_time=end_dt,
        status="confirmed",
        answers_json=json.dumps(answers),
        cancel_token=cancel_token
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Mock calendar event
    cal_result = create_calendar_event({
        "title": f"{et.name} with {name}",
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "invitee_email": email,
        "timezone": timezone
    })
    booking.google_event_id = cal_result.get("event_id", "")
    db.commit()

    # Mock emails
    booking_details = {
        "event_name": et.name,
        "invitee_name": name,
        "invitee_email": email,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "location": et.location_value or et.location_type
    }
    send_confirmation_email(email, booking_details)
    send_admin_notification(booking_details)

    return JSONResponse({
        "success": True,
        "booking_id": booking.id,
        "redirect": f"/booking/confirmation/{booking.id}"
    })


@router.get("/booking/confirmation/{booking_id}", response_class=HTMLResponse)
async def confirmation_page(request: Request, booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404)

    et = booking.event_type
    user = et.user

    # Get tracking settings
    meta_pixel = ""
    google_tag = ""
    settings = db.query(Setting).filter(Setting.user_id == user.id).all()
    for s in settings:
        if s.setting_key == "meta_pixel":
            meta_pixel = s.setting_value
        elif s.setting_key == "google_tag":
            google_tag = s.setting_value

    answers = json.loads(booking.answers_json) if booking.answers_json else {}

    return templates.TemplateResponse("booking/confirmation.html", {
        "request": request,
        "booking": booking,
        "event_type": et,
        "answers": answers,
        "meta_pixel": meta_pixel,
        "google_tag": google_tag
    })
