import json
import datetime
import urllib.request
import urllib.parse
from database.connection import get_session
from database.master_connection import get_master_session
from database.master_models import GlobalSMSGateway
from database.models import SMSLog


def get_active_sms_gateway():
    """Retrieve active SMS Gateway credentials from master database."""
    m_session = get_master_session()
    try:
        gw = m_session.query(GlobalSMSGateway).filter(GlobalSMSGateway.is_active == True).first()
        if gw:
            return {
                "provider": gw.provider,
                "sender_id": gw.sender_id or "ORION",
                "api_key": gw.api_key or "",
                "api_secret": gw.api_secret or "",
                "endpoint_url": gw.endpoint_url or ""
            }
        return None
    except Exception as e:
        print(f"[SMS GATEWAY ERROR] Failed to query master gateway config: {e}")
        return None
    finally:
        m_session.close()


def send_sms(phone: str, message: str, trigger_type: str = "Notice") -> tuple[bool, str]:
    if not phone or not message:
        return False, "Recipient phone and message body are required."

    gw = get_active_sms_gateway()
    dispatch_success = False
    dispatch_msg = "Dispatched via Gateway"

    if gw and gw.get("api_key"):
        provider = gw.get("provider", "Arkesel")
        sender = gw.get("sender_id", "ORION")
        api_key = gw.get("api_key", "")
        api_secret = gw.get("api_secret", "")

        try:
            if provider == "Arkesel":
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                clean_recipient = phone.strip()
                if clean_recipient.startswith("0") and len(clean_recipient) == 10:
                    clean_recipient = "233" + clean_recipient[1:]

                # 1. Arkesel GET API (User specification format)
                query_params = urllib.parse.urlencode({
                    "action": "send-sms",
                    "api_key": api_key,
                    "to": clean_recipient,
                    "from": sender or "ORION",
                    "sms": message
                })
                url = f"https://sms.arkesel.com/sms/api?{query_params}"

                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                        resp_text = resp.read().decode('utf-8')
                        resp_lower = resp_text.lower()
                        if resp.status in [200, 201] and ("success" in resp_lower or "sent" in resp_lower or "100" in resp_lower):
                            dispatch_success = True
                            dispatch_msg = f"Arkesel SMS Sent: {resp_text.strip()}"
                        else:
                            dispatch_msg = f"Arkesel Response: {resp_text.strip()}"
                except Exception as ex_v1:
                    # Fallback to Arkesel V2 JSON API
                    v2_url = "https://sms.arkesel.com/api/v2/sms/send"
                    v2_payload = json.dumps({
                        "sender": sender or "ORION",
                        "recipients": [clean_recipient],
                        "message": message
                    }).encode('utf-8')
                    v2_req = urllib.request.Request(v2_url, data=v2_payload, headers={
                        'api-key': api_key,
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                    })
                    with urllib.request.urlopen(v2_req, context=ctx, timeout=10) as v2_resp:
                        v2_data = json.loads(v2_resp.read().decode('utf-8'))
                        if v2_resp.status in [200, 201] and v2_data.get("status") in ["success", 200]:
                            dispatch_success = True
                            dispatch_msg = "Arkesel SMS Sent (v2)"
                        else:
                            dispatch_msg = f"Arkesel Error: {v2_data.get('message', 'Failed')}"

            elif provider == "Hubtel":
                # Hubtel SMS API
                params = urllib.parse.urlencode({
                    "From": sender,
                    "To": phone,
                    "Content": message,
                    "ClientId": api_key,
                    "ClientSecret": api_secret
                })
                url = f"https://smsc.hubtel.com/v1/messages/send?{params}"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    if resp.status == 200:
                        dispatch_success = True
                        dispatch_msg = "Hubtel SMS Sent"
                    else:
                        dispatch_msg = f"Hubtel Response Code: {resp.status}"

            elif provider == "mNotify":
                # mNotify Quick SMS API
                url = f"https://api.mnotify.com/api/sms/quick?key={api_key}"
                payload = json.dumps({
                    "recipient": [phone],
                    "sender": sender,
                    "message": message
                }).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    if resp_data.get("status") == "success":
                        dispatch_success = True
                        dispatch_msg = "mNotify SMS Sent"
                    else:
                        dispatch_msg = f"mNotify Error: {resp_data.get('message')}"

            elif provider == "Twilio":
                # Twilio SMS API
                account_sid = api_key
                auth_token = api_secret
                url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
                data = urllib.parse.urlencode({
                    "From": sender,
                    "To": phone,
                    "Body": message
                }).encode('utf-8')
                req = urllib.request.Request(url, data=data)
                import base64
                auth_str = base64.b64encode(f"{account_sid}:{auth_token}".encode('utf-8')).decode('utf-8')
                req.add_header("Authorization", f"Basic {auth_str}")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status in [200, 201]:
                        dispatch_success = True
                        dispatch_msg = "Twilio SMS Sent"
                    else:
                        dispatch_msg = f"Twilio HTTP {resp.status}"
            else:
                dispatch_success = True
                dispatch_msg = f"Simulated SMS ({provider})"
        except Exception as http_err:
            print(f"[SMS HTTP ERROR] Provider {provider} failed: {http_err}")
            dispatch_success = False
            dispatch_msg = f"Gateway Connection Error: {http_err}"
    else:
        # Sandbox mode (No API Key set)
        dispatch_success = True
        dispatch_msg = "Simulated SMS (Sandbox Mode - Add API Key in SysAdmin)"

    # Log to branch database
    session = get_session()
    try:
        log = SMSLog(
            recipient_phone=phone,
            message_content=message,
            sent_at=datetime.datetime.utcnow(),
            status="Sent" if dispatch_success else "Failed",
            trigger_type=trigger_type
        )
        session.add(log)
        session.commit()
        print(f"[SMS DISPATCH] [{trigger_type}] to {phone}: '{message}' | Result: {dispatch_msg}")
        return dispatch_success, dispatch_msg
    except Exception as e:
        session.rollback()
        print(f"[SMS LOG ERROR] Failed to log SMS: {e}")
        return dispatch_success, dispatch_msg
    finally:
        session.close()
