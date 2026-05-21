"""
CLC Oral Exam — Student Registration Portal
學生口試報名入口（僅限學生使用）

Shares Firebase DB with app.py (admin/teacher portal).
Deploy as a separate Streamlit app for a clean student-only URL.
"""

import streamlit as st
import os

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
# CONSTANTS (must match app.py exactly)
# ══════════════════════════════════════════════════════
DATES_EN  = ["5/26 (Mon)", "5/27 (Tue)", "5/28 (Wed)", "5/29 (Thu)"]
DATES_ZH  = ["5/26 (一)",  "5/27 (二)",  "5/28 (三)",  "5/29 (四)"]
AM_SLOTS  = ["08:00", "09:00", "10:00", "11:00"]
PM_SLOTS  = ["14:00", "15:00", "16:00", "17:00"]
AM_LOCAL  = ["Prev. night EDT 20:00", "EDT 21:00", "EDT 22:00", "EDT 23:00"]
PM_LOCAL  = ["CET 07:00", "CET 08:00", "CET 09:00", "CET 10:00"]
AM_EARLY  = ["Prev. night EDT 19:40", "EDT 20:40", "EDT 21:40", "EDT 22:40"]
PM_EARLY  = ["CET 06:40", "CET 07:40", "CET 08:40", "CET 09:40"]
ALL_SLOTS  = AM_SLOTS + PM_SLOTS
ALL_LOCAL  = AM_LOCAL + PM_LOCAL
ALL_EARLY  = AM_EARLY + PM_EARLY
SLOT_REG   = ["us"] * 4 + ["eu"] * 4   # 0-3 Americas, 4-7 Europe

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
[data-testid="stSidebar"]     { display: none; }
[data-testid="stDecoration"]  { display: none; }
footer                        { display: none !important; }

