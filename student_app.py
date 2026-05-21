"""
CLC Oral Exam — Student Registration Portal  v3
新增：學生選擇國家/時區 → 所有時段自動換算當地時間
"""

import streamlit as st
import os
import base64
import urllib.parse
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
# CONSTANTS (must match app.py)
# ══════════════════════════════════════════════════════
DATES_EN  = ["5/26 (Mon)", "5/27 (Tue)", "5/28 (Wed)", "5/29 (Thu)"]
DATES_ZH  = ["5/26 (一)",  "5/27 (二)",  "5/28 (三)",  "5/29 (四)"]
DATES_ISO = ["2025-05-26", "2025-05-27", "2025-05-28", "2025-05-29"]
AM_SLOTS  = ["08:00", "09:00", "10:00", "11:00"]
PM_SLOTS  = ["14:00", "15:00", "16:00", "17:00"]
ALL_SLOTS  = AM_SLOTS + PM_SLOTS
SLOT_TST_H = [8, 9, 10, 11, 14, 15, 16, 17]
SLOT_REG   = ["us"] * 4 + ["eu"] * 4

# ══════════════════════════════════════════════════════
# STUDENT TIMEZONE LIST
# Countries/regions shown to students for local time calc
# offset = UTC offset in hours (for May 2025, use summer/DST values)
# ══════════════════════════════════════════════════════
STUDENT_TIMEZONES = [
    # ── East Asia ──────────────────────────────────────
    {"label": "🇯🇵 Japan / 日本",                    "abbr": "JST",   "offset": 9},
    {"label": "🇰🇷 Korea / 韓國",                    "abbr": "KST",   "offset": 9},
    {"label": "🇨🇳 China / 中國大陸",               "abbr": "CST",   "offset": 8},
    {"label": "🇭🇰 Hong Kong / 香港",               "abbr": "HKT",   "offset": 8},
    {"label": "🇲🇴 Macau / 澳門",                   "abbr": "CST",   "offset": 8},
    # ── Southeast Asia ─────────────────────────────────
    {"label": "🇸🇬 Singapore / 新加坡",              "abbr": "SGT",   "offset": 8},
    {"label": "🇲🇾 Malaysia / 馬來西亞",             "abbr": "MYT",   "offset": 8},
    {"label": "🇵🇭 Philippines / 菲律賓",            "abbr": "PHT",   "offset": 8},
    {"label": "🇮🇩 Indonesia (Jakarta) / 雅加達",    "abbr": "WIB",   "offset": 7},
    {"label": "🇻🇳 Vietnam / 越南",                  "abbr": "ICT",   "offset": 7},
    {"label": "🇹🇭 Thailand / 泰國",                 "abbr": "ICT",   "offset": 7},
    {"label": "🇲🇲 Myanmar / 緬甸",                  "abbr": "MMT",   "offset": 6.5},
    # ── South Asia ─────────────────────────────────────
    {"label": "🇮🇳 India / 印度",                    "abbr": "IST",   "offset": 5.5},
    {"label": "🇵🇰 Pakistan / 巴基斯坦",             "abbr": "PKT",   "offset": 5},
    {"label": "🇧🇩 Bangladesh / 孟加拉",             "abbr": "BST",   "offset": 6},
    # ── Central / West Asia ────────────────────────────
    {"label": "🇦🇪 UAE / 阿聯 (Abu Dhabi, Dubai)",   "abbr": "GST",   "offset": 4},
    {"label": "🇸🇦 Saudi Arabia / 沙烏地",            "abbr": "AST",   "offset": 3},
    {"label": "🇮🇷 Iran / 伊朗",                     "abbr": "IRST",  "offset": 4.5},
    {"label": "🇹🇷 Turkey / 土耳其",                 "abbr": "TRT",   "offset": 3},
    {"label": "🇰🇿 Kazakhstan (Almaty)",              "abbr": "ALMT",  "offset": 6},
    # ── Europe (May 2025 = summer time) ────────────────
    {"label": "🇩🇪 Germany / 德國 (CEST UTC+2)",     "abbr": "CEST",  "offset": 2},
    {"label": "🇨🇭 Switzerland / 瑞士 (CEST UTC+2)", "abbr": "CEST",  "offset": 2},
    {"label": "🇦🇹 Austria / 奧地利 (CEST UTC+2)",   "abbr": "CEST",  "offset": 2},
    {"label": "🇫🇷 France / 法國 (CEST UTC+2)",      "abbr": "CEST",  "offset": 2},
    {"label": "🇮🇹 Italy / 義大利 (CEST UTC+2)",     "abbr": "CEST",  "offset": 2},
    {"label": "🇪🇸 Spain / 西班牙 (CEST UTC+2)",     "abbr": "CEST",  "offset": 2},
    {"label": "🇳🇱 Netherlands / 荷蘭 (CEST UTC+2)", "abbr": "CEST",  "offset": 2},
    {"label": "🇧🇪 Belgium / 比利時 (CEST UTC+2)",   "abbr": "CEST",  "offset": 2},
    {"label": "🇵🇱 Poland / 波蘭 (CEST UTC+2)",      "abbr": "CEST",  "offset": 2},
    {"label": "🇨🇿 Czech / 捷克 (CEST UTC+2)",       "abbr": "CEST",  "offset": 2},
    {"label": "🇭🇺 Hungary / 匈牙利 (CEST UTC+2)",   "abbr": "CEST",  "offset": 2},
    {"label": "🇸🇰 Slovakia / 斯洛伐克 (CEST UTC+2)","abbr": "CEST",  "offset": 2},
    {"label": "🇷🇴 Romania / 羅馬尼亞 (EEST UTC+3)", "abbr": "EEST",  "offset": 3},
    {"label": "🇬🇷 Greece / 希臘 (EEST UTC+3)",      "abbr": "EEST",  "offset": 3},
    {"label": "🇬🇧 UK / 英國 (BST UTC+1)",           "abbr": "BST",   "offset": 1},
    {"label": "🇮🇪 Ireland / 愛爾蘭 (IST UTC+1)",    "abbr": "IST_EU","offset": 1},
    {"label": "🇵🇹 Portugal / 葡萄牙 (WEST UTC+1)",  "abbr": "WEST",  "offset": 1},
    {"label": "🇷🇺 Russia (Moscow) / 莫斯科 (UTC+3)","abbr": "MSK",   "offset": 3},
    {"label": "🇺🇦 Ukraine / 烏克蘭 (EEST UTC+3)",   "abbr": "EEST",  "offset": 3},
    # ── Africa ─────────────────────────────────────────
    {"label": "🇿🇦 South Africa / 南非 (SAST UTC+2)","abbr": "SAST",  "offset": 2},
    {"label": "🇪🇬 Egypt / 埃及 (EET UTC+2)",        "abbr": "EET",   "offset": 2},
    {"label": "🇳🇬 Nigeria / 奈及利亞 (WAT UTC+1)",  "abbr": "WAT",   "offset": 1},
    {"label": "🇰🇪 Kenya / 肯亞 (EAT UTC+3)",        "abbr": "EAT",   "offset": 3},
    # ── Americas ───────────────────────────────────────
    {"label": "🇺🇸 USA – East / 美東 (EDT UTC-4)",   "abbr": "EDT",   "offset": -4},
    {"label": "🇺🇸 USA – Central / 美中 (CDT UTC-5)","abbr": "CDT",   "offset": -5},
    {"label": "🇺🇸 USA – Mountain / 美山 (MDT UTC-6)","abbr":"MDT",   "offset": -6},
    {"label": "🇺🇸 USA – West / 美西 (PDT UTC-7)",   "abbr": "PDT",   "offset": -7},
    {"label": "🇨🇦 Canada – East / 加東 (EDT UTC-4)","abbr": "EDT",   "offset": -4},
    {"label": "🇨🇦 Canada – West / 加西 (PDT UTC-7)","abbr": "PDT",   "offset": -7},
    {"label": "🇲🇽 Mexico City / 墨西哥市 (UTC-6)",  "abbr": "CDT",   "offset": -6},
    {"label": "🇧🇷 Brazil / 巴西 (BRT UTC-3)",       "abbr": "BRT",   "offset": -3},
    {"label": "🇦🇷 Argentina / 阿根廷 (ART UTC-3)",  "abbr": "ART",   "offset": -3},
    {"label": "🇨🇱 Chile / 智利 (CLT UTC-4)",        "abbr": "CLT",   "offset": -4},
    {"label": "🇨🇴 Colombia / 哥倫比亞 (COT UTC-5)", "abbr": "COT",   "offset": -5},
    # ── Oceania ────────────────────────────────────────
    {"label": "🇦🇺 Australia (Sydney) / 澳洲 (AEST UTC+10)","abbr":"AEST","offset":10},
    {"label": "🇳🇿 New Zealand / 紐西蘭 (NZST UTC+12)",     "abbr":"NZST","offset":12},
    # ── Custom / Other ─────────────────────────────────
    {"label": "🌐 Other UTC−10", "abbr": "UTC−10", "offset": -10},
    {"label": "🌐 Other UTC−9",  "abbr": "UTC−9",  "offset": -9},
    {"label": "🌐 Other UTC−8",  "abbr": "UTC−8",  "offset": -8},
    {"label": "🌐 Other UTC−7",  "abbr": "UTC−7",  "offset": -7},
    {"label": "🌐 Other UTC−6",  "abbr": "UTC−6",  "offset": -6},
    {"label": "🌐 Other UTC−5",  "abbr": "UTC−5",  "offset": -5},
    {"label": "🌐 Other UTC−4",  "abbr": "UTC−4",  "offset": -4},
    {"label": "🌐 Other UTC−3",  "abbr": "UTC−3",  "offset": -3},
    {"label": "🌐 Other UTC+0",  "abbr": "UTC",    "offset":  0},
    {"label": "🌐 Other UTC+1",  "abbr": "UTC+1",  "offset":  1},
    {"label": "🌐 Other UTC+2",  "abbr": "UTC+2",  "offset":  2},
    {"label": "🌐 Other UTC+3",  "abbr": "UTC+3",  "offset":  3},
    {"label": "🌐 Other UTC+4",  "abbr": "UTC+4",  "offset":  4},
    {"label": "🌐 Other UTC+5",  "abbr": "UTC+5",  "offset":  5},
    {"label": "🌐 Other UTC+6",  "abbr": "UTC+6",  "offset":  6},
    {"label": "🌐 Other UTC+7",  "abbr": "UTC+7",  "offset":  7},
    {"label": "🌐 Other UTC+8",  "abbr": "UTC+8",  "offset":  8},
    {"label": "🌐 Other UTC+9",  "abbr": "UTC+9",  "offset":  9},
    {"label": "🌐 Other UTC+10", "abbr": "UTC+10", "offset": 10},
    {"label": "🌐 Other UTC+11", "abbr": "UTC+11", "offset": 11},
    {"label": "🌐 Other UTC+12", "abbr": "UTC+12", "offset": 12},
]

