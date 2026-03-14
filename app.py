import streamlit as st
from datetime import datetime, date, timedelta
import json, calendar

st.set_page_config(page_title="Personal Assistant", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# === Init ===
defs = {"logged_in":False,"user":None,"current_page":"🏠 Dashboard","gemini_api_key":"","claude_api_key":"","ai_engine":"auto","editing_note":None,"theme":"light","transcript":""}
for k,v in defs.items():
    if k not in st.session_state: st.session_state[k] = v

try:
    from db_utils import *
    from ai_engine import *
    DB = True
except: DB = False

# === Theme ===
th = st.session_state.theme
if th == "dark":
    st.markdown('<style>.stApp{background:#1a1a2e;color:#e0e0e0}div[data-testid="stSidebar"]{background:#16213e}.stTextInput>div>div>input,.stTextArea>div>div>textarea{background:#0f3460;color:#e0e0e0;border-color:#1a1a4e}</style>', unsafe_allow_html=True)

st.markdown('<style>@media(max-width:768px){[data-testid="stHorizontalBlock"]>div{flex:100%!important;max-width:100%!important}}</style>', unsafe_allow_html=True)

COLOR_PRESETS = {"blue":"#3b82f6","red":"#ef4444","green":"#22c55e","purple":"#8b5cf6","orange":"#f97316","pink":"#ec4899","teal":"#14b8a6","yellow":"#eab308","gray":"#6b7280","indigo":"#6366f1"}

# === Sidebar ===
with st.sidebar:
    if not st.session_state.logged_in:
        st.markdown("## 🚀 Personal Assistant")
        tab = st.radio("",["Login","Sign Up"], horizontal=True, label_visibility="collapsed")
        if tab == "Login":
            em = st.text_input("Email", key="le")
            pw = st.text_input("Password", type="password", key="lp")
            if st.button("Login", use_container_width=True, type="primary"):
                if DB:
                    u, err = login_user(em, pw)
                    if u: st.session_state.logged_in=True; st.session_state.user=u; st.rerun()
                    else: st.error(err)
                else:
                    st.session_state.logged_in=True; st.session_state.user={"id":"demo","email":em,"display_name":em.split("@")[0]}; st.rerun()
        else:
            nm=st.text_input("Name",key="rn"); em=st.text_input("Email",key="re"); pw=st.text_input("Password",type="password",key="rp"); pw2=st.text_input("Confirm",type="password",key="rp2")
            if st.button("Sign Up", use_container_width=True, type="primary"):
                if pw!=pw2: st.error("Passwords don't match")
                elif DB:
                    u,err=register_user(em,pw,nm)
                    if u: st.success("Done! Please login.")
                    else: st.error(err)
    else:
        user = st.session_state.user
        uid = user["id"]
        dname = user.get("display_name", user.get("email","").split("@")[0])
        st.markdown(f"## 🚀 {dname}'s Assistant")
        st.markdown("---")

        # Quick Capture
        st.markdown("### ⚡ Quick Capture")
        qtext = st.text_input("", placeholder="Type anything...", label_visibility="collapsed", key="qi")
        if qtext and st.button("Save", use_container_width=True, key="qs"):
            if DB:
                c = smart_classify(qtext)
                ct = c.get("type","note")
                if ct=="task": create_task(uid, c.get("title",qtext)); st.success("✅ Task!")
                elif ct=="expense" and c.get("amount"): add_expense(uid, int(c["amount"]), c.get("category","기타"), qtext); st.success(f"💰 {int(c['amount']):,}₩")
                else: create_note(uid, c.get("title",qtext[:50]), qtext); st.success("📝 Note!")

        st.markdown("---")
        pages = ["🏠 Dashboard","📅 Calendar","✅ Tasks","📝 Notes","🎙️ Transcription","✨ AI Content","💹 Economy","📧 Email","🔗 Web Clipper","🍅 Pomodoro","📊 Weekly Report","🔍 Search","⚙️ Settings"]
        st.session_state.current_page = st.radio("", pages, label_visibility="collapsed")
        st.markdown("---")
        tt = st.radio("", ["☀️ Light","🌙 Dark"], horizontal=True, label_visibility="collapsed", index=0 if th=="light" else 1)
        nt = "light" if "Light" in tt else "dark"
        if nt != st.session_state.theme: st.session_state.theme=nt; st.rerun()
        if st.button("Logout", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

if not st.session_state.logged_in:
    st.markdown("# 🚀 Personal Assistant")
    st.markdown("### Notes · Tasks · Calendar · Economy · AI — All in One")
    st.info("👈 Login from sidebar"); st.stop()

user=st.session_state.user; uid=user["id"]; dname=user.get("display_name","User")
page=st.session_state.current_page

# ========== 🏠 DASHBOARD ==========
if page == "🏠 Dashboard":
    st.markdown(f"## 🏠 {dname}님, 좋은 하루 되세요!")
    if DB:
        tasks=get_tasks(uid); todo=[t for t in tasks if t["status"]=="todo"]; doing=[t for t in tasks if t["status"]=="doing"]; done=[t for t in tasks if t["status"]=="done"]
        c1,c2,c3 = st.columns(3)
        c1.metric("📋 To Do", len(todo)); c2.metric("🔄 In Progress", len(doing)); c3.metric("✅ Done", len(done))

        # Reminders
        upcoming = [t for t in todo+doing if t.get("due_date") and t["due_date"] <= str(date.today()+timedelta(days=2))]
        if upcoming:
            st.warning(f"⚠️ {len(upcoming)} tasks due soon!")
            for t in upcoming: st.markdown(f"- {'🔴' if t.get('priority')=='high' else '🟡'} **{t['title']}** — due {t['due_date']}")

        # Habits
        st.markdown("---")
        st.markdown("### 🎯 Habits")
        habits = get_habits(uid)
        if habits:
            logs = get_habit_logs(uid, date.today(), date.today())
            done_ids = {l["habit_id"] for l in logs if l.get("completed")}
            cols = st.columns(min(len(habits),6))
            for i,h in enumerate(habits):
                with cols[i%len(cols)]:
                    checked = st.checkbox(f"{h.get('icon','✅')} {h['name']}", value=h["id"] in done_ids, key=f"h_{h['id']}")
                    if checked != (h["id"] in done_ids): toggle_habit(h["id"],uid)
            ws = date.today()-timedelta(days=date.today().weekday())
            wl = get_habit_logs(uid,ws,date.today())
            wc = len([l for l in wl if l.get("completed")]); wt = len(habits)*(date.today().weekday()+1)
            r = int(wc/wt*100) if wt>0 else 0
            st.progress(r/100, text=f"Weekly: {r}% ({wc}/{wt})")
        else: st.info("Add habits in Settings!")

        # Pinned
        pins = get_pinned(uid)
        if pins:
            st.markdown("---")
            st.markdown("### 📌 Pinned")
            for p in pins: st.markdown(f"{'📝' if p['item_type']=='note' else '🔗'} **{p['title']}**")

        # Recent + Tasks
        st.markdown("---")
        co1,co2 = st.columns(2)
        with co1:
            st.markdown("### 📝 Recent Notes")
            for n in get_notes(uid)[:5]: st.markdown(f"**{n['title']}** · _{n.get('updated_at','')[:10]}_")
        with co2:
            st.markdown("### ✅ Today's Tasks")
            for t in todo[:5]:
                p="🔴" if t.get("priority")=="high" else "🟡" if t.get("priority")=="medium" else "🟢"
                st.markdown(f"{p} {t['title']}")
            if not todo: st.info("All done! 🎉")

        # Daily Review
        st.markdown("---")
        bc1,bc2 = st.columns(2)
        if bc1.button("☀️ Morning Briefing", type="primary", use_container_width=True):
            with st.spinner("..."):
                st.markdown(get_ai(f"오늘:{datetime.now().strftime('%Y-%m-%d %A')}. 할일:{len(todo)}, 진행:{len(doing)}.\n간결한 아침 브리핑: 1)오늘 집중 2)팁 3)동기부여", st.session_state.ai_engine, "summary"))
        if bc2.button("🌙 Daily Review", use_container_width=True):
            with st.spinner("..."):
                today_notes = [n for n in get_notes(uid) if n.get("updated_at","")[:10]==str(date.today())]
                st.markdown(get_ai(f"오늘 작성 노트: {len(today_notes)}개, 완료 태스크: {len(done)}개.\n오늘의 회고: 1)한일 2)배운점 3)내일계획", st.session_state.ai_engine, "summary"))


# ========== 📅 CALENDAR ==========
elif page == "📅 Calendar":
    st.markdown("## 📅 Calendar")
    view = st.radio("", ["Monthly","Weekly","Daily","List"], horizontal=True, label_visibility="collapsed")

    with st.expander("➕ New Event"):
        ec1,ec2 = st.columns(2)
        et=ec1.text_input("Title",key="et"); ed=ec1.date_input("Date",key="ed")
        etime=ec2.time_input("Time",key="etm"); edesc=ec2.text_input("Memo",key="edesc")
        cl = st.selectbox("Color", list(COLOR_PRESETS.keys()), format_func=lambda x: f"{'🔵🔴🟢🟣🟠🩷🟦🟡⚫🟤'[list(COLOR_PRESETS.keys()).index(x)]} {x}")
        if st.button("Add", type="primary", key="ae"):
            if et and DB: create_event(uid, et, datetime.combine(ed,etime), desc=edesc, color_label=cl); st.success("Added!"); st.rerun()

    if DB:
        today=date.today()
        if view=="Monthly":
            ms=today.replace(day=1)
            me=ms.replace(month=ms.month%12+1,year=ms.year+(1 if ms.month==12 else 0),day=1)-timedelta(days=1)
            evs=get_events(uid,datetime.combine(ms,datetime.min.time()),datetime.combine(me,datetime.max.time()))
            st.markdown(f"### {today.strftime('%Y년 %m월')}")
            hc=st.columns(7)
            for i,d in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]): hc[i].markdown(f"**{d}**")
            for week in calendar.monthcalendar(today.year,today.month):
                cols=st.columns(7)
                for i,day in enumerate(week):
                    if day==0: cols[i].markdown("")
                    else:
                        des=[e for e in evs if e.get("start_time","")[:10]==f"{today.year}-{today.month:02d}-{day:02d}"]
                        mk = f"👉**{day}**" if day==today.day else (f"**{day}**📌" if des else str(day))
                        cols[i].markdown(mk)
                        for e in des:
                            c=COLOR_PRESETS.get(e.get("color_label","blue"),"#3b82f6")
                            cols[i].markdown(f'<span style="color:{c};font-size:11px">⏰{e.get("start_time","")[11:16]} {e["title"][:8]}</span>',unsafe_allow_html=True)
        elif view=="Weekly":
            ws=today-timedelta(days=today.weekday())
            evs=get_events(uid,datetime.combine(ws,datetime.min.time()),datetime.combine(ws+timedelta(6),datetime.max.time()))
            for d in range(7):
                day=ws+timedelta(d); dn=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][d]
                des=[e for e in evs if e.get("start_time","")[:10]==str(day)]
                st.markdown(f"{'👉 ' if day==today else ''}**{day.strftime('%m/%d')} ({dn})**")
                for e in des:
                    c1,c2=st.columns([5,1]); c1.markdown(f"　⏰ {e.get('start_time','')[11:16]} - {e['title']}");
                    if c2.button("🗑️",key=f"de_{e['id']}"): delete_event(e["id"]); st.rerun()
                if not des: st.caption("　—")
        elif view=="Daily":
            sd=st.date_input("",value=today,label_visibility="collapsed")
            evs=get_events(uid,datetime.combine(sd,datetime.min.time()),datetime.combine(sd,datetime.max.time()))
            st.markdown(f"### {sd.strftime('%Y-%m-%d (%A)')}")
            for e in evs:
                c1,c2=st.columns([5,1]); c1.markdown(f"⏰ **{e.get('start_time','')[11:16]}** — {e['title']}");
                if c2.button("🗑️",key=f"de_{e['id']}"): delete_event(e["id"]); st.rerun()
            if not evs: st.info("No events")
        else:
            evs=get_events(uid,datetime.combine(today,datetime.min.time()),datetime.combine(today+timedelta(30),datetime.max.time()))
            for e in evs: st.markdown(f"📅 {e.get('start_time','')[:10]} ⏰{e.get('start_time','')[11:16]} — {e['title']}")
            if not evs: st.info("No upcoming events")


