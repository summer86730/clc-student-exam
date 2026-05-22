"""
CLC Oral Exam System v5
- Time slots: 08:10-09:00 format (50-min interviews, 10-min breaks)
- Teacher view: read-only schedule (admin assigns teachers)
- Sessions: country-based groups (admin-configurable)
- Pre-loaded teacher schedule from 5/27-5/29
"""

import streamlit as st
import json, os, copy
from datetime import datetime

st.set_page_config(page_title="CLC 口試排程系統", page_icon="🎓",
                   layout="centered", initial_sidebar_state="collapsed")

ADMIN_PW = st.secrets.get("admin_password", "CLC2026")

# ══════════════════════════════════════════════════════
# DEFAULT CONFIG
# ══════════════════════════════════════════════════════
DEFAULT_CONFIG = {
    "dates": [
        {"en":"5/27 (Wed)","zh":"5/27 星期三","iso":"2025-05-27"},
        {"en":"5/28 (Thu)","zh":"5/28 星期四","iso":"2025-05-28"},
        {"en":"5/29 (Fri)","zh":"5/29 星期五","iso":"2025-05-29"},
    ],
    "sessions": [
        {
            "id":"asia",
            "flag":"🌏","name_zh":"亞太場","name_en":"Asia-Pacific",
            "countries":"日本,越南,澳洲,印度,韓國,新加坡,菲律賓,泰國,印尼",
            "tz_preview":"JST (UTC+9)",
            "slots":[
                {"tst":"08:10","local":"JST 09:10","early":"JST 08:50"},
                {"tst":"09:10","local":"JST 10:10","early":"JST 09:50"},
                {"tst":"10:10","local":"JST 11:10","early":"JST 10:50"},
                {"tst":"11:10","local":"JST 12:10","early":"JST 11:50"},
            ],
        },
        {
            "id":"eu",
            "flag":"🇪🇺","name_zh":"歐洲場","name_en":"Europe",
            "countries":"波蘭,德國,瑞士,法國,英國,義大利,西班牙,荷蘭,奧地利,捷克,匈牙利,瑞典",
            "tz_preview":"CEST (UTC+2)",
            "slots":[
                {"tst":"13:10","local":"CEST 07:10","early":"CEST 06:50"},
                {"tst":"14:10","local":"CEST 08:10","early":"CEST 07:50"},
                {"tst":"15:10","local":"CEST 09:10","early":"CEST 08:50"},
                {"tst":"16:10","local":"CEST 10:10","early":"CEST 09:50"},
            ],
        },
        {
            "id":"us",
            "flag":"🌎","name_zh":"美洲場","name_en":"Americas",
            "countries":"美國,加拿大,墨西哥,巴西,阿根廷,哥倫比亞,智利",
            "tz_preview":"EDT (UTC-4)",
            "slots":[
                {"tst":"08:10","local":"EDT prev 20:10","early":"EDT prev 19:50"},
                {"tst":"09:10","local":"EDT prev 21:10","early":"EDT prev 20:50"},
                {"tst":"10:10","local":"EDT prev 22:10","early":"EDT prev 21:50"},
                {"tst":"11:10","local":"EDT prev 23:10","early":"EDT prev 22:50"},
            ],
        },
    ],
    # Pre-filled teacher assignments from schedule image
    "teacher_slots": {
        "2025-05-27_08:10": "芝彤 / 碧眞",
        "2025-05-27_09:10": "芝彤 / 碧眞",
        "2025-05-27_13:10": "怡慧 / 正芬",
        "2025-05-27_14:10": "怡慧 / 正芬",
        "2025-05-28_08:10": "芝彤 / 碧眞",
        "2025-05-28_09:10": "芝彤 / 碧眞",
        "2025-05-28_10:10": "育諾 / 怡慧",
        "2025-05-28_11:10": "育諾 / 怡慧",
        "2025-05-28_13:10": "琁婷 / 育諾",
        "2025-05-28_14:10": "琁婷 / 育諾",
        "2025-05-29_15:10": "琁婷 / 育諾",
        "2025-05-29_16:10": "琁婷 / 好靜",
    },
    "settings": {
        "registration_open": True,
        "deadline": "",
        "max_per_slot": 3,
        "meet_links": {},
    },
}