TZ_LABELS = [t["label"] for t in STUDENT_TIMEZONES]
TZ_BY_LABEL = {t["label"]: t for t in STUDENT_TIMEZONES}

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
.book-card {
  background: #e1f5ee; border: 1.5px solid #9fe1cb;
  border-radius: 12px; padding: 1.1rem 1.3rem; margin-bottom: 1.2rem;
}
.book-title { font-weight: 700; color: #085041; font-size: 1rem; margin-bottom: 6px; }
.book-time  { font-size: 1.05rem; font-weight: 600; color: #085041; }
.book-local { font-size: .88rem; margin-top: 5px; color: #0f6e56; }
.book-early { font-size: .82rem; color: #0f6e56; margin-top: 3px; }
.book-hint  { font-size: .75rem; color: #666; margin-top: 10px; border-top: 1px solid #b5e8d4; padding-top: 8px; }
.slot-opt { border: 1px solid #dde; border-radius: 10px; padding: 14px 16px; margin-bottom: 8px; }
.slot-sel { border: 2px solid #378add !important; background: #e6f1fb14; }
.slot-time-big  { font-size: 1rem; font-weight: 600; color: #1a1a18; }
.slot-time-local{ font-size: .95rem; font-weight: 500; color: #185fa5; margin-top: 3px; }
.slot-time-early{ font-size: .78rem; color: #888; margin-top: 2px; }
.tz-badge { display:inline-flex;align-items:center;gap:4px;background:#e6f1fb;color:#0c447c;
            padding:3px 10px;border-radius:6px;font-size:.8rem;font-weight:500; }
.notice {
  background: #f7f6f3; border: 1px solid #e0ddd6;
  border-radius: 8px; padding: 10px 14px;
  font-size: .82rem; color: #666; line-height: 1.65; margin-bottom: 1rem;
}
.email-section { background:#f0f7fe;border:1px solid #b5d4f4;border-radius:10px;padding:1rem 1.2rem;margin-top:1rem; }
.check-card { background:#fff8ec;border:1.5px solid #fac775;border-radius:12px;padding:1.1rem 1.3rem;margin-bottom:1rem; }
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
        with open(_LOCAL_PATH) as f: return json.load(f)
    return {}

def _local_save(data):
    import json
    with open(_LOCAL_PATH, "w") as f: json.dump(data, f)

def db_get(path):
    if FIREBASE_OK: return _fb.reference(path).get()
    data = _local_load()
    for k in path.strip("/").split("/"):
        data = data.get(k) if isinstance(data, dict) else None
        if data is None: return None
    return data

def db_set(path, value):
    if FIREBASE_OK: _fb.reference(path).set(value)
    else:
        import json
        data = _local_load()
        keys = path.strip("/").split("/")
        d = data
        for k in keys[:-1]: d = d.setdefault(k, {})
        d[keys[-1]] = value
        _local_save(data)

# ══════════════════════════════════════════════════════
# TIME UTILS
# ══════════════════════════════════════════════════════
def tst_to_local(si: int, tz_offset: float, tz_abbr: str) -> tuple:
    """
    Given slot index si and timezone offset, return (local_str, early_str, prev_day).
    TST = UTC+8.
    """
    tst_h = SLOT_TST_H[si]
    tst_min = tst_h * 60
    utc_min  = tst_min - 480
    local_min = utc_min + int(tz_offset * 60)
    early_min = local_min - 20

    def fmt(total_min):
        prev = total_min < 0
        nxt  = total_min >= 1440
        m2   = total_min % 1440
        hh, mm = divmod(m2, 60)
        prefix = "Prev. day " if prev else ("Next day " if nxt else "")
        return f"{prefix}{tz_abbr} {hh:02d}:{mm:02d}", prev

    local_str, prev = fmt(local_min)
    early_str, _    = fmt(early_min)
    return local_str, early_str, prev


def generate_ics(name: str, di: int, si: int) -> bytes:
    date      = datetime.strptime(DATES_ISO[di], "%Y-%m-%d")
    dt_start  = date.replace(hour=SLOT_TST_H[si]) - timedelta(hours=8)
    dt_end    = dt_start + timedelta(minutes=30)
    alarm_utc = dt_start - timedelta(minutes=20)
    fmt       = "%Y%m%dT%H%M%SZ"
    ics = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//CLC NCKU//Oral Exam 2025//EN\r\n"
        "CALSCALE:GREGORIAN\r\nMETHOD:PUBLISH\r\nBEGIN:VEVENT\r\n"
        f"DTSTART:{dt_start.strftime(fmt)}\r\nDTEND:{dt_end.strftime(fmt)}\r\n"
        f"SUMMARY:CLC Oral Placement Interview\r\n"
        f"DESCRIPTION:Registrant: {name}\\nTST: {ALL_SLOTS[si]}\\n"
        f"Zoom link will be sent by CLC staff.\r\n"
        f"LOCATION:Zoom (link to be sent by CLC)\r\nSTATUS:CONFIRMED\r\n"
        f"BEGIN:VALARM\r\nACTION:DISPLAY\r\n"
        f"TRIGGER;VALUE=DATE-TIME:{alarm_utc.strftime(fmt)}\r\n"
        f"DESCRIPTION:CLC oral interview in 20 minutes!\r\nEND:VALARM\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    return ics.encode("utf-8")


def generate_gcal_url(name: str, di: int, si: int) -> str:
    date     = datetime.strptime(DATES_ISO[di], "%Y-%m-%d")
    dt_start = date.replace(hour=SLOT_TST_H[si]) - timedelta(hours=8)
    dt_end   = dt_start + timedelta(minutes=30)
    fmt      = "%Y%m%dT%H%M%SZ"
    params = urllib.parse.urlencode({
        "action":   "TEMPLATE",
        "text":     "CLC Oral Placement Interview",
        "dates":    f"{dt_start.strftime(fmt)}/{dt_end.strftime(fmt)}",
        "details":  f"Registrant: {name}\nTaiwan Time: {ALL_SLOTS[si]} TST\nZoom link will be sent by CLC staff.",
        "location": "Zoom (link to be sent by CLC)",
    })
    return f"https://calendar.google.com/calendar/render?{params}"


def send_email(to_addr, name, di, si, tz_label="", local_str="", early_str=""):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    sender   = st.secrets.get("email_sender","")
    password = st.secrets.get("email_password","")
    if not sender or not password: return False, "not_configured"
    subject = f"CLC Interview Confirmed / 口試報名確認 — {DATES_EN[di]} {ALL_SLOTS[si]} TST"
    html_body = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
      <div style="background:#e6f1fb;padding:16px 20px;border-radius:10px 10px 0 0">
        <div style="font-size:1rem;font-weight:600;color:#0c447c">🎓 CLC Oral Placement Interview</div>
        <div style="font-size:.8rem;color:#378add">Chinese Language Center · NCKU</div>
      </div>
      <div style="background:#f9f9f7;padding:20px;border-radius:0 0 10px 10px;border:1px solid #ddd;border-top:none">
        <p>Dear <strong>{name}</strong>,</p>
        <p>Your oral placement interview has been confirmed / 您的口試報名已成功確認。</p>
        <div style="background:#e1f5ee;border:1px solid #9fe1cb;border-radius:8px;padding:14px;margin:16px 0">
          <div style="font-weight:600;color:#085041">✅ Registered / 已報名</div>
          <div style="font-size:.95rem;font-weight:600;color:#085041;margin-top:4px">{DATES_EN[di]} · {ALL_SLOTS[si]} Taiwan Time (TST)</div>
          {'<div style="font-size:.85rem;color:#0f6e56;margin-top:4px">📍 Location: '+tz_label+'</div>' if tz_label else ''}
          {'<div style="font-size:.85rem;color:#0f6e56;margin-top:2px">🕐 Your local time: <strong>'+local_str+'</strong></div>' if local_str else ''}
          {'<div style="font-size:.82rem;color:#0f6e56;margin-top:2px">⏰ Join 20 min early: <strong>'+early_str+'</strong></div>' if early_str else ''}
        </div>
        <p style="font-size:.82rem;color:#888">Zoom link will be sent by CLC staff before the interview.<br>Zoom 連結將由 CLC 工作人員另行寄送。</p>
      </div>
    </div>"""
    msg = MIMEMultipart("mixed")
    msg["From"] = f"CLC NCKU <{sender}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body,"html","utf-8"))
    ics_bytes = generate_ics(name, di, si)
    att = MIMEBase("text","calendar", method="REQUEST")
    att.set_payload(ics_bytes)
    encoders.encode_base64(att)
    att.add_header("Content-Disposition","attachment",filename="clc_interview.ics")
    msg.attach(att)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as srv:
            srv.login(sender, password); srv.send_message(msg)
        return True, "ok"
    except Exception as e:
        return False, str(e)

def email_configured():
    try: return bool(st.secrets.get("email_sender")) and bool(st.secrets.get("email_password"))
    except: return False

# ══════════════════════════════════════════════════════
# STUDENT-SIDE CONFIG (reads from Firebase)
# ══════════════════════════════════════════════════════
def _fix_fb(obj):
    if isinstance(obj, dict):
        if obj and all(k.isdigit() for k in obj.keys()):
            return [_fix_fb(obj[str(i)]) for i in range(len(obj))]
        return {k: _fix_fb(v) for k, v in obj.items()}
    return obj

def load_student_config():
    raw = db_get("config")
    if isinstance(raw, dict) and "settings" in raw:
        return _fix_fb(raw).get("settings", {})
    return {"registration_open": True, "deadline": "", "max_per_slot": 1, "meet_links": {}}

def get_meet_link_student(di, region):
    cfg = st.session_state.get("stu_config", {})
    iso = DATES_ISO[di] if di < len(DATES_ISO) else ""
    return cfg.get("meet_links", {}).get(f"{iso}_{region}", "")

def check_registration_status():
    cfg = st.session_state.get("stu_config", {})
    if not cfg.get("registration_open", True):
        return False, "Registration is closed. / 報名目前關閉。"
    dl = cfg.get("deadline", "")
    if dl:
        try:
            from datetime import datetime
            if datetime.now() > datetime.strptime(dl, "%Y-%m-%d %H:%M"):
                return False, f"Registration closed at {dl}. / 報名已於 {dl} 截止。"
        except: pass
    return True, ""

def get_max_per_slot():
    return int(st.session_state.get("stu_config", {}).get("max_per_slot", 1))

# ══════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════
for k, v in {
    "screen": "landing", "user_name": "", "tz_info": None,
    "my_booking": None, "open_slots": [], "email_sent": False, "stu_config": None,
}.items():
    if k not in st.session_state: st.session_state[k] = v

def go(s): st.session_state.screen = s; st.rerun()

# Load config once per session
if st.session_state.stu_config is None:
    st.session_state.stu_config = load_student_config()

# ══════════════════════════════════════════════════════
# HEADER
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
# SHARED: BOOKING CARD
# ══════════════════════════════════════════════════════
def render_booking_card(booking: dict, show_actions=True):
    di       = booking.get("di", 0)
    si       = booking.get("si", 0)
    name     = booking.get("name", "")
    tz_label = booking.get("tz_label", "")
    local_str= booking.get("local_str", "")
    early_str= booking.get("early_str", "")

    st.markdown(
        f'<div class="book-card">'
        f'<div class="book-title">✅ Registration confirmed · 報名已確認</div>'
        f'<div class="book-time">{DATES_EN[di]} &nbsp;·&nbsp; {ALL_SLOTS[si]} Taiwan Time (TST)</div>'
        + (f'<div class="book-local" style="margin-top:4px">📍 {tz_label}</div>' if tz_label else '')
        + (f'<div class="book-local">🕐 Your local time: <strong>{local_str}</strong></div>' if local_str else '')
        + (f'<div class="book-early">⏰ Join 20 min early at: <strong>{early_str}</strong></div>' if early_str else '')
        + ('<div class="book-hint">Need to change? Select a different slot below. · 如需更改，點選下方其他時段。</div>' if show_actions else '')
        + '</div>',
        unsafe_allow_html=True
    )

    if not show_actions: return

    # ── Google Meet link ───────────────────────────────
    region_b = booking.get("region", SLOT_REG[si] if si < len(SLOT_REG) else "eu")
    meet_url  = get_meet_link_student(di, region_b)
    if meet_url:
        st.markdown(
            f'<a href="{meet_url}" target="_blank" style="display:flex;align-items:center;justify-content:center;gap:8px;background:#e8f5e9;color:#1b5e20;border:1.5px solid #81c784;border-radius:10px;padding:14px;text-decoration:none;font-size:1rem;font-weight:700;margin-bottom:10px">🎥 Join Google Meet / 加入 Google Meet</a>',
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div style="background:#f7f6f3;border:1px solid #ddd;border-radius:8px;padding:10px 14px;font-size:.82rem;color:#888;margin-bottom:10px">🎥 Google Meet link will be sent by CLC staff. / Google Meet 連結將由 CLC 工作人員另行提供。</div>', unsafe_allow_html=True)

    # Calendar buttons (mobile-friendly HTML links)
    ics_bytes = generate_ics(name, di, si)
    ics_b64   = base64.b64encode(ics_bytes).decode()
    gcal_url  = generate_gcal_url(name, di, si)
    btn = ("display:inline-flex;align-items:center;justify-content:center;gap:6px;"
           "padding:10px 0;border-radius:8px;text-decoration:none;"
           "font-size:.88rem;font-weight:500;width:100%;box-sizing:border-box;")
    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">'
        f'<a href="{gcal_url}" target="_blank" style="{btn}background:#e6f1fb;color:#0c447c;border:1px solid #b5d4f4">📅 Google Calendar</a>'
        f'<a href="data:text/calendar;base64,{ics_b64}" download="clc_interview.ics" style="{btn}background:#f7f6f3;color:#1a1a18;border:1px solid #ddd">📎 Apple / Outlook (.ics)</a>'
        f'</div>'
        f'<div style="font-size:.72rem;color:#aaa;text-align:center;margin-bottom:10px">'
        f'iOS: tap Apple/Outlook → open in Calendar &nbsp;·&nbsp; Android: tap Google Calendar</div>',
        unsafe_allow_html=True
    )

    # Optional email
    st.markdown("""
    <div class="email-section">
      <div style="font-size:.9rem;font-weight:600;color:#0c447c;margin-bottom:4px">📧 Send a confirmation copy / 寄送確認信副本</div>
      <div style="font-size:.78rem;color:#378add;margin-bottom:.75rem">Optional · 可選填 — includes .ics calendar attachment</div>
    </div>""", unsafe_allow_html=True)

    col_e, col_btn = st.columns([3,1])
    with col_e:
        email_val = st.text_input("Email", placeholder="e.g. maria@example.com",
                                  label_visibility="collapsed", key="email_input_field")
    with col_btn:
        send_clicked = st.button("Send / 寄出", use_container_width=True, key="btn_send_email")

    if send_clicked:
        email_val = email_val.strip()
        if not email_val or "@" not in email_val:
            st.error("Please enter a valid email address.")
        elif not email_configured():
            subject = urllib.parse.quote(f"CLC Interview - {DATES_EN[di]} {ALL_SLOTS[si]} TST")
            body    = urllib.parse.quote(f"Hi {name},\n\nYour interview is confirmed:\n{DATES_EN[di]} {ALL_SLOTS[si]} TST\n{local_str}\nJoin early at {early_str}\n")
            st.markdown(f'<a href="mailto:{email_val}?subject={subject}&body={body}" target="_blank" style="display:inline-block;background:#0c447c;color:white;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:.88rem">📧 Open in email app</a>', unsafe_allow_html=True)
        else:
            with st.spinner("Sending..."):
                ok, msg = send_email(email_val, name, di, si, tz_label, local_str, early_str)
            if ok: st.success(f"✅ Sent to {email_val}")
            else:  st.error(f"❌ Failed: {msg}")

# ══════════════════════════════════════════════════════
# SCREEN: LANDING
# ══════════════════════════════════════════════════════
def screen_landing():
    st.markdown("#### What would you like to do? / 請選擇您的操作")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div style="border:1px solid #dde;border-radius:12px;padding:1.25rem 1rem;text-align:center"><div style="font-size:2rem;margin-bottom:8px">📝</div><div style="font-weight:600;font-size:.95rem;margin-bottom:3px">Register / 報名口試</div><div style="font-size:.78rem;color:#888">New registration or change slot</div></div>', unsafe_allow_html=True)
        if st.button("Register →", key="go_reg", use_container_width=True, type="primary"): go("identify")
    with c2:
        st.markdown('<div style="border:1px solid #dde;border-radius:12px;padding:1.25rem 1rem;text-align:center"><div style="font-size:2rem;margin-bottom:8px">🔍</div><div style="font-weight:600;font-size:.95rem;margin-bottom:3px">Check my registration / 查詢報名紀錄</div><div style="font-size:.78rem;color:#888">View your confirmed slot</div></div>', unsafe_allow_html=True)
        if st.button("Check →", key="go_check", use_container_width=True): go("check")
    st.markdown('<div class="notice" style="margin-top:1.25rem">⏰ <strong>Please join 20 minutes before your scheduled time.</strong> 請於口試時間<strong>提前 20 分鐘</strong>上線進行設備測試。</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# SCREEN: IDENTIFY
# ══════════════════════════════════════════════════════
def screen_identify():
    if st.button("← Back / 返回", key="back_id"): go("landing")
    st.markdown("#### Register / 報名口試")
    st.markdown('<div class="notice">This is the <strong>online placement interview</strong> registration for new students of the Chinese Language Center. After registering, you will receive a Zoom link via email.<br><span style="color:#888">此系統供新生報名線上分班口試，完成報名後將以 Email 寄送 Zoom 連結。</span></div>', unsafe_allow_html=True)

    name = st.text_input(
        "Your full name / 您的全名",
        value=st.session_state.user_name,
        placeholder="e.g. Maria Schmidt",
        help="Use the exact same name each time. / 每次登入請使用相同姓名。"
    )

    # ── Timezone selector ─────────────────────────────
    st.markdown("**Your current location & timezone / 您目前所在地區與時區**")
    st.caption("Select where you are right now — we'll calculate your local interview time automatically.\n選擇您目前的所在地，系統將自動換算您的當地口試時間。")

    saved_tz = st.session_state.tz_info
    saved_label = saved_tz["label"] if saved_tz and "label" in saved_tz else TZ_LABELS[0]
    saved_idx = TZ_LABELS.index(saved_label) if saved_label in TZ_LABELS else 0

    sel_label = st.selectbox(
        "Country / timezone",
        options=TZ_LABELS,
        index=saved_idx,
        label_visibility="collapsed",
        help="Can't find your country? Use the 'Other UTC+X' options at the bottom of the list."
    )

    tz = TZ_BY_LABEL[sel_label]

    # Live preview of what their local time would look like for first available slot
    st.markdown(
        f'<div style="background:#eaf3de;border-radius:6px;padding:6px 12px;font-size:.8rem;color:#27500a;margin:4px 0">'
        f'📍 <strong>{sel_label}</strong> · Example: Taiwan 14:00 TST → Your local time: '
        f'<strong>{tst_to_local(4, tz["offset"], tz["abbr"])[0]}</strong>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="notice" style="margin-top:.75rem">⏰ <strong>Please join 20 minutes before your scheduled time</strong> for a tech check.<br><span style="color:#888">請於口試時間<strong>提前 20 分鐘</strong>上線進行設備與音訊測試。</span></div>', unsafe_allow_html=True)

    # Registration status check
    reg_open, reg_msg = check_registration_status()
    if not reg_open:
        st.error(f"🔒 {reg_msg}")
        st.stop()

    # Deadline display
    dl = st.session_state.get("stu_config", {}).get("deadline", "")
    if dl:
        st.markdown(f'<div style="background:#fff8ec;border:1px solid #fac775;border-radius:7px;padding:7px 12px;font-size:.82rem;color:#633806;margin-bottom:.5rem">⏰ Registration deadline / 報名截止：<strong>{dl}</strong></div>', unsafe_allow_html=True)

    if st.button("View available slots → 查看可報名時段", type="primary", use_container_width=True):
        name = name.strip()
        if not name:
            st.error("Please enter your name. / 請輸入姓名。"); return
        st.session_state.user_name = name
        st.session_state.tz_info   = tz
        slots = db_get("open_slots") or []
        st.session_state.open_slots = slots if isinstance(slots, list) else []
        b = db_get(f"students/{name}")
        st.session_state.my_booking = b if isinstance(b, dict) else None
        go("slots")

# ══════════════════════════════════════════════════════
# SCREEN: SLOTS
# ══════════════════════════════════════════════════════
def screen_slots():
    name    = st.session_state.user_name
    tz      = st.session_state.tz_info or STUDENT_TIMEZONES[0]
    booking = st.session_state.my_booking

    col_h, col_b = st.columns([4,1])
    with col_h:
        st.markdown(f"#### Hello, **{name}** 👋")
        st.markdown(f'<span class="tz-badge">📍 {tz["label"]}</span>', unsafe_allow_html=True)
    with col_b:
        if st.button("← Back", key="back_slots"): go("landing")

    if booking and isinstance(booking, dict):
        render_booking_card(booking, show_actions=True)

    open_slots = st.session_state.open_slots
    if not open_slots:
        st.info("📭 **No slots available yet.** Please check back after the admin publishes the schedule.\n\n目前尚無開放時段，請等候管理員通知後再回來查看。")
        if st.button("↻ Refresh / 重新整理", use_container_width=True):
            st.session_state.open_slots = db_get("open_slots") or []
            st.rerun()
        return

    if booking: st.markdown("**Change slot / 更改時段**")
    else:        st.markdown("**Select your interview slot / 請選擇口試時段**")
    st.caption(f"All times shown in your local timezone ({tz['abbr']}) and Taiwan Standard Time (TST).")

    for o in open_slots:
        if not isinstance(o, dict): continue
        di, si   = o["di"], o["si"]
        local_str, early_str, prev = tst_to_local(si, tz["offset"], tz["abbr"])
        is_sel   = (booking and isinstance(booking, dict)
                    and booking.get("di") == di and booking.get("si") == si)
        prev_note = '<div style="font-size:.75rem;color:#aaa;margin-top:1px">* Previous calendar day in your timezone</div>' if prev else ""

        # Capacity check
        _booked  = _slot_counts.get(f"{di}_{si}", 0)
        _is_full = _max_per > 0 and _booked >= _max_per and not is_sel
        _rem     = max(0, _max_per - _booked) if _max_per > 0 else None
        _cap_badge = (
            '<span style="font-size:.75rem;background:#fcebeb;color:#a32d2d;padding:2px 8px;border-radius:4px;white-space:nowrap">額滿 Full</span>'
            if _is_full else (
            f'<span style="font-size:.75rem;background:#eaf3de;color:#27500a;padding:2px 8px;border-radius:4px;white-space:nowrap">剩 {_rem} 名</span>'
            if _rem is not None and _rem <= 3 else "")
        )

        st.markdown(
            f'<div class="slot-opt {"slot-sel" if is_sel else ""}" style="{"opacity:.55" if _is_full else ""}">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">'
            f'<div style="flex:1">'
            f'<div class="slot-time-big">{"✓  " if is_sel else ""}{DATES_EN[di]} &nbsp;·&nbsp; {ALL_SLOTS[si]} TST</div>'
            f'<div class="slot-time-local">🕐 Your local time: <strong>{local_str}</strong></div>'
            f'<div class="slot-time-early">⏰ Join 20 min early: {early_str}</div>'
            f'{prev_note}'
            f'</div>'
            f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">'
            f'<span style="font-size:.75rem;color:#aaa">{tz["abbr"]}</span>'
            f'{_cap_badge}'
            f'</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

        if _is_full:
            st.button(f"額滿 Full — {DATES_EN[di]} {ALL_SLOTS[si]}", key=f"full_{di}_{si}",
                      use_container_width=True, disabled=True)
            continue

        label = (f"✓ Keep this slot — {DATES_EN[di]} {ALL_SLOTS[si]}" if is_sel
                 else f"Register — {DATES_EN[di]} {ALL_SLOTS[si]} TST")
        if st.button(label, key=f"slot_{di}_{si}", use_container_width=True,
                     type="primary" if is_sel else "secondary"):
            if not is_sel:
                b = {
                    "name":       name,
                    "tz_label":   tz["label"],
                    "tz_abbr":    tz["abbr"],
                    "tz_offset":  tz["offset"],
                    "local_str":  local_str,
                    "early_str":  early_str,
                    "di":         di,
                    "si":         si,
                    "region":     SLOT_REG[si],
                }
                db_set(f"students/{name}", b)
                st.session_state.my_booking = b
                st.session_state.email_sent  = False
                st.success("✅ Registered! · 報名成功！")
                st.balloons(); st.rerun()

    st.divider()
    col_r, col_e = st.columns(2)
    with col_r:
        if st.button("↻ Refresh slots", use_container_width=True):
            st.session_state.open_slots = db_get("open_slots") or []
            b = db_get(f"students/{name}")
            st.session_state.my_booking = b if isinstance(b, dict) else None
            st.rerun()
    with col_e:
        if st.button("← Edit my details", use_container_width=True): go("landing")

# ══════════════════════════════════════════════════════
# SCREEN: CHECK REGISTRATION
# ══════════════════════════════════════════════════════
def screen_check():
    if st.button("← Back / 返回", key="back_check"): go("landing")
    st.markdown("#### 🔍 Check my registration / 查詢報名紀錄")
    st.markdown('<div class="notice">Enter the <strong>exact name</strong> you used when registering.<br><span style="color:#888">請輸入您報名時填寫的<strong>完全相同姓名</strong>（大小寫須一致）。</span></div>', unsafe_allow_html=True)

    name = st.text_input("Your registered name / 您的報名姓名",
                         placeholder="e.g. Maria Schmidt", key="check_name")
    if st.button("Look up / 查詢", type="primary", use_container_width=True):
        name = name.strip()
        if not name: st.error("Please enter your name. / 請輸入姓名。"); return
        booking = db_get(f"students/{name}")
        if not booking or not isinstance(booking, dict):
            st.markdown('<div class="check-card"><div style="font-weight:700;color:#633806;margin-bottom:6px">❌ No registration found / 查無報名紀錄</div><div style="font-size:.85rem;color:#633806">No registration was found for this name. Please check the spelling.<br><span style="color:#888">查無此姓名，請確認拼寫是否正確。</span></div></div>', unsafe_allow_html=True)
        else:
            st.session_state.user_name = name
            # Restore tz_info from booking if available
            if booking.get("tz_abbr"):
                st.session_state.tz_info = {
                    "label":  booking.get("tz_label",""),
                    "abbr":   booking.get("tz_abbr",""),
                    "offset": booking.get("tz_offset", 0),
                }
            render_booking_card(booking, show_actions=True)

# ══════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════
SCREENS = {"landing": screen_landing, "identify": screen_identify,
           "slots": screen_slots, "check": screen_check}
SCREENS.get(st.session_state.screen, screen_landing)()