# ========== ✅ TASKS ==========
elif page == "✅ Tasks":
    st.markdown("## ✅ Tasks")
    tab_kanban, tab_project = st.tabs(["📋 Kanban", "📁 Projects"])

    with tab_kanban:
        with st.expander("➕ New Task"):
            tc1,tc2=st.columns(2)
            tt=tc1.text_input("Task",key="tt"); tp=tc1.text_input("Project",key="tp")
            tpr=tc2.selectbox("Priority",["high","medium","low"],format_func=lambda x:{"high":"🔴High","medium":"🟡Medium","low":"🟢Low"}[x],index=1)
            tdu=tc2.date_input("Due",value=None,key="td")
            if st.button("Add",type="primary",key="at"):
                if tt and DB: create_task(uid,tt,"","todo",tpr,tdu,tp or None); st.success("✅"); st.rerun()

        if DB:
            at=get_tasks(uid)
            projs=list(set([t.get("project","") for t in at if t.get("project")]))
            if projs:
                pf=st.selectbox("Filter",["All"]+projs,key="pf")
                if pf!="All": at=[t for t in at if t.get("project")==pf]
            c1,c2,c3=st.columns(3)
            for col,s,lb in [(c1,"todo","📋 To Do"),(c2,"doing","🔄 Doing"),(c3,"done","✅ Done")]:
                with col:
                    st.markdown(f"### {lb}")
                    for t in [t for t in at if t["status"]==s]:
                        p="🔴" if t.get("priority")=="high" else "🟡" if t.get("priority")=="medium" else "🟢"
                        st.markdown(f"{p} **{t['title']}**")
                        if t.get("project"): st.caption(f"📁{t['project']}")
                        if t.get("due_date"): st.caption(f"📅{t['due_date']}")
                        bc=st.columns(3)
                        if s=="todo":
                            if bc[0].button("▶️",key=f"s_{t['id']}"): update_task(t["id"],status="doing"); st.rerun()
                            if bc[1].button("✅",key=f"d_{t['id']}"): update_task(t["id"],status="done"); st.rerun()
                            if bc[2].button("🗑️",key=f"x_{t['id']}"): delete_task(t["id"]); st.rerun()
                        elif s=="doing":
                            if bc[0].button("◀️",key=f"b_{t['id']}"): update_task(t["id"],status="todo"); st.rerun()
                            if bc[1].button("✅",key=f"d_{t['id']}"): update_task(t["id"],status="done"); st.rerun()
                        else:
                            if bc[0].button("🗑️",key=f"x_{t['id']}"): delete_task(t["id"]); st.rerun()
                        st.markdown("---")

    with tab_project:
        if DB:
            at=get_tasks(uid)
            projs=list(set([t.get("project","") for t in at if t.get("project")]))
            if projs:
                for proj in projs:
                    pt=[t for t in at if t.get("project")==proj]
                    td=len([t for t in pt if t["status"]=="done"]); tt_cnt=len(pt)
                    pct=int(td/tt_cnt*100) if tt_cnt>0 else 0
                    st.markdown(f"### 📁 {proj}")
                    st.progress(pct/100, text=f"{pct}% complete ({td}/{tt_cnt})")
                    for t in pt:
                        s={"todo":"⬜","doing":"🔄","done":"✅"}.get(t["status"],"⬜")
                        st.markdown(f"　{s} {t['title']}")
                    st.markdown("---")
            else: st.info("No projects. Add project name when creating tasks.")


