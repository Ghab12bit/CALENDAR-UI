from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.database import engine, Base, SessionLocal
from app.models import User, AvailabilitySchedule
from app.auth import hash_password

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Calendly Clone")
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
    """Create default admin user and availability if not exists."""
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
            for day in range(5):  # Mon=0 to Fri=4
                schedule = AvailabilitySchedule(
                    user_id=admin.id,
                    day_of_week=day,
                    start_time="09:00",
                    end_time="17:00",
                    is_enabled=True
                )
                db.add(schedule)
            # Sat and Sun disabled
            for day in range(5, 7):
                schedule = AvailabilitySchedule(
                    user_id=admin.id,
                    day_of_week=day,
                    start_time="09:00",
                    end_time="17:00",
                    is_enabled=False
                )
                db.add(schedule)
            db.commit()
            print("[SEED] Created admin user: admin@example.com / admin123")
            print("[SEED] Created default Mon-Fri 9am-5pm availability")
    finally:
        db.close()


@app.get("/")
async def root():
    return RedirectResponse(url="/login")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
