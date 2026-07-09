from database.connection import get_session
from database.models import SMSLog
import datetime

def send_sms(phone: str, message: str, trigger_type: str = "Notice") -> tuple[bool, str]:
    if not phone or not message:
        return False, "Recipient phone and message body are required."
        
    session = get_session()
    try:
        log = SMSLog(
            recipient_phone=phone,
            message_content=message,
            sent_at=datetime.datetime.utcnow(),
            status="Sent",
            trigger_type=trigger_type
        )
        session.add(log)
        session.commit()
        print(f"[SMS DISPATCH] [{trigger_type}] to {phone}: '{message}'")
        return True, "SMS dispatched successfully (Simulated)"
    except Exception as e:
        session.rollback()
        print(f"[SMS ERROR] Failed to send SMS to {phone}: {e}")
        return False, str(e)
    finally:
        session.close()