# ========== 📝 NOTES ==========
elif page == "📝 Notes":
    st.markdown("## 📝 Notes")
    nc1,nc2,nc3,nc4=st.columns([2,1,1,1])
    sq=nc1.text_input("🔍",placeholder="Search...",label_visibility="collapsed")
    nf=nc2.selectbox("",["All","Notes","Meetings","Daily","Ideas","Projects","Favorites"],label_visibility="collapsed")
    if nc3.button("📅 Daily",use_container_width=True):
        if DB: st.session_state.editing_note=get_daily_note(uid); st.rerun()
    if nc4.button("➕ New",type="primary",use_container_width=True):
        if DB: st.session_state.editing_note=create_note(uid,"New Note",""); st.rerun()

    # Folder nav
    if DB:
        with st.expander("📁 Folders"):
            folders=get_folders(uid)
            fc1,fc2=st.columns([3,1])
            fn=fc1.text_input("New folder",key="fn")
            if fc2.button("Create",key="cf"):
                if fn: create_folder(uid,fn); st.rerun()
            for f in folders:
                if st.button(f"📁 {f['name']}",key=f"fld_{f['id']}"):
                    st.session_state["folder_filter"]=f["id"]; st.rerun()
            if folders and st.button("Show All"):
                st.session_state.pop("folder_filter",None); st.rerun()

    if st.session_state.editing_note:
        note=st.session_state.editing_note
        new_title=st.text_input("Title",value=note.get("title",""),key="nt")

        # Type selection - auto loads template
        type_map={"note":"📝 Note","meeting":"📋 Meeting","daily":"📅 Daily","idea":"💡 Idea","project":"📁 Project"}
        nt_sel=st.selectbox("Type",list(type_map.keys()),format_func=lambda x:type_map[x],index=list(type_map.keys()).index(note.get("note_type","note")) if note.get("note_type","note") in type_map else 0)

        # Built-in templates per type
        builtin={"meeting":"## 📋 Meeting\n- Date: \n- Attendees: \n\n## Agenda\n1. \n\n## Discussion\n\n## Decisions\n\n## Action Items\n- [ ] \n\n## Next Steps\n- ",
                 "idea":"## 💡 Idea\n\n### Core Concept\n\n### Background\n\n### Expected Impact\n\n### Action Plan\n1. ",
                 "project":"## 📁 Project\n- Start: \n- Deadline: \n- Status: \n\n## Goals\n1. \n\n## Tasks\n- [ ] \n\n## Notes\n\n## Resources\n- ",
                 "daily":f"# {date.today().strftime('%Y-%m-%d %A')}\n\n## Notes\n\n\n## To Do\n- [ ] \n\n## Ideas\n\n"}

        # Custom templates
        if DB:
            tmps=get_templates(uid)
            if tmps:
                st.markdown("**Templates:**")
                tc=st.columns(min(len(tmps)+1,5))
                for i,t in enumerate(tmps):
                    if tc[i].button(f"{t.get('icon','📄')} {t['name']}",key=f"tmp_{t['id']}"):
                        st.session_state["_tmpl"]=t["content"]
                        st.rerun()

        # Determine content
        default_content = st.session_state.pop("_tmpl", None)
        if default_content is None:
            if not note.get("content") and nt_sel in builtin:
                default_content = builtin[nt_sel]
            else:
                default_content = note.get("content","")

        content=st.text_area("",value=default_content,height=400,label_visibility="collapsed",key="nc")

        # File upload
        uploaded=st.file_uploader("📎 Upload file (txt, md, docx, xlsx, csv, png, jpg, pdf)", type=["txt","md","docx","xlsx","csv","png","jpg","jpeg","pdf"], key="nf_upload")
        if uploaded:
            if uploaded.type.startswith("image"):
                st.image(uploaded)
                if st.button("🔍 OCR - Read text from image", key="ocr_btn"):
                    with st.spinner("Reading..."):
                        ocr_text = ocr_image(uploaded.read(), uploaded.type)
                        st.markdown("**Extracted text:**")
                        st.markdown(ocr_text)
                        st.session_state["_tmpl"] = content + "\n\n---\n## Extracted from image\n" + ocr_text
                        st.rerun()
            else:
                if st.button("📥 Import to note", key="import_btn"):
                    with st.spinner("Converting..."):
                        imported = file_to_markdown(uploaded)
                        st.session_state["_tmpl"] = content + "\n\n---\n## Imported\n" + imported
                        st.rerun()

        # Tags (below content)
        tag_input=st.text_input("🏷️ Tags",placeholder="#work, #project-a, #idea",key="ntags")

        # AI tools
        st.markdown("**AI Tools:**")
        ac=st.columns(4)
        if ac[0].button("🤖 Summary",use_container_width=True):
            if content:
                with st.spinner("..."): st.markdown(get_ai(f"핵심 3-5줄 요약:\n\n{content}",st.session_state.ai_engine,"summary"))
        if ac[1].button("🔗 Related",use_container_width=True):
            if DB and content:
                with st.spinner("..."):
                    for s in suggest_related(content,get_notes(uid)):
                        m=[n for n in get_notes(uid) if n["id"]==s]
                        if m: st.markdown(f"- 📝 {m[0]['title']}")
        if ac[2].button("✨ Expand",use_container_width=True):
            if content:
                with st.spinner("..."): st.markdown(get_ai(f"보완/확장:\n\n{content}",st.session_state.ai_engine,"content"))
        if ac[3].button("📄→MD",use_container_width=True,help="Convert to clean Markdown"):
            if content:
                with st.spinner("..."): st.markdown(get_ai(f"다음 내용을 깔끔한 마크다운으로 정리해주세요:\n\n{content}",st.session_state.ai_engine,"content"))

        # Save / Close / Delete / Export
        sc=st.columns([2,1,1,1])
        if sc[0].button("💾 Save",type="primary",use_container_width=True):
            if DB and note.get("id")!="demo":
                update_note(note["id"],title=new_title,content=content,note_type=nt_sel)
                if tag_input:
                    for tn in [t.strip().replace("#","") for t in tag_input.split(",") if t.strip()]:
                        tg=add_tag(uid,tn)
                        if tg: tag_note(note["id"],tg["id"])
                st.success("Saved!")
        if sc[1].button("Close",use_container_width=True): st.session_state.editing_note=None; st.rerun()
        if sc[2].button("🗑️",use_container_width=True):
            if DB: delete_note(note["id"])
            st.session_state.editing_note=None; st.rerun()
        if sc[3].button("📥 Export",use_container_width=True):
            st.download_button("Download .md", f"# {new_title}\n\n{content}", file_name=f"{new_title}.md", mime="text/markdown")
    else:
        if DB:
            fm={"All":None,"Notes":"note","Meetings":"meeting","Daily":"daily","Ideas":"idea","Projects":"project","Favorites":None}
            fid=st.session_state.get("folder_filter")
            notes=get_notes(uid,note_type=fm.get(nf),search=sq or None,fav_only=nf=="Favorites",folder_id=fid)
            for n in notes:
                icon={"meeting":"📋","daily":"📅","idea":"💡","project":"📁"}.get(n.get("note_type"),"📝")
                fav="⭐" if n.get("is_favorite") else ""
                cn,ca=st.columns([5,1])
                cn.markdown(f"{fav}{icon} **{n['title']}** · _{n.get('updated_at','')[:10]}_")
                if n.get("content"): cn.caption(n["content"][:120])
                if ca.button("Open",key=f"o_{n['id']}"): st.session_state.editing_note=n; st.rerun()
            if not notes: st.info("No notes found.")

        # Graph view
        st.markdown("---")
        if st.checkbox("🕸️ Show Note Graph"):
            if DB:
                all_n=get_notes(uid)
                all_l=get_all_links(uid)
                if all_n:
                    st.markdown("### Note Connections")
                    nmap={n["id"]:n["title"] for n in all_n}
                    for l in all_l:
                        s=nmap.get(l["source_id"],"?"); t=nmap.get(l["target_id"],"?")
                        st.markdown(f"📝 {s} ↔️ 📝 {t}")
                    if not all_l: st.info("No links yet. Use [[note title]] in content to create links.")

        # Backup/Export
        if st.checkbox("📦 Backup / Export All"):
            if DB:
                md = export_all_notes_md(uid)
                st.download_button("📥 Download all notes (.md)", md, "all_notes_backup.md", "text/markdown")

        # Folder summary
        if st.checkbox("📊 Folder Summary (AI)"):
            period = st.selectbox("Period", ["This week", "This month", "Last 7 days", "Last 30 days"])
            if st.button("Generate Summary", key="folder_sum"):
                if DB:
                    with st.spinner("Analyzing..."):
                        if "week" in period.lower():
                            start = date.today()-timedelta(days=date.today().weekday())
                        elif "month" in period.lower():
                            start = date.today().replace(day=1)
                        elif "7" in period:
                            start = date.today()-timedelta(days=7)
                        else:
                            start = date.today()-timedelta(days=30)
                        period_notes = [n for n in get_notes(uid) if n.get("updated_at","")[:10] >= str(start)]
                        st.markdown(folder_summary(period_notes, period))


