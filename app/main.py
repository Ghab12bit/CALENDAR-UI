from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.database import engine, Base, SessionLocal
from app.models import User, AvailabilitySchedule, EventType, Booking, CustomQuestion, Setting
from app.auth import hash_password, create_access_token, COOKIE_NAME

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SlotSync")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Register routers
from app.routers import (
    auth_router, admin_router, event_types_router,
    availability_router, questions_router, booking_router,
    settings_router, embed_router
)
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(event_types_router.router)
app.include_router(availability_router.router)
app.include_router(questions_router.router)
app.include_router(booking_router.router)
app.include_router(settings_router.router)
app.include_router(embed_router.router)


@app.on_event("startup")
def seed_data():
    """Create default admin user, availability, demo event types, and sample bookings."""
    import json
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            admin = User(
                email="admin@example.com",
                password_hash=hash_password("admin123"),
                name="Admin User",
                timezone="America/New_York"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

            # Default Mon-Fri 9am-5pm availability
            for day in range(5):
                db.add(AvailabilitySchedule(
                    user_id=admin.id, day_of_week=day,
                    start_time="09:00", end_time="17:00", is_enabled=True
                ))
            for day in range(5, 7):
                db.add(AvailabilitySchedule(
                    user_id=admin.id, day_of_week=day,
                    start_time="09:00", end_time="17:00", is_enabled=False
                ))
            db.commit()

            # --- Demo Event Types ---
            et1 = EventType(
                user_id=admin.id, name="30 Minute Meeting", slug="30min",
                duration_minutes=30, buffer_before=0, buffer_after=5,
                location_type="video", location_value="Zoom",
                description="A quick 30 minute video call to discuss your needs.",
                color="#0069ff", max_per_day=10
            )
            et2 = EventType(
                user_id=admin.id, name="60 Minute Consultation", slug="60min-consultation",
                duration_minutes=60, buffer_before=5, buffer_after=10,
                location_type="video", location_value="Google Meet",
                description="In-depth consultation for complex projects and strategy sessions.",
                color="#7c3aed", max_per_day=5
            )
            et3 = EventType(
                user_id=admin.id, name="15 Minute Quick Chat", slug="15min-chat",
                duration_minutes=15, buffer_before=0, buffer_after=0,
                location_type="phone", location_value="I'll call you",
                description="A brief phone call to answer a quick question.",
                color="#059669", max_per_day=15
            )
            db.add_all([et1, et2, et3])
            db.commit()
            db.refresh(et1)
            db.refresh(et2)
            db.refresh(et3)

            # --- Custom Questions for 30 min meeting ---
            db.add_all([
                CustomQuestion(
                    event_type_id=et1.id, question_text="What would you like to discuss?",
                    question_type="textarea", options_json="[]",
                    is_required=True, is_enabled=True, display_order=0
                ),
                CustomQuestion(
                    event_type_id=et1.id, question_text="How did you hear about us?",
                    question_type="dropdown",
                    options_json=json.dumps(["Google Search", "Social Media", "Referral", "Other"]),
                    is_required=False, is_enabled=True, display_order=1
                ),
                CustomQuestion(
                    event_type_id=et1.id, question_text="Your company name",
                    question_type="text", options_json="[]",
                    is_required=False, is_enabled=True, display_order=2
                ),
            ])

            # --- Custom Questions for 60 min consultation ---
            db.add_all([
                CustomQuestion(
                    event_type_id=et2.id, question_text="Describe your project",
                    question_type="textarea", options_json="[]",
                    is_required=True, is_enabled=True, display_order=0
                ),
                CustomQuestion(
                    event_type_id=et2.id, question_text="Budget range",
                    question_type="radio",
                    options_json=json.dumps(["Under $5k", "$5k-$20k", "$20k-$50k", "$50k+"]),
                    is_required=True, is_enabled=True, display_order=1
                ),
                CustomQuestion(
                    event_type_id=et2.id, question_text="Preferred contact method",
                    question_type="radio",
                    options_json=json.dumps(["Email", "Phone", "Slack"]),
                    is_required=False, is_enabled=True, display_order=2
                ),
            ])
            db.commit()

            # --- Sample Bookings ---
            now = datetime.utcnow()
            # Find next weekday
            def next_weekday(d, days_ahead):
                result = d + timedelta(days=days_ahead)
                while result.weekday() >= 5:
                    result += timedelta(days=1)
                return result

            bookings_data = [
                ("Alice Johnson", "alice@example.com", "+1 555-0101", et1.id, 1, 10, 0),
                ("Bob Smith", "bob@company.com", "+1 555-0202", et2.id, 2, 14, 0),
                ("Carol Davis", "carol@startup.io", "+1 555-0303", et1.id, 3, 11, 0),
                ("David Lee", "david@agency.com", "", et3.id, 4, 9, 0),
                ("Emma Wilson", "emma@freelance.dev", "+1 555-0505", et1.id, 5, 15, 30),
            ]
            for name, email, phone, et_id, days_ahead, hour, minute in bookings_data:
                et = db.query(EventType).filter(EventType.id == et_id).first()
                start = next_weekday(now, days_ahead).replace(hour=hour, minute=minute, second=0, microsecond=0)
                end = start + timedelta(minutes=et.duration_minutes)
                answers = {"What would you like to discuss?": f"Sample topic from {name}"}
                b = Booking(
                    event_type_id=et_id, invitee_name=name, invitee_email=email,
                    invitee_phone=phone, invitee_timezone="America/New_York",
                    start_time=start, end_time=end, status="confirmed",
                    answers_json=json.dumps(answers),
                    google_event_id=f"mock_event_{name.split()[0].lower()}"
                )
                db.add(b)
            db.commit()

            print("[SEED] Created admin user: admin@example.com / admin123")
            print("[SEED] Created 3 demo event types with custom questions")
            print("[SEED] Created 5 sample bookings")
            print("[SEED] Created default Mon-Fri 9am-5pm availability")
    finally:
        db.close()


@app.get("/")
async def root(request: Request):
    """Redirect to dashboard if logged in, otherwise to login."""
    from app.auth import _decode_token
    token = request.cookies.get(COOKIE_NAME)
    if token and _decode_token(token):
        return RedirectResponse(url="/admin/dashboard")
    return RedirectResponse(url="/login")


@app.get("/auto-login")
async def auto_login():
    """Auto-login as admin and redirect to dashboard (convenience route for development)."""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            return RedirectResponse(url="/login")
        token = create_access_token({"user_id": admin.id})
        response = RedirectResponse(url="/admin/dashboard", status_code=303)
        response.set_cookie(COOKIE_NAME, token, httponly=True, max_age=86400)
        return response
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
