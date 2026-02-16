# SlotSync - Meeting Scheduling Platform

A full-featured meeting scheduling platform built with FastAPI, SQLAlchemy, and modern HTML/CSS/JS.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The app will:
1. Create a SQLite database (`slotsync.db`)
2. Seed a default admin user
3. Set up Mon-Fri 9am-5pm availability

Then open http://localhost:8000

## Default Admin Credentials

| Field    | Value              |
|----------|--------------------|
| Email    | admin@example.com  |
| Password | admin123           |

**Change these immediately in production.**

## Features

### Fully Working
- **Admin Dashboard** - Stats, upcoming bookings overview
- **Event Type Management** - Full CRUD with slug-based URLs, durations, buffer times, colors
- **Availability Management** - Weekly recurring schedule, date-specific overrides, timezone config
- **Custom Questions** - 6 question types (text, textarea, radio, checkbox, dropdown, phone), drag-and-drop reorder, required/optional toggle
- **Booking Page** - Month calendar view, time slot selection, timezone auto-detect, form validation
- **Booking Flow** - Saves to database, shows confirmation page
- **Thank You Page** - Meta Pixel and Google Tag injection with conversion events
- **Embed System** - Inline iframe, popup modal, floating widget button with copy-to-clipboard
- **Settings** - Profile, password change, tracking pixel configuration
- **Responsive Design** - Works on mobile and desktop

### Mock (Wire Up Tomorrow)
- **Google Calendar** - Returns empty busy times, prints to console
- **Email Sending** - Prints to console instead of sending

## Project Structure

```
app/
├── main.py                  # FastAPI app entry point + seed data
├── database.py              # SQLAlchemy engine and session
├── models.py                # All database models (7 tables)
├── auth.py                  # HMAC-based token auth + bcrypt passwords
├── availability_engine.py   # Slot calculation engine
├── mock_services.py         # Mock Google Calendar + Email functions
├── routers/
│   ├── auth_router.py       # Login/logout
│   ├── admin_router.py      # Dashboard, bookings list, booking detail
│   ├── event_types_router.py # Event type CRUD
│   ├── availability_router.py # Schedule + overrides management
│   ├── questions_router.py   # Custom questions CRUD + reorder
│   ├── booking_router.py     # Public booking page + submission + confirmation
│   ├── settings_router.py    # Profile, password, tracking pixels
│   └── embed_router.py       # Embed code generation + test page
├── templates/
│   ├── base.html             # Base layout
│   ├── admin/                # All admin panel templates
│   ├── booking/              # Booking page + confirmation
│   └── embed/                # Embed test page
└── static/
    └── css/                  # Stylesheets
```

## Database Schema

| Table                    | Purpose                              |
|--------------------------|--------------------------------------|
| `users`                  | Admin accounts                       |
| `event_types`            | Meeting types with settings          |
| `availability_schedules` | Weekly recurring hours               |
| `availability_overrides` | Date-specific blocks/custom hours    |
| `custom_questions`       | Per-event-type booking form questions|
| `bookings`               | All bookings with answers            |
| `settings`               | Key-value settings (tracking pixels) |

## API Endpoints

### Public
- `GET /book/{slug}` - Booking page
- `GET /api/available-dates/{event_type_id}?month=&year=` - Available dates
- `GET /api/available-slots/{event_type_id}?date_str=&tz=` - Available time slots
- `POST /book/{slug}/submit` - Submit booking
- `GET /booking/confirmation/{booking_id}` - Thank you page

### Admin
- `GET/POST /login` - Authentication
- `GET /admin/dashboard` - Dashboard
- `GET /admin/event-types` - List event types
- `GET/POST /admin/event-types/new` - Create event type
- `GET/POST /admin/event-types/{id}/edit` - Edit event type
- `POST /admin/event-types/{id}/delete` - Delete event type
- `GET /admin/availability` - Availability settings
- `POST /admin/availability/schedule` - Save weekly schedule
- `POST /admin/availability/override` - Add date override
- `GET /admin/bookings` - Bookings list with filter/search
- `GET /admin/bookings/{id}` - Booking detail
- `POST /admin/bookings/{id}/cancel` - Cancel booking
- `GET /admin/questions/{event_type_id}` - Manage custom questions
- `GET /admin/settings` - Settings page
- `GET /admin/embed/{event_type_id}` - Embed codes
- `GET /admin/embed/test/{event_type_id}` - Embed test page

---

## TOMORROW: Adding Google Calendar & Email

### Google Calendar Integration

**Files to update:** `app/mock_services.py` (lines 17-62)

1. Go to https://console.cloud.google.com/
2. Create a project and enable the Google Calendar API
3. Create OAuth 2.0 credentials (Web application)
4. Download `credentials.json` and place in project root
5. Install: `pip install google-auth-oauthlib google-api-python-client`
6. Replace the three functions in `app/mock_services.py`:
   - `get_calendar_events()` (line 17) - Fetch real busy times
   - `create_calendar_event()` (line 46) - Create real calendar events
   - `delete_calendar_event()` (line 63) - Delete calendar events

Each function has a detailed TODO comment showing the exact replacement code.

### Email (SMTP) Integration

**Files to update:** `app/mock_services.py` (lines 70-109)

1. Get SMTP credentials (Gmail, SendGrid, Mailgun, etc.)
2. Replace the three functions in `app/mock_services.py`:
   - `send_confirmation_email()` (line 72) - Send booking confirmation
   - `send_admin_notification()` (line 95) - Notify admin of new booking
   - `send_cancellation_email()` (line 105) - Send cancellation notice

Each function has a detailed TODO comment showing the exact replacement code.

### Settings Page Integration

**File:** `app/templates/admin/settings.html`

The settings page already has "Connect Google Calendar" and "Configure Email" buttons (currently disabled). To enable them:

1. Add an OAuth flow endpoint for Google Calendar authorization
2. Add SMTP configuration fields to the settings form
3. Remove the `disabled` attribute from the buttons

### Quick Checklist

- [ ] `pip install google-auth-oauthlib google-api-python-client`
- [ ] Add `credentials.json` from Google Cloud Console
- [ ] Implement OAuth flow in a new router
- [ ] Replace `get_calendar_events()` in `mock_services.py`
- [ ] Replace `create_calendar_event()` in `mock_services.py`
- [ ] Replace `delete_calendar_event()` in `mock_services.py`
- [ ] Set SMTP credentials (host, port, user, pass)
- [ ] Replace `send_confirmation_email()` in `mock_services.py`
- [ ] Replace `send_admin_notification()` in `mock_services.py`
- [ ] Replace `send_cancellation_email()` in `mock_services.py`
- [ ] Enable buttons in settings page
