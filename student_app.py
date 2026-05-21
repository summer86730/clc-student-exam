"""
CLC Oral Exam — Student Registration Portal  v2
新增：查詢報名紀錄入口 / 自選 Email 確認信 / .ics 行事曆下載
"""

import streamlit as st
import os
from datetime import datetime, timedelta

# ══════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════
st.set_page_config(
    page_title="CLC Oral Exam Registration",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════
DATES_EN  = ["5/26 (Mon)", "5/27 (Tue)", "5/28 (Wed)", "5/29 (Thu)"]
DATES_ZH  = ["5/26 (一)",  "5/27 (二)",  "5/28 (三)",  "5/29 (四)"]
DATES_ISO = ["2025-05-26", "2025-05-27", "2025-05-28", "2025-05-29"]
AM_SLOTS  = ["08:00", "09:00", "10:00", "11:00"]
PM_SLOTS  = ["14:00", "15:00", "16:00", "17:00"]
AM_LOCAL  = ["Prev. night EDT 20:00", "EDT 21:00", "EDT 22:00", "EDT 23:00"]
PM_LOCAL  = ["CET 07:00", "CET 08:00", "CET 09:00", "CET 10:00"]
AM_EARLY  = ["Prev. night EDT 19:40", "EDT 20:40", "EDT 21:40", "EDT 22:40"]
PM_EARLY  = ["CET 06:40", "CET 07:40", "CET 08:40", "CET 09:40"]
ALL_SLOTS  = AM_SLOTS + PM_SLOTS
ALL_LOCAL  = AM_LOCAL + PM_LOCAL
ALL_EARLY  = AM_EARLY + PM_EARLY
# TST hours for each slot index (0-7)
SLOT_TST_H = [8, 9, 10, 11, 14, 15, 16, 17]
SLOT_REG   = ["us"] * 4 + ["eu"] * 4

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
[data-testid="stSidebar"]    { display: none; }
[data-testid="stDecoration"] { display: none; }
footer                       { display: none !important; }

.clc-header {
  background: #e6f1fb; border-bottom: 1px solid #b5d4f4;
  padding: 1rem 1.25rem .8rem; margin: -1rem -1rem 1.5rem;
  display: flex; align-items: center; gap: 12px;
}
.clc-logo  { font-size: 1.8rem; }
.clc-title { font-size: 1rem; font-weight: 600; color: #0c447c; }
.clc-sub   { font-size: .78rem; color: #378add; margin-top: 1px; }

/* Landing role buttons */
.role-btn {
  border: 1px solid #dde; border-radius: 12px;
  padding: 1.25rem 1rem; text-align: center;
  cursor: pointer; transition: border-color .15s, background .15s;
  background: white;
}
.role-btn:hover { border-color: #378add; background: #f0f7fe; }
.role-icon { font-size: 2rem; margin-bottom: 8px; }
.role-name { font-size: .95rem; font-weight: 600; color: #1a1a18; margin-bottom: 3px; }
.role-desc { font-size: .78rem; color: #888; }

/* Booking confirmed card */
.book-card {
  background: #e1f5ee; border: 1.5px solid #9fe1cb;
  border-radius: 12px; padding: 1.1rem 1.3rem; margin-bottom: 1.2rem;
}
.book-title { font-weight: 700; color: #085041; font-size: 1rem; margin-bottom: 6px; }
.book-time  { font-size: 1.05rem; font-weight: 600; color: #085041; }
.book-local { font-size: .88rem; margin-top: 5px; color: #0f6e56; }
.book-early { font-size: .82rem; color: #0f6e56; margin-top: 3px; }
.book-hint  { font-size: .75rem; color: #666; margin-top: 10px; border-top: 1px solid #b5e8d4; padding-top: 8px; }

/* Slot option cards */
.slot-opt { border: 1px solid #dde; border-radius: 10px; padding: 14px 16px; margin-bottom: 8px; }
.slot-sel-am { border: 2px solid #ef9f27 !important; background: #faeeda14; }
.slot-sel-pm { border: 2px solid #378add !important; background: #e6f1fb14; }

/* Tags */
.tag-am { background:#faeeda; color:#633806; padding:3px 10px; border-radius:6px; font-size:.8rem; font-weight:500; }
.tag-pm { background:#e6f1fb; color:#0c447c; padding:3px 10px; border-radius:6px; font-size:.8rem; font-weight:500; }

/* Divider text */
.or-divider { text-align:center; color:#aaa; font-size:.82rem; margin:.5rem 0; }

/* Notice */
.notice {
  background:#f7f6f3; border:1px solid #e0ddd6;
  border-radius:8px; padding:10px 14px;
  font-size:.82rem; color:#666; line-height:1.65; margin-bottom:1rem;
}

/* Email section */
.email-section {
  background:#f0f7fe; border:1px solid #b5d4f4;
  border-radius:10px; padding:1rem 1.2rem; margin-top:1rem;
}
.email-title { font-size:.9rem; font-weight:600; color:#0c447c; margin-bottom:4px; }
.email-sub   { font-size:.78rem; color:#378add; margin-bottom:.75rem; }

/* Check page */
.check-card {
  background: #fff8ec; border: 1.5px solid #fac775;
  border-radius: 12px; padding: 1.1rem 1.3rem; margin-bottom: 1rem;
}
.check-title { font-weight: 700; color: #633806; font-size: .95rem; margin-bottom: 6px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# FIREBASE / STORAGE
# ══════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def init_firebase():
    try:
        import firebase_admin
        from firebase_admin import credentials, db
        if not firebase_admin._apps:
            cred_dict = dict(st.secrets["firebase_credentials"])
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {"databaseURL": st.secrets["firebase_url"]})
        return db, True
    except Exception:
        return None, False

_fb, FIREBASE_OK = init_firebase()
_LOCAL_PATH = "/tmp/clc_local_db.json"

def _local_load():
    import json
    if os.path.exists(_LOCAL_PATH):
        with open(_LOCAL_PATH) as f:
            return json.load(f)
    return {}

def _local_save(data):
    import json
    with open(_LOCAL_PATH, "w") as f:
        json.dump(data, f)

def db_get(path: str):
    if FIREBASE_OK:
        return _fb.reference(path).get()
    data = _local_load()
    for k in path.strip("/").split("/"):
        data = data.get(k) if isinstance(data, dict) else None
        if data is None:
            return None
    return data

def db_set(path: str, value):
    import json
    if FIREBASE_OK:
        _fb.reference(path).set(value)
    else:
        data = _local_load()
        keys = path.strip("/").split("/")
        d = data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        _local_save(data)

# ══════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════
for k, v in {
    "screen":       "landing",
    "user_name":    "",
    "region":       "eu",
    "my_booking":   None,
    "open_slots":   [],
    "email_sent":   False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def go(screen: str):
    st.session_state.screen = screen
    st.rerun()

# ══════════════════════════════════════════════════════
# UTILS: ICS + EMAIL
# ══════════════════════════════════════════════════════
def generate_ics(name: str, di: int, si: int) -> bytes:
    """Generate iCalendar .ics file content for the booked slot."""
    date = datetime.strptime(DATES_ISO[di], "%Y-%m-%d")
    tst_hour = SLOT_TST_H[si]
    # Taiwan = UTC+8
    dt_start_utc = date.replace(hour=tst_hour) - timedelta(hours=8)
    dt_end_utc   = dt_start_utc + timedelta(minutes=30)
    alarm_utc    = dt_start_utc - timedelta(minutes=20)

    fmt = "%Y%m%dT%H%M%SZ"
    session_label = "Americas" if SLOT_REG[si] == "us" else "Europe"

    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//CLC NCKU//Oral Exam 2025//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"DTSTART:{dt_start_utc.strftime(fmt)}\r\n"
        f"DTEND:{dt_end_utc.strftime(fmt)}\r\n"
        f"SUMMARY:CLC Oral Placement Interview ({session_label})\r\n"
        f"DESCRIPTION:Registrant: {name}\\n"
        f"Taiwan Time (TST): {ALL_SLOTS[si]}\\n"
        f"Your local time: {ALL_LOCAL[si]}\\n"
        f"Please join 20 minutes early at {ALL_EARLY[si]}.\\n"
        f"Zoom link will be sent by CLC staff via email.\r\n"
        "LOCATION:Zoom (link to be sent by CLC)\r\n"
        "STATUS:CONFIRMED\r\n"
        "BEGIN:VALARM\r\n"
        "ACTION:DISPLAY\r\n"
        f"TRIGGER;VALUE=DATE-TIME:{alarm_utc.strftime(fmt)}\r\n"
        "DESCRIPTION:Join your CLC oral interview in 20 minutes!\r\n"
        "END:VALARM\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    return ics.encode("utf-8")


def send_email(to_addr: str, name: str, di: int, si: int) -> tuple[bool, str]:
    """Send confirmation email with .ics attachment via Gmail SMTP."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    sender   = st.secrets.get("email_sender", "")
    password = st.secrets.get("email_password", "")
    if not sender or not password:
        return False, "not_configured"

    session_label = "Americas session / 美洲場" if SLOT_REG[si] == "us" else "Europe session / 歐洲場"
    is_am = SLOT_REG[si] == "us"
    prev_note = "<br><small style='color:#888'>* US: previous calendar day</small>" if is_am else ""

    subject = f"CLC Interview Confirmed / 口試報名確認 — {DATES_EN[di]} {ALL_SLOTS[si]} TST"

    html_body = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
      <div style="background:#e6f1fb;padding:16px 20px;border-radius:10px 10px 0 0">
        <div style="font-size:1rem;font-weight:600;color:#0c447c">🎓 CLC Oral Placement Interview</div>
        <div style="font-size:.8rem;color:#378add;margin-top:2px">Chinese Language Center · NCKU</div>
      </div>
      <div style="background:#f9f9f7;padding:20px;border-radius:0 0 10px 10px;border:1px solid #ddd;border-top:none">
        <p style="margin:0 0 14px">Dear <strong>{name}</strong>,</p>
        <p style="margin:0 0 14px">
          Your oral placement interview has been confirmed. Please see the details below.<br>
          <span style="color:#888;font-size:.88rem">您的口試報名已成功確認，詳情如下。</span>
        </p>

        <div style="background:#e1f5ee;border:1px solid #9fe1cb;border-radius:8px;padding:14px 16px;margin-bottom:16px">
          <div style="font-weight:600;color:#085041;margin-bottom:6px">✅ Registration confirmed / 報名確認</div>
          <div style="font-size:.95rem;font-weight:600;color:#085041">{DATES_EN[di]} &nbsp;·&nbsp; {ALL_SLOTS[si]} Taiwan Time (TST)</div>
          <div style="font-size:.85rem;color:#0f6e56;margin-top:4px">Session: {session_label}</div>
          <div style="font-size:.85rem;color:#0f6e56;margin-top:2px">
            Your local time / 您的當地時間：<strong>{ALL_LOCAL[si]}</strong>{prev_note}
          </div>
          <div style="font-size:.82rem;color:#0f6e56;margin-top:4px">
            ⏰ Please join <strong>20 min early</strong> at / 請於 <strong>{ALL_EARLY[si]}</strong> 上線
          </div>
        </div>

        <div style="background:#fff8ec;border:1px solid #fac775;border-radius:8px;padding:12px 14px;margin-bottom:16px">
          <div style="font-size:.88rem;color:#633806">
            📎 A calendar invite (.ics) is attached to this email.<br>
            You can import it into Google Calendar, Apple Calendar, or Outlook.<br>
            <span style="color:#888">行事曆邀請（.ics）已附於此信件，可匯入 Google / Apple / Outlook 行事曆。</span>
          </div>
        </div>

        <div style="font-size:.82rem;color:#888;margin-top:12px">
          📧 A Zoom link will be sent to you by CLC staff before the interview date.<br>
          Zoom 連結將由 CLC 工作人員於口試前另行寄送。
        </div>
        <hr style="border:none;border-top:1px solid #eee;margin:16px 0">
        <div style="font-size:.75rem;color:#aaa">
          This is an automated confirmation from the CLC Oral Exam Registration System.<br>
          Chinese Language Center · National Cheng Kung University (NCKU)
        </div>
      </div>
    </div>
    """

    msg = MIMEMultipart("mixed")
    msg["From"]    = f"CLC NCKU <{sender}>"
    msg["To"]      = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Attach .ics
    ics_bytes = generate_ics(name, di, si)
    att = MIMEBase("text", "calendar", method="REQUEST")
    att.set_payload(ics_bytes)
    encoders.encode_base64(att)
    att.add_header("Content-Disposition", "attachment", filename="clc_interview.ics")
    msg.attach(att)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as srv:
            srv.login(sender, password)
            srv.send_message(msg)
        return True, "ok"
    except Exception as e:
        return False, str(e)


def generate_gcal_url(name: str, di: int, si: int) -> str:
    """Generate a Google Calendar 'add event' URL."""
    import urllib.parse
    date     = datetime.strptime(DATES_ISO[di], "%Y-%m-%d")
    tst_hour = SLOT_TST_H[si]
    dt_start = date.replace(hour=tst_hour) - timedelta(hours=8)
    dt_end   = dt_start + timedelta(minutes=30)
    fmt      = "%Y%m%dT%H%M%SZ"
    session_label = "Americas" if SLOT_REG[si] == "us" else "Europe"
    params = urllib.parse.urlencode({
        "action":   "TEMPLATE",
        "text":     f"CLC Oral Placement Interview ({session_label})",
        "dates":    f"{dt_start.strftime(fmt)}/{dt_end.strftime(fmt)}",
        "details":  (f"Registrant: {name}\n"
                     f"Taiwan Time (TST): {ALL_SLOTS[si]}\n"
                     f"Your local time: {ALL_LOCAL[si]}\n"
                     f"Please join 20 min early at {ALL_EARLY[si]}\n"
                     f"Zoom link will be sent by CLC staff."),
        "location": "Zoom (link to be sent by CLC)",
    })
    return f"https://calendar.google.com/calendar/render?{params}"


def email_configured() -> bool:
    try:
        return bool(st.secrets.get("email_sender")) and bool(st.secrets.get("email_password"))
    except Exception:
        return False


# ══════════════════════════════════════════════════════
# SHARED HEADER
# ══════════════════════════════════════════════════════
st.markdown("""
<div class="clc-header">
  <div class="clc-logo">🎓</div>
  <div>
    <div class="clc-title">CLC Oral Placement Interview</div>
    <div class="clc-sub">Chinese Language Center · NCKU &nbsp;·&nbsp; 5/26–5/29, 2025 &nbsp;·&nbsp; 線上口試報名</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# SHARED: BOOKING CARD + EMAIL + ICS
# ══════════════════════════════════════════════════════
def render_booking_card(booking: dict, show_actions: bool = True):
    """Render the green confirmed booking card, calendar buttons, and email."""
    import base64
    di   = booking.get("di", 0)
    si   = booking.get("si", 0)
    name = booking.get("name", "")
    is_am = SLOT_REG[si] == "us"
    tag   = '<span class="tag-am">Americas</span>' if is_am else '<span class="tag-pm">Europe</span>'

    st.markdown(
        f'<div class="book-card">'
        f'<div class="book-title">✅ Registration confirmed · 報名已確認</div>'
        f'<div class="book-time">{DATES_EN[di]} &nbsp;·&nbsp; {ALL_SLOTS[si]} Taiwan Time (TST) &nbsp;{tag}</div>'
        f'<div class="book-local">🕐 Your local time / 您的當地時間：<strong>{ALL_LOCAL[si]}</strong></div>'
        f'<div class="book-early">⏰ Join 20 min early at / 請提前 20 分鐘上線：<strong>{ALL_EARLY[si]}</strong></div>'
        f'{"<div class=book-hint>Need to change? Select a different slot below. · 如需更改，點選下方其他時段。</div>" if show_actions else ""}'
        f'</div>',
        unsafe_allow_html=True
    )

    if not show_actions:
        return

    # ── Calendar buttons (mobile-compatible HTML links) ──
    ics_bytes = generate_ics(name, di, si)
    ics_b64   = base64.b64encode(ics_bytes).decode()
    ics_uri   = f"data:text/calendar;base64,{ics_b64}"
    gcal_url  = generate_gcal_url(name, di, si)

    btn_style = (
        "display:inline-flex;align-items:center;justify-content:center;gap:6px;"
        "padding:10px 0;border-radius:8px;text-decoration:none;"
        "font-size:.88rem;font-weight:500;width:100%;box-sizing:border-box;"
    )
    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">'
        # Google Calendar — opens in app/browser, best for mobile
        f'<a href="{gcal_url}" target="_blank" style="{btn_style}'
        f'background:#e6f1fb;color:#0c447c;border:1px solid #b5d4f4">'
        f'📅 Google Calendar</a>'
        # .ics — works on iOS Calendar, Outlook, Apple Calendar
        f'<a href="{ics_uri}" download="clc_interview.ics" style="{btn_style}'
        f'background:#f7f6f3;color:#1a1a18;border:1px solid #ddd">'
        f'📎 Apple / Outlook (.ics)</a>'
        f'</div>'
        f'<div style="font-size:.72rem;color:#aaa;margin-bottom:10px;text-align:center">'
        f'iOS: tap Apple/Outlook → open in Calendar app &nbsp;·&nbsp; Android: tap Google Calendar'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Optional email ─────────────────────────────────
    st.markdown("""
    <div class="email-section">
      <div class="email-title">📧 Send a confirmation copy to yourself / 寄送確認信副本</div>
      <div class="email-sub">Optional · 可選填 — includes calendar invite attachment / 含 .ics 行事曆附件</div>
    </div>
    """, unsafe_allow_html=True)

    col_e, col_btn = st.columns([3, 1])
    with col_e:
        email_val = st.text_input(
            "Your email address / 您的 Email",
            placeholder="e.g. maria@example.com",
            label_visibility="collapsed",
            key="email_input_field",
        )
    with col_btn:
        send_clicked = st.button("Send / 寄出", use_container_width=True, key="btn_send_email")

    if send_clicked:
        email_val = email_val.strip()
        if not email_val or "@" not in email_val:
            st.error("Please enter a valid email address. / 請輸入有效的 Email 地址。")
        elif not email_configured():
            # Fallback: show mailto link
            subject = f"CLC Interview Confirmed - {DATES_EN[di]} {ALL_SLOTS[si]} TST"
            body = (
                f"Dear {name},%0A%0A"
                f"Your CLC oral placement interview is confirmed.%0A"
                f"Date: {DATES_EN[di]}%0A"
                f"Taiwan time: {ALL_SLOTS[si]} TST%0A"
                f"Your local time: {ALL_LOCAL[si]}%0A"
                f"Please join 20 min early at: {ALL_EARLY[si]}%0A%0A"
                f"A Zoom link will be sent by CLC staff before the interview."
            )
            mailto = f"mailto:{email_val}?subject={subject}&body={body}"
            st.markdown(
                f'<a href="{mailto}" target="_blank" style="display:inline-block;background:#0c447c;color:white;'
                f'padding:8px 16px;border-radius:6px;text-decoration:none;font-size:.88rem">'
                f'📧 Click to open in your email app / 點此用您的郵件程式寄送</a>',
                unsafe_allow_html=True
            )
        else:
            with st.spinner("Sending... / 寄送中..."):
                ok, msg = send_email(email_val, name, di, si)
            if ok:
                st.success(f"✅ Confirmation email sent to {email_val} / 確認信已寄至 {email_val}")
                st.session_state.email_sent = True
            else:
                st.error(f"❌ Failed to send email ({msg}). Please try again. / 寄送失敗，請稍後再試。")


# ══════════════════════════════════════════════════════
# SCREEN: LANDING
# ══════════════════════════════════════════════════════
def screen_landing():
    st.markdown("#### What would you like to do? / 請選擇您的操作")
    st.markdown('<div style="height:.25rem"></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="role-btn">
          <div class="role-icon">📝</div>
          <div class="role-name">Register / 報名口試</div>
          <div class="role-desc">New registration or change slot<br>新報名或更改時段</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Register →", key="go_register", use_container_width=True, type="primary"):
            go("identify")

    with c2:
        st.markdown("""
        <div class="role-btn">
          <div class="role-icon">🔍</div>
          <div class="role-name">Check my registration / 查詢報名紀錄</div>
          <div class="role-desc">View your confirmed slot<br>查看已報名的時段</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Check →", key="go_check", use_container_width=True):
            go("check")

    st.markdown("""
    <div class="notice" style="margin-top:1.25rem">
    ⏰ <strong>Please join the Zoom call 20 minutes before your scheduled time.</strong><br>
    <span style="color:#888">請於口試時間<strong>提前 20 分鐘</strong>上線進行設備與音訊測試。</span>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# SCREEN: IDENTIFY (register flow)
# ══════════════════════════════════════════════════════
def screen_identify():
    if st.button("← Back / 返回", key="back_identify"):
        go("landing")

    st.markdown("#### Register / 報名口試")
    st.markdown("""
    <div class="notice">
    This is the <strong>online placement interview</strong> registration for new students of the Chinese Language Center.
    After registering, you will receive a Zoom link via email.<br>
    <span style="color:#888">此系統供新生報名線上分班口試，完成報名後將以 Email 寄送 Zoom 連結。</span>
    </div>
    """, unsafe_allow_html=True)

    name = st.text_input(
        "Your full name / 您的全名",
        value=st.session_state.user_name,
        placeholder="e.g. Maria Schmidt",
        help="Use the exact same name each time you log in. / 每次登入請使用相同姓名。"
    )
    region = st.radio(
        "Your current location / 您目前所在地區",
        options=["eu", "us"],
        format_func=lambda x: (
            "🇪🇺  Europe / 歐洲  (interview: afternoon Taiwan time / 台灣下午)"
            if x == "eu" else
            "🌎  Americas / 美洲  (interview: morning Taiwan time / 台灣早上)"
        ),
        index=0 if st.session_state.region == "eu" else 1,
        horizontal=False,
    )

    if st.button("View available slots → 查看可報名時段", type="primary", use_container_width=True):
        name = name.strip()
        if not name:
            st.error("Please enter your name. / 請輸入姓名。")
            return
        st.session_state.user_name = name
        st.session_state.region    = region
        slots = db_get("open_slots") or []
        st.session_state.open_slots = slots if isinstance(slots, list) else []
        booking = db_get(f"students/{name}")
        st.session_state.my_booking = booking if isinstance(booking, dict) else None
        go("slots")


# ══════════════════════════════════════════════════════
# SCREEN: SLOT SELECTION
# ══════════════════════════════════════════════════════
def screen_slots():
    name    = st.session_state.user_name
    region  = st.session_state.region
    booking = st.session_state.my_booking

    col_h, col_b = st.columns([4, 1])
    with col_h:
        st.markdown(f"#### Hello, **{name}** 👋")
        st.caption("🇪🇺 Europe session" if region == "eu" else "🌎 Americas session")
    with col_b:
        if st.button("← Back", key="back_slots"):
            go("landing")

    # Already booked
    if booking:
        render_booking_card(booking, show_actions=True)

    # Available slots
    open_slots = st.session_state.open_slots
    relevant   = [
        o for o in open_slots
        if isinstance(o, dict) and (
            (region == "eu" and SLOT_REG[o["si"]] == "eu") or
            (region == "us" and SLOT_REG[o["si"]] == "us")
        )
    ]

    if not relevant:
        st.info(
            "📭 **No slots are available yet.**  \n"
            "Please check back after the admin publishes the schedule.  \n"
            "目前尚無開放的時段，請等候管理員通知後再回來查看。"
        )
        if st.button("↻ Refresh / 重新整理", use_container_width=True):
            slots = db_get("open_slots") or []
            st.session_state.open_slots = slots if isinstance(slots, list) else []
            st.rerun()
        return

    if booking:
        st.markdown("**Change slot / 更改時段**")
    else:
        st.markdown("**Select your interview slot / 請選擇口試時段**")
    st.caption("Click a slot to register. Saved automatically. / 點選時段即報名，自動儲存。")

    for o in relevant:
        di, si  = o["di"], o["si"]
        is_am   = SLOT_REG[si] == "us"
        is_sel  = (booking and isinstance(booking, dict)
                   and booking.get("di") == di and booking.get("si") == si)
        sel_cls  = ("slot-sel-am" if is_am else "slot-sel-pm") if is_sel else ""
        tag_html = ('<span class="tag-am">Americas</span>' if is_am
                    else '<span class="tag-pm">Europe</span>')
        note = ("<br><span style='font-size:.75rem;color:#aaa'>"
                "* Previous calendar day (US) / 美國時間為前一日</span>") if is_am else ""

        st.markdown(
            f'<div class="slot-opt {sel_cls}">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">'
            f'<div>'
            f'<div style="font-weight:600;font-size:.98rem">{"✓  " if is_sel else ""}{DATES_EN[di]} · {ALL_SLOTS[si]} TST</div>'
            f'<div style="font-size:.88rem;color:#555;margin-top:4px">🕐 Your local time: <strong>{ALL_LOCAL[si]}</strong></div>'
            f'<div style="font-size:.78rem;color:#999;margin-top:2px">Join 20 min early: {ALL_EARLY[si]}{note}</div>'
            f'</div>{tag_html}</div></div>',
            unsafe_allow_html=True
        )
        label = (f"✓ Keep this slot — {DATES_EN[di]} {ALL_SLOTS[si]}" if is_sel
                 else f"Register — {DATES_EN[di]} {ALL_SLOTS[si]} TST")
        if st.button(label, key=f"slot_{di}_{si}", use_container_width=True,
                     type="primary" if is_sel else "secondary"):
            if not is_sel:
                b = {"name": name, "region": region, "di": di, "si": si}
                db_set(f"students/{name}", b)
                st.session_state.my_booking = b
                st.session_state.email_sent  = False
                st.success("✅ Registered! · 報名成功！")
                st.balloons()
                st.rerun()

    st.divider()
    if st.button("↻ Refresh slots / 更新時段", use_container_width=True):
        slots = db_get("open_slots") or []
        st.session_state.open_slots = slots if isinstance(slots, list) else []
        b = db_get(f"students/{name}")
        st.session_state.my_booking = b if isinstance(b, dict) else None
        st.rerun()


# ══════════════════════════════════════════════════════
# SCREEN: CHECK REGISTRATION  ← NEW
# ══════════════════════════════════════════════════════
def screen_check():
    if st.button("← Back / 返回", key="back_check"):
        go("landing")

    st.markdown("#### 🔍 Check my registration / 查詢報名紀錄")

    st.markdown("""
    <div class="notice">
    Enter the <strong>exact name</strong> you used when registering.<br>
    <span style="color:#888">請輸入您報名時填寫的<strong>完全相同姓名</strong>（大小寫須一致）。</span>
    </div>
    """, unsafe_allow_html=True)

    name = st.text_input(
        "Your registered name / 您的報名姓名",
        placeholder="e.g. Maria Schmidt",
        key="check_name_input"
    )

    if st.button("Look up / 查詢", type="primary", use_container_width=True):
        name = name.strip()
        if not name:
            st.error("Please enter your name. / 請輸入姓名。")
            return

        booking = db_get(f"students/{name}")

        if not booking or not isinstance(booking, dict):
            st.markdown(
                '<div class="check-card">'
                '<div class="check-title">❌ No registration found / 查無報名紀錄</div>'
                '<div style="font-size:.85rem;color:#633806">'
                'No registration was found for this name. Please check the spelling, '
                'or go back to register a new slot.<br>'
                '<span style="color:#888">查無此姓名的報名紀錄，請確認拼寫是否正確，或返回重新報名。</span>'
                '</div>'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            st.session_state.user_name  = name
            st.session_state.my_booking = booking
            st.session_state.email_sent  = False
            render_booking_card(booking, show_actions=True)


# ══════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════
SCREENS = {
    "landing":  screen_landing,
    "identify": screen_identify,
    "slots":    screen_slots,
    "check":    screen_check,
}
SCREENS.get(st.session_state.screen, screen_landing)()