# ========== 🎙️ TRANSCRIPTION ==========
elif page == "🎙️ Transcription":
    st.markdown("## 🎙️ Transcription & Meeting Notes")
    tab1,tab2=st.tabs(["🎙️ Transcribe","📖 Dictionary"])
    with tab1:
        audio=st.file_uploader("Upload audio",type=["mp3","wav","m4a","ogg","webm"])
        if audio:
            st.audio(audio)
            if st.button("🎙️ Transcribe",type="primary"):
                with st.spinner("..."): t=transcribe(audio); t=apply_terms(uid,t) if DB else t; st.session_state.transcript=t
        st.markdown("---")
        manual=st.text_area("Or paste transcript here",height=200,key="mt")
        if manual:
            corrected=apply_terms(uid,manual) if DB else manual
            if corrected!=manual: st.info("✅ Terms auto-corrected")
            st.session_state.transcript=corrected or manual

        if st.session_state.get("transcript"):
            st.text_area("Transcript",value=st.session_state.transcript,height=200,key="tv",disabled=True)
            st.markdown("**Save as:**")
            save_type=st.selectbox("Format",["📋 Meeting Notes","📊 Summary Only","✅ Action Items Only","📝 Raw Note"])
            if st.button("💾 Process & Save to Notes",type="primary"):
                with st.spinner("Processing..."):
                    if "Meeting" in save_type:
                        result=summarize_meeting(st.session_state.transcript)
                        if DB: create_note(uid,f"📋 Meeting {date.today()}",result,"meeting"); st.success("Saved!")
                    elif "Summary" in save_type:
                        result=get_ai(f"5줄 핵심 요약:\n\n{st.session_state.transcript}",st.session_state.ai_engine,"summary")
                        if DB: create_note(uid,f"Summary {date.today()}",result,"note"); st.success("Saved!")
                    elif "Action" in save_type:
                        result=get_ai(f"액션아이템 체크박스로:\n\n{st.session_state.transcript}",st.session_state.ai_engine,"analysis")
                        if DB: create_note(uid,f"Actions {date.today()}",result,"note"); st.success("Saved!")
                    else:
                        if DB: create_note(uid,f"Transcript {date.today()}",st.session_state.transcript,"note"); st.success("Saved!")
                    st.markdown(result if "Raw" not in save_type else "")
    with tab2:
        tc1,tc2=st.columns(2)
        w=tc1.text_input("Wrong",placeholder="케이피아이"); c=tc2.text_input("Correct",placeholder="KPI")
        if st.button("Add",type="primary",key="at2"):
            if w and c and DB: add_term(uid,w,c); st.success(f"'{w}'→'{c}'"); st.rerun()
        if DB:
            for w,c in get_terms(uid).items(): st.markdown(f"~~{w}~~ → **{c}**")


