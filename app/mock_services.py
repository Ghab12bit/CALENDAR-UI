"""
Mock services for Google Calendar and Email.
These are placeholder functions that return dummy data.
Wire up real APIs tomorrow by replacing these functions.
"""
from datetime import datetime, timedelta


# =============================================================================
# MOCK GOOGLE CALENDAR INTEGRATION
# =============================================================================

def get_calendar_events(start_date: str, end_date: str) -> list:
    """
    TODO: Wire up Google Calendar API tomorrow.

    To integrate:
    1. Get Google OAuth credentials from https://console.cloud.google.com/
    2. Enable the Google Calendar API
    3. Set up OAuth2 flow for user authorization
    4. Replace this function with real API call:

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    def get_calendar_events(start_date, end_date):
        creds = Credentials.from_authorized_user_file('token.json')
        service = build('calendar', 'v3', credentials=creds)
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_date + 'T00:00:00Z',
            timeMax=end_date + 'T23:59:59Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    For now, returns mock busy times.
    """
    print(f"[MOCK CALENDAR] Would fetch events from {start_date} to {end_date}")
    # Return empty list so all configured availability slots are shown
    return []


def create_calendar_event(booking_data: dict) -> dict:
    """
    TODO: Wire up Google Calendar API tomorrow.

    To integrate, replace with:

    def create_calendar_event(booking_data):
        creds = Credentials.from_authorized_user_file('token.json')
        service = build('calendar', 'v3', credentials=creds)
        event = {
            'summary': booking_data['title'],
            'start': {'dateTime': booking_data['start_time'], 'timeZone': booking_data['timezone']},
            'end': {'dateTime': booking_data['end_time'], 'timeZone': booking_data['timezone']},
            'attendees': [{'email': booking_data['invitee_email']}],
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return {'event_id': event['id'], 'link': event.get('htmlLink')}
    """
    print(f"[MOCK CALENDAR] Would create event: {booking_data.get('title', 'Meeting')}")
    print(f"  Start: {booking_data.get('start_time')}")
    print(f"  End: {booking_data.get('end_time')}")
    print(f"  Invitee: {booking_data.get('invitee_email')}")
    return {"event_id": f"mock_event_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}", "link": ""}


def delete_calendar_event(event_id: str) -> bool:
    """
    TODO: Wire up Google Calendar API tomorrow.
    """
    print(f"[MOCK CALENDAR] Would delete event: {event_id}")
    return True


# =============================================================================
# MOCK EMAIL SYSTEM
# =============================================================================

def send_confirmation_email(to_email: str, booking_details: dict):
    """
    TODO: Wire up SMTP tomorrow.

    To integrate:
    1. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS in settings
    2. Replace with:

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    def send_confirmation_email(to_email, booking_details):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Booking Confirmed: {booking_details['event_name']}"
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        html = render_confirmation_template(booking_details)
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    """
    print(f"[MOCK EMAIL] Would send confirmation to {to_email}")
    print(f"  Event: {booking_details.get('event_name', 'Meeting')}")
    print(f"  Time: {booking_details.get('start_time')} - {booking_details.get('end_time')}")
    print(f"  Status: Confirmation email would be sent")


def send_admin_notification(booking_details: dict):
    """
    TODO: Wire up SMTP tomorrow.

    Same SMTP setup as send_confirmation_email.
    """
    print(f"[MOCK EMAIL] Would notify admin about new booking")
    print(f"  Invitee: {booking_details.get('invitee_name')} ({booking_details.get('invitee_email')})")
    print(f"  Event: {booking_details.get('event_name')}")
    print(f"  Time: {booking_details.get('start_time')}")


def send_cancellation_email(to_email: str, booking_details: dict):
    """
    TODO: Wire up SMTP tomorrow.
    """
    print(f"[MOCK EMAIL] Would send cancellation notice to {to_email}")
    print(f"  Event: {booking_details.get('event_name')}")
