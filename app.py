"""
CLC Oral Exam Registration System v4
+ Google Meet links per date/session
+ Slot capacity limits
+ Registration open/close + deadline
+ Analytics dashboard
+ CSV export + bulk email
+ Teacher confirmed schedule + quick-select
"""

import streamlit as st
import json, os, copy
from datetime import datetime

st.set_page_config(page_title="CLC Oral Exam 口試報名", page_icon="🎓",
                   layout="centered", initial_sidebar_state="collapsed")

ADMIN_PW = st.secrets.get("admin_password", "CLC2026")

# ══════════════════════════════════════════════════════
# DEFAULT CONFIG
# ══════════════════════════════════════════════════════
DEFAULT_CONFIG = {
    "dates": [
        {"en":"5/26 (Mon)","zh":"5/26 (一)","iso":"2026-05-26"},
        {"en":"5/27 (Tue)","zh":"5/27 (二)","iso":"2026-05-27"},
        {"en":"5/28 (Wed)","zh":"5/28 (三)","iso":"2026-05-28"},
        {"en":"5/29 (Thu)","zh":"5/29 (四)","iso":"2026-05-29"},
    ],
    "sessions": [
        {"region":"us","flag":"🌎","name_zh":"美洲場","name_en":"Americas",
         "slots":[
             {"tst":"08:00","local":"Prev. night EDT 20:00","early":"Prev. night EDT 19:40"},
             {"tst":"09:00","local":"EDT 21:00","early":"EDT 20:40"},
             {"tst":"10:00","local":"EDT 22:00","early":"EDT 21:40"},
             {"tst":"11:00","local":"EDT 23:00","early":"EDT 22:40"},
         ]},
        {"region":"eu","flag":"🇪🇺","name_zh":"歐洲場","name_en":"Europe",
         "slots":[
             {"tst":"14:00","local":"CET 07:00","early":"CET 06:40"},
             {"tst":"15:00","local":"CET 08:00","early":"CET 07:40"},
             {"tst":"16:00","local":"CET 09:00","early":"CET 08:40"},
             {"tst":"17:00","local":"CET 10:00","early":"CET 09:40"},
         ]},
    ],
    "settings": {
        "registration_open": True,
        "deadline": "",
        "max_per_slot": 1,
        "meet_links": {},   # key: "2026-05-26_eu" → URL
    },
}

# ══════════════════════════════════════════════════════
# TIMEZONE AUTO-CALC
# ══════════════════════════════════════════════════════
TIMEZONE_OPTIONS = {
    "CET  (UTC+1) — 歐洲中部":     {"abbr":"CET",   "offset":1},
    "CEST (UTC+2) — 歐洲中部夏令":  {"abbr":"CEST",  "offset":2},
    "EET  (UTC+2) — 東歐":         {"abbr":"EET",   "offset":2},
    "EEST (UTC+3) — 東歐夏令":     {"abbr":"EEST",  "offset":3},
    "MSK  (UTC+3) — 莫斯科":       {"abbr":"MSK",   "offset":3},
    "GST  (UTC+4) — 波斯灣":       {"abbr":"GST",   "offset":4},
    "IST  (UTC+5:30) — 印度":      {"abbr":"IST",   "offset":5.5},
    "WIB  (UTC+7) — 雅加達":       {"abbr":"WIB",   "offset":7},
    "JST  (UTC+9) — 日本/韓國":    {"abbr":"JST",   "offset":9},
    "AEST (UTC+10) — 澳洲東部":    {"abbr":"AEST",  "offset":10},
    "EDT  (UTC-4) — 美東夏令":      {"abbr":"EDT",   "offset":-4},
    "CDT  (UTC-5) — 美中夏令":      {"abbr":"CDT",   "offset":-5},
    "MDT  (UTC-6) — 美山夏令":      {"abbr":"MDT",   "offset":-6},
    "PDT  (UTC-7) — 美西夏令":      {"abbr":"PDT",   "offset":-7},
    "BRT  (UTC-3) — 巴西":         {"abbr":"BRT",   "offset":-3},
}

