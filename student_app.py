"""
CLC Oral Exam — Student Portal v4
- Country selector → auto-assigned to session group
- Shows slots with student's actual local time
- All times in 08:10–09:00 format
"""

import streamlit as st
import os, base64, urllib.parse
from datetime import datetime, timedelta

st.set_page_config(page_title="CLC 口試報名", page_icon="🎓",
                   layout="centered", initial_sidebar_state="collapsed")

# ══════════════════════════════════════════════════════
# COUNTRY LIST with timezone info
# ══════════════════════════════════════════════════════
COUNTRIES = [
    # Asia-Pacific
    {"country":"日本 Japan",       "abbr":"JST",   "offset":9,    "group":"asia"},
    {"country":"越南 Vietnam",     "abbr":"ICT",   "offset":7,    "group":"asia"},
    {"country":"澳洲 Australia",   "abbr":"AEST",  "offset":10,   "group":"asia"},
    {"country":"印度 India",       "abbr":"IST",   "offset":5.5,  "group":"asia"},
    {"country":"韓國 Korea",       "abbr":"KST",   "offset":9,    "group":"asia"},
    {"country":"新加坡 Singapore", "abbr":"SGT",   "offset":8,    "group":"asia"},
    {"country":"泰國 Thailand",    "abbr":"ICT",   "offset":7,    "group":"asia"},
    {"country":"菲律賓 Philippines","abbr":"PHT",  "offset":8,    "group":"asia"},
    {"country":"馬來西亞 Malaysia","abbr":"MYT",  "offset":8,    "group":"asia"},
    {"country":"印尼 Indonesia",   "abbr":"WIB",   "offset":7,    "group":"asia"},
    {"country":"紐西蘭 New Zealand","abbr":"NZST", "offset":12,   "group":"asia"},
    # Europe
    {"country":"德國 Germany",     "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"瑞士 Switzerland", "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"波蘭 Poland",      "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"法國 France",      "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"英國 UK",          "abbr":"BST",   "offset":1,    "group":"eu"},
    {"country":"義大利 Italy",     "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"西班牙 Spain",     "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"荷蘭 Netherlands", "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"奧地利 Austria",   "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"捷克 Czech Rep.",  "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"匈牙利 Hungary",   "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"瑞典 Sweden",      "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"挪威 Norway",      "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"丹麥 Denmark",     "abbr":"CEST",  "offset":2,    "group":"eu"},
    {"country":"俄羅斯 Russia",    "abbr":"MSK",   "offset":3,    "group":"eu"},
    {"country":"土耳其 Turkey",    "abbr":"TRT",   "offset":3,    "group":"eu"},
    {"country":"南非 South Africa","abbr":"SAST",  "offset":2,    "group":"eu"},
    # Americas
    {"country":"美國東岸 USA (East)","abbr":"EDT", "offset":-4,   "group":"us"},
    {"country":"美國西岸 USA (West)","abbr":"PDT", "offset":-7,   "group":"us"},
    {"country":"加拿大 Canada",    "abbr":"EDT",   "offset":-4,   "group":"us"},
    {"country":"墨西哥 Mexico",    "abbr":"CDT",   "offset":-5,   "group":"us"},
    {"country":"巴西 Brazil",      "abbr":"BRT",   "offset":-3,   "group":"us"},
    {"country":"阿根廷 Argentina", "abbr":"ART",   "offset":-3,   "group":"us"},
    {"country":"哥倫比亞 Colombia","abbr":"COT",   "offset":-5,   "group":"us"},
    {"country":"智利 Chile",       "abbr":"CLT",   "offset":-4,   "group":"us"},
]
COUNTRY_LABELS=[c["country"] for c in COUNTRIES]
COUNTRY_BY_LABEL={c["country"]:c for c in COUNTRIES}

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
[data-testid="stSidebar"]{display:none}
[data-testid="stDecoration"]{display:none}
footer{display:none!important}
.clc-hdr{background:#e6f1fb;border-bottom:1px solid #b5d4f4;padding:.875rem 1.25rem .75rem;margin:-1rem -1rem 1.5rem;display:flex;align-items:center;gap:12px}
.clc-title{font-size:1rem;font-weight:600;color:#0c447c}
.clc-sub{font-size:.75rem;color:#378add;margin-top:1px}
.book-card{background:#e1f5ee;border:1.5px solid #9fe1cb;border-radius:12px;padding:1rem 1.2rem;margin-bottom:1rem}
.slot-opt{border:1px solid var(--color-border-tertiary);border-radius:10px;padding:14px 16px;margin-bottom:8px}
.slot-sel{border:2px solid #378add!important;background:#e6f1fb14}
.slot-full{opacity:.5}
.slot-time{font-size:1rem;font-weight:600}
.slot-local{font-size:.95rem;font-weight:500;color:#185fa5;margin-top:4px}
.slot-early{font-size:.78rem;color:var(--color-text-secondary);margin-top:2px}
.tz-pill{display:inline-block;background:#e6f1fb;color:#0c447c;padding:3px 10px;border-radius:6px;font-size:.78rem;font-weight:500}
.notice{background:var(--color-background-secondary);border-radius:8px;padding:10px 14px;font-size:.82rem;color:var(--color-text-secondary);line-height:1.65;margin-bottom:1rem}
.email-box{background:#f0f7fe;border:1px solid #b5d4f4;border-radius:10px;padding:.875rem 1rem;margin-top:.75rem}
.check-card{background:#fff8ec;border:1.5px solid #fac775;border-radius:12px;padding:1rem 1.2rem;margin-bottom:1rem}
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
            cred_dict=dict(st.secrets["firebase_credentials"])
            if "private_key" in cred_dict:
                cred_dict["private_key"]=cred_dict["private_key"].replace("\\n","\n")
            firebase_admin.initialize_app(credentials.Certificate(cred_dict),
                                           {"databaseURL":st.secrets["firebase_url"]})
        return db, True
    except: return None, False

_fb, FIREBASE_OK=init_firebase()
_LP="/tmp/clc_local_db.json"

def _ll():
    import json
    if os.path.exists(_LP):
        with open(_LP) as f: return json.load(f)
    return {}

def db_get(path):
    if FIREBASE_OK: return _fb.reference(path).get()
    data=_ll()
    for k in path.strip("/").split("/"):
        data=data.get(k) if isinstance(data,dict) else None
        if data is None: return None
    return data

def db_set(path,value):
    import json
    if FIREBASE_OK: _fb.reference(path).set(value)
    else:
        data=_ll(); keys=path.strip("/").split("/"); d=data
        for k in keys[:-1]: d=d.setdefault(k,{})
        d[keys[-1]]=value
        with open(_LP,"w") as f: json.dump(data,f)

# ══════════════════════════════════════════════════════
# CONFIG & UTILS
# ══════════════════════════════════════════════════════
def _fix(obj):
    if isinstance(obj,dict):
        if obj and all(k.isdigit() for k in obj.keys()):
            return [_fix(obj[str(i)]) for i in range(len(obj))]
        return {k:_fix(v) for k,v in obj.items()}
    return obj

def load_app_config():
    raw=db_get("config")
    if isinstance(raw,dict) and "sessions" in raw: return _fix(raw)
    return None

def get_sys_settings(cfg):
    return (cfg or {}).get("settings",{})

def get_session_by_group(cfg, group_id):
    if not cfg: return None
    return next((s for s in cfg.get("sessions",[]) if s.get("id")==group_id), None)

def get_meet_link_cfg(cfg, di, sess_id):
    dates=cfg.get("dates",[]) if cfg else []
    iso=dates[di]["iso"] if di<len(dates) else ""
    return get_sys_settings(cfg).get("meet_links",{}).get(f"{iso}_{sess_id}","")

def tst_to_local(tst, tz_offset, tz_abbr):
    try: h,m=map(int,tst.split(":"))
    except: return tst, tst, False
    local_min=(h*60+m)-480+int(tz_offset*60)
    early_min=local_min-20
    def fmt(t):
        prev=t<0; nxt=t>=1440; m2=t%1440; hh,mm=divmod(m2,60)
        return f"{'Prev. night ' if prev else 'Next day ' if nxt else ''}{tz_abbr} {hh:02d}:{mm:02d}",prev
    ls,prev=fmt(local_min); es,_=fmt(early_min)
    return ls,es,prev

def get_slot_count(all_students, di, tst):
    count=0
    for s in all_students.values():
        if isinstance(s,dict) and s.get("di")==di and s.get("tst")==tst: count+=1
    return count

def generate_ics(name, date_iso, tst, local_str, early_str):
    try:
        h,m=map(int,tst.split(":"))
        dt=datetime.strptime(date_iso,"%Y-%m-%d").replace(hour=h,minute=m)-timedelta(hours=8)
        dt_end=dt+timedelta(minutes=50)
        alarm=dt-timedelta(minutes=20)
        fmt="%Y%m%dT%H%M%SZ"
        ics=(f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//CLC NCKU//EN\r\n"
             f"BEGIN:VEVENT\r\nDTSTART:{dt.strftime(fmt)}\r\nDTEND:{dt_end.strftime(fmt)}\r\n"
             f"SUMMARY:CLC Oral Placement Interview\r\n"
             f"DESCRIPTION:Registrant: {name}\\nTST: {tst}\\nLocal: {local_str}\\nJoin early: {early_str}\r\n"
             f"LOCATION:Google Meet (link sent by CLC)\r\nSTATUS:CONFIRMED\r\n"
             f"BEGIN:VALARM\r\nACTION:DISPLAY\r\nTRIGGER;VALUE=DATE-TIME:{alarm.strftime(fmt)}\r\n"
             f"DESCRIPTION:Interview in 20 min!\r\nEND:VALARM\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
        return ics.encode()
    except: return b""

def generate_gcal(name, date_iso, tst):
    try:
        h,m=map(int,tst.split(":"))
        dt=datetime.strptime(date_iso,"%Y-%m-%d").replace(hour=h,minute=m)-timedelta(hours=8)
        dt_end=dt+timedelta(minutes=50)
        fmt="%Y%m%dT%H%M%SZ"
        p=urllib.parse.urlencode({"action":"TEMPLATE","text":"CLC Oral Placement Interview",
            "dates":f"{dt.strftime(fmt)}/{dt_end.strftime(fmt)}",
            "details":f"Registrant: {name}\nZoom/Meet link will be sent by CLC staff.",
            "location":"Google Meet"})
        return f"https://calendar.google.com/calendar/render?{p}"
    except: return "#"

# ══════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════
for k,v in {"screen":"landing","user_name":"","country_info":None,
            "my_booking":None,"open_slots":[],"app_cfg":None}.items():
    if k not in st.session_state: st.session_state[k]=v

if st.session_state.app_cfg is None:
    st.session_state.app_cfg=load_app_config()

def go(s): st.session_state.screen=s; st.rerun()

# ══════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════
st.markdown('<div class="clc-hdr"><div style="font-size:1.8rem">🎓</div><div>'
            '<div class="clc-title">CLC Oral Placement Interview 口試報名</div>'
            '<div class="clc-sub">Chinese Language Center · NCKU · 5/27–5/29, 2025</div>'
            '</div></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# BOOKING CARD COMPONENT
# ══════════════════════════════════════════════════════
def render_booking_card(booking, show_actions=True):
    import json as _j
    di=booking.get("di",0); tst=booking.get("tst","")
    name=booking.get("name",""); country=booking.get("country","")
    local_str=booking.get("local_str",""); early_str=booking.get("early_str","")
    date_iso=booking.get("date_iso",""); sess_id=booking.get("sess_id","")
    cfg=st.session_state.app_cfg
    dates=(cfg or {}).get("dates",[])
    date_en=dates[di]["en"] if di<len(dates) else ""
    meet_url=get_meet_link_cfg(cfg,di,sess_id)

    abbr=booking.get("tz_abbr","")
    st.markdown(
        f'<div class="book-card">'
        f'<div style="font-weight:600;color:#085041;font-size:.82rem;margin-bottom:8px">✅ Registration confirmed / 報名確認</div>'
        # ── Local time: PRIMARY ──────────────────────────────
        f'<div style="font-size:1.5rem;font-weight:700;color:#085041;line-height:1.2">{local_str}</div>'
        f'<div style="font-size:.82rem;color:#0F6E56;margin-top:2px">⏰ Join early / 提前上線：<strong>{early_str}</strong></div>'
        # ── Secondary info ───────────────────────────────────
        f'<div style="border-top:1px solid #b5e8d4;margin-top:8px;padding-top:8px">'
        f'<div style="font-size:.82rem;color:#0F6E56">'
        f'{"📍 "+country+" &nbsp;·&nbsp; " if country else ""}'
        f'📅 {date_en} &nbsp;·&nbsp; 🕐 Taiwan: {tst} TST'
        f'</div></div>'
        f'{"<div style=\\'font-size:.75rem;color:#666;margin-top:8px\\'>Need to change? Select a different slot below. / 如需更改請點選其他時段。</div>" if show_actions else ""}'
        f'</div>',unsafe_allow_html=True)

    if not show_actions: return

    # Meet link (if set by admin)
    if meet_url:
        st.markdown(f'<a href="{meet_url}" target="_blank" style="display:flex;align-items:center;justify-content:center;gap:8px;background:#e8f5e9;color:#1b5e20;border:1.5px solid #81c784;border-radius:10px;padding:14px;text-decoration:none;font-size:1rem;font-weight:700;margin-bottom:10px">🎥 Join Google Meet / 加入 Google Meet</a>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="notice">🎥 Google Meet link will be sent by CLC staff before the interview date.<br>Google Meet 連結將由 CLC 工作人員於口試前寄送。</div>',unsafe_allow_html=True)

    # Calendar buttons
    ics=generate_ics(name,date_iso,tst,local_str,early_str)
    ics_b64=base64.b64encode(ics).decode() if ics else ""
    gcal=generate_gcal(name,date_iso,tst)
    btn="display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:10px 0;border-radius:8px;text-decoration:none;font-size:.88rem;font-weight:500;width:100%;box-sizing:border-box;"
    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">'
        f'<a href="{gcal}" target="_blank" style="{btn}background:#e6f1fb;color:#0c447c;border:1px solid #b5d4f4">📅 Google Calendar</a>'
        f'<a href="data:text/calendar;base64,{ics_b64}" download="clc_interview.ics" style="{btn}background:var(--color-background-secondary);color:var(--color-text-primary);border:1px solid var(--color-border-tertiary)">📎 Apple / Outlook (.ics)</a>'
        f'</div>'
        f'<div style="font-size:.72rem;color:var(--color-text-secondary);text-align:center;margin-bottom:10px">iOS: tap Apple/Outlook · Android: tap Google Calendar</div>',
        unsafe_allow_html=True)

    # Optional email
    st.markdown('<div class="email-box"><div style="font-size:.88rem;font-weight:500;color:#0c447c;margin-bottom:4px">📧 Send confirmation to yourself / 寄確認信副本</div><div style="font-size:.75rem;color:#378add;margin-bottom:.5rem">Optional · 可選填</div></div>',unsafe_allow_html=True)
    col_e,col_btn=st.columns([3,1])
    with col_e: email_v=st.text_input("email",placeholder="your@email.com",label_visibility="collapsed",key="email_inp")
    with col_btn:
        if st.button("寄出",use_container_width=True,key="btn_email"):
            email_v=email_v.strip()
            if not email_v or "@" not in email_v: st.error("請輸入有效 Email")
            else:
                subj=urllib.parse.quote(f"CLC Interview Confirmed – {date_en} {tst} TST")
                body=urllib.parse.quote(f"Hi {name},\n\nYour oral interview is confirmed:\nDate: {date_en}\nTaiwan Time: {tst} TST\nYour local time: {local_str}\nJoin 20 min early: {early_str}\n\nGoogle Meet link will be sent by CLC staff.")
                st.markdown(f'<a href="mailto:{email_v}?subject={subj}&body={body}" target="_blank" style="background:#0c447c;color:white;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:.82rem">📧 Open email app</a>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# SCREEN: LANDING
# ══════════════════════════════════════════════════════
def screen_landing():
    st.markdown("#### What would you like to do? / 請選擇操作")
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div style="border:1px solid var(--color-border-tertiary);border-radius:12px;padding:1.25rem 1rem;text-align:center"><div style="font-size:2rem;margin-bottom:8px">📝</div><div style="font-weight:500;font-size:.95rem;margin-bottom:3px">Register / 報名口試</div><div style="font-size:.75rem;color:var(--color-text-secondary)">New registration or change slot</div></div>',unsafe_allow_html=True)
        if st.button("Register →",key="go_reg",use_container_width=True,type="primary"): go("identify")
    with c2:
        st.markdown('<div style="border:1px solid var(--color-border-tertiary);border-radius:12px;padding:1.25rem 1rem;text-align:center"><div style="font-size:2rem;margin-bottom:8px">🔍</div><div style="font-weight:500;font-size:.95rem;margin-bottom:3px">Check registration / 查詢報名紀錄</div><div style="font-size:.75rem;color:var(--color-text-secondary)">View your confirmed slot</div></div>',unsafe_allow_html=True)
        if st.button("Check →",key="go_check",use_container_width=True): go("check")
    st.markdown('<div class="notice" style="margin-top:1.25rem">⏰ <strong>Please join 20 minutes before your scheduled time</strong> for a tech check.<br>請於口試時間<strong>提前 20 分鐘</strong>上線進行設備測試。</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# SCREEN: IDENTIFY
# ══════════════════════════════════════════════════════
def screen_identify():
    if st.button("← Back",key="back_id"): go("landing")
    st.markdown("#### 📝 Register / 報名口試")

    cfg=st.session_state.app_cfg
    settings=get_sys_settings(cfg)

    # Registration status check
    if not settings.get("registration_open",True):
        st.error("🔒 Registration is currently closed. / 報名目前關閉。"); st.stop()
    dl=settings.get("deadline","")
    if dl:
        try:
            if datetime.now()>datetime.strptime(dl,"%Y-%m-%d %H:%M"):
                st.error(f"⏰ Registration closed at {dl}. / 報名已截止。"); st.stop()
            else: st.info(f"⏰ Registration deadline / 報名截止：{dl}")
        except: pass

    st.markdown('<div class="notice">This is the online placement interview registration for new students of the Chinese Language Center.<br><span style="color:var(--color-text-secondary)">此系統供新生報名線上分班口試，完成報名後將以 Email 寄送 Google Meet 連結。</span></div>',unsafe_allow_html=True)

    name=st.text_input("Your full name / 您的全名",value=st.session_state.user_name,
                        placeholder="e.g. Maria Schmidt",
                        help="Use the exact same name each time / 每次請用相同姓名")

    st.markdown("**Your current country / 您目前所在國家**")
    st.caption("We'll calculate your local interview time automatically. / 系統將自動換算您的當地口試時間。")

    saved_country=st.session_state.country_info
    saved_label=saved_country["country"] if saved_country else COUNTRY_LABELS[0]
    saved_idx=COUNTRY_LABELS.index(saved_label) if saved_label in COUNTRY_LABELS else 0

    sel_country=st.selectbox("Country / 國家",options=COUNTRY_LABELS,index=saved_idx,label_visibility="collapsed")
    cinfo=COUNTRY_BY_LABEL[sel_country]

    # Preview
    _ex_local,_,_=tst_to_local("14:10",cinfo["offset"],cinfo["abbr"])
    st.markdown(f'<div style="background:#eaf3de;border-radius:6px;padding:7px 12px;font-size:.8rem;color:#27500a;margin:4px 0">📍 <strong>{sel_country}</strong> · Example: Taiwan 14:10 TST → Your local: <strong>{_ex_local}</strong></div>',unsafe_allow_html=True)

    st.markdown('<div class="notice" style="margin-top:.75rem">⏰ <strong>Please join 20 minutes before your scheduled time.</strong> 請<strong>提前 20 分鐘</strong>上線。</div>',unsafe_allow_html=True)

    if st.button("View available slots → 查看可報名時段",type="primary",use_container_width=True):
        name=name.strip()
        if not name: st.error("Please enter your name / 請輸入姓名"); return
        st.session_state.user_name=name
        st.session_state.country_info=cinfo

        # Load open slots
        raw=db_get("open_slots") or []
        st.session_state.open_slots=raw if isinstance(raw,list) else []

        # Load existing booking
        b=db_get(f"students/{name}")
        st.session_state.my_booking=b if isinstance(b,dict) else None
        go("slots")

# ══════════════════════════════════════════════════════
# SCREEN: SLOTS
# ══════════════════════════════════════════════════════
def screen_slots():
    name=st.session_state.user_name
    cinfo=st.session_state.country_info or COUNTRIES[0]
    booking=st.session_state.my_booking
    cfg=st.session_state.app_cfg
    settings=get_sys_settings(cfg)
    max_per=int(settings.get("max_per_slot",3))
    dates=(cfg or {}).get("dates",[])
    sessions=(cfg or {}).get("sessions",[])

    col_h,col_b=st.columns([4,1])
    with col_h:
        st.markdown(f"#### Hello, **{name}** 👋")
        st.markdown(f'<span class="tz-pill">📍 {cinfo["country"]} · {cinfo["abbr"]}</span>',unsafe_allow_html=True)
    with col_b:
        if st.button("← Back",key="back_slots"): go("landing")

    if booking and isinstance(booking,dict):
        render_booking_card(booking,show_actions=True)

    # Load student counts for capacity
    all_students=db_get("students") or {}

    open_slots=st.session_state.open_slots
    # Filter to user's group
    group=cinfo.get("group","asia")
    relevant=[o for o in open_slots if isinstance(o,dict) and o.get("sess_id")==group]

    if not relevant:
        st.info("📭 No slots available yet. / 目前尚無開放時段，請等候管理員通知後再回來查看。")
        if st.button("↻ Refresh / 重新整理",use_container_width=True):
            raw=db_get("open_slots") or []
            st.session_state.open_slots=raw if isinstance(raw,list) else []
            st.rerun()
        return

    if booking: st.markdown("**Change slot / 更改時段**")
    else:        st.markdown("**Available interview slots / 可報名時段**")
    st.caption(f"Times shown in your local timezone ({cinfo['abbr']}). Taiwan time (TST) shown in smaller text.")

    sess_data=get_session_by_group(cfg,group)
    teacher_slots=(cfg or {}).get("teacher_slots",{})

    for o in relevant:
        di=o["di"]; tst=o["tst"]; sess_id=o.get("sess_id","")
        d=dates[di] if di<len(dates) else {"en":"?","zh":"?","iso":""}
        local_str,early_str,is_prev=tst_to_local(tst,cinfo["offset"],cinfo["abbr"])
        is_sel=(booking and isinstance(booking,dict)
                and booking.get("di")==di and booking.get("tst")==tst)
        booked=get_slot_count(all_students,di,tst)
        is_full=max_per>0 and booked>=max_per and not is_sel
        rem=max(0,max_per-booked) if max_per>0 else None
        ts_key=f"{d.get('iso','')}_{tst}"
        teachers=teacher_slots.get(ts_key,"")
        cap_badge=f'<span style="font-size:.75rem;background:#fcebeb;color:#a32d2d;padding:2px 8px;border-radius:4px">額滿 Full</span>' if is_full else (f'<span style="font-size:.75rem;background:#eaf3de;color:#27500a;padding:2px 8px;border-radius:4px">剩 {rem} 名</span>' if rem is not None and rem<=3 else "")
        prev_note=f'<div style="font-size:.73rem;color:var(--color-text-secondary);margin-top:2px">* Previous calendar day in {cinfo["abbr"]}</div>' if is_prev else ""

        st.markdown(
            f'<div class="slot-opt {"slot-sel" if is_sel else ""} {"slot-full" if is_full else ""}">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">'
            f'<div style="flex:1">'
            # ── LOCAL TIME: primary, large ───────────────────
            f'<div style="font-size:1.25rem;font-weight:700;color:var(--color-text-primary);line-height:1.2">{"✓  " if is_sel else ""}{local_str}</div>'
            f'<div style="font-size:.82rem;color:var(--color-text-secondary);margin-top:2px">⏰ Join early: <strong style="color:var(--color-text-primary)">{early_str}</strong></div>'
            # ── TST: secondary, small ────────────────────────
            f'<div style="font-size:.75rem;color:var(--color-text-secondary);margin-top:6px;padding-top:6px;border-top:0.5px solid var(--color-border-tertiary)">'
            f'📅 {d["en"]} &nbsp;·&nbsp; 🕐 Taiwan: <strong>{tst} TST</strong>'
            f'{"&nbsp;·&nbsp; 👥 "+teachers if teachers else ""}'
            f'</div>'
            f'{prev_note}'
            f'</div>'
            f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">'
            f'<span style="font-size:.75rem;color:var(--color-text-secondary)">{cinfo["abbr"]}</span>'
            f'{cap_badge}'
            f'</div>'
            f'</div></div>',unsafe_allow_html=True)

        if is_full:
            st.button(f"額滿 Full — {d['en']} {tst}",key=f"full_{di}_{tst}",disabled=True,use_container_width=True)
            continue

        lbl=(f"✓ Keep this slot — {d['en']} {tst}" if is_sel else f"Register — {d['en']} {tst} TST")
        if st.button(lbl,key=f"slot_{di}_{tst}_{sess_id}",use_container_width=True,
                     type="primary" if is_sel else "secondary"):
            if not is_sel:
                sess_obj=get_session_by_group(cfg,group)
                b={"name":name,"country":cinfo["country"],"sess_id":sess_id,
                   "sess_name":f"{sess_obj['flag']} {sess_obj['name_zh']}" if sess_obj else sess_id,
                   "di":di,"tst":tst,"date_iso":d.get("iso",""),
                   "local_str":local_str,"early_str":early_str,
                   "tz_abbr":cinfo["abbr"],"tz_offset":cinfo["offset"]}
                db_set(f"students/{name}",b)
                st.session_state.my_booking=b
                st.success("✅ Registered! 報名成功！"); st.balloons(); st.rerun()

    st.divider()
    c1,c2=st.columns(2)
    with c1:
        if st.button("↻ Refresh / 更新",use_container_width=True):
            raw=db_get("open_slots") or []
            st.session_state.open_slots=raw if isinstance(raw,list) else []
            b=db_get(f"students/{name}")
            st.session_state.my_booking=b if isinstance(b,dict) else None
            st.rerun()
    with c2:
        if st.button("← Edit details / 修改",use_container_width=True): go("landing")

# ══════════════════════════════════════════════════════
# SCREEN: CHECK
# ══════════════════════════════════════════════════════
def screen_check():
    if st.button("← Back",key="back_ck"): go("landing")
    st.markdown("#### 🔍 Check my registration / 查詢報名紀錄")
    st.markdown('<div class="notice">Enter the <strong>exact name</strong> you used when registering.<br><span style="color:var(--color-text-secondary)">請輸入報名時填寫的<strong>完全相同姓名</strong>。</span></div>',unsafe_allow_html=True)
    name=st.text_input("Registered name / 報名姓名",placeholder="e.g. Maria Schmidt",key="ck_name")
    if st.button("Look up / 查詢",type="primary",use_container_width=True):
        name=name.strip()
        if not name: st.error("Please enter your name."); return
        b=db_get(f"students/{name}")
        if not b or not isinstance(b,dict):
            st.markdown('<div class="check-card"><div style="font-weight:600;color:#633806;margin-bottom:4px">❌ No registration found / 查無報名紀錄</div><div style="font-size:.85rem;color:#854F0B">Please check the spelling. / 請確認拼寫是否正確。</div></div>',unsafe_allow_html=True)
        else:
            st.session_state.user_name=name
            if b.get("tz_abbr"):
                st.session_state.country_info={"country":b.get("country",""),"abbr":b.get("tz_abbr",""),"offset":b.get("tz_offset",0),"group":b.get("sess_id","asia")}
            render_booking_card(b,show_actions=True)

# ══════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════
SCREENS={"landing":screen_landing,"identify":screen_identify,"slots":screen_slots,"check":screen_check}
SCREENS.get(st.session_state.screen,screen_landing)()
