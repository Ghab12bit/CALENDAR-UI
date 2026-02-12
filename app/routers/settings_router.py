from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Setting, User
from app.auth import get_current_user

router = APIRouter(prefix="/admin/settings")
templates = Jinja2Templates(directory="app/templates")


def require_auth(request, db):
    from app.routers.admin_router import require_auth as ra
    return ra(request, db)


def get_setting(db, user_id, key, default=""):
    s = db.query(Setting).filter(Setting.user_id == user_id, Setting.setting_key == key).first()
    return s.setting_value if s else default


def set_setting(db, user_id, key, value):
    s = db.query(Setting).filter(Setting.user_id == user_id, Setting.setting_key == key).first()
    if s:
        s.setting_value = value
    else:
        s = Setting(user_id=user_id, setting_key=key, setting_value=value)
        db.add(s)
    db.commit()


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    meta_pixel = get_setting(db, user.id, "meta_pixel")
    google_tag = get_setting(db, user.id, "google_tag")

    return templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "user": user,
        "meta_pixel": meta_pixel,
        "google_tag": google_tag,
        "active_page": "settings",
        "saved": request.query_params.get("saved", "")
    })


@router.post("/tracking")
async def save_tracking(
    request: Request,
    meta_pixel: str = Form(""),
    google_tag: str = Form(""),
    db: Session = Depends(get_db)
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    set_setting(db, user.id, "meta_pixel", meta_pixel)
    set_setting(db, user.id, "google_tag", google_tag)
    return RedirectResponse(url="/admin/settings?saved=tracking", status_code=303)


@router.post("/profile")
async def save_profile(
    request: Request,
    name: str = Form(""),
    timezone: str = Form("America/New_York"),
    db: Session = Depends(get_db)
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user.name = name
    user.timezone = timezone
    db.commit()
    return RedirectResponse(url="/admin/settings?saved=profile", status_code=303)


@router.post("/password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = require_auth(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    from app.auth import verify_password, hash_password
    if not verify_password(current_password, user.password_hash):
        return RedirectResponse(url="/admin/settings?saved=password_error", status_code=303)

    user.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse(url="/admin/settings?saved=password", status_code=303)