TIMEZONE_OPTIONS = {
    "CET  (UTC+1) — 歐洲中部":   {"abbr":"CET",  "offset":1},
    "CEST (UTC+2) — 歐洲夏令":   {"abbr":"CEST", "offset":2},
    "EET  (UTC+2) — 東歐":       {"abbr":"EET",  "offset":2},
    "EEST (UTC+3) — 東歐夏令":   {"abbr":"EEST", "offset":3},
    "MSK  (UTC+3) — 莫斯科":     {"abbr":"MSK",  "offset":3},
    "GST  (UTC+4) — 波斯灣":     {"abbr":"GST",  "offset":4},
    "IST  (UTC+5:30) — 印度":    {"abbr":"IST",  "offset":5.5},
    "WIB  (UTC+7) — 雅加達":     {"abbr":"WIB",  "offset":7},
    "JST  (UTC+9) — 日本/韓國":  {"abbr":"JST",  "offset":9},
    "AEST (UTC+10) — 澳洲東部":  {"abbr":"AEST", "offset":10},
    "EDT  (UTC-4) — 美東夏令":   {"abbr":"EDT",  "offset":-4},
    "CDT  (UTC-5) — 美中夏令":   {"abbr":"CDT",  "offset":-5},
    "PDT  (UTC-7) — 美西夏令":   {"abbr":"PDT",  "offset":-7},
    "BRT  (UTC-3) — 巴西":      {"abbr":"BRT",  "offset":-3},
}

