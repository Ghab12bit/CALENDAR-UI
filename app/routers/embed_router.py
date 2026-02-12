from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import EventType
from app.auth import get_current_user

router = APIRouter(prefix="/admin/embed")
templates = Jinja2Templates(directory="app/templates")


def require_auth(request, db):
    from app.routers.admin_router import require_auth as ra
    return ra(request, db)


@router.get("/{event_type_id}", response_class=HTMLResponse)
async def embed_page(request: Request, event_type_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=303)

    et = db.query(EventType).filter(EventType.id == event_type_id, EventType.user_id == user.id).first()
    if not et:
        raise HTTPException(status_code=404)

    base_url = str(request.base_url).rstrip("/")
    booking_url = f"{base_url}/book/{et.slug}"

    return templates.TemplateResponse("admin/embed.html", {
        "request": request,
        "user": user,
        "event_type": et,
        "booking_url": booking_url,
        "base_url": base_url,
        "active_page": "event_types"
    })


@router.get("/test/{event_type_id}", response_class=HTMLResponse)
async def embed_test_page(request: Request, event_type_id: int, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=303)

    et = db.query(EventType).filter(EventType.id == event_type_id, EventType.user_id == user.id).first()
    if not et:
        raise HTTPException(status_code=404)

    base_url = str(request.base_url).rstrip("/")
    booking_url = f"{base_url}/book/{et.slug}"

    return templates.TemplateResponse("embed/test_page.html", {
        "request": request,
        "event_type": et,
        "booking_url": booking_url,
        "base_url": base_url
    })
