"""
Availability Calculation Engine.
Computes available time slots for a given date, considering:
- Weekly availability rules
- Date-specific overrides
- Calendar events (from mock/real calendar)
- Buffer times
- Max bookings per day
- Event duration
"""
from datetime import datetime, timedelta, date, time
from sqlalchemy.orm import Session
from app.models import (
    AvailabilitySchedule, AvailabilityOverride, Booking, EventType
)
from app.mock_services import get_calendar_events


def get_available_slots(
    db: Session,
    user_id: int,
    event_type_id: int,
    target_date: date,
    requester_timezone: str = "UTC"
) -> list:
    """
    Returns a list of available time slots for a specific date.
    Each slot is a dict: {"start": "HH:MM", "end": "HH:MM"}
    Times are in UTC for storage; frontend converts to requester_timezone.
    """
    event_type = db.query(EventType).filter(EventType.id == event_type_id).first()
    if not event_type:
        return []

    duration = event_type.duration_minutes
    buffer_before = event_type.buffer_before
    buffer_after = event_type.buffer_after

    # 1. Check for date-specific override
    override = db.query(AvailabilityOverride).filter(
        AvailabilityOverride.user_id == user_id,
        AvailabilityOverride.override_date == target_date
    ).first()

    if override:
        if not override.is_available:
            return []  # Day is blocked
        time_ranges = [{"start": override.start_time, "end": override.end_time}]
    else:
        # 2. Get weekly schedule for this day of week
        day_of_week = target_date.weekday()  # 0=Monday
        schedules = db.query(AvailabilitySchedule).filter(
            AvailabilitySchedule.user_id == user_id,
            AvailabilitySchedule.day_of_week == day_of_week,
            AvailabilitySchedule.is_enabled == True
        ).all()

        if not schedules:
            return []

        time_ranges = [{"start": s.start_time, "end": s.end_time} for s in schedules]

    # 3. Get existing bookings for this date
    day_start = datetime.combine(target_date, time.min)
    day_end = datetime.combine(target_date, time.max)

    existing_bookings = db.query(Booking).filter(
        Booking.event_type_id.in_(
            db.query(EventType.id).filter(EventType.user_id == user_id)
        ),
        Booking.start_time >= day_start,
        Booking.start_time <= day_end,
        Booking.status != "cancelled"
    ).all()

    # Check max bookings per day
    if len(existing_bookings) >= event_type.max_per_day:
        return []

    # 4. Get calendar events (mock or real)
    calendar_events = get_calendar_events(
        target_date.isoformat(),
        target_date.isoformat()
    )

    # 5. Build busy periods (bookings + calendar events)
    busy_periods = []
    for booking in existing_bookings:
        busy_start = booking.start_time - timedelta(minutes=buffer_before)
        busy_end = booking.end_time + timedelta(minutes=buffer_after)
        busy_periods.append((busy_start, busy_end))

    for cal_event in calendar_events:
        try:
            start = datetime.fromisoformat(cal_event["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(cal_event["end"].replace("Z", "+00:00"))
            # Strip tzinfo for naive comparison
            start = start.replace(tzinfo=None)
            end = end.replace(tzinfo=None)
            busy_periods.append((start, end))
        except (KeyError, ValueError):
            continue

    # 6. Generate available slots
    available_slots = []
    for time_range in time_ranges:
        start_h, start_m = map(int, time_range["start"].split(":"))
        end_h, end_m = map(int, time_range["end"].split(":"))

        range_start = datetime.combine(target_date, time(start_h, start_m))
        range_end = datetime.combine(target_date, time(end_h, end_m))

        current = range_start
        while current + timedelta(minutes=duration) <= range_end:
            slot_start = current
            slot_end = current + timedelta(minutes=duration)

            # Check with buffers
            buffered_start = slot_start - timedelta(minutes=buffer_before)
            buffered_end = slot_end + timedelta(minutes=buffer_after)

            is_available = True
            for busy_start, busy_end in busy_periods:
                if buffered_start < busy_end and buffered_end > busy_start:
                    is_available = False
                    break

            if is_available:
                available_slots.append({
                    "start": slot_start.strftime("%H:%M"),
                    "end": slot_end.strftime("%H:%M"),
                    "start_iso": slot_start.isoformat(),
                    "end_iso": slot_end.isoformat()
                })

            current += timedelta(minutes=15)  # 15-min slot increments

    return available_slots


def get_available_dates(
    db: Session,
    user_id: int,
    event_type_id: int,
    start_date: date,
    end_date: date
) -> list:
    """
    Returns list of dates that have at least one available slot.
    """
    available_dates = []
    current = start_date
    while current <= end_date:
        slots = get_available_slots(db, user_id, event_type_id, current)
        if slots:
            available_dates.append(current.isoformat())
        current += timedelta(days=1)
    return available_dates