# ========== ✨ AI CONTENT ==========
elif page == "✨ AI Content":
    st.markdown("## ✨ AI Content")
    ct=st.selectbox("Type",["Blog","Instagram","Twitter Thread","Full Package"])
    topic=st.text_area("📌 Topic",placeholder="e.g. 5 ways AI boosts productivity")
    kw=st.text_input("🔑 Keywords")
    img=st.file_uploader("📷 Image (optional)",type=["png","jpg","jpeg"],key="ci")
    eng=st.radio("Engine",["Auto","Gemini","Claude"],horizontal=True)

    if st.button("✨ Generate",type="primary",use_container_width=True):
        if topic:
            with st.spinner("Generating..."):
                if img:
                    img_data=img.read()
                    result=analyze_image_for_content(img_data,img.type,ct)
                    st.markdown(result)
                else:
                    em={"Auto":"auto","Gemini":"gemini","Claude":"claude"}
                    prompts={"Blog":f"주제:{topic}\n키워드:{kw}\n\n블로그: 제목3개, SEO메타, 본문1500-2000자, 해시태그10개",
                             "Instagram":f"주제:{topic}\n키워드:{kw}\n\n인스타: 훅, 본문2000자이내, 해시태그30개",
                             "Twitter Thread":f"주제:{topic}\n키워드:{kw}\n\n트위터 5-8개, 각280자"}
                    if ct=="Full Package":
                        for t in ["Blog","Instagram","Twitter Thread"]:
                            st.markdown(f"### {t}"); st.markdown(get_ai(prompts[t],em[eng],"content")); st.markdown("---")
                    else: result=get_ai(prompts[ct],em[eng],"content"); st.markdown(result)

                # Save & copy options
                st.markdown("---")
                sc1,sc2=st.columns(2)
                if sc1.button("📝 Save to Notes",key="sc_note"):
                    if DB: create_note(uid,f"[Content] {topic[:30]}",result if 'result' in dir() else "","note"); st.success("Saved!")
                sc2.download_button("📥 Download",result if 'result' in dir() else "",f"content_{ct}.txt","text/plain")


