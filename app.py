"""
CLC Oral Exam Registration System / 口試報名系統
Chinese Language Center · NCKU
Bilingual ZH / EN · Firebase Realtime DB backend
v3: Dynamic config — admin can adjust dates, sessions, timezones from UI
"""

import streamlit as st
import json, os, copy

# ══════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════
st.set_page_config(
    page_title="CLC Oral Exam 口試報名",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

ADMIN_PW = st.secrets.get("admin_password", "CLC2026")

# ══════════════════════════════════════════════════════
# DEFAULT CONFIG  (used when Firebase has no config yet)
# ══════════════════════════════════════════════════════
DEFAULT_CONFIG = {
    "dates": [
        {"en": "5/26 (Mon)", "zh": "5/26 (一)", "iso": "2025-05-26"},
        {"en": "5/27 (Tue)", "zh": "5/27 (二)", "iso": "2025-05-27"},
        {"en": "5/28 (Wed)", "zh": "5/28 (三)", "iso": "2025-05-28"},
        {"en": "5/29 (Thu)", "zh": "5/29 (四)", "iso": "2025-05-29"},
    ],
    "sessions": [
        {
            "region": "us",
            "flag": "🌎",
            "name_zh": "美洲場",
            "name_en": "Americas",
            "slots": [
                {"tst": "08:00", "local": "Prev. night EDT 20:00", "early": "Prev. night EDT 19:40"},
                {"tst": "09:00", "local": "EDT 21:00",             "early": "EDT 20:40"},
                {"tst": "10:00", "local": "EDT 22:00",             "early": "EDT 21:40"},
                {"tst": "11:00", "local": "EDT 23:00",             "early": "EDT 22:40"},
            ],
        },
        {
            "region": "eu",
            "flag": "🇪🇺",
            "name_zh": "歐洲場",
            "name_en": "Europe",
            "slots": [
                {"tst": "14:00", "local": "CET 07:00", "early": "CET 06:40"},
                {"tst": "15:00", "local": "CET 08:00", "early": "CET 07:40"},
                {"tst": "16:00", "local": "CET 09:00", "early": "CET 08:40"},
                {"tst": "17:00", "local": "CET 10:00", "early": "CET 09:40"},
            ],
        },
    ],
}

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
.bi { display:flex; flex-direction:column; line-height:1.35; }
.bi .zh { font-size:.92rem; color:#1a1a18; }
.bi .en { font-size:.75rem; color:#888; margin-top:1px; }
.cnt-ok   { background:#eaf3de; color:#27500a; padding:2px 9px; border-radius:5px; font-weight:600; font-size:.82rem; }
.cnt-warn { background:#faeeda; color:#633806; padding:2px 9px; border-radius:5px; font-weight:600; font-size:.82rem; }
.cnt-bad  { background:#fcebeb; color:#a32d2d; padding:2px 9px; border-radius:5px; font-weight:600; font-size:.82rem; }
.cnt-zero { background:#f1efe8; color:#aaa;    padding:2px 9px; border-radius:5px; font-size:.82rem; }
.tag-am { background:#faeeda; color:#633806; padding:3px 10px; border-radius:6px; font-size:.78rem; font-weight:500; }
.tag-pm { background:#e6f1fb; color:#0c447c; padding:3px 10px; border-radius:6px; font-size:.78rem; font-weight:500; }
.book-card { background:#e1f5ee; border:1px solid #9fe1cb; border-radius:10px; padding:1rem 1.2rem; margin-bottom:1rem; }
.slot-opt { border:1px solid #ddd; border-radius:10px; padding:14px 16px; margin-bottom:8px; }
.slot-sel-am { border:2px solid #ef9f27 !important; background:#faeeda18; }
.slot-sel-pm { border:2px solid #378add !important; background:#e6f1fb18; }
.sec-am { background:#faeeda; color:#633806; padding:7px 14px; border-radius:8px 8px 0 0; font-weight:500; font-size:.88rem; }
.sec-pm { background:#e6f1fb; color:#0c447c; padding:7px 14px; border-radius:8px 8px 0 0; font-weight:500; font-size:.88rem; }
.phase-bar { background:#f7f6f3; border:1px solid #e8e7e2; border-radius:8px; padding:8px 14px; font-size:.82rem; color:#666; display:flex; align-items:center; gap:10px; margin-bottom:1.2rem; }
.phase-on  { background:#e6f1fb; color:#0c447c; padding:4px 10px; border-radius:5px; font-weight:500; }
.cfg-row   { background:#f7f6f3; border:0.5px solid #e0ddd6; border-radius:8px; padding:10px 12px; margin-bottom:8px; }
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

def _local_load() -> dict:
    if os.path.exists(_LOCAL_PATH):
        with open(_LOCAL_PATH) as f: return json.load(f)
    return {}

def _local_save(data: dict):
    with open(_LOCAL_PATH, "w") as f: json.dump(data, f)

def db_get(path: str):
    if FIREBASE_OK: return _fb.reference(path).get()
    data = _local_load()
    for k in path.strip("/").split("/"):
        data = data.get(k) if isinstance(data, dict) else None
        if data is None: return None
    return data

def db_set(path: str, value):
    if FIREBASE_OK: _fb.reference(path).set(value)
    else:
        data = _local_load()
        keys = path.strip("/").split("/")
        d = data
        for k in keys[:-1]: d = d.setdefault(k, {})
        d[keys[-1]] = value
        _local_save(data)

def db_get_all(path: str) -> dict:
    if FIREBASE_OK: return _fb.reference(path).get() or {}
    data = _local_load()
    for k in path.strip("/").split("/"):
        data = data.get(k) if isinstance(data, dict) else None
        if data is None: return {}
    return data if isinstance(data, dict) else {}

def db_delete(path: str):
    if FIREBASE_OK: _fb.reference(path).delete()
    else:
        data = _local_load()
        keys = path.strip("/").split("/")
        d = data
        for k in keys[:-1]:
            if isinstance(d, dict) and k in d: d = d[k]
            else: return
        if isinstance(d, dict) and keys[-1] in d: del d[keys[-1]]
        _local_save(data)

# ══════════════════════════════════════════════════════
# CONFIG SYSTEM
# ══════════════════════════════════════════════════════
def _fix_firebase_lists(obj):
    """Firebase stores lists as {0: v, 1: v}. Recursively convert back."""
    if isinstance(obj, dict):
        # Check if all keys are numeric strings → it's a list
        if obj and all(k.isdigit() for k in obj.keys()):
            return [_fix_firebase_lists(obj[str(i)]) for i in range(len(obj))]
        return {k: _fix_firebase_lists(v) for k, v in obj.items()}
    return obj

def load_config() -> dict:
    raw = db_get("config")
    if isinstance(raw, dict) and "sessions" in raw and "dates" in raw:
        return _fix_firebase_lists(raw)
    return copy.deepcopy(DEFAULT_CONFIG)

def save_config(cfg: dict):
    db_set("config", cfg)
    st.session_state.app_config = cfg

def derive(cfg: dict):
    """Derive flat arrays from config. Returns (DATES_EN, DATES_ZH, DATES_ISO,
    ALL_SLOTS, ALL_LOCAL, ALL_EARLY, SLOT_REG, N_D, N_S)"""
    dates_en  = [d["en"]  for d in cfg["dates"]]
    dates_zh  = [d["zh"]  for d in cfg["dates"]]
    dates_iso = [d.get("iso","2025-01-01") for d in cfg["dates"]]
    slots, local, early, reg = [], [], [], []
    for sess in cfg["sessions"]:
        for s in sess["slots"]:
            slots.append(s["tst"])
            local.append(s["local"])
            early.append(s["early"])
            reg.append(sess["region"])
    return dates_en, dates_zh, dates_iso, slots, local, early, reg, len(dates_en), len(slots)

# ── Load config once per session (admin can force-reload) ──
if "app_config" not in st.session_state:
    st.session_state.app_config = load_config()

_C = st.session_state.app_config
DATES_EN, DATES_ZH, DATES_ISO, ALL_SLOTS, ALL_LOCAL, ALL_EARLY, SLOT_REG, N_D, N_S = derive(_C)

# ══════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════
_defaults = {
    "screen":       "landing",
    "user_name":    "",
    "region":       "eu",
    "my_booking":   None,
    "open_slots":   [],
    "counts":       [[0]*N_S for _ in range(N_D)],
    "students":     {},
    "admin_open":   [],
    "avail_loaded": False,
    "pw_error":     False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════
def go(s): st.session_state.screen = s; st.rerun()

def badge(n):
    cls = "cnt-ok" if n>=3 else "cnt-warn" if n==2 else "cnt-bad" if n==1 else "cnt-zero"
    return f'<span class="{cls}">{n}</span>'

def bi(zh, en):
    return f'<div class="bi"><span class="zh">{zh}</span><span class="en">{en}</span></div>'

def load_counts():
    teachers = db_get_all("teachers")
    counts = [[0]*N_S for _ in range(N_D)]
    for avail in teachers.values():
        if isinstance(avail, list):
            for di, row in enumerate(avail):
                for si, v in enumerate(row):
                    if v and di < N_D and si < N_S: counts[di][si] += 1
    st.session_state.counts = counts

def load_open_slots():
    slots = db_get("open_slots") or []
    st.session_state.open_slots = slots if isinstance(slots, list) else []

def load_students():
    st.session_state.students = db_get_all("students")

def session_for_si(si):
    """Return the session dict that owns slot index si."""
    idx = 0
    for sess in _C["sessions"]:
        for _ in sess["slots"]:
            if idx == si: return sess
            idx += 1
    return _C["sessions"][0]

def sec_cls(si):
    sess = session_for_si(si)
    return "sec-am" if sess["region"] == "us" else "sec-pm"

# ══════════════════════════════════════════════════════
# SCREEN: LANDING
# ══════════════════════════════════════════════════════
def screen_landing():
    st.markdown("### 🎓 CLC Oral Exam Registration")
    st.caption("Chinese Language Center · NCKU")
    if not FIREBASE_OK:
        st.warning("⚠️ **Demo mode** — Firebase not configured. Data saved locally only.")
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**🧑‍🏫**")
        st.markdown(bi("老師","Teacher"), unsafe_allow_html=True)
        st.caption("填寫可用空堂時段\nFill in availability")
        if st.button("進入 / Enter →", key="go_teacher", use_container_width=True): go("teacher_id")
    with c2:
        st.markdown("**🎓**")
        st.markdown(bi("學生","Student"), unsafe_allow_html=True)
        st.caption("查看並報名口試時段\nView & register slots")
        if st.button("進入 / Enter →", key="go_student", use_container_width=True): go("student_id")
    with c3:
        st.markdown("**🛡️**")
        st.markdown(bi("管理員","Admin"), unsafe_allow_html=True)
        st.caption("確認時段並開放報名\nPublish slots")
        if st.button("進入 / Enter →", key="go_admin", use_container_width=True): go("admin_id")
    st.divider()
    st.markdown('<div style="font-size:.8rem;color:#888">🔒 每位使用者僅能讀寫自己的資料。Each user writes only their own record.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# SCREEN: TEACHER IDENTIFY
# ══════════════════════════════════════════════════════
def screen_teacher_id():
    if st.button("← Back / 返回", key="back_tid"): go("landing")
    st.markdown("### 🧑‍🏫 " + bi("老師空堂填寫","Teacher Availability"), unsafe_allow_html=True)
    st.info("您只能修改自己的那一列，不會影響其他老師的填寫。\nYou can only edit your own row.")
    name = st.text_input(bi("姓名（作為識別）","Name — your unique ID"),
                         value=st.session_state.user_name, placeholder="e.g. 陳老師 / Prof. Chen", key="inp_tname")
    if st.button("開始填寫 / Continue →", type="primary", use_container_width=True):
        name = name.strip()
        if not name: st.error("請輸入姓名 / Please enter your name"); return
        st.session_state.user_name = name
        st.session_state.avail_loaded = False
        go("teacher_grid")

# ══════════════════════════════════════════════════════
# SCREEN: TEACHER GRID
# ══════════════════════════════════════════════════════
def screen_teacher_grid():
    name = st.session_state.user_name
    if not st.session_state.avail_loaded:
        load_counts()
        saved = db_get(f"teachers/{name}")
        for di in range(N_D):
            for si in range(N_S):
                k = f"avail_{di}_{si}"
                try: st.session_state[k] = bool(saved[di][si]) if isinstance(saved, list) else False
                except: st.session_state[k] = False
        st.session_state.avail_loaded = True

    col_h, col_btn = st.columns([3,1])
    with col_h:
        st.markdown(f"### 🧑‍🏫 {name}")
        st.caption("勾選您可用的時段 · Check your available slots")
    with col_btn:
        if st.button("← Back", key="back_tgrid"):
            st.session_state.avail_loaded = False; go("landing")

    counts = st.session_state.counts
    st.markdown('<div style="font-size:.8rem;color:#666;margin-bottom:.5rem">數字 = 目前確認老師數 · 綠≥3 · 橘=2 · 紅=1</div>', unsafe_allow_html=True)

    def render_section(sess_idx):
        sess = _C["sessions"][sess_idx]
        is_am = sess["region"] == "us"
        cls = "sec-am" if is_am else "sec-pm"
        st.markdown(f'<div class="{cls}">{sess["flag"]} {sess["name_zh"]} {sess["name_en"]} — 台灣早上 TST morning</div>' if is_am
                    else f'<div class="{cls}">{sess["flag"]} {sess["name_zh"]} {sess["name_en"]} — 台灣下午 TST afternoon</div>',
                    unsafe_allow_html=True)
        slots = sess["slots"]
        offset = sum(len(_C["sessions"][i]["slots"]) for i in range(sess_idx))

        hdr = st.columns([1.8] + [1]*len(slots))
        hdr[0].markdown('<div class="bi"><span class="zh">日期</span><span class="en">Date</span></div>', unsafe_allow_html=True)
        for i, s in enumerate(slots):
            hdr[i+1].markdown(
                f'<div style="font-size:1rem;font-weight:700;color:var(--text-color)">{s["tst"]}</div>'
                f'<div style="font-size:.7rem;color:#aaa;margin-top:3px;line-height:1.4">{s["local"]}</div>',
                unsafe_allow_html=True)

        st.markdown('<hr style="margin:4px 0 8px;border-color:#eee">', unsafe_allow_html=True)
        for di in range(N_D):
            cols = st.columns([1.8] + [1]*len(slots))
            cols[0].markdown(f'<div class="bi"><span class="zh">{DATES_ZH[di]}</span><span class="en">{DATES_EN[di]}</span></div>', unsafe_allow_html=True)
            for i in range(len(slots)):
                si = offset + i
                n  = counts[di][si] if di < len(counts) and si < len(counts[di]) else 0
                with cols[i+1]:
                    st.checkbox("", key=f"avail_{di}_{si}", label_visibility="collapsed")
                    st.markdown(badge(n), unsafe_allow_html=True)

    with st.container(border=True):
        for idx in range(len(_C["sessions"])):
            render_section(idx)
            if idx < len(_C["sessions"])-1:
                st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

    if st.button("💾 儲存我的空堂 / Save my availability", type="primary", use_container_width=True):
        avail = [[bool(st.session_state.get(f"avail_{di}_{si}", False)) for si in range(N_S)] for di in range(N_D)]
        db_set(f"teachers/{name}", avail)
        load_counts()
        st.success("✅ 儲存成功！/ Saved!")
        st.rerun()

# ══════════════════════════════════════════════════════
# SCREEN: ADMIN IDENTIFY
# ══════════════════════════════════════════════════════
def screen_admin_id():
    if st.button("← Back / 返回", key="back_aid"): go("landing")
    st.markdown("### 🛡️ " + bi("管理員登入","Admin Login"), unsafe_allow_html=True)
    pw = st.text_input(bi("管理密碼","Password"), type="password", placeholder="Enter password")
    if st.session_state.pw_error: st.error("❌ 密碼錯誤 / Incorrect password")
    if st.button("登入 / Login", type="primary", use_container_width=True):
        if pw == ADMIN_PW:
            st.session_state.pw_error = False
            load_counts(); load_open_slots(); load_students()
            st.session_state.admin_open = [
                f"{o['di']}_{o['si']}" for o in st.session_state.open_slots if isinstance(o, dict)]
            go("admin_dash")
        else:
            st.session_state.pw_error = True; st.rerun()
    st.caption(f"預設密碼 / Default password: `{ADMIN_PW}`")

# ══════════════════════════════════════════════════════
# SCREEN: ADMIN DASHBOARD
# ══════════════════════════════════════════════════════
def screen_admin_dash():
    col_h, col_r = st.columns([4,1])
    with col_h: st.markdown("### 🛡️ " + bi("管理員儀表板","Admin Dashboard"), unsafe_allow_html=True)
    with col_r:
        if st.button("↻", key="admin_refresh", help="Refresh data"):
            load_counts(); load_students(); st.rerun()
    if st.button("← Back", key="back_adash"): go("landing")

    counts = st.session_state.counts
    st.markdown('<div class="phase-bar"><span class="phase-on">Phase 1 老師填寫空堂</span><span>›</span><span class="phase-on">Phase 2 開放學生報名</span></div>', unsafe_allow_html=True)

    tab_slots, tab_teachers, tab_students, tab_cfg = st.tabs([
        "🔓 開放時段管理", "🧑‍🏫 老師空堂總覽", "🎓 學生報名狀況", "⚙️ 設定"
    ])

    # ════════════════════════════
    # TAB 1: 開放時段管理
    # ════════════════════════════
    with tab_slots:
        st.markdown(bi("各時段老師確認人數 · 勾選開放給學生的時段",
                       "Teacher count per slot · Check to publish to students"), unsafe_allow_html=True)

        def slot_section_admin(sess_idx):
            sess = _C["sessions"][sess_idx]
            is_am = sess["region"] == "us"
            cls = "sec-am" if is_am else "sec-pm"
            st.markdown(f'<div class="{cls}">{sess["flag"]} {sess["name_zh"]} · {sess["name_en"]}</div>', unsafe_allow_html=True)
            slots = sess["slots"]
            offset = sum(len(_C["sessions"][i]["slots"]) for i in range(sess_idx))
            hdr = st.columns([1.6] + [1]*len(slots))
            hdr[0].markdown(bi("日期","Date"), unsafe_allow_html=True)
            for i, s in enumerate(slots): hdr[i+1].markdown(f"**{s['tst']}**")
            for di in range(N_D):
                cols = st.columns([1.6] + [1]*len(slots))
                cols[0].markdown(f'<div class="bi"><span class="zh">{DATES_ZH[di]}</span><span class="en">{DATES_EN[di]}</span></div>', unsafe_allow_html=True)
                for i in range(len(slots)):
                    si = offset + i
                    n = counts[di][si] if di < len(counts) and si < len(counts[di]) else 0
                    key = f"{di}_{si}"
                    with cols[i+1]:
                        st.markdown(badge(n), unsafe_allow_html=True)
                        if n >= 3:
                            checked = key in st.session_state.admin_open
                            if st.checkbox("開放", value=checked, key=f"adm_{key}"):
                                if key not in st.session_state.admin_open: st.session_state.admin_open.append(key)
                            else:
                                if key in st.session_state.admin_open: st.session_state.admin_open.remove(key)

        with st.container(border=True):
            for idx in range(len(_C["sessions"])):
                slot_section_admin(idx)
                if idx < len(_C["sessions"])-1: st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

        n_open = len(st.session_state.admin_open)
        if st.button(f"🔓 確認開放 {n_open} 個時段 / Publish {n_open} slot(s)", type="primary", use_container_width=True):
            slots_to_save = [{"di": int(k.split("_")[0]), "si": int(k.split("_")[1])} for k in st.session_state.admin_open]
            db_set("open_slots", slots_to_save)
            st.session_state.open_slots = slots_to_save
            st.success(f"✅ 已開放 {n_open} 個時段！")

    # ════════════════════════════
    # TAB 2: 老師空堂總覽
    # ════════════════════════════
    with tab_teachers:
        st.markdown(bi("所有老師填寫的空堂 · 管理員可新增或刪除",
                       "All teacher availability · Admin can add or delete"), unsafe_allow_html=True)
        teachers_raw = db_get_all("teachers")
        if not teachers_raw:
            st.info("尚無老師填寫空堂。/ No teacher data yet.")
        else:
            import pandas as pd
            for t_name, avail in teachers_raw.items():
                if not isinstance(avail, list): continue
                total = sum(1 for row in avail for v in row if v)
                with st.expander(f"🧑‍🏫 {t_name}  ·  {total} 個時段可用"):
                    rows = []
                    for di in range(min(N_D, len(avail))):
                        for si in range(min(N_S, len(avail[di]))):
                            if avail[di][si]:
                                sess = session_for_si(si)
                                rows.append({"日期 Date": f"{DATES_ZH[di]} {DATES_EN[di]}",
                                             "台灣時間 TST": ALL_SLOTS[si],
                                             "場次": f"{sess['flag']} {sess['name_zh']}",
                                             "當地時間 Local": ALL_LOCAL[si]})
                    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                    else: st.caption("尚未勾選任何時段。/ No slots selected.")
                    _, col_del = st.columns([3,1])
                    with col_del:
                        ck = f"cdel_{t_name}"
                        if st.session_state.get(ck):
                            st.error(f"確定刪除 {t_name}？")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("✅ 確定", key=f"dodel_{t_name}", use_container_width=True):
                                    db_delete(f"teachers/{t_name}"); st.session_state[ck]=False; load_counts(); st.rerun()
                            with c2:
                                if st.button("❌ 取消", key=f"cxdel_{t_name}", use_container_width=True):
                                    st.session_state[ck]=False; st.rerun()
                        else:
                            if st.button("🗑️ 刪除", key=f"del_{t_name}", use_container_width=True):
                                st.session_state[ck]=True; st.rerun()
        st.divider()
        with st.expander("➕ 手動新增老師空堂 / Add teacher manually"):
            new_n = st.text_input("老師姓名 Teacher name", key="new_t_name", placeholder="例：林老師")
            new_avail = [[False]*N_S for _ in range(N_D)]
            for sess_idx, sess in enumerate(_C["sessions"]):
                offset = sum(len(_C["sessions"][i]["slots"]) for i in range(sess_idx))
                st.markdown(f"*{sess['flag']} {sess['name_zh']}*")
                hdr2 = st.columns([1.6]+[1]*len(sess["slots"]))
                hdr2[0].markdown("**日期**")
                for i, s in enumerate(sess["slots"]): hdr2[i+1].markdown(f"**{s['tst']}**")
                for di in range(N_D):
                    cols2 = st.columns([1.6]+[1]*len(sess["slots"]))
                    cols2[0].write(DATES_ZH[di])
                    for i in range(len(sess["slots"])):
                        si = offset+i
                        new_avail[di][si] = cols2[i+1].checkbox("", key=f"nt_{di}_{si}", label_visibility="collapsed")
            if st.button("💾 儲存 / Save", type="primary", use_container_width=True, key="save_new_t"):
                n = new_n.strip()
                if not n: st.error("請輸入姓名")
                else:
                    db_set(f"teachers/{n}", new_avail); load_counts()
                    st.success(f"✅ 已儲存 {n} 的空堂資料！"); st.rerun()

    # ════════════════════════════
    # TAB 3: 學生報名狀況
    # ════════════════════════════
    with tab_students:
        students = st.session_state.students
        st.markdown(bi(f"學生報名狀況（{len(students)} 人）", f"Student registrations ({len(students)} total)"), unsafe_allow_html=True)
        if not students:
            st.caption("尚無學生報名。/ No registrations yet.")
        else:
            import pandas as pd
            rows = []
            for s_key, s in students.items():
                if not isinstance(s, dict): continue
                di, si = s.get("di",0), s.get("si",0)
                sess = session_for_si(si)
                rows.append({"_key": s_key, "姓名/Name": s.get("name",""),
                              "區域/Region": f"{sess['flag']} {sess['name_zh']}",
                              "日期/Date": f"{DATES_ZH[di]}" if di < N_D else "?",
                              "台灣時段 TST": ALL_SLOTS[si] if si < N_S else "?",
                              "當地時間 Local": ALL_LOCAL[si] if si < N_S else "?",
                              "提前上線 Join early": ALL_EARLY[si] if si < N_S else "?"})
            st.dataframe(pd.DataFrame(rows).drop(columns=["_key"]), use_container_width=True, hide_index=True)
            st.divider()
            st.markdown("**刪除學生報名紀錄 / Delete registration**")
            names = [r["_key"] for r in rows]
            del_n = st.selectbox("選擇學生 Select student", ["— 請選擇 —"] + names)
            if del_n and del_n != "— 請選擇 —":
                cks = "cdelstu"
                if st.session_state.get(cks) == del_n:
                    st.error(f"確定刪除 {del_n}？")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ 確定刪除", key="dodel_stu", use_container_width=True):
                            db_delete(f"students/{del_n}"); st.session_state[cks]=None; load_students(); st.rerun()
                    with c2:
                        if st.button("❌ 取消", key="cxdel_stu", use_container_width=True):
                            st.session_state[cks]=None; st.rerun()
                else:
                    if st.button(f"🗑️ 刪除 {del_n}", use_container_width=True):
                        st.session_state[cks]=del_n; st.rerun()
        if st.button("↻ Refresh / 重新整理", key="ref_stu"): load_students(); st.rerun()

    # ════════════════════════════
    # TAB 4: ⚙️ 設定 (NEW)
    # ════════════════════════════
    with tab_cfg:
        st.markdown(bi("系統設定 — 調整考試日期、場次、時區標籤",
                       "System config — edit dates, sessions, timezone labels"), unsafe_allow_html=True)
        st.caption("修改後按「儲存設定」即生效，老師端和學生端下次載入時自動套用。Changes apply on next page load.")

        # Init or reset draft
        col_info, col_rst = st.columns([4,1])
        with col_rst:
            if st.button("↺ 重置草稿", key="reset_draft", help="Discard edits and reload from Firebase"):
                st.session_state.pop("cfg_draft", None); st.rerun()

        if "cfg_draft" not in st.session_state:
            st.session_state.cfg_draft = copy.deepcopy(st.session_state.app_config)

        draft = st.session_state.cfg_draft

        # ── Section A: 考試日期 ──────────────────────────
        st.markdown("#### 📅 考試日期 Exam Dates")
        st.caption("EN label: shown to students / ZH label: shown to teachers / ISO: used for calendar (.ics)")

        remove_di = None
        hdr_cols = st.columns([2.2, 2.2, 2.2, 0.4])
        for h, t in zip(hdr_cols, ["EN label (e.g. 5/26 Mon)", "ZH label (e.g. 5/26 一)", "ISO date (YYYY-MM-DD)", ""]):
            h.markdown(f"<div style='font-size:.78rem;color:#888'>{t}</div>", unsafe_allow_html=True)

        for i, d in enumerate(draft["dates"]):
            c1, c2, c3, c4 = st.columns([2.2, 2.2, 2.2, 0.4])
            with c1: d["en"]  = st.text_input("en",  value=d.get("en",""),  key=f"de_{i}", label_visibility="collapsed")
            with c2: d["zh"]  = st.text_input("zh",  value=d.get("zh",""),  key=f"dz_{i}", label_visibility="collapsed")
            with c3: d["iso"] = st.text_input("iso", value=d.get("iso",""), key=f"di_{i}", label_visibility="collapsed")
            with c4:
                if len(draft["dates"]) > 1 and st.button("✕", key=f"rmd_{i}", help="Remove this date"):
                    remove_di = i

        if remove_di is not None:
            draft["dates"].pop(remove_di); st.rerun()

        if st.button("＋ 新增日期 Add date", key="add_date"):
            draft["dates"].append({"en":"New Date (Day)","zh":"日期","iso":"2025-01-01"})
            st.rerun()

        st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

        # ── Section B: 場次設定 ──────────────────────────
        st.markdown("#### 🕐 場次與時區 Sessions & Timezone Labels")

        for si_s, sess in enumerate(draft["sessions"]):
            is_am = sess.get("region","eu") == "us"
            exp_title = f"{sess.get('flag','🌐')} {sess.get('name_zh','')} / {sess.get('name_en','')}  ·  {len(sess['slots'])} 個時段"
            with st.expander(exp_title, expanded=True):
                # Session metadata row
                c1, c2, c3, c4 = st.columns([0.8, 2, 2, 2])
                with c1: sess["flag"]    = st.text_input("旗幟", value=sess.get("flag","🌐"), key=f"sf_{si_s}")
                with c2: sess["name_zh"] = st.text_input("中文名稱", value=sess.get("name_zh",""), key=f"snz_{si_s}")
                with c3: sess["name_en"] = st.text_input("English name", value=sess.get("name_en",""), key=f"sne_{si_s}")
                with c4:
                    opts = ["us","eu","other"]
                    cur = sess.get("region","eu")
                    idx_r = opts.index(cur) if cur in opts else 1
                    sess["region"] = st.selectbox("區域代碼 Region code", options=opts, index=idx_r, key=f"sr_{si_s}",
                                                   help="us = Americas, eu = Europe")

                st.markdown("**時段列表 Slots:**")
                hdr2 = st.columns([1.5, 2.5, 2.5, 0.4])
                for h2, t2 in zip(hdr2, ["台灣時間 TST","當地時間 Local time","提前上線 Early (20 min)",""]): 
                    h2.markdown(f"<div style='font-size:.78rem;color:#888'>{t2}</div>", unsafe_allow_html=True)

                remove_slot = None
                for j, slot in enumerate(sess["slots"]):
                    sc1, sc2, sc3, sc4 = st.columns([1.5, 2.5, 2.5, 0.4])
                    with sc1: slot["tst"]   = st.text_input("tst",   value=slot.get("tst",""),   key=f"st_{si_s}_{j}", label_visibility="collapsed")
                    with sc2: slot["local"] = st.text_input("local", value=slot.get("local",""), key=f"sl_{si_s}_{j}", label_visibility="collapsed")
                    with sc3: slot["early"] = st.text_input("early", value=slot.get("early",""), key=f"se_{si_s}_{j}", label_visibility="collapsed")
                    with sc4:
                        if len(sess["slots"]) > 1 and st.button("✕", key=f"rms_{si_s}_{j}", help="Remove slot"):
                            remove_slot = j

                if remove_slot is not None:
                    sess["slots"].pop(remove_slot); st.rerun()

                if st.button(f"＋ 新增時段 Add slot", key=f"adds_{si_s}"):
                    sess["slots"].append({"tst":"12:00","local":"Local time","early":"11:40 local"})
                    st.rerun()

        # ── Save / Reset to defaults ─────────────────────
        st.divider()
        c_save, c_def = st.columns(2)
        with c_save:
            if st.button("💾 儲存設定 Save config", type="primary", use_container_width=True, key="save_cfg"):
                save_config(draft)
                st.session_state.pop("cfg_draft", None)
                st.session_state.pop("app_config", None)  # force reload on next run
                st.success("✅ 設定已儲存！頁面將重新載入套用新設定。")
                st.rerun()
        with c_def:
            ck_def = "confirm_reset_default"
            if st.session_state.get(ck_def):
                st.warning("確定還原預設值？目前設定將被覆蓋。")
                cr1, cr2 = st.columns(2)
                with cr1:
                    if st.button("✅ 確定還原", use_container_width=True, key="do_reset_def"):
                        save_config(copy.deepcopy(DEFAULT_CONFIG))
                        st.session_state.pop("cfg_draft", None)
                        st.session_state.pop("app_config", None)
                        st.session_state[ck_def] = False; st.rerun()
                with cr2:
                    if st.button("❌ 取消", use_container_width=True, key="cx_reset_def"):
                        st.session_state[ck_def] = False; st.rerun()
            else:
                if st.button("↺ 還原預設值 Restore defaults", use_container_width=True, key="reset_def"):
                    st.session_state[ck_def] = True; st.rerun()

        st.markdown("""
        <div style="background:#f7f6f3;border-radius:8px;padding:10px 14px;font-size:.8rem;color:#888;margin-top:.75rem">
        ⚠️ 修改場次數量或時段數量後，老師端的現有勾選資料可能需要重新填寫。<br>
        Changing the number of sessions or slots may require teachers to re-fill their availability.
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# SCREENS: STUDENT (kept for this portal)
# ══════════════════════════════════════════════════════
def screen_student_id():
    if st.button("← Back / 返回", key="back_sid"): go("landing")
    st.markdown("### 🎓 Oral Exam Registration")
    name = st.text_input("Your full name / 姓名", value=st.session_state.user_name, placeholder="e.g. Maria Schmidt")
    region = st.radio("Your location / 所在地區",
        options=[s["region"] for s in _C["sessions"]],
        format_func=lambda r: next((f"{s['flag']} {s['name_en']} / {s['name_zh']}" for s in _C["sessions"] if s["region"]==r), r),
        index=0, horizontal=True)
    if st.button("查看可報名時段 / View available slots →", type="primary", use_container_width=True):
        name = name.strip()
        if not name: st.error("Please enter your name / 請輸入姓名"); return
        st.session_state.user_name = name
        st.session_state.region = region
        load_open_slots()
        b = db_get(f"students/{name}")
        st.session_state.my_booking = b if isinstance(b, dict) else None
        go("student_slots")

def screen_student_slots():
    name = st.session_state.user_name
    region = st.session_state.region
    col_h, col_b = st.columns([4,1])
    with col_h:
        st.markdown(f"### 🎓 {name}")
        sess_info = next((s for s in _C["sessions"] if s["region"]==region), _C["sessions"][0])
        st.caption(f"{sess_info['flag']} {sess_info['name_en']} session")
    with col_b:
        if st.button("← Back", key="back_ssl"): go("landing")

    booking = st.session_state.my_booking
    if booking and isinstance(booking, dict):
        di, si = booking.get("di",0), booking.get("si",0)
        sess_b = session_for_si(si)
        st.markdown(
            f'<div class="book-card">'
            f'<div style="font-weight:600;color:#085041;margin-bottom:4px">✅ Registered · 已成功報名</div>'
            f'<div style="font-size:1rem;font-weight:500">{DATES_EN[di] if di<N_D else "?"} · {ALL_SLOTS[si] if si<N_S else "?"} TST</div>'
            f'<div style="font-size:.88rem;margin-top:4px">Your local time: <strong>{ALL_LOCAL[si] if si<N_S else "?"}</strong></div>'
            f'<div style="font-size:.82rem;color:#0f6e56;margin-top:3px">Join 20 min early at / 請於 <strong>{ALL_EARLY[si] if si<N_S else "?"}</strong> 上線</div>'
            f'</div>', unsafe_allow_html=True)

    open_slots = st.session_state.open_slots
    relevant = [o for o in open_slots if isinstance(o, dict) and SLOT_REG[o["si"]]==region]
    if not relevant:
        st.warning("No slots available yet. 目前尚無開放時段。"); return

    for o in relevant:
        di, si = o["di"], o["si"]
        is_sel = booking and isinstance(booking,dict) and booking.get("di")==di and booking.get("si")==si
        sess_o = session_for_si(si)
        sel_cls = ("slot-sel-am" if sess_o["region"]=="us" else "slot-sel-pm") if is_sel else ""
        tag_cls = "tag-am" if sess_o["region"]=="us" else "tag-pm"
        st.markdown(
            f'<div class="slot-opt {sel_cls}"><div style="display:flex;justify-content:space-between">'
            f'<div><div style="font-weight:500">{DATES_EN[di]} · {ALL_SLOTS[si]} TST</div>'
            f'<div style="font-size:.85rem;color:#666">🕐 {ALL_LOCAL[si]}</div>'
            f'<div style="font-size:.78rem;color:#aaa">20 min early: {ALL_EARLY[si]}</div></div>'
            f'<span class="tag {tag_cls}">{"✓ " if is_sel else ""}{sess_o["name_en"]}</span>'
            f'</div></div>', unsafe_allow_html=True)
        if st.button(f"{'✓ Selected — ' if is_sel else 'Register — '}{DATES_EN[di]} {ALL_SLOTS[si]}",
                     key=f"slot_{di}_{si}", use_container_width=True):
            if not is_sel:
                b = {"name":name,"region":region,"di":di,"si":si}
                db_set(f"students/{name}", b)
                st.session_state.my_booking = b
                st.success("✅ Registered! 報名成功！"); st.rerun()

# ══════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════
ROUTES = {
    "landing":       screen_landing,
    "teacher_id":    screen_teacher_id,
    "teacher_grid":  screen_teacher_grid,
    "admin_id":      screen_admin_id,
    "admin_dash":    screen_admin_dash,
    "student_id":    screen_student_id,
    "student_slots": screen_student_slots,
}
ROUTES.get(st.session_state.screen, screen_landing)()