def calc_local_early(tst_str, tz_abbr, tz_offset):
    try: h,m = map(int, tst_str.strip().split(":"))
    except: return tst_str, tst_str
    local_min = (h*60+m) - 480 + int(tz_offset*60)
    early_min = local_min - 20
    def fmt(t):
        prev=t<0; nxt=t>=1440; m2=t%1440; hh,mm=divmod(m2,60)
        return f"{'Prev. night ' if prev else 'Next day ' if nxt else ''}{tz_abbr} {hh:02d}:{mm:02d}"
    return fmt(local_min), fmt(early_min)

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
.bi{display:flex;flex-direction:column;line-height:1.35}
.bi .zh{font-size:.92rem;color:var(--color-text-primary)}
.bi .en{font-size:.75rem;color:var(--color-text-secondary);margin-top:1px}
.sch-cell{border-radius:6px;padding:6px 8px;text-align:center;font-size:.78rem;font-weight:500}
.sch-asia{background:#E1F5EE;color:#085041}
.sch-eu{background:#E6F1FB;color:#0C447C}
.sch-us{background:#FAEEDA;color:#633806}
.sch-empty{background:var(--color-background-secondary);color:var(--color-text-secondary)}
.sess-asia{background:#E1F5EE;border-left:3px solid #1D9E75;padding:8px 12px;border-radius:0 6px 6px 0;margin-bottom:6px}
.sess-eu{background:#E6F1FB;border-left:3px solid #378ADD;padding:8px 12px;border-radius:0 6px 6px 0;margin-bottom:6px}
.sess-us{background:#FAEEDA;border-left:3px solid #EF9F27;padding:8px 12px;border-radius:0 6px 6px 0;margin-bottom:6px}
.stat{background:var(--color-background-secondary);border-radius:var(--border-radius-md);padding:.625rem .75rem;text-align:center}
.sv{font-size:20px;font-weight:500}
.sl{font-size:11px;color:var(--color-text-secondary);margin-top:2px}
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
                                           {"databaseURL":st.secrets["firebase_url"]})
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
        for key in ("teacher_slots","settings"):
            if key not in cfg: cfg[key]=copy.deepcopy(DEFAULT_CONFIG[key])
        return cfg
    return copy.deepcopy(DEFAULT_CONFIG)

def save_config(cfg):
    db_set("config",cfg); st.session_state.app_config=cfg

if "app_config" not in st.session_state:
    st.session_state.app_config=load_config()

_C=st.session_state.app_config

def get_sessions(): return _C.get("sessions",[])
def get_dates(): return _C.get("dates",[])
def get_teacher_slots(): return _C.get("teacher_slots",{})
def get_settings(): return _C.get("settings",DEFAULT_CONFIG["settings"])

def get_all_tst_times():
    times=[]
    seen=set()
    for sess in get_sessions():
        for s in sess.get("slots",[]):
            t=s["tst"]
            if t not in seen: times.append(t); seen.add(t)
    return sorted(times)

def get_meet_link(di,sess_id):
    iso=get_dates()[di]["iso"] if di<len(get_dates()) else ""
    return get_settings().get("meet_links",{}).get(f"{iso}_{sess_id}","")

def get_slot_booking_count(di,tst,sess_id=None):
    students=st.session_state.get("students",{})
    count=0
    for s in students.values():
        if isinstance(s,dict) and s.get("di")==di and s.get("tst")==tst:
            if sess_id is None or s.get("sess_id")==sess_id:
                count+=1
    return count

def session_class(sess_id):
    return {"asia":"sch-asia","eu":"sch-eu","us":"sch-us"}.get(sess_id,"sch-empty")

def session_style(sess_id):
    return {"asia":"sess-asia","eu":"sess-eu","us":"sess-us"}.get(sess_id,"")

def load_students(): st.session_state.students=db_get_all("students")
def load_open_slots():
    raw=db_get("open_slots") or []
    # Filter: only accept new format {di, tst, sess_id}; discard old {di, si} entries
    if isinstance(raw,list):
        st.session_state.open_slots=[o for o in raw if isinstance(o,dict) and "tst" in o]
    else:
        st.session_state.open_slots=[]

# Session state
for k,v in {"screen":"landing","user_name":"","pw_error":False,
            "students":{},"open_slots":[],"adm_open":[]}.items():
    if k not in st.session_state: st.session_state[k]=v

def go(s): st.session_state.screen=s; st.rerun()
def bi(zh,en): return f'<div class="bi"><span class="zh">{zh}</span><span class="en">{en}</span></div>'

# ══════════════════════════════════════════════════════
# SCREEN: LANDING
# ══════════════════════════════════════════════════════
def screen_landing():
    st.markdown("### 🎓 CLC 口試排程系統")
    st.caption("Chinese Language Center · NCKU · 5/27–5/29, 2025")
    if not FIREBASE_OK:
        st.warning("⚠️ Demo mode — Firebase not configured.")
    st.divider()
    c1,c2,c3=st.columns(3)
    with c1:
        st.markdown("**🧑‍🏫**"); st.markdown(bi("老師","Teacher"),unsafe_allow_html=True)
        st.caption("查看您的口試班表\nView your schedule")
        if st.button("查看班表 →",key="go_t",use_container_width=True): go("teacher_id")
    with c2:
        st.markdown("**🎓**"); st.markdown(bi("學生","Student"),unsafe_allow_html=True)
        st.caption("報名口試時段\nRegister for a slot")
        if st.button("進入報名 →",key="go_s",use_container_width=True): go("student_id")
    with c3:
        st.markdown("**🛡️**"); st.markdown(bi("管理員","Admin"),unsafe_allow_html=True)
        st.caption("排班與報名管理\nManage schedule")
        if st.button("管理後台 →",key="go_a",use_container_width=True): go("admin_id")

# ══════════════════════════════════════════════════════
# SCREEN: TEACHER (read-only schedule view)
# ══════════════════════════════════════════════════════
def screen_teacher_id():
    if st.button("← 返回",key="back_tid"): go("landing")
    st.markdown("### 🧑‍🏫 老師班表查詢")
    st.info("輸入您的姓名，系統自動顯示您被分配到的口試時段。")
    name=st.text_input("您的姓名 Your name",placeholder="e.g. 芝彤",key="t_name_inp")
    if st.button("查看我的班表 →",type="primary",use_container_width=True):
        name=name.strip()
        if not name: st.error("請輸入姓名"); return
        st.session_state.user_name=name; go("teacher_schedule")

def screen_teacher_schedule():
    name=st.session_state.user_name
    if st.button("← 返回",key="back_ts"): go("landing")
    st.markdown(f"### 🧑‍🏫 {name} 的口試班表")

    teacher_slots=get_teacher_slots()
    dates=get_dates()
    all_times=get_all_tst_times()

    # Find slots where this teacher is assigned
    my_slots=[]
    for k,v in teacher_slots.items():
        if isinstance(v,str) and name in v:
            parts=k.split("_",1)
            if len(parts)==2:
                iso,tst=parts
                di=next((i for i,d in enumerate(dates) if d["iso"]==iso),None)
                if di is not None:
                    my_slots.append({"di":di,"iso":iso,"tst":tst,"teachers":v})

    if not my_slots:
        st.warning(f"找不到「{name}」的班表。請確認姓名拼寫是否與管理員設定一致。")
        return

    my_slots.sort(key=lambda x:(x["di"],x["tst"]))

    st.markdown(f"共 **{len(my_slots)}** 個口試時段（台灣時間）：")
    load_students()

    for slot in my_slots:
        di,tst=slot["di"],slot["tst"]
        d=dates[di]; iso=d["iso"]
        booked=get_slot_booking_count(di,tst)
        meet_url=""
        for sess in get_sessions():
            ml=get_meet_link(di,sess["id"])
            if ml: meet_url=ml; break

        with st.container(border=True):
            c1,c2=st.columns([3,1])
            with c1:
                # Only TST shown — no local time conversion
                st.markdown(f"**{d['zh']} {d['en']}**")
                st.markdown(
                    f'<div style="font-size:1.35rem;font-weight:700;color:var(--color-text-primary)">'
                    f'🕐 {tst} TST</div>'
                    f'<div style="font-size:.82rem;color:var(--color-text-secondary);margin-top:2px">'
                    f'👥 {slot["teachers"]} &nbsp;·&nbsp; 📝 {booked} 人已報名</div>',
                    unsafe_allow_html=True)
            with c2:
                if meet_url:
                    st.markdown(f'<a href="{meet_url}" target="_blank" style="display:flex;align-items:center;justify-content:center;gap:6px;background:#E8F5E9;color:#1B5E20;border:1px solid #81C784;border-radius:8px;padding:8px;text-decoration:none;font-size:.82rem;font-weight:500;text-align:center">🎥 Join Meet</a>',unsafe_allow_html=True)
                else:
                    st.caption("Meet 連結\n待設定")

    # Show student list for this teacher's slots
    st.divider()
    st.markdown("**分配到您場次的學生 Students in your sessions**")
    students=st.session_state.students
    my_tst_set={(s["di"],s["tst"]) for s in my_slots}
    my_students=[(k,v) for k,v in students.items()
                 if isinstance(v,dict) and (v.get("di"),v.get("tst")) in my_tst_set]
    if not my_students:
        st.caption("尚無學生報名您的時段。")
    else:
        import pandas as pd
        rows=[]
        for _,s in sorted(my_students,key=lambda x:(x[1].get("di",0),x[1].get("tst",""))):
            di=s.get("di",0); tst=s.get("tst","")
            d=dates[di] if di<len(dates) else {"zh":"?","en":"?"}
            rows.append({"姓名":s.get("name",""),"國籍":s.get("country",""),"場次":s.get("sess_name",""),
                         "日期":d["zh"],"時段 TST":tst,"當地時間":s.get("local_str","")})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

# ══════════════════════════════════════════════════════
# SCREEN: ADMIN ID
# ══════════════════════════════════════════════════════
def screen_admin_id():
    if st.button("← 返回",key="back_aid"): go("landing")
    st.markdown("### 🛡️ 管理員登入")
    pw=st.text_input("密碼",type="password",placeholder="Enter password")
    if st.session_state.pw_error: st.error("❌ 密碼錯誤")
    if st.button("登入",type="primary",use_container_width=True):
        if pw==ADMIN_PW:
            st.session_state.pw_error=False
            load_students(); load_open_slots()
            # Sync admin_open from stored open_slots
            st.session_state.adm_open=[
                f"{o.get('di','')}_{o.get('tst','')}_{o.get('sess_id','')}"
                for o in st.session_state.open_slots if isinstance(o,dict) and o.get('tst')]
            go("admin_dash")
        else: st.session_state.pw_error=True; st.rerun()

# ══════════════════════════════════════════════════════
# SCREEN: ADMIN DASHBOARD
# ══════════════════════════════════════════════════════
def screen_admin_dash():
    col_h,col_r=st.columns([4,1])
    with col_h: st.markdown("### 🛡️ 管理員儀表板")
    with col_r:
        if st.button("↻",key="adm_ref"): load_students(); load_open_slots(); st.rerun()
    if st.button("← 返回",key="back_ad"): go("landing")

    settings=get_settings()
    if not settings.get("registration_open",True):
        st.error("🔒 報名目前**關閉**中")
    else:
        dl=settings.get("deadline","")
        if dl:
            try:
                diff=datetime.strptime(dl,"%Y-%m-%d %H:%M")-datetime.now()
                hrs=max(0,int(diff.total_seconds()//3600))
                st.info(f"🟢 報名開放中 · 截止：{dl}（剩約 {hrs} 小時）")
            except: st.success("🟢 報名開放中")
        else: st.success("🟢 報名開放中")

    dates=get_dates(); sessions=get_sessions()
    teacher_slots=get_teacher_slots()
    students=st.session_state.students

    tab_sch,tab_open,tab_stu,tab_cfg=st.tabs(["📋 排班管理","🔓 開放時段","🎓 學生報名","⚙️ 設定"])

    # ══════════════════════════════════════
    # TAB 1: 排班管理
    # ══════════════════════════════════════
    with tab_sch:
        st.markdown("**老師分配表 Teacher assignment grid**")
        st.caption("直接在格子裡填入老師名字，填完按「儲存排班」。空白格 = 無老師/該時段不開放。")

        all_times=get_all_tst_times()
        draft_ts={}
        if "cfg_draft" in st.session_state:
            draft_ts=st.session_state.cfg_draft.get("teacher_slots",{})
        else:
            draft_ts=copy.deepcopy(teacher_slots)

        # Table header
        hdr=st.columns([1]+[1.5]*len(dates))
        hdr[0].markdown('<div style="font-size:.78rem;color:var(--color-text-secondary)">時段 TST</div>',unsafe_allow_html=True)
        for i,d in enumerate(dates):
            hdr[i+1].markdown(f'<div style="font-size:.78rem;font-weight:500;text-align:center">{d["zh"]}<br><span style="font-size:.72rem;color:var(--color-text-secondary)">{d["en"]}</span></div>',unsafe_allow_html=True)

        # Determine if morning or afternoon for styling
        def is_morning(t):
            h=int(t.split(":")[0])
            return h<12

        changed=False
        for t in all_times:
            cols=st.columns([1]+[1.5]*len(dates))
            bg="#E1F5EE" if is_morning(t) else "#E6F1FB"
            tc="#085041" if is_morning(t) else "#0C447C"
            cols[0].markdown(f'<div style="font-size:.82rem;font-weight:500;color:{tc};background:{bg};padding:4px 6px;border-radius:4px">{t}</div>',unsafe_allow_html=True)
            for di,d in enumerate(dates):
                k=f"{d['iso']}_{t}"
                cur=draft_ts.get(k,"")
                new_val=cols[di+1].text_input(f"t_{di}_{t}",value=cur,label_visibility="collapsed",
                                               placeholder="老師1 / 老師2")
                if new_val!=cur: draft_ts[k]=new_val; changed=True

        if st.button("💾 儲存排班 Save schedule",type="primary",use_container_width=True,key="save_ts"):
            if "cfg_draft" not in st.session_state:
                st.session_state.cfg_draft=copy.deepcopy(st.session_state.app_config)
            st.session_state.cfg_draft["teacher_slots"]={k:v for k,v in draft_ts.items() if v.strip()}
            save_config(st.session_state.cfg_draft)
            st.session_state.pop("cfg_draft",None); st.session_state.pop("app_config",None)
            st.success("✅ 排班已儲存！"); st.rerun()

        # Also show student bookings per slot
        if students:
            st.divider()
            st.markdown("**各時段報名人數**")
            for t in all_times:
                for di,d in enumerate(dates):
                    total=get_slot_booking_count(di,t)
                    if total>0:
                        k=f"{d['iso']}_{t}"
                        teachers=teacher_slots.get(k,"未分配")
                        st.markdown(f"**{d['zh']} {t}**　👥 {teachers}　📝 {total} 人已報名")

    # ══════════════════════════════════════
    # TAB 2: 開放時段
    # ══════════════════════════════════════
    with tab_open:
        st.markdown("**各場次開放設定**")
        st.caption("勾選要開放給學生報名的時段（只有已填老師的時段才能開放）。")
        max_per=int(settings.get("max_per_slot",3))
        st.caption(f"每時段名額上限：{max_per} 人（可在「⚙️ 設定」修改）")

        adm_open=st.session_state.adm_open

        for sess in sessions:
            sid=sess["id"]; flag=sess["flag"]; nz=sess["name_zh"]; ne=sess["name_en"]
            scls=session_style(sid)
            st.markdown(f'<div class="{scls}"><strong>{flag} {nz} / {ne}</strong>　<span style="font-size:.78rem">{sess.get("tz_preview","")}</span></div>',unsafe_allow_html=True)

            for slot in sess.get("slots",[]):
                tst=slot["tst"]
                for di,d in enumerate(dates):
                    k=f"{d['iso']}_{tst}"
                    teachers=teacher_slots.get(k,"")
                    open_key=f"{di}_{tst}_{sid}"
                    booked=get_slot_booking_count(di,tst,sid)
                    rem=max(0,max_per-booked)

                    col1,col2,col3,col4=st.columns([1.5,2,1.5,1])
                    with col1: st.write(f"{d['zh']} {tst}")
                    with col2:
                        if teachers:
                            st.markdown(f'<span class="sch-cell {session_class(sid)}">{teachers}</span>',unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="sch-cell sch-empty">— 無老師 —</span>',unsafe_allow_html=True)
                    with col3:
                        if booked>0:
                            st.markdown(f'<span style="font-size:.78rem;color:#185fa5">{booked} 人已報名，剩 {rem}</span>',unsafe_allow_html=True)
                        else:
                            st.caption("尚無報名")
                    with col4:
                        if not teachers:
                            st.button("需填老師",key=f"nf_{open_key}",disabled=True,use_container_width=True)
                        else:
                            checked=open_key in adm_open
                            if st.checkbox("開放",value=checked,key=f"op_{open_key}"):
                                if open_key not in adm_open: adm_open.append(open_key)
                            else:
                                if open_key in adm_open: adm_open.remove(open_key)

        st.markdown('<div style="height:.5rem"></div>',unsafe_allow_html=True)
        n=len(adm_open)
        if st.button(f"🔓 確認開放 {n} 個時段",type="primary",use_container_width=True):
            slots_to_save=[]
            for key in adm_open:
                parts=key.split("_")
                if len(parts)>=3:
                    di=int(parts[0]); tst=parts[1]; sid="_".join(parts[2:])
                    sess_data=next((s for s in sessions if s["id"]==sid),None)
                    slot_data=next((s for s in (sess_data.get("slots",[]) if sess_data else []) if s["tst"]==tst),None)
                    slots_to_save.append({
                        "di":di,"tst":tst,"sess_id":sid,
                        "local":slot_data["local"] if slot_data else tst,
                        "early":slot_data["early"] if slot_data else tst,
                    })
            db_set("open_slots",slots_to_save)
            st.session_state.open_slots=slots_to_save
            st.success(f"✅ 已開放 {n} 個時段！")

    # ══════════════════════════════════════
    # TAB 3: 學生報名
    # ══════════════════════════════════════
    with tab_stu:
        import pandas as pd
        st.markdown(f"**學生報名狀況（{len(students)} 人）**")

        # Summary by session
        sess_cnt={}
        for s in students.values():
            if isinstance(s,dict):
                k=s.get("sess_name","未分組")
                sess_cnt[k]=sess_cnt.get(k,0)+1
        if sess_cnt:
            mcols=st.columns(len(sess_cnt))
            for i,(k,v) in enumerate(sess_cnt.items()):
                with mcols[i]:
                    st.markdown(f'<div class="stat"><div class="sv">{v}</div><div class="sl">{k}</div></div>',unsafe_allow_html=True)
            st.markdown('<div style="height:.5rem"></div>',unsafe_allow_html=True)

        if students:
            rows=[]
            for sk,s in students.items():
                if not isinstance(s,dict): continue
                di=s.get("di",0); tst=s.get("tst","")
                d=dates[di] if di<len(dates) else {"zh":"?","en":"?"}
                ts_key=f"{d.get('iso','')}_{tst}"
                rows.append({"_key":sk,"姓名":s.get("name",""),"國籍":s.get("country",""),
                              "場次":s.get("sess_name",""),"日期":d["zh"],"TST":tst,
                              "當地時間":s.get("local_str",""),"提前上線":s.get("early_str",""),
                              "老師":teacher_slots.get(ts_key,"未分配")})
            df=pd.DataFrame(rows)
            st.dataframe(df.drop(columns=["_key"]),use_container_width=True,hide_index=True)
            csv=df.drop(columns=["_key"]).to_csv(index=False,encoding="utf-8-sig")
            st.download_button("📥 匯出 CSV",data=csv.encode("utf-8-sig"),file_name="clc_registrations.csv",mime="text/csv",use_container_width=True)
            st.divider()
            names=[r["_key"] for r in rows]
            del_n=st.selectbox("刪除學生報名",["— 請選擇 —"]+names)
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
    # TAB 4: 設定
    # ══════════════════════════════════════
    with tab_cfg:
        col_i,col_rst=st.columns([4,1])
        with col_rst:
            if st.button("↺ 重置草稿",key="rst_d"): st.session_state.pop("cfg_draft",None); st.rerun()
        if "cfg_draft" not in st.session_state:
            st.session_state.cfg_draft=copy.deepcopy(st.session_state.app_config)
        draft=st.session_state.cfg_draft
        if "settings" not in draft: draft["settings"]=copy.deepcopy(DEFAULT_CONFIG["settings"])
        s=draft["settings"]

        # Registration settings
        st.markdown("#### 🔓 報名設定")
        with st.container(border=True):
            s["registration_open"]=st.toggle("報名開放",value=s.get("registration_open",True))
            s["deadline"]=st.text_input("截止時間 (YYYY-MM-DD HH:MM，留空=無限)",value=s.get("deadline",""),placeholder="2025-05-26 23:59")
            s["max_per_slot"]=st.number_input("每時段名額上限 (0=無限)",min_value=0,value=int(s.get("max_per_slot",3)),step=1)

        # Meet links
        st.markdown("#### 🎥 Google Meet 連結")
        if "meet_links" not in s: s["meet_links"]={}
        for sess in draft.get("sessions",[]):
            st.markdown(f"**{sess['flag']} {sess['name_zh']}**")
            for d in draft.get("dates",[]):
                k=f"{d['iso']}_{sess['id']}"
                cur=s["meet_links"].get(k,"")
                new_url=st.text_input(f"{d['zh']}",value=cur,placeholder="https://meet.google.com/xxx",key=f"meet_{k}")
                s["meet_links"][k]=new_url.strip()

        # Dates
        st.markdown("#### 📅 考試日期")
        rm_d=None
        hdr2=st.columns([2,2,2.5,0.4])
        for h,t in zip(hdr2,["EN","ZH","ISO (YYYY-MM-DD)",""]): h.markdown(f"<div style='font-size:.75rem;color:var(--color-text-secondary)'>{t}</div>",unsafe_allow_html=True)
        for i,d in enumerate(draft.get("dates",[])):
            c1,c2,c3,c4=st.columns([2,2,2.5,0.4])
            with c1: d["en"]=st.text_input("en",value=d.get("en",""),key=f"de_{i}",label_visibility="collapsed")
            with c2: d["zh"]=st.text_input("zh",value=d.get("zh",""),key=f"dz_{i}",label_visibility="collapsed")
            with c3: d["iso"]=st.text_input("iso",value=d.get("iso",""),key=f"di_{i}",label_visibility="collapsed")
            with c4:
                if len(draft.get("dates",[]))>1 and st.button("✕",key=f"rmd_{i}"): rm_d=i
        if rm_d is not None: draft["dates"].pop(rm_d); st.rerun()
        if st.button("＋ 新增日期",key="add_d"): draft.setdefault("dates",[]).append({"en":"New","zh":"新日期","iso":"2025-01-01"}); st.rerun()

        # Sessions (country groups)
        st.markdown("#### 🗂️ 場次與國家群組")
        st.caption("每個場次一個群組，逗號分隔國家名稱。學生選擇國籍後自動分配到對應場次。")
        tz_keys=list(TIMEZONE_OPTIONS.keys())
        for si_s,sess in enumerate(draft.get("sessions",[])):
            with st.expander(f"{sess.get('flag','🌐')} {sess.get('name_zh','')}  ·  {len(sess.get('slots',[]))} 個時段",expanded=False):
                c1,c2,c3,c4=st.columns([0.6,1.8,2,1.5])
                with c1: sess["flag"]=st.text_input("旗幟",value=sess.get("flag","🌐"),key=f"sf_{si_s}")
                with c2: sess["name_zh"]=st.text_input("中文名稱",value=sess.get("name_zh",""),key=f"snz_{si_s}")
                with c3: sess["name_en"]=st.text_input("English name",value=sess.get("name_en",""),key=f"sne_{si_s}")
                with c4: sess["id"]=st.text_input("ID代碼",value=sess.get("id",""),key=f"sid_{si_s}",help="英文小寫，如 asia/eu/us/jp")

                sess["countries"]=st.text_area(
                    "包含國家 (逗號分隔)",value=sess.get("countries",""),
                    key=f"sc_{si_s}",height=68,
                    help="例：日本,越南,澳洲,印度  每個國名需與學生端選項完全一致")

                st.markdown("**時段設定 + 時區自動計算**")
                saved_tz=sess.get("_tz_name",tz_keys[0]); saved_idx=tz_keys.index(saved_tz) if saved_tz in tz_keys else 0
                tz_col,btn_col=st.columns([3,1])
                with tz_col: sel_tz=st.selectbox("選擇時區",options=tz_keys,index=saved_idx,key=f"stz_{si_s}"); sess["_tz_name"]=sel_tz
                with btn_col:
                    st.markdown('<div style="height:1.75rem"></div>',unsafe_allow_html=True)
                    if st.button("🔄 自動填入",key=f"atz_{si_s}",use_container_width=True):
                        tz_info=TIMEZONE_OPTIONS[sel_tz]
                        for j,slot in enumerate(sess.get("slots",[])):
                            tst_v=st.session_state.get(f"st_{si_s}_{j}",slot.get("tst",""))
                            if tst_v.strip():
                                l,e=calc_local_early(tst_v,tz_info["abbr"],tz_info["offset"])
                                st.session_state[f"sl_{si_s}_{j}"]=l; st.session_state[f"se_{si_s}_{j}"]=e
                                slot["local"]=l; slot["early"]=e
                        st.rerun()

                hdr3=st.columns([1.5,2.5,2.5,0.4])
                for h3,t3 in zip(hdr3,["台灣時間 TST","當地時間","提前上線",""]): h3.markdown(f"<div style='font-size:.75rem;color:var(--color-text-secondary)'>{t3}</div>",unsafe_allow_html=True)
                rm_s=None
                for j,slot in enumerate(sess.get("slots",[])):
                    sc1,sc2,sc3,sc4=st.columns([1.5,2.5,2.5,0.4])
                    with sc1: slot["tst"]=st.text_input("t",value=slot.get("tst",""),key=f"st_{si_s}_{j}",label_visibility="collapsed",placeholder="HH:MM")
                    with sc2: slot["local"]=st.text_input("l",value=slot.get("local",""),key=f"sl_{si_s}_{j}",label_visibility="collapsed")
                    with sc3: slot["early"]=st.text_input("e",value=slot.get("early",""),key=f"se_{si_s}_{j}",label_visibility="collapsed")
                    with sc4:
                        if len(sess.get("slots",[]))>1 and st.button("✕",key=f"rms_{si_s}_{j}"): rm_s=j
                if rm_s is not None: sess["slots"].pop(rm_s); st.rerun()
                if st.button("＋ 新增時段",key=f"adds_{si_s}"): sess.setdefault("slots",[]).append({"tst":"","local":"","early":""}); st.rerun()
                c_del,_=st.columns([1,3])
                with c_del:
                    ck_sess=f"del_sess_{si_s}"
                    if st.session_state.get(ck_sess):
                        st.error("確定刪除此場次？")
                        ca,cb=st.columns(2)
                        with ca:
                            if st.button("✅",key=f"dodel_sess_{si_s}",use_container_width=True):
                                draft["sessions"].pop(si_s); st.session_state[ck_sess]=False; st.rerun()
                        with cb:
                            if st.button("❌",key=f"cx_sess_{si_s}",use_container_width=True): st.session_state[ck_sess]=False; st.rerun()
                    else:
                        if st.button("🗑️ 刪除此場次",key=f"del_sess_btn_{si_s}"): st.session_state[ck_sess]=True; st.rerun()

        if st.button("＋ 新增場次 Add session",key="add_sess"):
            draft.setdefault("sessions",[]).append({"id":"new","flag":"🌐","name_zh":"新場次","name_en":"New Session","countries":"","tz_preview":"","slots":[{"tst":"","local":"","early":""}]})
            st.rerun()

        st.divider()
        c_s,c_d=st.columns(2)
        with c_s:
            if st.button("💾 儲存設定",type="primary",use_container_width=True,key="save_cfg"):
                save_config(draft); st.session_state.pop("cfg_draft",None); st.session_state.pop("app_config",None)
                st.success("✅ 設定已儲存！"); st.rerun()
        with c_d:
            ck_def="creset"
            if st.session_state.get(ck_def):
                cr1,cr2=st.columns(2)
                with cr1:
                    if st.button("✅ 確定還原",use_container_width=True,key="do_r"):
                        save_config(copy.deepcopy(DEFAULT_CONFIG)); st.session_state.pop("cfg_draft",None); st.session_state.pop("app_config",None); st.session_state[ck_def]=False; st.rerun()
                with cr2:
                    if st.button("❌ 取消",use_container_width=True,key="cx_r"): st.session_state[ck_def]=False; st.rerun()
            else:
                if st.button("↺ 還原預設值",use_container_width=True,key="reset_def"): st.session_state[ck_def]=True; st.rerun()

# ══════════════════════════════════════════════════════
# STUDENT SCREENS (keep in app.py for admin preview)
# ══════════════════════════════════════════════════════
def screen_student_id():
    if st.button("← 返回",key="back_sid"): go("landing")
    st.markdown("### 🎓 口試報名")
    go("landing")

def screen_student_slots():
    go("landing")

# ══════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════
ROUTES={
    "landing":screen_landing,"teacher_id":screen_teacher_id,"teacher_schedule":screen_teacher_schedule,
    "admin_id":screen_admin_id,"admin_dash":screen_admin_dash,
    "student_id":screen_student_id,"student_slots":screen_student_slots,
}
ROUTES.get(st.session_state.screen,screen_landing)()