# ========== 💹 ECONOMY ==========
elif page == "💹 Economy":
    st.markdown("## 💹 Economy")
    tabs=st.tabs(["📊 Dashboard","💰 Finance","📈 Market","🤖 Analysis"])

    with tabs[0]:
        if DB:
            cm=datetime.now().strftime("%Y-%m")
            exps=get_expenses(uid,cm); inc=get_income(uid,cm); loans=get_loans(uid)
            te=sum(e.get("amount",0) for e in exps); ti=sum(i.get("amount",0) for i in inc); tl=sum(l.get("remaining_amount",0) for l in loans)
            c1,c2,c3,c4=st.columns(4)
            c1.metric("💵 Income",f"{ti:,}₩"); c2.metric("💸 Expenses",f"{te:,}₩"); c3.metric("💰 Balance",f"{ti-te:,}₩"); c4.metric("🏦 Debt",f"{tl:,}₩")
            if exps:
                cats={}
                for e in exps: cats[e.get("category","기타")]=cats.get(e.get("category","기타"),0)+e.get("amount",0)
                st.markdown("### Category Breakdown")
                for cat,amt in sorted(cats.items(),key=lambda x:-x[1]):
                    st.progress(min(amt/te,1) if te>0 else 0,text=f"{cat}: {amt:,}₩ ({amt/te*100:.0f}%)")

    with tabs[1]:
        sub=st.radio("",["Expenses","Income","Loans","Upload"],horizontal=True,label_visibility="collapsed")
        if sub=="Expenses":
            fc1,fc2,fc3=st.columns(3)
            ea=fc1.number_input("₩",min_value=0,step=1000,key="ea"); ecat=fc2.selectbox("Cat",["식비","교통비","쇼핑","생활비","의료","교육","여가","카페","구독","기타"]); edt=fc3.date_input("",key="edt",label_visibility="collapsed")
            edsc=st.text_input("Memo",key="edsc")
            if st.button("Record",type="primary",key="re"):
                if ea>0 and DB: add_expense(uid,ea,ecat,edsc,edt); st.success("✅"); st.rerun()
            if DB:
                for e in get_expenses(uid,datetime.now().strftime("%Y-%m"))[:20]:
                    st.markdown(f"- {e.get('expense_date','')} | {e.get('category','')} | {e.get('amount',0):,}₩ | {e.get('description','')}")
        elif sub=="Income":
            ic1,ic2=st.columns(2)
            ia=ic1.number_input("₩",min_value=0,step=100000,key="ia"); isrc=ic2.text_input("Source",key="isrc")
            if st.button("Record",type="primary",key="ri"):
                if ia>0 and DB: add_income(uid,ia,isrc); st.success("✅"); st.rerun()
            if DB:
                for i in get_income(uid,datetime.now().strftime("%Y-%m")): st.markdown(f"- {i.get('income_date','')} | {i.get('source','')} | {i.get('amount',0):,}₩")
        elif sub=="Loans":
            lc1,lc2=st.columns(2)
            ln=lc1.text_input("Name"); lt=lc2.number_input("Total₩",min_value=0,step=1000000,key="lt")
            lr=lc1.number_input("Remaining₩",min_value=0,step=1000000,key="lr"); li=lc2.number_input("Rate%",min_value=0.0,step=0.1,key="li")
            if st.button("Add",type="primary",key="al"):
                if ln and DB: add_loan(uid,ln,lt,lr,li); st.success("✅"); st.rerun()
            if DB:
                for l in get_loans(uid):
                    pct=(1-l.get("remaining_amount",0)/max(l.get("total_amount",1),1))*100
                    st.progress(pct/100,text=f"{l['name']}: {l.get('remaining_amount',0):,}₩ ({pct:.0f}% paid)")
        elif sub=="Upload":
            uploaded=st.file_uploader("Excel/CSV/Text",type=["csv","xlsx","txt"],key="eu")
            text_in=st.text_area("Or paste data",height=100,key="eti")
            if st.button("🤖 AI Import",type="primary"):
                data=""
                if uploaded:
                    if uploaded.name.endswith(".csv"):
                        import pandas as pd; data=pd.read_csv(uploaded).to_string()
                    elif uploaded.name.endswith(".xlsx"):
                        import pandas as pd; data=pd.read_excel(uploaded).to_string()
                    else: data=uploaded.read().decode("utf-8")
                elif text_in: data=text_in
                if data:
                    with st.spinner("..."):
                        items=classify_expenses(data)
                        if items:
                            for c in items: st.markdown(f"- {c.get('date','')} | {c.get('category','')} | {c.get('amount',0):,}₩")
                            if st.button("✅ Import All",key="imp"):
                                if DB: bulk_add_expenses(uid,items); st.success(f"{len(items)} imported!")

    with tabs[2]:
        if st.button("🔄 Latest Market Info",type="primary"):
            with st.spinner("..."): st.markdown(get_ai("US(S&P500,NASDAQ,DOW)+KR(KOSPI,KOSDAQ)+환율(USD/KRW,EUR/KRW,JPY/KRW)+경제뉴스5개. 간결하게.",st.session_state.ai_engine,"analysis"))
        st.markdown("---")
        st.markdown("### ⭐ Watchlist")
        wc1,wc2,wc3=st.columns([2,2,1])
        ws=wc1.text_input("Symbol",key="ws"); wn=wc2.text_input("Name",key="wn"); wm=wc3.selectbox("",["US","KR"],key="wm",label_visibility="collapsed")
        if st.button("Add",key="aw"):
            if ws and wn and DB: add_watch(uid,ws,wn,wm); st.rerun()
        if DB:
            for w in get_watchlist(uid):
                c1,c2=st.columns([5,1]); c1.markdown(f"{'🇺🇸' if w.get('market')=='US' else '🇰🇷'} **{w['name']}** ({w['symbol']})")
                if c2.button("🗑️",key=f"dw_{w['id']}"): del_watch(w["id"]); st.rerun()

    with tabs[3]:
        if st.button("🤖 Full Analysis",type="primary"):
            if DB:
                cm=datetime.now().strftime("%Y-%m")
                with st.spinner("..."): st.markdown(analyze_finances(get_expenses(uid,cm),get_income(uid,cm),get_loans(uid)))


