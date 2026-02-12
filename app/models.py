from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, Time,
    ForeignKey, Float, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), default="")
    timezone = Column(String(100), default="America/New_York")
    created_at = Column(DateTime, default=datetime.utcnow)

    event_types = relationship("EventType", back_populates="user")
    availability_schedules = relationship("AvailabilitySchedule", back_populates="user")
    availability_overrides = relationship("AvailabilityOverride", back_populates="user")
    settings = relationship("Setting", back_populates="user")


class EventType(Base):
    __tablename__ = "event_types"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=False, default=30)
    buffer_before = Column(Integer, default=0)
    buffer_after = Column(Integer, default=0)
    location_type = Column(String(50), default="video")  # video, phone, in_person, custom
    location_value = Column(String(500), default="")
    description = Column(Text, default="")
    color = Column(String(7), default="#0069ff")
    max_per_day = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="event_types")
    custom_questions = relationship("CustomQuestion", back_populates="event_type", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="event_type")


class AvailabilitySchedule(Base):
    __tablename__ = "availability_schedules"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Mon, 6=Sun
    start_time = Column(String(5), nullable=False)  # "09:00"
    end_time = Column(String(5), nullable=False)    # "17:00"
    is_enabled = Column(Boolean, default=True)

    user = relationship("User", back_populates="availability_schedules")


class AvailabilityOverride(Base):
    __tablename__ = "availability_overrides"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    override_date = Column(Date, nullable=False)
    is_available = Column(Boolean, default=False)
    start_time = Column(String(5), nullable=True)  # "09:00" or null if unavailable
    end_time = Column(String(5), nullable=True)

    user = relationship("User", back_populates="availability_overrides")


class CustomQuestion(Base):
    __tablename__ = "custom_questions"
    id = Column(Integer, primary_key=True, index=True)
    event_type_id = Column(Integer, ForeignKey("event_types.id"), nullable=False)
    question_text = Column(String(500), nullable=False)
    question_type = Column(String(50), nullable=False)  # text, textarea, radio, checkbox, dropdown, phone
    options_json = Column(Text, default="[]")  # JSON array for radio/checkbox/dropdown
    is_required = Column(Boolean, default=False)
    is_enabled = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    event_type = relationship("EventType", back_populates="custom_questions")


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    event_type_id = Column(Integer, ForeignKey("event_types.id"), nullable=False)
    invitee_name = Column(String(255), nullable=False)
    invitee_email = Column(String(255), nullable=False)
    invitee_phone = Column(String(50), default="")
    invitee_timezone = Column(String(100), default="UTC")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(20), default="confirmed")  # confirmed, cancelled, rescheduled
    answers_json = Column(Text, default="{}")
    google_event_id = Column(String(255), default="")
    cancel_token = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event_type = relationship("EventType", back_populates="bookings")


class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    setting_key = Column(String(100), nullable=False)
    setting_value = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="settings")
