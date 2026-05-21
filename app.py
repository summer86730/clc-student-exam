"""
CLC Oral Exam Registration System / 口試報名系統
Chinese Language Center · NCKU
Bilingual ZH / EN · Firebase Realtime DB backend
"""

import streamlit as st
import json
import os

# ══════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════
st.set_page_config(
    page_title="CLC Oral Exam 口試報名",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════
DATES_EN = ["5/26 (Mon)", "5/27 (Tue)", "5/28 (Wed)", "5/29 (Thu)"]
DATES_ZH = ["5/26 (一)",  "5/27 (二)",  "5/28 (三)",  "5/29 (四)"]
AM_SLOTS  = ["08:00", "09:00", "10:00", "11:00"]
PM_SLOTS  = ["14:00", "15:00", "16:00", "17:00"]
AM_LOCAL  = ["Prev. night EDT 20:00", "EDT 21:00", "EDT 22:00", "EDT 23:00"]
PM_LOCAL  = ["CET 07:00", "CET 08:00", "CET 09:00", "CET 10:00"]
AM_EARLY  = ["Prev. night EDT 19:40", "EDT 20:40", "EDT 21:40", "EDT 22:40"]
PM_EARLY  = ["CET 06:40", "CET 07:40", "CET 08:40", "CET 09:40"]
ALL_SLOTS  = AM_SLOTS + PM_SLOTS    # index 0-3 = Americas, 4-7 = Europe
ALL_LOCAL  = AM_LOCAL + PM_LOCAL
ALL_EARLY  = AM_EARLY + PM_EARLY
SLOT_REG   = ["us"] * 4 + ["eu"] * 4
N_D, N_S   = 4, 8
ADMIN_PW   = st.secrets.get("admin_password", "CLC2026")

# ══════════════════════════════════════════════════════
# CUSTOM CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Bilingual label ── */
.bi { display:flex; flex-direction:column; line-height:1.35; }
.bi .zh { font-size:.92rem; color:#1a1a18; }
.bi .en { font-size:.75rem; color:#888; margin-top:1px; }

/* ── Count badges ── */
.cnt-ok   { background:#eaf3de; color:#27500a; padding:2px 9px; border-radius:5px; font-weight:600; font-size:.82rem; }
.cnt-warn { background:#faeeda; color:#633806; padding:2px 9px; border-radius:5px; font-weight:600; font-size:.82rem; }
.cnt-bad  { background:#fcebeb; color:#a32d2d; padding:2px 9px; border-radius:5px; font-weight:600; font-size:.82rem; }
.cnt-zero { background:#f1efe8; color:#aaa;    padding:2px 9px; border-radius:5px; font-size:.82rem; }

/* ── Session tags ── */
.tag-am { background:#faeeda; color:#633806; padding:3px 10px; border-radius:6px; font-size:.78rem; font-weight:500; }
.tag-pm { background:#e6f1fb; color:#0c447c; padding:3px 10px; border-radius:6px; font-size:.78rem; font-weight:500; }
.tag-ok { background:#e1f5ee; color:#085041; padding:3px 10px; border-radius:6px; font-size:.78rem; font-weight:500; }

/* ── Booking confirmed card ── */
.book-card {
  background:#e1f5ee; border:1px solid #9fe1cb;
  border-radius:10px; padding:1rem 1.2rem; margin-bottom:1rem;
}

/* ── Slot options ── */
.slot-opt {
  border:1px solid #ddd; border-radius:10px;
  padding:14px 16px; margin-bottom:8px;
  transition: border-color .15s;
}
.slot-sel-am { border:2px solid #ef9f27 !important; background:#faeeda18; }
.slot-sel-pm { border:2px solid #378add !important; background:#e6f1fb18; }

/* ── Section headers ── */
.sec-am { background:#faeeda; color:#633806; padding:7px 14px; border-radius:8px 8px 0 0; font-weight:500; font-size:.88rem; }
.sec-pm { background:#e6f1fb; color:#0c447c; padding:7px 14px; border-radius:8px 8px 0 0; font-weight:500; font-size:.88rem; }

/* ── Phase banner ── */
.phase-bar {
  background:#f7f6f3; border:1px solid #e8e7e2;
  border-radius:8px; padding:8px 14px;
  font-size:.82rem; color:#666;
  display:flex; align-items:center; gap:10px;
  margin-bottom:1.2rem;
}
.phase-on  { background:#e6f1fb; color:#0c447c; padding:4px 10px; border-radius:5px; font-weight:500; }
.phase-off { color:#bbb; }

/* ── Misc ── */
[data-testid="stSidebar"] { display:none; }
.stButton button { border-radius:8px !important; }
footer { display:none !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# FIREBASE SETUP
# ══════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def init_firebase():
    """Init Firebase Admin SDK once. Returns (db_module, True) or (None, False)."""
    try:
        import firebase_admin
        from firebase_admin import credentials, db
        if not firebase_admin._apps:
            cred_dict = dict(st.secrets["firebase_credentials"])
            # Streamlit secrets store \n as literal \\n – fix it
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

# ── Local JSON fallback (single-user dev mode) ──────────
_LOCAL_PATH = "/tmp/clc_local_db.json"

def _local_load() -> dict:
    if os.path.exists(_LOCAL_PATH):
        with open(_LOCAL_PATH) as f:
            return json.load(f)
    return {}

def _local_save(data: dict):
    with open(_LOCAL_PATH, "w") as f:
        json.dump(data, f)

# ── Generic get / set / get_all ─────────────────────────
def db_get(path: str):
    if FIREBASE_OK:
        return _fb.reference(path).get()
    data = _local_load()
    keys = path.strip("/").split("/")
    for k in keys:
        if isinstance(data, dict) and k in data:
            data = data[k]
        else:
            return None
    return data

def db_set(path: str, value):
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

def db_get_all(path: str) -> dict:
    if FIREBASE_OK:
        return _fb.reference(path).get() or {}
    data = _local_load()
    keys = path.strip("/").split("/")
    for k in keys:
        if isinstance(data, dict) and k in data:
            data = data[k]
        else:
            return {}
    return data if isinstance(data, dict) else {}

# ══════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════
_defaults = {
    "screen":         "landing",
    "user_name":      "",
    "region":         "eu",
    "my_booking":     None,
    "open_slots":     [],
    "counts":         [[0] * N_S for _ in range(N_D)],
    "students":       {},
    "admin_open":     [],
    "avail_loaded":   False,
    "pw_error":       False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════
def go(screen: str):
    st.session_state.screen = screen
    st.rerun()

def badge(n: int) -> str:
    if n >= 3: cls = "cnt-ok"
    elif n == 2: cls = "cnt-warn"
    elif n == 1: cls = "cnt-bad"
    else: cls = "cnt-zero"
    return f'<span class="{cls}">{n}</span>'

def bi(zh: str, en: str) -> str:
    return f'<div class="bi"><span class="zh">{zh}</span><span class="en">{en}</span></div>'

def load_counts():
    teachers = db_get_all("teachers")
    counts = [[0] * N_S for _ in range(N_D)]
    for avail in teachers.values():
        if isinstance(avail, list):
            for di, row in enumerate(avail):
                for si, v in enumerate(row):
                    if v and di < N_D and si < N_S:
                        counts[di][si] += 1
    st.session_state.counts = counts

def load_open_slots():
    slots = db_get("open_slots") or []
    st.session_state.open_slots = slots if isinstance(slots, list) else []

def load_students():
    st.session_state.students = db_get_all("students")

def my_avail_key(di: int, si: int) -> str:
    return f"avail_{di}_{si}"

def collect_my_avail() -> list:
    return [
        [bool(st.session_state.get(my_avail_key(di, si), False)) for si in range(N_S)]
        for di in range(N_D)
    ]

# ══════════════════════════════════════════════════════
# SCREEN: LANDING
# ══════════════════════════════════════════════════════
def screen_landing():
    st.markdown("### 🎓 CLC Oral Exam Registration")
    st.caption("Chinese Language Center · NCKU &nbsp;|&nbsp; 5/26–5/29, 2025")

    if not FIREBASE_OK:
        st.warning(
            "⚠️ **Demo mode** – Firebase not configured. "
            "Data saves to a local file and is not shared across users. "
            "Configure `secrets.toml` to enable multi-user sharing.\n\n"
            "⚠️ **示範模式** — Firebase 尚未設定，資料僅存於本機，無法多人共享。"
        )

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**🧑‍🏫**")
        st.markdown(bi("老師", "Teacher"), unsafe_allow_html=True)
        st.caption("填寫可用空堂時段  \nFill in availability")
        if st.button("進入 / Enter →", key="go_teacher", use_container_width=True):
            go("teacher_id")
    with c2:
        st.markdown("**🎓**")
        st.markdown(bi("學生", "Student"), unsafe_allow_html=True)
        st.caption("查看並報名口試時段  \nView & register slots")
        if st.button("進入 / Enter →", key="go_student", use_container_width=True):
            go("student_id")
    with c3:
        st.markdown("**🛡️**")
        st.markdown(bi("管理員", "Admin"), unsafe_allow_html=True)
        st.caption("確認時段並開放報名  \nPublish slots")
        if st.button("進入 / Enter →", key="go_admin", use_container_width=True):
            go("admin_id")

    st.divider()
    st.markdown(
        '<div style="font-size:.8rem;color:#888">'
        '🔒 每位使用者僅能讀寫自己的資料，不會影響他人。'
        '<br>Each user reads and writes only their own record — no data collisions.'
        '</div>',
        unsafe_allow_html=True
    )

# ══════════════════════════════════════════════════════
# SCREEN: TEACHER IDENTIFY
# ══════════════════════════════════════════════════════
def screen_teacher_id():
    if st.button("← Back / 返回", key="back_tid"):
        go("landing")

    st.markdown("### 🧑‍🏫 " + bi("老師空堂填寫", "Teacher Availability"), unsafe_allow_html=True)
    st.info(
        "您只能修改自己的那一列，不會影響其他老師的填寫。  \n"
        "You can only edit your own row — other teachers' data is untouched."
    )

    name = st.text_input(
        bi("姓名（作為識別，下次可重新登入繼續填寫）",
           "Your name — used as your ID; log in again anytime to update"),
        value=st.session_state.user_name,
        placeholder="e.g. 陳老師 / Prof. Chen",
        key="inp_teacher_name"
    )

    if st.button("開始填寫 / Continue →", type="primary", use_container_width=True):
        name = name.strip()
        if not name:
            st.error("請輸入姓名 / Please enter your name")
            return
        st.session_state.user_name = name
        st.session_state.avail_loaded = False  # force reload
        go("teacher_grid")

# ══════════════════════════════════════════════════════
# SCREEN: TEACHER GRID
# ══════════════════════════════════════════════════════
def screen_teacher_grid():
    name = st.session_state.user_name

    # Load teacher's own data once per session
    if not st.session_state.avail_loaded:
        load_counts()
        saved = db_get(f"teachers/{name}")
        if isinstance(saved, list):
            for di in range(N_D):
                for si in range(N_S):
                    try:
                        st.session_state[my_avail_key(di, si)] = bool(saved[di][si])
                    except (IndexError, TypeError):
                        st.session_state[my_avail_key(di, si)] = False
        else:
            for di in range(N_D):
                for si in range(N_S):
                    if my_avail_key(di, si) not in st.session_state:
                        st.session_state[my_avail_key(di, si)] = False
        st.session_state.avail_loaded = True

    # Header
    col_h, col_btn = st.columns([3, 1])
    with col_h:
        st.markdown(f"### 🧑‍🏫 {name}")
        st.caption("勾選您可用的時段 · Check your available slots")
    with col_btn:
        if st.button("← Back", key="back_tgrid"):
            st.session_state.avail_loaded = False
            go("landing")

    counts = st.session_state.counts

    st.markdown(
        '<div style="font-size:.8rem;color:#666;margin-bottom:.5rem">'
        '數字 = 目前確認老師數（含您已儲存的部分）· 綠≥3 · 橘=2 · 紅=1'
        '<br>Number = teachers confirmed (incl. your saved data) · Green≥3 · Orange=2 · Red=1'
        '</div>',
        unsafe_allow_html=True
    )

    def render_section(is_am: bool):
        slots     = AM_SLOTS if is_am else PM_SLOTS
        local_lbl = AM_LOCAL if is_am else PM_LOCAL
        offset    = 0 if is_am else 4
        cls       = "sec-am" if is_am else "sec-pm"
        title     = (
            "🌎 美洲場 Americas — 台灣早上 TST morning"
            if is_am else
            "🇪🇺 歐洲場 Europe — 台灣下午 TST afternoon"
        )
        st.markdown(f'<div class="{cls}">{title}</div>', unsafe_allow_html=True)

        # Header row — TST large & bold, local timezone small muted below
        cols = st.columns([1.8] + [1] * len(slots))
        cols[0].markdown(
            '<div style="font-size:.95rem;font-weight:600;color:var(--text-color)">日期</div>'
            '<div style="font-size:.72rem;color:#aaa;margin-top:2px">Date</div>',
            unsafe_allow_html=True
        )
        for i, (t, lbl) in enumerate(zip(slots, local_lbl)):
            cols[i + 1].markdown(
                f'<div style="font-size:1rem;font-weight:700;color:var(--text-color);letter-spacing:-.3px">{t}</div>'
                f'<div style="font-size:.7rem;font-weight:400;color:#aaa;margin-top:3px;line-height:1.4">{lbl}</div>',
                unsafe_allow_html=True
            )

        st.markdown('<hr style="margin:4px 0 8px;border-color:#eee">', unsafe_allow_html=True)

        for di, (d_en, d_zh) in enumerate(zip(DATES_EN, DATES_ZH)):
            cols = st.columns([1.8] + [1] * len(slots))
            cols[0].markdown(
                f'<div class="bi"><span class="zh">{d_zh}</span><span class="en">{d_en}</span></div>',
                unsafe_allow_html=True
            )
            for i in range(len(slots)):
                si = offset + i
                n  = counts[di][si]
                key = my_avail_key(di, si)
                with cols[i + 1]:
                    st.checkbox("", key=key, label_visibility="collapsed")
                    st.markdown(badge(n), unsafe_allow_html=True)

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    with st.container(border=True):
        render_section(True)
        st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)
        render_section(False)

    st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)
    if st.button("💾 儲存我的空堂 / Save my availability", type="primary", use_container_width=True):
        avail = collect_my_avail()
        db_set(f"teachers/{name}", avail)
        load_counts()  # refresh counts immediately
        st.success("✅ 儲存成功！/ Saved successfully!")
        st.rerun()

# ══════════════════════════════════════════════════════
# SCREEN: ADMIN IDENTIFY
# ══════════════════════════════════════════════════════
def screen_admin_id():
    if st.button("← Back / 返回", key="back_aid"):
        go("landing")

    st.markdown("### 🛡️ " + bi("管理員登入", "Admin Login"), unsafe_allow_html=True)

    pw = st.text_input(
        bi("管理密碼", "Password"),
        type="password",
        placeholder="Enter password"
    )
    if st.session_state.pw_error:
        st.error("❌ 密碼錯誤 / Incorrect password")

    if st.button("登入 / Login", type="primary", use_container_width=True):
        if pw == ADMIN_PW:
            st.session_state.pw_error = False
            load_counts()
            load_open_slots()
            load_students()
            st.session_state.admin_open = [
                f"{o['di']}_{o['si']}" for o in st.session_state.open_slots
                if isinstance(o, dict)
            ]
            go("admin_dash")
        else:
            st.session_state.pw_error = True
            st.rerun()

    st.caption(f"預設密碼 / Default password: `{ADMIN_PW}`")

# ══════════════════════════════════════════════════════
# SCREEN: ADMIN DASHBOARD
# ══════════════════════════════════════════════════════
def screen_admin_dash():
    col_h, col_r = st.columns([4, 1])
    with col_h:
        st.markdown("### 🛡️ " + bi("管理員儀表板", "Admin Dashboard"), unsafe_allow_html=True)
    with col_r:
        if st.button("↻ Refresh", key="admin_refresh"):
            load_counts()
            load_students()
            st.rerun()

    if st.button("← Back", key="back_adash"):
        go("landing")

    counts = st.session_state.counts

    # ── Phase banner ──
    st.markdown(
        '<div class="phase-bar">'
        '<span class="phase-on">Phase 1 老師填寫空堂</span>'
        '<span>›</span>'
        '<span class="phase-on">Phase 2 開放學生報名</span>'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(bi("各時段老師確認人數 · 勾選開放給學生的時段",
                   "Teacher count per slot · Check to publish slots to students"),
                unsafe_allow_html=True)

    # ── Slot grid ──
    def slot_section(is_am: bool):
        slots  = AM_SLOTS if is_am else PM_SLOTS
        offset = 0 if is_am else 4
        cls    = "sec-am" if is_am else "sec-pm"
        label  = ("🌎 Americas · 美洲場" if is_am else "🇪🇺 Europe · 歐洲場")
        st.markdown(f'<div class="{cls}">{label}</div>', unsafe_allow_html=True)

        hdr = st.columns([1.6] + [1] * len(slots))
        hdr[0].markdown('<div class="bi"><span class="zh">日期</span><span class="en">Date</span></div>', unsafe_allow_html=True)
        for i, t in enumerate(slots):
            hdr[i + 1].markdown(f"**{t}**", unsafe_allow_html=False)

        for di, (d_en, d_zh) in enumerate(zip(DATES_EN, DATES_ZH)):
            cols = st.columns([1.6] + [1] * len(slots))
            cols[0].markdown(
                f'<div class="bi"><span class="zh">{d_zh}</span><span class="en">{d_en}</span></div>',
                unsafe_allow_html=True
            )
            for i in range(len(slots)):
                si  = offset + i
                n   = counts[di][si]
                key = f"{di}_{si}"
                with cols[i + 1]:
                    st.markdown(badge(n), unsafe_allow_html=True)
                    if n >= 3:
                        checked = key in st.session_state.admin_open
                        if st.checkbox("開放", value=checked, key=f"adm_{key}"):
                            if key not in st.session_state.admin_open:
                                st.session_state.admin_open.append(key)
                        else:
                            if key in st.session_state.admin_open:
                                st.session_state.admin_open.remove(key)

    with st.container(border=True):
        slot_section(True)
        st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)
        slot_section(False)

    n_open = len(st.session_state.admin_open)
    if st.button(
        f"🔓 確認開放 {n_open} 個時段 / Publish {n_open} slot{'s' if n_open != 1 else ''}",
        type="primary", use_container_width=True
    ):
        slots_to_save = [
            {"di": int(k.split("_")[0]), "si": int(k.split("_")[1])}
            for k in st.session_state.admin_open
        ]
        db_set("open_slots", slots_to_save)
        st.session_state.open_slots = slots_to_save
        st.success(f"✅ 已開放 {n_open} 個時段！/ {n_open} slot(s) published!")

    # ── Student registrations ──
    st.divider()
    students = st.session_state.students
    st.markdown(bi(f"學生報名狀況（{len(students)} 人）",
                   f"Student registrations ({len(students)} total)"),
                unsafe_allow_html=True)

    if not students:
        st.caption("尚無學生報名。開放時段後通知學生填寫。  \nNo registrations yet. Notify students after publishing slots.")
    else:
        rows = []
        for s in students.values():
            if not isinstance(s, dict):
                continue
            di, si = s.get("di", 0), s.get("si", 0)
            rows.append({
                "姓名 / Name": s.get("name", ""),
                "區域 / Region": ("🇪🇺 Europe" if s.get("region") == "eu" else "🌎 Americas"),
                "日期 / Date": f"{DATES_ZH[di]} {DATES_EN[di]}",
                "台灣時段 TST": ALL_SLOTS[si],
                "當地時間 Local": ALL_LOCAL[si],
                "提前上線 Join early": ALL_EARLY[si],
            })
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if st.button("↻ Refresh student list / 重新整理", key="refresh_students"):
        load_students()
        st.rerun()

# ══════════════════════════════════════════════════════
# SCREEN: STUDENT IDENTIFY
# ══════════════════════════════════════════════════════
def screen_student_id():
    if st.button("← Back / 返回", key="back_sid"):
        go("landing")

    st.markdown("### 🎓 Oral Exam Registration")
    st.markdown(bi("口試報名系統", "Chinese Language Center · NCKU"), unsafe_allow_html=True)

    st.info(
        "Welcome to the CLC Online Placement Interview registration.  \n"
        "歡迎使用成大華語中心線上分班口試報名系統。"
    )

    name = st.text_input(
        "Your full name / 姓名",
        value=st.session_state.user_name,
        placeholder="e.g. Maria Schmidt"
    )

    region = st.radio(
        "Your location / 所在地區",
        options=["eu", "us"],
        format_func=lambda x: "🇪🇺 Europe / 歐洲" if x == "eu" else "🌎 Americas / 美洲",
        index=0 if st.session_state.region == "eu" else 1,
        horizontal=True
    )

    if st.button("查看可報名時段 / View available slots →", type="primary", use_container_width=True):
        name = name.strip()
        if not name:
            st.error("Please enter your name / 請輸入姓名")
            return
        st.session_state.user_name = name
        st.session_state.region = region
        load_open_slots()
        booking = db_get(f"students/{name}")
        st.session_state.my_booking = booking if isinstance(booking, dict) else None
        go("student_slots")

    st.markdown(
        '<div style="font-size:.82rem;color:#666;margin-top:.75rem">'
        'Please join the Zoom call <strong>20 minutes before</strong> your scheduled time for a tech check.  <br>'
        '請於口試時間<strong>提前 20 分鐘</strong>上線進行設備測試。'
        '</div>',
        unsafe_allow_html=True
    )

# ══════════════════════════════════════════════════════
# SCREEN: STUDENT SLOT SELECTION
# ══════════════════════════════════════════════════════
def screen_student_slots():
    name   = st.session_state.user_name
    region = st.session_state.region

    col_h, col_b = st.columns([4, 1])
    with col_h:
        st.markdown(f"### 🎓 {name}")
        st.caption("🇪🇺 Europe" if region == "eu" else "🌎 Americas")
    with col_b:
        if st.button("← Back", key="back_sslot"):
            go("landing")

    # ── Confirmed booking banner ──
    booking = st.session_state.my_booking
    if booking and isinstance(booking, dict):
        di, si = booking.get("di", 0), booking.get("si", 0)
        st.markdown(
            f'<div class="book-card">'
            f'<div style="font-weight:600;color:#085041;margin-bottom:4px">✅ Registered · 已成功報名</div>'
            f'<div style="font-size:1rem;font-weight:500">{DATES_EN[di]} &nbsp;·&nbsp; {ALL_SLOTS[si]} Taiwan time (TST)</div>'
            f'<div style="font-size:.88rem;margin-top:4px">Your local time / 您的當地時間：<strong>{ALL_LOCAL[si]}</strong></div>'
            f'<div style="font-size:.82rem;color:#0f6e56;margin-top:3px">'
            f'Join 20 min early at / 請於 <strong>{ALL_EARLY[si]}</strong> 上線</div>'
            f'<div style="font-size:.75rem;color:#666;margin-top:8px">'
            f'To change your slot, click another option below. · 如需更改，點選下方其他時段。</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Available slots ──
    open_slots = st.session_state.open_slots
    relevant = [
        o for o in open_slots
        if isinstance(o, dict) and (
            (region == "eu" and SLOT_REG[o["si"]] == "eu") or
            (region == "us" and SLOT_REG[o["si"]] == "us")
        )
    ]

    if not relevant:
        st.warning(
            "No slots are available yet. Please check back after the admin publishes the schedule.\n\n"
            "目前尚無開放時段，請等候通知後再回來查看。"
        )
        return

    st.markdown("**Available interview slots · 可報名時段**")
    st.caption("Click a slot to register. · 點選時段即可報名，系統自動儲存。")

    for o in relevant:
        di, si  = o["di"], o["si"]
        is_am   = SLOT_REG[si] == "us"
        is_sel  = (booking and isinstance(booking, dict)
                   and booking.get("di") == di and booking.get("si") == si)
        sel_cls = ("slot-sel-am" if is_am else "slot-sel-pm") if is_sel else ""
        checkmark = "✓ " if is_sel else ""
        tag_cls = "tag-am" if is_am else "tag-pm"
        tag_lbl = "Americas" if is_am else "Europe"
        note    = "<br><span style='font-size:.75rem;color:#aaa'>* Previous calendar day (US)</span>" if is_am else ""

        st.markdown(
            f'<div class="slot-opt {sel_cls}">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
            f'<div>'
            f'<div style="font-weight:500;font-size:.95rem">'
            f'{DATES_EN[di]} &nbsp;·&nbsp; {ALL_SLOTS[si]} Taiwan time (TST)</div>'
            f'<div style="font-size:.85rem;color:#666;margin-top:3px">'
            f'Your local time: <strong>{ALL_LOCAL[si]}</strong></div>'
            f'<div style="font-size:.78rem;color:#aaa;margin-top:2px">'
            f'Join 20 min early: {ALL_EARLY[si]}{note}</div>'
            f'</div>'
            f'<span class="tag {tag_cls}">{checkmark}{tag_lbl}</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )
        btn_label = f"{'✓ Selected · ' if is_sel else ''}Register · 報名 — {DATES_EN[di]} {ALL_SLOTS[si]} TST"
        if st.button(btn_label, key=f"slot_{di}_{si}", use_container_width=True):
            b = {"name": name, "region": region, "di": di, "si": si}
            db_set(f"students/{name}", b)
            st.session_state.my_booking = b
            st.success("✅ Registered! · 報名成功！")
            st.rerun()

# ══════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════
ROUTES = {
    "landing":      screen_landing,
    "teacher_id":   screen_teacher_id,
    "teacher_grid": screen_teacher_grid,
    "admin_id":     screen_admin_id,
    "admin_dash":   screen_admin_dash,
    "student_id":   screen_student_id,
    "student_slots":screen_student_slots,
}

ROUTES.get(st.session_state.screen, screen_landing)()