# ========== 📧 EMAIL ==========
elif page == "📧 Email":
    st.markdown("## 📧 Email")
    to=st.text_input("To"); subj=st.text_input("Subject"); body=st.text_area("Body",height=200)
    with st.expander("⚙️ Gmail Settings"):
        ga=st.text_input("Gmail",key="ga"); gp=st.text_input("App Password",type="password",key="gp")
    if st.button("📨 Send",type="primary"):
        if all([to,subj,body,ga,gp]):
            ok,msg=send_gmail(to,subj,body,ga,gp)
            st.success(msg) if ok else st.error(msg)

# ========== 🔗 WEB CLIPPER ==========
elif page == "🔗 Web Clipper":
    st.markdown("## 🔗 Web Clipper")
    url=st.text_input("URL",placeholder="https://...")
    if st.button("📥 Clip & Summarize",type="primary"):
        if url:
            with st.spinner("..."):
                s=web_summary(url); st.markdown(s)
                if DB: create_note(uid,f"🔗 {url[:50]}",f"URL: {url}\n\n---\n{s}","note"); st.success("Saved!")
    if DB:
        clips=[n for n in get_notes(uid) if n.get("content","").startswith("URL:")]
        if clips:
            st.markdown("### 📚 Saved")
            for c in clips[:10]: st.markdown(f"🔗 **{c['title']}** · _{c.get('updated_at','')[:10]}_")