/* Top header banner */
.clc-header {
  background: #e6f1fb;
  border-bottom: 1px solid #b5d4f4;
  padding: 1rem 1.25rem .8rem;
  margin: -1rem -1rem 1.5rem;
  display: flex; align-items: center; gap: 12px;
}
.clc-logo  { font-size: 1.8rem; }
.clc-title { font-size: 1rem;  font-weight: 600; color: #0c447c; }
.clc-sub   { font-size: .78rem; color: #378add; margin-top: 1px; }

/* Booking confirmed card */
.book-card {
  background: #e1f5ee; border: 1px solid #9fe1cb;
  border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem;
}
.book-title  { font-weight: 600; color: #085041; font-size: .95rem; margin-bottom: 5px; }
.book-time   { font-size: 1.05rem; font-weight: 500; color: #085041; }
.book-local  { font-size: .88rem; margin-top: 4px; color: #0f6e56; }
.book-early  { font-size: .82rem; color: #0f6e56; margin-top: 2px; }
.book-hint   { font-size: .75rem; color: #666; margin-top: 8px; }

/* Slot option cards */
.slot-opt {
  border: 1px solid #dde; border-radius: 10px;
  padding: 14px 16px; margin-bottom: 8px;
}
.slot-sel-am { border: 2px solid #ef9f27 !important; background: #faeeda14; }
.slot-sel-pm { border: 2px solid #378add !important; background: #e6f1fb14; }

/* Region / session tags */
.tag-am { background: #faeeda; color: #633806; padding: 3px 10px; border-radius: 6px; font-size: .8rem; font-weight: 500; }
.tag-pm { background: #e6f1fb; color: #0c447c; padding: 3px 10px; border-radius: 6px; font-size: .8rem; font-weight: 500; }

/* Notice box */
.notice {
  background: #f7f6f3; border: 1px solid #e0ddd6;
  border-radius: 8px; padding: 10px 14px;
  font-size: .82rem; color: #666; line-height: 1.65;
  margin-bottom: 1rem;
}
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
            firebase_admin.initialize_app(cred, {
                "databaseURL": st.secrets["firebase_url"]
            })
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
    "screen":     "identify",
    "user_name":  "",
    "region":     "eu",
    "my_booking": None,
    "open_slots": [],
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def go(screen: str):
    st.session_state.screen = screen
    st.rerun()

# ══════════════════════════════════════════════════════
# HEADER (shown on every screen)
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
# SCREEN 1 — IDENTIFY
# ══════════════════════════════════════════════════════
def screen_identify():
    st.markdown("#### Please enter your details to register / 請填寫資料以完成報名")

    st.markdown("""
    <div class="notice">
    This is the <strong>online placement interview</strong> registration for new students of the Chinese Language Center.
    After registering, you will receive a Zoom link via email.<br>
    <span style="color:#888">此系統供新生報名線上分班口試，完成報名後將以 Email 寄送 Zoom 連結。</span>
    </div>
    """, unsafe_allow_html=True)

    name = st.text_input(
        "Your full name &nbsp;/&nbsp; 您的全名",
        value=st.session_state.user_name,
        placeholder="e.g. Maria Schmidt",
        help="Enter the name you used when applying to CLC."
    )

    region = st.radio(
        "Your current location &nbsp;/&nbsp; 您目前所在地區",
        options=["eu", "us"],
        format_func=lambda x: (
            "🇪🇺  Europe / 歐洲  (interview slots: afternoon Taiwan time / 台灣下午)"
            if x == "eu" else
            "🌎  Americas / 美洲  (interview slots: morning Taiwan time / 台灣早上)"
        ),
        index=0 if st.session_state.region == "eu" else 1,
        horizontal=False,
    )

    st.markdown("""
    <div class="notice" style="margin-top:.75rem">
    ⏰ <strong>Please join the Zoom call 20 minutes before your scheduled time</strong> for a tech check and sound test.<br>
    <span style="color:#888">請於口試時間<strong>提前 20 分鐘</strong>上線進行設備與音訊測試。</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button(
        "View available slots &nbsp;→&nbsp; 查看可報名時段",
        type="primary",
        use_container_width=True,
    ):
        name = name.strip()
        if not name:
            st.error("Please enter your name. / 請輸入姓名。")
            return

        st.session_state.user_name = name
        st.session_state.region    = region

        # Load open slots from Firebase
        slots = db_get("open_slots") or []
        st.session_state.open_slots = slots if isinstance(slots, list) else []

        # Load existing booking if any
        booking = db_get(f"students/{name}")
        st.session_state.my_booking = booking if isinstance(booking, dict) else None

        go("slots")

# ══════════════════════════════════════════════════════
# SCREEN 2 — SLOT SELECTION
# ══════════════════════════════════════════════════════
def screen_slots():
    name    = st.session_state.user_name
    region  = st.session_state.region
    booking = st.session_state.my_booking

    st.markdown(f"#### Hello, **{name}** 👋")
    st.caption(
        ("🇪🇺 Europe session / 歐洲場" if region == "eu" else "🌎 Americas session / 美洲場")
        + " &nbsp;·&nbsp; [Change details / 重新填寫](#)"
    )

    # ── Already booked banner ──────────────────────────
    if booking:
        di, si = booking.get("di", 0), booking.get("si", 0)
        is_am  = SLOT_REG[si] == "us"
        tag    = '<span class="tag-am">Americas</span>' if is_am else '<span class="tag-pm">Europe</span>'
        st.markdown(
            f'<div class="book-card">'
            f'<div class="book-title">✅ You are registered · 您已成功報名</div>'
            f'<div class="book-time">{DATES_EN[di]} &nbsp;·&nbsp; {ALL_SLOTS[si]} Taiwan Time (TST) &nbsp; {tag}</div>'
            f'<div class="book-local">🕐 Your local time / 您的當地時間：<strong>{ALL_LOCAL[si]}</strong></div>'
            f'<div class="book-early">📎 Please join <strong>20 min early</strong> at / 請於 <strong>{ALL_EARLY[si]}</strong> 上線</div>'
            f'<div class="book-hint">Need to change? Select a different slot below. · 需要更改？點選下方其他時段。</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Available slots ────────────────────────────────
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
            "The admin has not published the schedule. Please check back later or wait for an email notification.  \n\n"
            "目前尚無開放的時段，請等候管理員通知後再回來查看。"
        )

        if st.button("↻ Refresh / 重新整理", use_container_width=True):
            slots = db_get("open_slots") or []
            st.session_state.open_slots = slots if isinstance(slots, list) else []
            st.rerun()

        if st.button("← Edit my details / 修改資料", use_container_width=True):
            go("identify")
        return

    st.markdown("**Select your preferred interview slot / 請選擇您方便的口試時段**")
    st.caption(
        "All times shown in your **local time** and Taiwan Standard Time (TST).  \n"
        "所有時間均標示當地時間與台灣標準時間（TST）。"
    )

    for o in relevant:
        di, si  = o["di"], o["si"]
        is_am   = SLOT_REG[si] == "us"
        is_sel  = (
            booking and isinstance(booking, dict)
            and booking.get("di") == di
            and booking.get("si") == si
        )
        sel_cls  = ("slot-sel-am" if is_am else "slot-sel-pm") if is_sel else ""
        tag_html = (
            '<span class="tag-am">Americas session</span>' if is_am
            else '<span class="tag-pm">Europe session</span>'
        )
        tick     = "✓ &nbsp;" if is_sel else ""
        note     = (
            "<br><span style='font-size:.75rem;color:#aaa'>"
            "* Previous calendar day (US timezone) / 美國時間為前一日</span>"
        ) if is_am else ""

        st.markdown(
            f'<div class="slot-opt {sel_cls}">'
            f'  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">'
            f'    <div>'
            f'      <div style="font-weight:600;font-size:.98rem">'
            f'        {tick}{DATES_EN[di]} &nbsp;·&nbsp; {ALL_SLOTS[si]} TST'
            f'      </div>'
            f'      <div style="font-size:.88rem;color:#555;margin-top:4px">'
            f'        🕐 Your local time: &nbsp;<strong>{ALL_LOCAL[si]}</strong>'
            f'      </div>'
            f'      <div style="font-size:.78rem;color:#999;margin-top:2px">'
            f'        Join 20 min early: {ALL_EARLY[si]}{note}'
            f'      </div>'
            f'    </div>'
            f'    {tag_html}'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True
        )

        label = (
            f"✓  Keep this slot · 維持此時段 — {DATES_EN[di]} {ALL_SLOTS[si]}"
            if is_sel else
            f"Register for this slot · 報名此時段 — {DATES_EN[di]} {ALL_SLOTS[si]}"
        )
        if st.button(label, key=f"slot_{di}_{si}", use_container_width=True,
                     type="primary" if is_sel else "secondary"):
            if not is_sel:
                b = {"name": name, "region": region, "di": di, "si": si}
                db_set(f"students/{name}", b)
                st.session_state.my_booking = b
                st.success("✅ Registered! Your slot has been saved. · 報名成功！時段已儲存。")
                st.balloons()
                st.rerun()

    st.divider()

    col_r, col_b = st.columns(2)
    with col_r:
        if st.button("↻ Refresh slots / 更新時段", use_container_width=True):
            slots = db_get("open_slots") or []
            st.session_state.open_slots = slots if isinstance(slots, list) else []
            booking = db_get(f"students/{name}")
            st.session_state.my_booking = booking if isinstance(booking, dict) else None
            st.rerun()
    with col_b:
        if st.button("← Edit my details / 修改資料", use_container_width=True):
            go("identify")

    # ── Footer notice ──────────────────────────────────
    st.markdown("""
    <div class="notice" style="margin-top:1rem">
    📧 After registering, please wait for a confirmation email with your Zoom link from CLC staff.<br>
    <span style="color:#888">報名後，請等待 CLC 工作人員寄送含有 Zoom 連結的確認信件。</span>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════
if st.session_state.screen == "slots":
    screen_slots()
else:
    screen_identify()
