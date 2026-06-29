"""
The management dashboard — one polished page served by the backend, for BOTH:
  • Clinics: sign in with their Business ID + api_key → see bookings, edit settings,
    grab their widget link.
  • Admin (you): sign in with just the admin key → list all clinics, open any one,
    and onboard new clinics (which generates their api_key).

It's only the app shell; every data call sends the key in the X-API-Key header,
so the backend (not the page) enforces who can see what.
"""

DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard · Agent Platform</title>
<style>
  :root{ --a1:#6366f1; --a2:#8b5cf6; --a3:#ec4899; --ink:#1b1830; --muted:#7c7896; --line:#ece9f5; --bg:#f4f3fb; --card:#fff; }
  *{box-sizing:border-box;}
  body{margin:0; font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    color:var(--ink); background:linear-gradient(135deg,#6366f1 0%, #8b5cf6 52%, #ec4899 100%); background-attachment:fixed; min-height:100vh;}
  .hidden{display:none !important;}
  button{font:inherit; cursor:pointer; border:none; border-radius:10px; padding:10px 16px; font-weight:600;}
  .btn{background:linear-gradient(135deg,var(--a1),var(--a2)); color:#fff; box-shadow:0 6px 16px rgba(99,102,241,.32);}
  .btn:active{transform:translateY(1px);}
  .btn.ghost{background:#fff; color:var(--a2); border:1px solid var(--line); box-shadow:none;}
  input,textarea,select{font:inherit; width:100%; padding:10px 12px; border:1px solid #d7dee4; border-radius:10px; outline:none; background:#fff;}
  input:focus,textarea:focus,select:focus{border-color:var(--a2); box-shadow:0 0 0 4px rgba(139,92,246,.16);}
  label{display:block; font-size:13px; font-weight:600; color:var(--muted); margin:12px 0 5px;}
  .card{background:var(--card); border:1px solid var(--line); border-radius:16px; box-shadow:0 8px 30px rgba(15,23,42,.06);}
  /* login */
  #login{min-height:100vh; display:grid; place-items:center; padding:20px;}
  #login .card{padding:28px; width:100%; max-width:380px;}
  #login h1{margin:0 0 4px; font-size:20px;} #login p{margin:0 0 16px; color:var(--muted); font-size:13px;}
  .err{color:#dc2626; font-size:13px; margin-top:10px; min-height:16px;}
  /* app */
  #app{max-width:1000px; margin:0 auto; padding:18px;}
  .topbar{display:flex; align-items:center; gap:12px; margin-bottom:18px;}
  .orb{width:36px;height:36px;border-radius:11px;background:linear-gradient(135deg,var(--a1),var(--a2) 55%,var(--a3));box-shadow:0 6px 16px rgba(124,58,237,.45);}
  .topbar b{font-size:18px;} .grow{flex:1;}
  .layout{display:flex; gap:18px; align-items:flex-start;}
  .side{width:260px; flex:none;}
  .side .card{padding:12px;}
  .biz-item{padding:10px 12px; border-radius:10px; cursor:pointer; display:flex; flex-direction:column;}
  .biz-item:hover{background:#f5f3fc;} .biz-item.active{background:#f0edfb;}
  .biz-item b{font-size:14px;} .biz-item small{color:var(--muted);}
  .main{flex:1; min-width:0;}
  .tabs{display:flex; gap:6px; margin-bottom:14px;}
  .tab{padding:8px 14px; border-radius:999px; background:#fff; border:1px solid var(--line); color:var(--muted); font-weight:600; font-size:14px;}
  .tab.active{background:linear-gradient(135deg,var(--a1),var(--a2)); color:#fff; border-color:transparent;}
  .panel{padding:20px;}
  table{width:100%; border-collapse:collapse; font-size:14px;}
  th,td{text-align:left; padding:10px 8px; border-bottom:1px solid var(--line);}
  th{color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em;}
  .empty{color:var(--muted); padding:24px 0; text-align:center;}
  .row2{display:flex; gap:12px;} .row2 > div{flex:1;}
  .note{font-size:13px; color:var(--muted); margin-top:6px;}
  .keybox{background:#0f172a; color:#7dffd6; padding:12px; border-radius:10px; font-family:ui-monospace,Menlo,Consolas,monospace; font-size:13px; word-break:break-all; margin-top:8px;}
  .toast{position:fixed; bottom:20px; left:50%; transform:translateX(-50%); background:#0f172a; color:#fff; padding:12px 18px; border-radius:12px; font-size:14px; box-shadow:0 8px 24px rgba(0,0,0,.25); opacity:0; transition:opacity .2s;}
  .toast.show{opacity:1;}
</style>
</head>
<body>

<!-- LOGIN -->
<div id="login">
  <div class="card">
    <h1>Dashboard</h1>
    <p>Clinic: enter your Business ID + key. Admin: leave Business ID blank.</p>
    <label>Business ID <span style="font-weight:400">(blank = admin)</span></label>
    <input id="bid" placeholder="e.g. bright-smile" autocomplete="off">
    <label>API Key</label>
    <input id="key" type="password" placeholder="your key" autocomplete="off">
    <div style="margin-top:16px;"><button class="btn" style="width:100%" onclick="signIn()">Sign in</button></div>
    <div class="err" id="loginErr"></div>
  </div>
</div>

<!-- APP -->
<div id="app" class="hidden">
  <div class="topbar">
    <div class="orb"></div>
    <b id="appTitle">Dashboard</b>
    <span class="grow"></span>
    <button class="btn ghost" onclick="signOut()">Sign out</button>
  </div>
  <div class="layout">
    <div class="side hidden" id="side">
      <div class="card">
        <button class="btn" style="width:100%; margin-bottom:10px" onclick="showOnboard()">+ Onboard clinic</button>
        <div id="bizList"></div>
      </div>
    </div>
    <div class="main">
      <div id="bizPanel" class="hidden">
        <div class="tabs">
          <div class="tab active" data-tab="bookings" onclick="setTab('bookings')">Bookings</div>
          <div class="tab" data-tab="leads" onclick="setTab('leads')">Leads</div>
          <div class="tab" data-tab="settings" onclick="setTab('settings')">Settings</div>
          <div class="tab" data-tab="widget" onclick="setTab('widget')">Widget</div>
        </div>
        <div class="card panel" id="tabBody"></div>
      </div>
      <div id="onboardPanel" class="card panel hidden"></div>
      <div id="adminHome" class="card panel hidden empty">Select a clinic on the left, or onboard a new one.</div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
  let KEY=null, MODE=null, CURRENT=null, TAB="bookings";
  const $ = id => document.getElementById(id);
  const val = id => $(id).value;
  function toast(t){ const el=$("toast"); el.textContent=t; el.classList.add("show"); setTimeout(()=>el.classList.remove("show"),2200); }
  function esc(s){ return (s==null?"":String(s)).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}[c])); }

  function api(path, opts){
    opts = opts || {};
    opts.headers = Object.assign({ "X-API-Key": KEY, "Content-Type": "application/json" }, opts.headers||{});
    return fetch(path, opts);
  }

  async function signIn(){
    $("loginErr").textContent = "";
    const bid = val("bid").trim(), key = val("key").trim();
    if(!key){ $("loginErr").textContent="Enter your API key."; return; }
    KEY = key;
    if(bid){
      const r = await api("/manage/"+encodeURIComponent(bid));
      if(!r.ok){ $("loginErr").textContent = r.status===403||r.status===401 ? "Wrong Business ID or key." : "Could not sign in."; return; }
      MODE="clinic"; CURRENT=bid;
      const biz = await r.json();
      enterApp(biz.name || bid);
      $("side").classList.add("hidden");
      openBusiness(bid, biz);
    } else {
      const r = await api("/businesses");
      if(!r.ok){ $("loginErr").textContent = r.status===503 ? "Admin not configured on the server." : "Invalid admin key."; return; }
      MODE="admin";
      enterApp("Admin");
      $("side").classList.remove("hidden");
      $("adminHome").classList.remove("hidden");
      renderBizList(await r.json());
    }
  }

  function enterApp(title){ $("login").classList.add("hidden"); $("app").classList.remove("hidden"); $("appTitle").textContent = title; }
  function signOut(){ KEY=null; MODE=null; CURRENT=null; location.reload(); }

  // ---- admin: list + onboard ----
  function renderBizList(list){
    const box = $("bizList");
    box.innerHTML = (list||[]).map(b =>
      `<div class="biz-item" data-id="${esc(b.id)}" onclick="openBusiness('${esc(b.id)}')">
         <b>${esc(b.name)}</b><small>${esc(b.type)} · ${esc(b.id)}</small></div>`).join("") || "<div class='empty'>No clinics yet.</div>";
  }
  function showOnboard(){
    CURRENT=null;
    $("bizPanel").classList.add("hidden"); $("adminHome").classList.add("hidden");
    const p = $("onboardPanel"); p.classList.remove("hidden");
    p.innerHTML = `<h3 style="margin-top:0">Onboard a new clinic</h3>
      <div class="row2"><div><label>Business ID</label><input id="o_id" placeholder="velvet-hair"></div>
      <div><label>Name</label><input id="o_name" placeholder="Velvet Hair Studio"></div></div>
      <div class="row2"><div><label>Type</label><input id="o_type" placeholder="hair salon"></div>
      <div><label>Tone</label><input id="o_tone" placeholder="warm and friendly"></div></div>
      <label>Vertical</label><select id="o_vertical"><option value="general">general</option><option value="clinic">clinic</option><option value="salon">salon</option><option value="real_estate">real_estate</option></select>
      <label>Hours (display)</label><input id="o_hours" placeholder="Mon-Fri 9am-5pm">
      <label>Services</label><input id="o_services" placeholder="checkups, cleanings...">
      <label>FAQ / knowledge</label><textarea id="o_faq" rows="3" placeholder="Insurance, parking, policies..."></textarea>
      <div class="row2"><div><label>Open hour (0-23)</label><input id="o_open" type="number" value="9"></div>
      <div><label>Close hour (0-23)</label><input id="o_close" type="number" value="17"></div>
      <div><label>Slot mins</label><input id="o_slot" type="number" value="30"></div></div>
      <div style="margin-top:16px"><button class="btn" onclick="doOnboard()">Create clinic</button></div>
      <div id="onboardResult"></div>`;
  }
  async function doOnboard(){
    const body = { id:val("o_id").trim(), name:val("o_name").trim(), type:val("o_type").trim(),
      tone:val("o_tone").trim()||"warm and professional", hours:val("o_hours").trim(), services:val("o_services").trim(),
      faq:val("o_faq").trim(), open_hour:+val("o_open"), close_hour:+val("o_close"), slot_minutes:+val("o_slot"),
      vertical:val("o_vertical") };
    if(!body.id||!body.name||!body.type){ toast("ID, name and type are required."); return; }
    const r = await api("/admin/businesses", { method:"POST", body: JSON.stringify(body) });
    const d = await r.json();
    if(!r.ok){ toast(d.detail || "Could not create."); return; }
    $("onboardResult").innerHTML = `<div class="note" style="margin-top:14px">Clinic created. Give them this key (shown once):</div>
      <div class="keybox">${esc(d.api_key)}</div>
      <div class="note">Widget link: <code>/widget?business_id=${esc(d.id)}</code></div>`;
    const r2 = await api("/businesses"); if(r2.ok) renderBizList(await r2.json());
  }

  // ---- shared business panel ----
  async function openBusiness(id, preBiz){
    CURRENT = id; TAB = "bookings";
    $("onboardPanel").classList.add("hidden"); $("adminHome").classList.add("hidden");
    $("bizPanel").classList.remove("hidden");
    document.querySelectorAll(".biz-item").forEach(e => e.classList.toggle("active", e.dataset.id===id));
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab==="bookings"));
    renderTab();
  }
  function setTab(t){ TAB=t; document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x.dataset.tab===t)); renderTab(); }

  async function renderTab(){
    const body = $("tabBody"); body.innerHTML = "<div class='empty'>Loading…</div>";
    if(TAB==="bookings"){
      const r = await api("/bookings?business_id="+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML="<div class='empty'>Could not load bookings.</div>"; return; }
      const rows = await r.json();
      body.innerHTML = rows.length ? `<table><thead><tr><th>Date</th><th>Time</th><th>Patient</th><th>Phone</th><th>Reason</th></tr></thead>
        <tbody>${rows.map(b=>`<tr><td>${esc(b.date)}</td><td>${esc(b.time)}</td><td>${esc(b.patient_name)}</td><td>${esc(b.phone)}</td><td>${esc(b.reason)}</td></tr>`).join("")}</tbody></table>`
        : "<div class='empty'>No bookings yet.</div>";
    } else if(TAB==="leads"){
      const r = await api("/leads?business_id="+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML="<div class='empty'>Could not load leads.</div>"; return; }
      const rows = await r.json();
      body.innerHTML = rows.length ? `<table><thead><tr><th>Name</th><th>Phone</th><th>Interest</th><th>Notes</th></tr></thead>
        <tbody>${rows.map(l=>`<tr><td>${esc(l.name)}</td><td>${esc(l.phone)}</td><td>${esc(l.interest)}</td><td>${esc(l.notes)}</td></tr>`).join("")}</tbody></table>`
        : "<div class='empty'>No leads yet.</div>";
    } else if(TAB==="settings"){
      const r = await api("/manage/"+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML="<div class='empty'>Could not load settings.</div>"; return; }
      const b = await r.json();
      body.innerHTML = `<h3 style="margin-top:0">Settings</h3>
        <div class="row2"><div><label>Name</label><input id="s_name" value="${esc(b.name)}"></div>
        <div><label>Type</label><input id="s_type" value="${esc(b.type)}"></div></div>
        <label>Vertical (drives the agent's behaviour)</label>
        <select id="s_vertical"><option value="clinic">clinic</option><option value="salon">salon</option><option value="real_estate">real_estate</option><option value="general">general</option></select>
        <label>Tone</label><input id="s_tone" value="${esc(b.tone)}">
        <label>Hours (display)</label><input id="s_hours" value="${esc(b.hours)}">
        <label>Services</label><input id="s_services" value="${esc(b.services)}">
        <label>FAQ / knowledge the agent can use</label><textarea id="s_faq" rows="4">${esc(b.faq)}</textarea>
        <div class="row2"><div><label>Open hour</label><input id="s_open" type="number" value="${esc(b.open_hour)}"></div>
        <div><label>Close hour</label><input id="s_close" type="number" value="${esc(b.close_hour)}"></div>
        <div><label>Slot mins</label><input id="s_slot" type="number" value="${esc(b.slot_minutes)}"></div></div>
        <div style="margin-top:16px"><button class="btn" onclick="saveSettings()">Save changes</button></div>`;
      $("s_vertical").value = b.vertical || "general";
    } else {
      const url = location.origin + "/widget?business_id=" + encodeURIComponent(CURRENT);
      body.innerHTML = `<h3 style="margin-top:0">Patient widget</h3>
        <div class="note">Share this link with patients, or embed it on the clinic's site.</div>
        <div class="keybox">${esc(url)}</div>
        <div style="margin:12px 0"><a href="${esc(url)}" target="_blank"><button class="btn">Open widget ↗</button></a></div>
        <label>Embed snippet</label>
        <div class="keybox">&lt;iframe src="${esc(url)}" style="width:380px;height:560px;border:0;border-radius:16px"&gt;&lt;/iframe&gt;</div>`;
    }
  }

  async function saveSettings(){
    const body = { name:val("s_name"), type:val("s_type"), tone:val("s_tone"), hours:val("s_hours"),
      services:val("s_services"), faq:val("s_faq"), open_hour:+val("s_open"), close_hour:+val("s_close"),
      slot_minutes:+val("s_slot"), vertical:val("s_vertical") };
    const r = await api("/manage/"+encodeURIComponent(CURRENT), { method:"POST", body: JSON.stringify(body) });
    toast(r.ok ? "Saved ✓" : "Save failed");
  }
</script>
</body>
</html>"""