# ========== 🍅 POMODORO ==========
elif page == "🍅 Pomodoro":
    st.markdown("## 🍅 Pomodoro")
    tn=st.text_input("Working on:",key="pt")
    st.markdown('<div style="text-align:center;padding:2rem"><div style="font-size:4rem;font-weight:bold">25:00</div><p>Focus 25 min → Break 5 min</p></div>',unsafe_allow_html=True)
    c1,c2,c3=st.columns(3)
    if c1.button("▶️ Start",type="primary",use_container_width=True): st.info("⏱️ Focus mode! Use phone timer alongside.")
    if c2.button("☕ Break",use_container_width=True): st.info("☕ 5 min break!")
    if c3.button("✅ Complete",use_container_width=True):
        if DB: log_pomo(uid,25,tn); st.success("🍅 Done!"); st.balloons()
    if DB:
        logs=get_pomo_logs(uid,7)
        if logs: st.markdown(f"### This week: {len(logs)} 🍅 ({len(logs)*25}min)")

# ========== 📊 WEEKLY REPORT ==========
elif page == "📊 Weekly Report":
    st.markdown("## 📊 Weekly Report")
    period=st.selectbox("Period",["This week","Last 7 days","Last 14 days","This month"])
    if period=="This week": start=date.today()-timedelta(days=date.today().weekday())
    elif "7" in period: start=date.today()-timedelta(7)
    elif "14" in period: start=date.today()-timedelta(14)
    else: start=date.today().replace(day=1)

    if st.button("📊 Generate Report",type="primary"):
        if DB:
            with st.spinner("Generating report..."):
                notes=[n for n in get_notes(uid) if n.get("updated_at","")[:10]>=str(start)]
                tasks=get_tasks(uid)
                exps=[e for e in get_expenses(uid,datetime.now().strftime("%Y-%m"))]
                report=weekly_report(notes,tasks,exps)
                st.markdown(report)
                sc1,sc2=st.columns(2)
                if sc1.button("📝 Save to Notes",key="sr"):
                    create_note(uid,f"📊 Report {date.today()}",report,"note")
                    st.success("Saved!")
                sc2.download_button("📥 Download",report,f"report_{date.today()}.md","text/markdown")

# ========== 🔍 SEARCH ==========
elif page == "🔍 Search":
    st.markdown("## 🔍 Smart Search")
    kw=st.text_input("",placeholder="Search notes, tasks, events...",label_visibility="collapsed")
    if kw and DB:
        results=search_all(uid,kw)
        if results:
            st.markdown(f"**{len(results)} results:**")
            for r in results:
                icon={"note":"📝","task":"✅","event":"📅"}.get(r["type"],"📄")
                st.markdown(f"{icon} **{r['title']}** · {r['type']} · {r.get('date','')}")
        else: st.info("No results.")

# ========== ⚙️ SETTINGS ==========
elif page == "⚙️ Settings":
    st.markdown("## ⚙️ Settings")
    st.markdown("### 👤 Profile")
    nn=st.text_input("Display Name",value=dname,key="sn")
    if st.button("Update"):
        if DB: update_profile(uid,display_name=nn); st.session_state.user["display_name"]=nn; st.success("Updated!"); st.rerun()

    st.markdown("---")
    st.markdown("### 🔑 API Keys")
    gk=st.text_input("Gemini",value=st.session_state.gemini_api_key,type="password",key="sgk")
    ck=st.text_input("Claude (optional)",value=st.session_state.claude_api_key,type="password",key="sck")
    if st.button("Save Keys",type="primary"):
        st.session_state.gemini_api_key=gk; st.session_state.claude_api_key=ck; st.success("Saved!")

    st.markdown("---")
    st.markdown("### 🤖 AI Engine")
    st.session_state.ai_engine=st.radio("",["auto","gemini","claude"],format_func=lambda x:{"auto":"🔄 Auto","gemini":"Gemini","claude":"Claude"}[x],horizontal=True,label_visibility="collapsed")

    st.markdown("---")
    st.markdown("### 🎯 Habits")
    hc1,hc2=st.columns([3,1])
    hn=hc1.text_input("New habit"); hi=hc2.text_input("Icon",value="✅",key="hi")
    if st.button("Add",key="ah"):
        if hn and DB: create_habit(uid,hn,hi); st.rerun()
    if DB:
        for h in get_habits(uid):
            c1,c2=st.columns([5,1]); c1.markdown(f"{h.get('icon','✅')} {h['name']}")
            if c2.button("🗑️",key=f"dh_{h['id']}"): delete_habit(h["id"]); st.rerun()

    st.markdown("---")
    st.markdown("### 📄 Custom Templates")
    tn=st.text_input("Template name",key="tn"); ti=st.text_input("Icon",value="📄",key="ti")
    tc=st.text_area("Template content (Markdown)",height=150,key="tc")
    if st.button("Save Template",key="st"):
        if tn and tc and DB: create_template(uid,tn,tc,icon=ti); st.success("Saved!"); st.rerun()
    if DB:
        for t in get_templates(uid):
            c1,c2=st.columns([5,1]); c1.markdown(f"{t.get('icon','📄')} {t['name']}")
            if c2.button("🗑️",key=f"dt_{t['id']}"): delete_template(t["id"]); st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Stats")
    if DB:
        c1,c2,c3=st.columns(3)
        c1.metric("Notes",len(get_notes(uid))); c2.metric("Tasks",len(get_tasks(uid))); c3.metric("DB","✅")

st.markdown("---")
st.caption(f"🚀 {dname}'s Personal Assistant v3.0")