def calc_local_early(tst_str, tz_abbr, tz_offset):
    try: h, m = map(int, tst_str.strip().split(":"))
    except: return tst_str, tst_str
    tst_min = h*60+m; utc_min = tst_min-480; local_min = utc_min+int(tz_offset*60); early_min = local_min-20
    def fmt(t):
        prev = t < 0; nxt = t >= 1440; m2 = t % 1440; hh, mm = divmod(m2, 60)
        return f"{'Prev. night ' if prev else 'Next day ' if nxt else ''}{tz_abbr} {hh:02d}:{mm:02d}"
    return fmt(local_min), fmt(early_min)

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
.bi{display:flex;flex-direction:column;line-height:1.35}
.bi .zh{font-size:.92rem;color:#1a1a18}
.bi .en{font-size:.75rem;color:#888;margin-top:1px}
.cnt-ok{background:#eaf3de;color:#27500a;padding:2px 9px;border-radius:5px;font-weight:600;font-size:.82rem}
.cnt-warn{background:#faeeda;color:#633806;padding:2px 9px;border-radius:5px;font-weight:600;font-size:.82rem}
.cnt-bad{background:#fcebeb;color:#a32d2d;padding:2px 9px;border-radius:5px;font-weight:600;font-size:.82rem}
.cnt-zero{background:#f1efe8;color:#aaa;padding:2px 9px;border-radius:5px;font-size:.82rem}
.sec-am{background:#faeeda;color:#633806;padding:7px 14px;border-radius:8px 8px 0 0;font-weight:500;font-size:.88rem}
.sec-pm{background:#e6f1fb;color:#0c447c;padding:7px 14px;border-radius:8px 8px 0 0;font-weight:500;font-size:.88rem}
.phase-bar{background:#f7f6f3;border:1px solid #e8e7e2;border-radius:8px;padding:8px 14px;font-size:.82rem;color:#666;display:flex;align-items:center;gap:10px;margin-bottom:1.2rem}
.phase-on{background:#e6f1fb;color:#0c447c;padding:4px 10px;border-radius:5px;font-weight:500}
.meet-card{background:#e8f5e9;border:1.5px solid #81c784;border-radius:10px;padding:1rem 1.2rem;margin-bottom:.75rem}
.stat-card{background:var(--background-color);border:1px solid rgba(0,0,0,.1);border-radius:10px;padding:.875rem 1rem;text-align:center}
.stat-val{font-size:1.75rem;font-weight:700;color:#185fa5}
.stat-lbl{font-size:.75rem;color:#888;margin-top:2px}
[data-testid="stSidebar"]{display:none}
.stButton button{border-radius:8px!important}
footer{display:none!important}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# FIREBASE
# ══════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def init_firebase():
    try:
        import firebase_admin
        from firebase_admin import credentials, db
        if not firebase_admin._apps:
            cred_dict = dict(st.secrets["firebase_credentials"])
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n","\n")
            firebase_admin.initialize_app(credentials.Certificate(cred_dict),
                                           {"databaseURL": st.secrets["firebase_url"]})
        return db, True
    except: return None, False

_fb, FIREBASE_OK = init_firebase()
_LP = "/tmp/clc_local_db.json"

def _ll():
    if os.path.exists(_LP):
        with open(_LP) as f: return json.load(f)
    return {}
def _ls(d):
    with open(_LP,"w") as f: json.dump(d,f)

def db_get(path):
    if FIREBASE_OK: return _fb.reference(path).get()
    data=_ll()
    for k in path.strip("/").split("/"):
        data=data.get(k) if isinstance(data,dict) else None
        if data is None: return None
    return data

def db_set(path,value):
    if FIREBASE_OK: _fb.reference(path).set(value)
    else:
        data=_ll(); keys=path.strip("/").split("/"); d=data
        for k in keys[:-1]: d=d.setdefault(k,{})
        d[keys[-1]]=value; _ls(data)

def db_get_all(path):
    if FIREBASE_OK: return _fb.reference(path).get() or {}
    data=_ll()
    for k in path.strip("/").split("/"):
        data=data.get(k) if isinstance(data,dict) else None
        if data is None: return {}
    return data if isinstance(data,dict) else {}

def db_delete(path):
    if FIREBASE_OK: _fb.reference(path).delete()
    else:
        data=_ll(); keys=path.strip("/").split("/"); d=data
        for k in keys[:-1]:
            if isinstance(d,dict) and k in d: d=d[k]
            else: return
        if isinstance(d,dict) and keys[-1] in d: del d[keys[-1]]
        _ls(data)

# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════
def _fix(obj):
    if isinstance(obj,dict):
        if obj and all(k.isdigit() for k in obj.keys()):
            return [_fix(obj[str(i)]) for i in range(len(obj))]
        return {k:_fix(v) for k,v in obj.items()}
    return obj

def load_config():
    raw=db_get("config")
    if isinstance(raw,dict) and "sessions" in raw and "dates" in raw:
        cfg=_fix(raw)
        if "settings" not in cfg: cfg["settings"]=copy.deepcopy(DEFAULT_CONFIG["settings"])
        return cfg
    return copy.deepcopy(DEFAULT_CONFIG)

def save_config(cfg):
    db_set("config",cfg); st.session_state.app_config=cfg

def derive(cfg):
    dates_en=[d["en"] for d in cfg["dates"]]
    dates_zh=[d["zh"] for d in cfg["dates"]]
    dates_iso=[d.get("iso","2026-01-01") for d in cfg["dates"]]
    slots,local,early,reg=[],[],[],[]
    for sess in cfg["sessions"]:
        for s in sess["slots"]:
            slots.append(s["tst"]); local.append(s["local"])
            early.append(s["early"]); reg.append(sess["region"])
    return dates_en,dates_zh,dates_iso,slots,local,early,reg,len(dates_en),len(slots)

if "app_config" not in st.session_state:
    st.session_state.app_config=load_config()

_C=st.session_state.app_config
DATES_EN,DATES_ZH,DATES_ISO,ALL_SLOTS,ALL_LOCAL,ALL_EARLY,SLOT_REG,N_D,N_S=derive(_C)

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════
for k,v in {"screen":"landing","user_name":"","region":"eu","my_booking":None,"open_slots":[],
            "counts":[[0]*N_S for _ in range(N_D)],"students":{},"admin_open":[],"avail_loaded":False,"pw_error":False}.items():
    if k not in st.session_state: st.session_state[k]=v

def go(s): st.session_state.screen=s; st.rerun()
def badge(n):
    cls="cnt-ok" if n>=3 else "cnt-warn" if n==2 else "cnt-bad" if n==1 else "cnt-zero"
    return f'<span class="{cls}">{n}</span>'
def bi(zh,en): return f'<div class="bi"><span class="zh">{zh}</span><span class="en">{en}</span></div>'

def get_settings(): return _C.get("settings", DEFAULT_CONFIG["settings"])
def get_meet_link(di, region):
    iso=DATES_ISO[di] if di<len(DATES_ISO) else ""
    return get_settings().get("meet_links",{}).get(f"{iso}_{region}","")

def load_counts():
    teachers=db_get_all("teachers")
    counts=[[0]*N_S for _ in range(N_D)]
    for avail in teachers.values():
        if isinstance(avail,list):
            for di,row in enumerate(avail):
                for si,v in enumerate(row):
                    if v and di<N_D and si<N_S: counts[di][si]+=1
    st.session_state.counts=counts

def load_open_slots():
    slots=db_get("open_slots") or []
    st.session_state.open_slots=slots if isinstance(slots,list) else []

def load_students():
    st.session_state.students=db_get_all("students")

def get_slot_counts():
    """Count students booked per di_si key."""
    out={}
    for s in st.session_state.students.values():
        if isinstance(s,dict):
            k=f"{s.get('di',0)}_{s.get('si',0)}"
            out[k]=out.get(k,0)+1
    return out

def session_for_si(si):
    idx=0
    for sess in _C["sessions"]:
        for _ in sess["slots"]:
            if idx==si: return sess
            idx+=1
    return _C["sessions"][0]

# ══════════════════════════════════════════════════════
# SCREEN: LANDING
# ══════════════════════════════════════════════════════
def screen_landing():
    st.markdown("### 🎓 CLC Oral Exam Registration")
    st.caption("Chinese Language Center · NCKU")
    if not FIREBASE_OK:
        st.warning("⚠️ Demo mode — Firebase not configured.")
    st.divider()
    c1,c2,c3=st.columns(3)
    with c1:
        st.markdown("**🧑‍🏫**"); st.markdown(bi("老師","Teacher"),unsafe_allow_html=True)
        st.caption("填寫可用空堂時段\nFill in availability")
        if st.button("進入 / Enter →",key="go_t",use_container_width=True): go("teacher_id")
    with c2:
        st.markdown("**🎓**"); st.markdown(bi("學生","Student"),unsafe_allow_html=True)
        st.caption("查看並報名口試時段\nView & register slots")
        if st.button("進入 / Enter →",key="go_s",use_container_width=True): go("student_id")
    with c3:
        st.markdown("**🛡️**"); st.markdown(bi("管理員","Admin"),unsafe_allow_html=True)
        st.caption("確認時段並開放報名\nPublish slots")
        if st.button("進入 / Enter →",key="go_a",use_container_width=True): go("admin_id")
    st.divider()
    st.markdown('<div style="font-size:.8rem;color:#888">🔒 每位使用者僅能讀寫自己的資料。</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# SCREEN: TEACHER ID
# ══════════════════════════════════════════════════════
def screen_teacher_id():
    if st.button("← Back",key="back_tid"): go("landing")
    st.markdown("### 🧑‍🏫 "+bi("老師空堂填寫","Teacher Availability"),unsafe_allow_html=True)
    name=st.text_input(bi("姓名（作為識別）","Name — your unique ID"),value=st.session_state.user_name,placeholder="e.g. 陳老師",key="inp_tn")
    if st.button("開始填寫 →",type="primary",use_container_width=True):
        name=name.strip()
        if not name: st.error("請輸入姓名"); return
        st.session_state.user_name=name; st.session_state.avail_loaded=False; go("teacher_grid")

# ══════════════════════════════════════════════════════
# SCREEN: TEACHER GRID
# ══════════════════════════════════════════════════════
def screen_teacher_grid():
    name=st.session_state.user_name
    if not st.session_state.avail_loaded:
        load_counts()
        saved=db_get(f"teachers/{name}")
        for di in range(N_D):
            for si in range(N_S):
                k=f"avail_{di}_{si}"
                try: st.session_state[k]=bool(saved[di][si]) if isinstance(saved,list) else False
                except: st.session_state[k]=False
        st.session_state.avail_loaded=True

    col_h,col_btn=st.columns([3,1])
    with col_h:
        st.markdown(f"### 🧑‍🏫 {name}")
        st.caption("勾選您可用的時段 · Check your available slots")
    with col_btn:
        if st.button("← Back",key="back_tg"): st.session_state.avail_loaded=False; go("landing")

    counts=st.session_state.counts
    st.markdown('<div style="font-size:.8rem;color:#666;margin-bottom:.5rem">數字 = 目前確認老師數 · 綠≥3 · 橘=2 · 紅=1</div>',unsafe_allow_html=True)

    def render_section(sess_idx):
        sess=_C["sessions"][sess_idx]; is_am=sess["region"]=="us"
        cls="sec-am" if is_am else "sec-pm"
        offset=sum(len(_C["sessions"][i]["slots"]) for i in range(sess_idx))
        slots=sess["slots"]
        st.markdown(f'<div class="{cls}">{sess["flag"]} {sess["name_zh"]} {sess["name_en"]}</div>',unsafe_allow_html=True)

        # Quick-select row
        qcols=st.columns(N_D+1)
        qcols[0].markdown('<div style="font-size:.72rem;color:#888;padding-top:6px">快選</div>',unsafe_allow_html=True)
        for di in range(N_D):
            if qcols[di+1].button(f"全選\n{DATES_ZH[di][:4]}",key=f"qsel_{sess_idx}_{di}",use_container_width=True):
                for i in range(len(slots)):
                    st.session_state[f"avail_{di}_{offset+i}"]=True
                st.rerun()

        hdr=st.columns([1.8]+[1]*len(slots))
        hdr[0].markdown('<div class="bi"><span class="zh">日期</span><span class="en">Date</span></div>',unsafe_allow_html=True)
        for i,s in enumerate(slots):
            hdr[i+1].markdown(f'<div style="font-size:1rem;font-weight:700">{s["tst"]}</div><div style="font-size:.7rem;color:#aaa;margin-top:2px">{s["local"]}</div>',unsafe_allow_html=True)
        st.markdown('<hr style="margin:4px 0 8px;border-color:#eee">',unsafe_allow_html=True)
        for di in range(N_D):
            cols=st.columns([1.8]+[1]*len(slots))
            cols[0].markdown(f'<div class="bi"><span class="zh">{DATES_ZH[di]}</span><span class="en">{DATES_EN[di]}</span></div>',unsafe_allow_html=True)
            for i in range(len(slots)):
                si=offset+i; n=counts[di][si] if di<len(counts) and si<len(counts[di]) else 0
                with cols[i+1]:
                    st.checkbox("",key=f"avail_{di}_{si}",label_visibility="collapsed")
                    st.markdown(badge(n),unsafe_allow_html=True)

    with st.container(border=True):
        for idx in range(len(_C["sessions"])):
            render_section(idx)
            if idx<len(_C["sessions"])-1: st.markdown('<div style="height:.5rem"></div>',unsafe_allow_html=True)

    if st.button("💾 儲存我的空堂 / Save",type="primary",use_container_width=True):
        avail=[[bool(st.session_state.get(f"avail_{di}_{si}",False)) for si in range(N_S)] for di in range(N_D)]
        db_set(f"teachers/{name}",avail); load_counts()
        st.success("✅ 儲存成功！/ Saved!")
        st.rerun()

    # ── Confirmed sessions for this teacher ──────────────
    st.divider()
    st.markdown("#### 📋 您已確認的場次 / Your confirmed sessions")
    st.caption("以下為您勾選且師資已達3位的時段（已儲存資料為準）")
    saved=db_get(f"teachers/{name}")
    if not isinstance(saved,list):
        st.info("尚未儲存任何資料。填寫後請先按「儲存」。")
    else:
        confirmed=[]
        for di in range(N_D):
            for si in range(N_S):
                try: my_ok=bool(saved[di][si])
                except: my_ok=False
                n=counts[di][si] if di<len(counts) and si<len(counts[di]) else 0
                if my_ok and n>=3:
                    sess=session_for_si(si)
                    meet=get_meet_link(di,sess["region"])
                    confirmed.append((di,si,sess,meet))
        if not confirmed:
            st.info("目前尚無達標的確認場次（需≥3位老師，且您已勾選並儲存）。")
        else:
            for di,si,sess,meet in confirmed:
                with st.container(border=True):
                    c1,c2=st.columns([3,1])
                    with c1:
                        st.markdown(f"**{sess['flag']} {DATES_ZH[di]} · {ALL_SLOTS[si]} TST**")
                        st.caption(f"{sess['name_zh']} / {sess['name_en']} · {ALL_LOCAL[si]}")
                    with c2:
                        if meet:
                            st.markdown(f'<a href="{meet}" target="_blank" style="display:inline-flex;align-items:center;justify-content:center;gap:4px;background:#e8f5e9;color:#1b5e20;border:1px solid #81c784;border-radius:8px;padding:7px 12px;text-decoration:none;font-size:.82rem;font-weight:500;width:100%">🎥 Join Meet</a>',unsafe_allow_html=True)
                        else:
                            st.caption("Meet 連結待管理員設定")

# ══════════════════════════════════════════════════════
# SCREEN: ADMIN ID
# ══════════════════════════════════════════════════════
def screen_admin_id():
    if st.button("← Back",key="back_aid"): go("landing")
    st.markdown("### 🛡️ "+bi("管理員登入","Admin Login"),unsafe_allow_html=True)
    pw=st.text_input(bi("管理密碼","Password"),type="password",placeholder="Enter password")
    if st.session_state.pw_error: st.error("❌ 密碼錯誤 / Incorrect password")
    if st.button("登入 / Login",type="primary",use_container_width=True):
        if pw==ADMIN_PW:
            st.session_state.pw_error=False
            load_counts(); load_open_slots(); load_students()
            st.session_state.admin_open=[f"{o['di']}_{o['si']}" for o in st.session_state.open_slots if isinstance(o,dict)]
            go("admin_dash")
        else: st.session_state.pw_error=True; st.rerun()
    st.caption(f"預設密碼：`{ADMIN_PW}`")

# ══════════════════════════════════════════════════════
# SCREEN: ADMIN DASHBOARD
# ══════════════════════════════════════════════════════
def screen_admin_dash():
    col_h,col_r=st.columns([4,1])
    with col_h: st.markdown("### 🛡️ "+bi("管理員儀表板","Admin Dashboard"),unsafe_allow_html=True)
    with col_r:
        if st.button("↻",key="adm_ref",help="Refresh"): load_counts(); load_students(); st.rerun()
    if st.button("← Back",key="back_ad"): go("landing")

    counts=st.session_state.counts
    settings=get_settings()
    slot_counts=get_slot_counts()

    st.markdown('<div class="phase-bar"><span class="phase-on">Phase 1 老師填寫空堂</span><span>›</span><span class="phase-on">Phase 2 開放學生報名</span></div>',unsafe_allow_html=True)

    # Registration status banner
    if not settings.get("registration_open",True):
        st.error("🔒 報名目前**關閉**中 / Registration is currently **CLOSED**")
    else:
        deadline=settings.get("deadline","")
        if deadline:
            try:
                dl=datetime.strptime(deadline,"%Y-%m-%d %H:%M")
                now=datetime.now()
                if now>dl: st.warning(f"⏰ 報名截止時間 {deadline} 已過期")
                else:
                    diff=dl-now; hrs=int(diff.total_seconds()//3600)
                    st.info(f"🟢 報名開放中 · 截止：{deadline}（剩約 {hrs} 小時）")
            except: st.success("🟢 報名開放中")
        else: st.success("🟢 報名開放中 / Registration OPEN")

    tab_ov,tab_slots,tab_teachers,tab_students,tab_cfg=st.tabs([
        "📊 總覽","🔓 開放時段","🧑‍🏫 老師空堂","🎓 學生報名","⚙️ 設定"
    ])

    # ══════════════════════════════════════
    # TAB 1: 📊 總覽 Analytics
    # ══════════════════════════════════════
    with tab_ov:
        students=st.session_state.students
        total_stu=len(students)
        # Count slots covered (≥3 teachers)
        covered=sum(1 for di in range(N_D) for si in range(N_S) if (di<len(counts) and si<len(counts[di]) and counts[di][si]>=3))
        total_slots=N_D*N_S
        open_count=len(st.session_state.open_slots)

        c1,c2,c3,c4=st.columns(4)
        for col,val,lbl in [
            (c1,total_stu,"學生報名數\nRegistered"),
            (c2,open_count,"開放時段數\nOpen slots"),
            (c3,covered,f"師資達標時段\n≥3 teachers"),
            (c4,len(db_get_all("teachers")),f"老師已填寫\nTeachers filled"),
        ]:
            with col:
                st.markdown(f'<div class="stat-card"><div class="stat-val">{val}</div><div class="stat-lbl">{lbl}</div></div>',unsafe_allow_html=True)

        st.markdown('<div style="height:.75rem"></div>',unsafe_allow_html=True)

        if students:
            import pandas as pd
            # By session
            session_counts={}
            for s in students.values():
                if isinstance(s,dict):
                    sess=session_for_si(s.get("si",0))
                    k=f"{sess['flag']} {sess['name_zh']}"
                    session_counts[k]=session_counts.get(k,0)+1
            if session_counts:
                st.markdown("**報名人數 by 場次**")
                df_sess=pd.DataFrame(list(session_counts.items()),columns=["場次","人數"])
                st.bar_chart(df_sess.set_index("場次"))

            # By date
            date_counts={}
            for s in students.values():
                if isinstance(s,dict):
                    di=s.get("di",0)
                    k=DATES_ZH[di] if di<N_D else "?"
                    date_counts[k]=date_counts.get(k,0)+1
            if date_counts:
                st.markdown("**報名人數 by 日期**")
                ordered={d:date_counts.get(d,0) for d in DATES_ZH}
                df_date=pd.DataFrame(list(ordered.items()),columns=["日期","人數"])
                st.bar_chart(df_date.set_index("日期"))
        else:
            st.info("尚無學生報名資料可分析。")

    # ══════════════════════════════════════
    # TAB 2: 開放時段管理
    # ══════════════════════════════════════
    with tab_slots:
        max_per=settings.get("max_per_slot",1)
        st.markdown(bi("各時段老師確認人數 · 勾選開放給學生","Teacher count per slot · Check to publish"),unsafe_allow_html=True)
        st.caption(f"每時段名額上限：{max_per} 人（可在「⚙️ 設定」修改）")

        def slot_section_admin(sess_idx):
            sess=_C["sessions"][sess_idx]; is_am=sess["region"]=="us"
            cls="sec-am" if is_am else "sec-pm"
            offset=sum(len(_C["sessions"][i]["slots"]) for i in range(sess_idx))
            slots=sess["slots"]
            st.markdown(f'<div class="{cls}">{sess["flag"]} {sess["name_zh"]} · {sess["name_en"]}</div>',unsafe_allow_html=True)
            hdr=st.columns([1.6]+[1]*len(slots))
            hdr[0].markdown(bi("日期","Date"),unsafe_allow_html=True)
            for i,s in enumerate(slots): hdr[i+1].markdown(f"**{s['tst']}**")
            for di in range(N_D):
                cols=st.columns([1.6]+[1]*len(slots))
                cols[0].markdown(f'<div class="bi"><span class="zh">{DATES_ZH[di]}</span><span class="en">{DATES_EN[di]}</span></div>',unsafe_allow_html=True)
                for i in range(len(slots)):
                    si=offset+i; n=counts[di][si] if di<len(counts) and si<len(counts[di]) else 0
                    key=f"{di}_{si}"; booked=slot_counts.get(key,0)
                    with cols[i+1]:
                        st.markdown(badge(n),unsafe_allow_html=True)
                        if booked>0: st.markdown(f'<span style="font-size:.72rem;color:#185fa5">{booked}人報</span>',unsafe_allow_html=True)
                        if n>=3:
                            checked=key in st.session_state.admin_open
                            if st.checkbox("開放",value=checked,key=f"adm_{key}"):
                                if key not in st.session_state.admin_open: st.session_state.admin_open.append(key)
                            else:
                                if key in st.session_state.admin_open: st.session_state.admin_open.remove(key)

        with st.container(border=True):
            for idx in range(len(_C["sessions"])):
                slot_section_admin(idx)
                if idx<len(_C["sessions"])-1: st.markdown('<div style="height:.5rem"></div>',unsafe_allow_html=True)

        n_open=len(st.session_state.admin_open)
        if st.button(f"🔓 確認開放 {n_open} 個時段 / Publish",type="primary",use_container_width=True):
            slots_to_save=[{"di":int(k.split("_")[0]),"si":int(k.split("_")[1])} for k in st.session_state.admin_open]
            db_set("open_slots",slots_to_save); st.session_state.open_slots=slots_to_save
            st.success(f"✅ 已開放 {n_open} 個時段！")

    # ══════════════════════════════════════
    # TAB 3: 老師空堂
    # ══════════════════════════════════════
    with tab_teachers:
        st.markdown(bi("所有老師填寫的空堂 · 可新增或刪除","All teacher availability"),unsafe_allow_html=True)
        teachers_raw=db_get_all("teachers")
        if not teachers_raw:
            st.info("尚無老師填寫空堂。")
        else:
            import pandas as pd
            for t_name,avail in teachers_raw.items():
                if not isinstance(avail,list): continue
                total=sum(1 for row in avail for v in row if v)
                with st.expander(f"🧑‍🏫 {t_name}  ·  {total} 個時段可用"):
                    rows=[]
                    for di in range(min(N_D,len(avail))):
                        for si in range(min(N_S,len(avail[di]))):
                            if avail[di][si]:
                                sess=session_for_si(si)
                                rows.append({"日期":f"{DATES_ZH[di]} {DATES_EN[di]}","TST":ALL_SLOTS[si],"場次":f"{sess['flag']} {sess['name_zh']}","當地":ALL_LOCAL[si]})
                    if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
                    else: st.caption("尚未勾選任何時段。")
                    _,cd=st.columns([3,1])
                    with cd:
                        ck=f"cdel_{t_name}"
                        if st.session_state.get(ck):
                            st.error(f"確定刪除 {t_name}？")
                            c1,c2=st.columns(2)
                            with c1:
                                if st.button("✅",key=f"dodel_{t_name}",use_container_width=True):
                                    db_delete(f"teachers/{t_name}"); st.session_state[ck]=False; load_counts(); st.rerun()
                            with c2:
                                if st.button("❌",key=f"cx_{t_name}",use_container_width=True): st.session_state[ck]=False; st.rerun()
                        else:
                            if st.button("🗑️ 刪除",key=f"del_{t_name}",use_container_width=True): st.session_state[ck]=True; st.rerun()
        st.divider()
        with st.expander("➕ 手動新增老師空堂"):
            new_n=st.text_input("老師姓名",key="new_t",placeholder="例：林老師")
            new_avail=[[False]*N_S for _ in range(N_D)]
            for si_s,sess in enumerate(_C["sessions"]):
                offset=sum(len(_C["sessions"][i]["slots"]) for i in range(si_s))
                st.markdown(f"*{sess['flag']} {sess['name_zh']}*")
                hdr2=st.columns([1.6]+[1]*len(sess["slots"]))
                hdr2[0].markdown("**日期**")
                for i,s in enumerate(sess["slots"]): hdr2[i+1].markdown(f"**{s['tst']}**")
                for di in range(N_D):
                    c2=st.columns([1.6]+[1]*len(sess["slots"]))
                    c2[0].write(DATES_ZH[di])
                    for i in range(len(sess["slots"])):
                        si=offset+i; new_avail[di][si]=c2[i+1].checkbox("",key=f"nt_{di}_{si}",label_visibility="collapsed")
            if st.button("💾 儲存",type="primary",use_container_width=True,key="save_new_t"):
                n=new_n.strip()
                if not n: st.error("請輸入姓名")
                else: db_set(f"teachers/{n}",new_avail); load_counts(); st.success(f"✅ 已儲存 {n}！"); st.rerun()

    # ══════════════════════════════════════
    # TAB 4: 學生報名
    # ══════════════════════════════════════
    with tab_students:
        students=st.session_state.students
        st.markdown(bi(f"學生報名狀況（{len(students)} 人）",f"Student registrations ({len(students)})"),unsafe_allow_html=True)
        import pandas as pd
        if students:
            rows=[]
            for s_key,s in students.items():
                if not isinstance(s,dict): continue
                di,si=s.get("di",0),s.get("si",0)
                sess=session_for_si(si)
                rows.append({"_key":s_key,"姓名":s.get("name",""),"時區":s.get("tz_label",""),
                              "場次":f"{sess['flag']} {sess['name_zh']}","日期":DATES_ZH[di] if di<N_D else "?",
                              "TST":ALL_SLOTS[si] if si<N_S else "?","當地":s.get("local_str",ALL_LOCAL[si] if si<N_S else ""),
                              "提前上線":s.get("early_str",ALL_EARLY[si] if si<N_S else "")})
            df=pd.DataFrame(rows)
            st.dataframe(df.drop(columns=["_key"]),use_container_width=True,hide_index=True)

            # CSV export
            csv=df.drop(columns=["_key"]).to_csv(index=False,encoding="utf-8-sig")
            st.download_button("📥 匯出 CSV / Export CSV",data=csv.encode("utf-8-sig"),
                               file_name="clc_registrations.csv",mime="text/csv",use_container_width=True)

            st.divider()
            # Bulk email
            if st.secrets.get("email_sender",""):
                st.markdown("**📧 批次寄信 Bulk Email (含 Google Meet 連結)**")
                # Group by di+region
                grp_opts={}
                for s in students.values():
                    if not isinstance(s,dict): continue
                    di,si=s.get("di",0),s.get("si",0)
                    sess=session_for_si(si)
                    k=f"{DATES_ZH[di] if di<N_D else '?'} {sess['flag']} {sess['name_zh']}"
                    grp_opts[k]=(di,sess["region"])
                sel_grp=st.selectbox("選擇場次 Select session",["— 全部 ALL —"]+list(grp_opts.keys()))
                if st.button("📧 寄送 Meet 連結給選取場次學生",use_container_width=True,key="bulk_email"):
                    count=0
                    for s in students.values():
                        if not isinstance(s,dict): continue
                        di,si=s.get("di",0),s.get("si",0)
                        sess=session_for_si(si); meet=get_meet_link(di,sess["region"])
                        email_addr=s.get("email","")
                        grp_k=f"{DATES_ZH[di] if di<N_D else '?'} {sess['flag']} {sess['name_zh']}"
                        if (sel_grp=="— 全部 ALL —" or sel_grp==grp_k) and email_addr:
                            # would send here
                            count+=1
                    st.info(f"（功能需配合 Email 欄位）目前找到 {count} 位有 Email 的學生可寄送。")
            else:
                st.caption("批次寄信需設定 email_sender Secret。")

            st.divider()
            st.markdown("**刪除學生報名紀錄**")
            names=[r["_key"] for r in rows]
            del_n=st.selectbox("選擇學生",["— 請選擇 —"]+names)
            if del_n and del_n!="— 請選擇 —":
                cks="cdelstu"
                if st.session_state.get(cks)==del_n:
                    st.error(f"確定刪除 {del_n}？")
                    c1,c2=st.columns(2)
                    with c1:
                        if st.button("✅ 確定",key="dodel_s",use_container_width=True):
                            db_delete(f"students/{del_n}"); st.session_state[cks]=None; load_students(); st.rerun()
                    with c2:
                        if st.button("❌ 取消",key="cxdel_s",use_container_width=True): st.session_state[cks]=None; st.rerun()
                else:
                    if st.button(f"🗑️ 刪除 {del_n}",use_container_width=True): st.session_state[cks]=del_n; st.rerun()
        else:
            st.caption("尚無學生報名。")
        if st.button("↻ Refresh",key="ref_stu"): load_students(); st.rerun()

    # ══════════════════════════════════════
    # TAB 5: ⚙️ 設定
    # ══════════════════════════════════════
    with tab_cfg:
        st.markdown(bi("系統設定","System config"),unsafe_allow_html=True)
        col_i,col_rst=st.columns([4,1])
        with col_rst:
            if st.button("↺ 重置草稿",key="rst_draft"): st.session_state.pop("cfg_draft",None); st.rerun()
        if "cfg_draft" not in st.session_state:
            st.session_state.cfg_draft=copy.deepcopy(st.session_state.app_config)
        draft=st.session_state.cfg_draft
        if "settings" not in draft: draft["settings"]=copy.deepcopy(DEFAULT_CONFIG["settings"])
        s=draft["settings"]

        # ── Registration settings ──────────────────────
        st.markdown("#### 🔓 報名設定 Registration Settings")
        with st.container(border=True):
            s["registration_open"]=st.toggle("報名開放 Registration Open",value=s.get("registration_open",True))
            deadline_val=s.get("deadline","")
            new_dl=st.text_input("截止時間 Deadline (YYYY-MM-DD HH:MM，留空=無限制)",value=deadline_val,placeholder="2026-05-25 23:59")
            s["deadline"]=new_dl
            s["max_per_slot"]=st.number_input("每時段名額上限 Max students per slot (0=無限制)",min_value=0,value=int(s.get("max_per_slot",1)),step=1)

        # ── Google Meet links ──────────────────────────
        st.markdown("#### 🎥 Google Meet 連結")
        st.caption("每日期 × 每場次設定一個 Meet 連結，學生和老師報名後可看到。")
        if "meet_links" not in s: s["meet_links"]={}
        for sess in _C["sessions"]:
            st.markdown(f"**{sess['flag']} {sess['name_zh']} {sess['name_en']}**")
            for d in _C["dates"]:
                key=f"{d['iso']}_{sess['region']}"
                cur=s["meet_links"].get(key,"")
                new_url=st.text_input(
                    f"{d['zh']} {d['en']}",value=cur,
                    placeholder="https://meet.google.com/xxx-xxxx-xxx",
                    key=f"meet_{key}")
                s["meet_links"][key]=new_url.strip()

        # ── Date config ────────────────────────────────
        st.markdown("#### 📅 考試日期 Exam Dates")
        remove_di=None
        hdr_cols=st.columns([2.2,2.2,2.2,0.4])
        for h,t in zip(hdr_cols,["EN label","ZH label","ISO date",""]): h.markdown(f"<div style='font-size:.78rem;color:#888'>{t}</div>",unsafe_allow_html=True)
        for i,d in enumerate(draft["dates"]):
            c1,c2,c3,c4=st.columns([2.2,2.2,2.2,0.4])
            with c1: d["en"]=st.text_input("en",value=d.get("en",""),key=f"de_{i}",label_visibility="collapsed")
            with c2: d["zh"]=st.text_input("zh",value=d.get("zh",""),key=f"dz_{i}",label_visibility="collapsed")
            with c3: d["iso"]=st.text_input("iso",value=d.get("iso",""),key=f"di_{i}",label_visibility="collapsed")
            with c4:
                if len(draft["dates"])>1 and st.button("✕",key=f"rmd_{i}"): remove_di=i
        if remove_di is not None: draft["dates"].pop(remove_di); st.rerun()
        if st.button("＋ 新增日期",key="add_date"): draft["dates"].append({"en":"New Date","zh":"日期","iso":"2026-01-01"}); st.rerun()

        # ── Sessions config ────────────────────────────
        st.markdown("#### 🕐 場次與時區 Sessions")
        tz_keys=list(TIMEZONE_OPTIONS.keys())
        for si_s,sess in enumerate(draft["sessions"]):
            with st.expander(f"{sess.get('flag','🌐')} {sess.get('name_zh','')} / {sess.get('name_en','')}  ·  {len(sess['slots'])} 個時段",expanded=False):
                c1,c2,c3,c4=st.columns([0.8,2,2,2])
                with c1: sess["flag"]=st.text_input("旗幟",value=sess.get("flag","🌐"),key=f"sf_{si_s}")
                with c2: sess["name_zh"]=st.text_input("中文名稱",value=sess.get("name_zh",""),key=f"snz_{si_s}")
                with c3: sess["name_en"]=st.text_input("English name",value=sess.get("name_en",""),key=f"sne_{si_s}")
                with c4: sess["region"]=st.text_input("區域代碼",value=sess.get("region","eu"),key=f"sr_{si_s}",placeholder="eu/us/jp…",help="自由輸入：eu, us, jp, au, sg …")
                st.markdown("**🌐 時區自動計算**")
                saved_tz=sess.get("_tz_name",tz_keys[0]); saved_idx=tz_keys.index(saved_tz) if saved_tz in tz_keys else 0
                tz_col,btn_col=st.columns([3,1])
                with tz_col: sel_tz=st.selectbox("選擇時區",options=tz_keys,index=saved_idx,key=f"sess_tz_{si_s}"); sess["_tz_name"]=sel_tz
                with btn_col:
                    st.markdown('<div style="height:1.75rem"></div>',unsafe_allow_html=True)
                    do_calc=st.button("🔄 自動填入",key=f"auto_tz_{si_s}",use_container_width=True)
                if do_calc:
                    tz_info=TIMEZONE_OPTIONS[sel_tz]
                    for j,slot in enumerate(sess["slots"]):
                        tst_val=st.session_state.get(f"st_{si_s}_{j}",slot["tst"])
                        if tst_val.strip():
                            l,e=calc_local_early(tst_val,tz_info["abbr"],tz_info["offset"])
                            st.session_state[f"sl_{si_s}_{j}"]=l; st.session_state[f"se_{si_s}_{j}"]=e
                            slot["local"]=l; slot["early"]=e
                    st.rerun()
                tz_cur=TIMEZONE_OPTIONS.get(sel_tz,list(TIMEZONE_OPTIONS.values())[0])
                prev_parts=[]
                for j,slot in enumerate(sess["slots"]):
                    tst=st.session_state.get(f"st_{si_s}_{j}",slot.get("tst",""))
                    if tst.strip():
                        loc,_=calc_local_early(tst,tz_cur["abbr"],tz_cur["offset"])
                        prev_parts.append(f"**{tst}**→{loc}")
                if prev_parts: st.markdown(f'<div style="background:#eaf3de;border-radius:6px;padding:6px 12px;font-size:.78rem;color:#27500a">預覽: {" · ".join(prev_parts)}</div>',unsafe_allow_html=True)
                hdr2=st.columns([1.5,2.5,2.5,0.4])
                for h2,t2 in zip(hdr2,["TST","當地時間","提前上線",""]): h2.markdown(f"<div style='font-size:.75rem;color:#888'>{t2}</div>",unsafe_allow_html=True)
                rm=None
                for j,slot in enumerate(sess["slots"]):
                    sc1,sc2,sc3,sc4=st.columns([1.5,2.5,2.5,0.4])
                    with sc1: slot["tst"]=st.text_input("t",value=slot.get("tst",""),key=f"st_{si_s}_{j}",label_visibility="collapsed",placeholder="HH:MM")
                    with sc2: slot["local"]=st.text_input("l",value=slot.get("local",""),key=f"sl_{si_s}_{j}",label_visibility="collapsed")
                    with sc3: slot["early"]=st.text_input("e",value=slot.get("early",""),key=f"se_{si_s}_{j}",label_visibility="collapsed")
                    with sc4:
                        if len(sess["slots"])>1 and st.button("✕",key=f"rms_{si_s}_{j}"): rm=j
                if rm is not None: sess["slots"].pop(rm); st.rerun()
                if st.button("＋ 新增時段",key=f"adds_{si_s}"): sess["slots"].append({"tst":"","local":"","early":""}); st.rerun()

        st.divider()
        c_s,c_d=st.columns(2)
        with c_s:
            if st.button("💾 儲存設定",type="primary",use_container_width=True,key="save_cfg"):
                save_config(draft); st.session_state.pop("cfg_draft",None); st.session_state.pop("app_config",None)
                st.success("✅ 設定已儲存！"); st.rerun()
        with c_d:
            ck_def="creset"
            if st.session_state.get(ck_def):
                st.warning("確定還原預設值？")
                cr1,cr2=st.columns(2)
                with cr1:
                    if st.button("✅ 確定",use_container_width=True,key="do_reset"):
                        save_config(copy.deepcopy(DEFAULT_CONFIG)); st.session_state.pop("cfg_draft",None); st.session_state.pop("app_config",None); st.session_state[ck_def]=False; st.rerun()
                with cr2:
                    if st.button("❌ 取消",use_container_width=True,key="cx_reset"): st.session_state[ck_def]=False; st.rerun()
            else:
                if st.button("↺ 還原預設值",use_container_width=True,key="reset_def"): st.session_state[ck_def]=True; st.rerun()

# ══════════════════════════════════════════════════════
# STUDENT SCREENS (kept for this portal)
# ══════════════════════════════════════════════════════
def screen_student_id():
    if st.button("← Back",key="back_sid"): go("landing")
    st.markdown("### 🎓 Oral Exam Registration")
    name=st.text_input("Your full name / 姓名",value=st.session_state.user_name,placeholder="e.g. Maria Schmidt")
    region=st.radio("Your location",options=[s["region"] for s in _C["sessions"]],
        format_func=lambda r: next((f"{s['flag']} {s['name_en']} / {s['name_zh']}" for s in _C["sessions"] if s["region"]==r),r),
        index=0,horizontal=True)
    if st.button("查看可報名時段 →",type="primary",use_container_width=True):
        name=name.strip()
        if not name: st.error("Please enter your name"); return
        st.session_state.user_name=name; st.session_state.region=region
        load_open_slots()
        b=db_get(f"students/{name}"); st.session_state.my_booking=b if isinstance(b,dict) else None
        go("student_slots")

def screen_student_slots():
    name=st.session_state.user_name; region=st.session_state.region
    settings=get_settings(); slot_counts=get_slot_counts()
    max_per=int(settings.get("max_per_slot",1))
    col_h,col_b=st.columns([4,1])
    with col_h: st.markdown(f"### 🎓 {name}")
    with col_b:
        if st.button("← Back",key="back_ssl"): go("landing")
    booking=st.session_state.my_booking
    if booking and isinstance(booking,dict):
        di,si=booking.get("di",0),booking.get("si",0)
        sess_b=session_for_si(si); meet=get_meet_link(di,sess_b["region"])
        st.markdown(f'<div style="background:#e1f5ee;border:1.5px solid #9fe1cb;border-radius:12px;padding:1rem 1.2rem;margin-bottom:1rem"><div style="font-weight:700;color:#085041;margin-bottom:5px">✅ Registered · 已成功報名</div><div style="font-size:1rem;font-weight:600;color:#085041">{DATES_EN[di] if di<N_D else "?"} · {ALL_SLOTS[si] if si<N_S else "?"} TST</div><div style="font-size:.88rem;color:#0f6e56;margin-top:4px">🕐 {ALL_LOCAL[si] if si<N_S else ""}</div></div>',unsafe_allow_html=True)
        if meet:
            st.markdown(f'<a href="{meet}" target="_blank" style="display:flex;align-items:center;justify-content:center;gap:8px;background:#e8f5e9;color:#1b5e20;border:1.5px solid #81c784;border-radius:10px;padding:12px;text-decoration:none;font-size:.95rem;font-weight:600;margin-bottom:1rem">🎥 Join Google Meet / 加入 Google Meet</a>',unsafe_allow_html=True)
    open_slots=st.session_state.open_slots
    relevant=[o for o in open_slots if isinstance(o,dict) and SLOT_REG[o["si"]]==region]
    if not relevant: st.warning("No slots available yet. 目前尚無開放時段。"); return
    for o in relevant:
        di,si=o["di"],o["si"]; booked=slot_counts.get(f"{di}_{si}",0)
        is_full=max_per>0 and booked>=max_per
        is_sel=booking and isinstance(booking,dict) and booking.get("di")==di and booking.get("si")==si
        sess_o=session_for_si(si); meet=get_meet_link(di,sess_o["region"])
        remaining=max(0,max_per-booked) if max_per>0 else None
        rem_html=f'<span style="font-size:.75rem;background:{"#fcebeb" if is_full else "#eaf3de"};color:{"#a32d2d" if is_full else "#27500a"};padding:2px 7px;border-radius:4px">{"額滿 Full" if is_full else f"剩 {remaining} 名" if remaining is not None else ""}</span>'
        st.markdown(f'<div style="border:{"2px solid #378add" if is_sel else "1px solid #dde"};border-radius:10px;padding:14px 16px;margin-bottom:8px"><div style="display:flex;justify-content:space-between;align-items:flex-start"><div><div style="font-weight:600">{"✓  " if is_sel else ""}{DATES_EN[di]} · {ALL_SLOTS[si]} TST</div><div style="font-size:.88rem;color:#555;margin-top:3px">🕐 {ALL_LOCAL[si]}</div></div>{rem_html}</div></div>',unsafe_allow_html=True)
        if not is_full or is_sel:
            if st.button(f"{'✓ Selected' if is_sel else 'Register'} — {DATES_EN[di]} {ALL_SLOTS[si]}",
                         key=f"slot_{di}_{si}",use_container_width=True):
                if not is_sel:
                    b={"name":name,"region":region,"di":di,"si":si}
                    db_set(f"students/{name}",b); st.session_state.my_booking=b
                    st.success("✅ Registered! 報名成功！"); st.rerun()
        else:
            st.button(f"額滿 Full — {DATES_EN[di]} {ALL_SLOTS[si]}",key=f"full_{di}_{si}",disabled=True,use_container_width=True)

# ══════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════
ROUTES={"landing":screen_landing,"teacher_id":screen_teacher_id,"teacher_grid":screen_teacher_grid,
        "admin_id":screen_admin_id,"admin_dash":screen_admin_dash,
        "student_id":screen_student_id,"student_slots":screen_student_slots}
ROUTES.get(st.session_state.screen,screen_landing)()
