"""
The management dashboard — one polished page served by the backend, for BOTH:
  • Clinics: sign in with their Business ID + api_key → see bookings, edit settings,
    grab their widget link.
  • Admin (you): sign in with just the admin key → list all clinics, open any one,
    and onboard new clinics (which generates their api_key).

It's only the app shell; every data call sends the key in the X-API-Key header,
so the backend (not the page) enforces who can see what. The 2026 restyle is
purely visual: same IDs, functions and API flows, plus a client-side KPI row
computed from the already-authorized /bookings and /leads endpoints.
"""

DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard · ReceptionAI</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root{
    --canvas:#fdfdff; --surface:#f7f6fb; --surface-2:#f1effa; --card:#ffffff;
    --hairline:#e9e7f2; --ink:#17151f; --body:#4e4b5c; --muted:#8a8798;
    --accent:#7c5cff; --accent-deep:#6847e6; --accent-soft:#efeaff;
    --focus:rgba(124,92,255,.35);
    --shadow-card:0 0 0 1px rgba(23,21,31,.04),0 1px 1px rgba(46,26,110,.03),0 2px 4px rgba(46,26,110,.04),0 8px 16px -4px rgba(46,26,110,.06);
    --shadow-float:0 1px 1px rgba(46,26,110,.03),0 8px 16px -4px rgba(46,26,110,.06),0 24px 32px -8px rgba(46,26,110,.12);
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;
    font-feature-settings:'cv11','ss01';-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
    color:var(--ink);background:var(--canvas);font-size:16px;line-height:1.55}
  ::selection{background:rgba(124,92,255,.22)}
  :focus-visible{outline:2px solid var(--focus);outline-offset:2px}
  .hidden{display:none !important}
  h3{font-size:20px;font-weight:600;letter-spacing:-.015em;margin:0 0 12px}
  /* buttons */
  button{font:inherit;cursor:pointer;border:0}
  .btn{display:inline-flex;align-items:center;justify-content:center;padding:12px 22px;border-radius:999px;
    font-size:14.5px;font-weight:600;background:var(--accent);color:#fff;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.18);transition:background .15s,transform .15s}
  .btn:hover{background:var(--accent-deep);transform:translateY(-1px)}
  .btn:active{transform:translateY(0)}
  .btn.ghost{background:var(--card);color:var(--body);border:1px solid var(--hairline);box-shadow:none}
  .btn.ghost:hover{background:var(--surface);color:var(--ink);transform:none}
  /* forms */
  input,textarea,select{font:inherit;font-size:14.5px;width:100%;padding:10px 12px;border:1px solid var(--hairline);
    border-radius:8px;outline:none;background:var(--card);color:var(--ink);transition:border-color .15s,box-shadow .15s}
  input:focus,textarea:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--focus)}
  label{display:block;font-size:13px;font-weight:500;color:var(--muted);margin:14px 0 6px}
  .card{background:var(--card);border:1px solid var(--hairline);border-radius:12px;box-shadow:var(--shadow-card)}
  /* login */
  #login{position:relative;min-height:100vh;display:grid;place-items:center;padding:20px;overflow:hidden}
  .hero-glow{position:absolute;inset:-20% -10% auto;height:70%;
    background:radial-gradient(38% 45% at 22% 30%,rgba(124,92,255,.28),transparent 70%),
      radial-gradient(30% 40% at 68% 20%,rgba(255,158,122,.25),transparent 70%),
      radial-gradient(28% 35% at 85% 55%,rgba(255,122,198,.16),transparent 70%);
    filter:blur(60px);pointer-events:none;opacity:.55}
  #login .card{position:relative;padding:32px 28px;width:100%;max-width:400px;box-shadow:var(--shadow-float)}
  .wordmark{font-size:17px;font-weight:700;letter-spacing:-.015em}
  .wordmark span{color:var(--accent)}
  #login h1{margin:18px 0 4px;font-size:20px;font-weight:600;letter-spacing:-.015em}
  #login .hint{margin:0 0 6px;color:var(--muted);font-size:13px}
  label .soft{font-weight:400;color:var(--muted)}
  .err{color:#c02543;font-size:13px;margin-top:12px;min-height:16px}
  /* app shell */
  #app{display:flex;min-height:100vh;align-items:stretch}
  .side{width:240px;flex:none;background:var(--surface);border-right:1px solid var(--hairline);
    padding:18px 12px;position:sticky;top:0;height:100vh;overflow-y:auto}
  .side .wordmark{display:block;padding:4px 10px 16px}
  .onboard-row{display:block;width:100%;text-align:left;padding:10px 12px;margin-bottom:10px;border-radius:8px;
    font-size:14px;font-weight:600;color:var(--accent-deep);background:var(--accent-soft);transition:background .15s}
  .onboard-row:hover{background:#e4dcff}
  .biz-item{padding:9px 12px;border-radius:8px;cursor:pointer;display:flex;flex-direction:column;gap:1px;transition:background .15s}
  .biz-item:hover{background:var(--surface-2)}
  .biz-item.active{background:var(--accent-soft)}
  .biz-item b{font-size:14px;font-weight:600;color:var(--ink)}
  .biz-item.active b{color:var(--accent-deep)}
  .biz-item small{font-size:12px;color:var(--muted)}
  .main{flex:1;min-width:0;max-width:1120px;margin:0 auto;padding:22px 32px 56px}
  .topbar{display:flex;align-items:center;gap:12px;margin-bottom:22px}
  .topbar b{font-size:20px;font-weight:600;letter-spacing:-.015em}
  .grow{flex:1}
  .topbar .btn.ghost{padding:9px 16px;font-size:13.5px}
  /* KPI stat row */
  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:20px}
  .kpi{background:var(--card);border:1px solid var(--hairline);border-radius:12px;box-shadow:var(--shadow-card);padding:16px 20px}
  .klabel{display:block;font-size:13px;font-weight:500;color:var(--muted)}
  .knum{display:block;font-size:28px;font-weight:600;letter-spacing:-.015em;font-variant-numeric:tabular-nums;margin-top:2px}
  /* tabs — segmented control */
  .tabs{display:inline-flex;gap:2px;background:var(--surface);border:1px solid var(--hairline);border-radius:999px;padding:4px;margin-bottom:16px}
  .tab{padding:8px 16px;border-radius:999px;color:var(--muted);font-weight:500;font-size:14px;cursor:pointer;transition:color .15s,background .15s}
  .tab:hover{color:var(--ink)}
  .tab.active{background:var(--card);color:var(--ink);font-weight:600;box-shadow:var(--shadow-card)}
  .panel{padding:24px}
  /* tables */
  .tablewrap{margin:-24px;max-height:65vh;overflow:auto;border-radius:12px}
  table{width:100%;border-collapse:collapse;font-size:14px}
  th{position:sticky;top:0;z-index:1;background:var(--card);text-align:left;padding:12px 14px;
    font-size:13px;font-weight:500;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
    border-bottom:1px solid var(--hairline)}
  td{text-align:left;padding:0 14px;height:52px;border-bottom:1px solid var(--hairline);color:var(--body)}
  tbody tr:last-child td{border-bottom:0}
  tbody tr:hover{background:var(--surface)}
  td.num{font-variant-numeric:tabular-nums}
  .who{display:flex;align-items:center;gap:10px;color:var(--ink);font-weight:500}
  .wav{width:32px;height:32px;border-radius:50%;flex:none;display:inline-flex;align-items:center;justify-content:center;
    font-size:13px;font-weight:600}
  .chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:500;padding:3px 10px;border-radius:999px}
  .chip::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor}
  .chip.confirmed{background:#e8f7ee;color:#147a3d}
  .chip.new{background:var(--accent-soft);color:var(--accent-deep)}
  /* empty + loading states */
  .empty{color:var(--muted);padding:28px 0;text-align:center;font-size:14px}
  .estate{text-align:center;padding:40px 20px}
  .eico{width:56px;height:56px;border-radius:50%;background:var(--accent-soft);display:inline-flex;
    align-items:center;justify-content:center;font-size:24px;margin-bottom:14px}
  .etitle{font-size:16px;font-weight:600;letter-spacing:-.01em}
  .ehint{font-size:13.5px;color:var(--muted);margin-top:4px}
  /* misc */
  .row2{display:flex;gap:12px} .row2 > div{flex:1}
  .note{font-size:13px;color:var(--muted);margin-top:6px}
  .keybox{background:var(--ink);color:#cfc3ff;padding:12px 14px;border-radius:8px;
    font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;word-break:break-all;margin-top:8px}
  .toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--ink);color:#fff;
    padding:12px 22px;border-radius:999px;font-size:14px;font-weight:500;box-shadow:var(--shadow-float);
    opacity:0;pointer-events:none;transition:opacity .2s}
  .toast.show{opacity:1}
  @media (prefers-reduced-motion: reduce){ *{transition:none !important} }
  @media (max-width:860px){
    #app{flex-direction:column}
    .side{width:100%;height:auto;position:static;border-right:0;border-bottom:1px solid var(--hairline)}
    .main{padding:18px 20px 48px}
    .stats{grid-template-columns:1fr;gap:10px}
  }
</style>
</head>
<body>

<!-- LOGIN -->
<div id="login">
  <div class="hero-glow"></div>
  <div class="card">
    <div class="wordmark">Reception<span>AI</span></div>
    <h1>Dashboard</h1>
    <p class="hint">Clinic: enter your Business ID + key. Admin: leave Business ID blank.</p>
    <label>Business ID <span class="soft">(blank = admin)</span></label>
    <input id="bid" placeholder="e.g. bright-smile" autocomplete="off">
    <label>API Key</label>
    <input id="key" type="password" placeholder="your key" autocomplete="off">
    <div style="margin-top:20px"><button class="btn" style="width:100%" onclick="signIn()">Sign in</button></div>
    <div class="err" id="loginErr"></div>
  </div>
</div>

<!-- APP -->
<div id="app" class="hidden">
  <div class="side hidden" id="side">
    <span class="wordmark">Reception<span>AI</span></span>
    <button class="onboard-row" onclick="showOnboard()">+ Onboard new</button>
    <div id="bizList"></div>
  </div>
  <div class="main">
    <div class="topbar">
      <b id="appTitle">Dashboard</b>
      <span class="grow"></span>
      <button class="btn ghost" onclick="signOut()">Sign out</button>
    </div>
    <div id="bizPanel" class="hidden">
      <div class="stats">
        <div class="kpi"><span class="klabel">Upcoming bookings</span><span class="knum" id="statUpcoming">–</span></div>
        <div class="kpi"><span class="klabel">Total bookings</span><span class="knum" id="statTotal">–</span></div>
        <div class="kpi"><span class="klabel">Leads</span><span class="knum" id="statLeads">–</span></div>
      </div>
      <div class="tabs">
        <div class="tab active" data-tab="bookings" onclick="setTab('bookings')">Bookings</div>
        <div class="tab" data-tab="leads" onclick="setTab('leads')">Leads</div>
        <div class="tab" data-tab="settings" onclick="setTab('settings')">Settings</div>
        <div class="tab" data-tab="widget" onclick="setTab('widget')">Widget</div>
      </div>
      <div class="card panel" id="tabBody"></div>
    </div>
    <div id="onboardPanel" class="card panel hidden"></div>
    <div id="adminHome" class="card panel hidden">
      <div class="estate"><div class="eico">🏥</div>
        <div class="etitle">No clinic selected</div>
        <div class="ehint">Select a clinic on the left, or onboard a new one.</div></div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
  let KEY=null, MODE=null, CURRENT=null, TAB="bookings";
  const $ = id => document.getElementById(id);
  const val = id => $(id).value;
  function toast(t){ const el=$("toast"); el.textContent=t; el.classList.add("show"); setTimeout(()=>el.classList.remove("show"),2200); }
  function esc(s){ return (s==null?"":String(s)).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
  // FastAPI sends validation failures (422) as a LIST of {loc, msg} — format it
  // readably instead of toasting "[object Object]".
  function apiErr(d, fallback){
    if(!d || !d.detail) return fallback;
    if(typeof d.detail === "string") return d.detail;
    if(Array.isArray(d.detail)) return d.detail.map(e=>{
      const f=(e.loc||[]).slice(1).join("."); return (f?f+": ":"")+(e.msg||"invalid value");
    }).join(" · ");
    return fallback;
  }

  // ---- purely-visual helpers (initials avatars, chips, empty states, KPIs) ----
  function nameHue(s){ s=String(s==null?"":s); let h=0; for(let i=0;i<s.length;i++){ h=(h*31+s.charCodeAt(i))>>>0; } return h%360; }
  function avatar(name){
    const n=String(name==null?"":name).trim()||"?"; const h=nameHue(n);
    return `<span class="wav" style="background:hsl(${h},55%,88%);color:hsl(${h},55%,35%)">${esc(n.charAt(0).toUpperCase())}</span>`;
  }
  function who(name){ return `<span class="who">${avatar(name)}<span>${esc(name)}</span></span>`; }
  function estate(ico, title, hint){
    return `<div class="estate"><div class="eico">${ico}</div><div class="etitle">${esc(title)}</div><div class="ehint">${esc(hint)}</div></div>`;
  }
  function todayISO(){
    const t=new Date();
    return t.getFullYear()+"-"+String(t.getMonth()+1).padStart(2,"0")+"-"+String(t.getDate()).padStart(2,"0");
  }
  function statsFromBookings(rows){
    $("statTotal").textContent = rows.length;
    const iso = todayISO();
    $("statUpcoming").textContent = rows.filter(b => String(b.date||"") >= iso).length;
  }
  // one extra read of the two already-authorized endpoints when a business opens —
  // no new backend surface, numbers are computed entirely client-side.
  async function loadStats(){
    const biz = CURRENT;
    $("statUpcoming").textContent="–"; $("statTotal").textContent="–"; $("statLeads").textContent="–";
    try{
      const [rb, rl] = await Promise.all([
        api("/bookings?business_id="+encodeURIComponent(biz)),
        api("/leads?business_id="+encodeURIComponent(biz))
      ]);
      if(biz !== CURRENT) return;
      if(rb.ok) statsFromBookings(await rb.json());
      if(rl.ok){ const rows = await rl.json(); $("statLeads").textContent = rows.length; }
    }catch(e){}
  }

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
    p.innerHTML = `<h3>Onboard a new clinic</h3>
      <div class="row2"><div><label>Business ID (lowercase-and-dashes)</label><input id="o_id" placeholder="velvet-hair"></div>
      <div><label>Name</label><input id="o_name" placeholder="Velvet Hair Studio"></div></div>
      <div class="row2"><div><label>Type</label><input id="o_type" placeholder="hair salon"></div>
      <div><label>Tone</label><input id="o_tone" placeholder="warm and friendly"></div></div>
      <label>Vertical</label><select id="o_vertical"><option value="general">general</option><option value="clinic">clinic</option><option value="salon">salon</option><option value="real_estate">real_estate</option></select>
      <label>Hours (display)</label><input id="o_hours" placeholder="Mon-Fri 9am-5pm">
      <label>Services</label><input id="o_services" placeholder="checkups, cleanings...">
      <label>FAQ / knowledge</label><textarea id="o_faq" rows="3" placeholder="Insurance, parking, policies..."></textarea>
      <div class="row2"><div><label>Open hour (0-23)</label><input id="o_open" type="number" min="0" max="23" value="9"></div>
      <div><label>Close hour (1-24)</label><input id="o_close" type="number" min="1" max="24" value="17"></div>
      <div><label>Slot mins (5-240)</label><input id="o_slot" type="number" min="5" max="240" value="30"></div></div>
      <div style="margin-top:18px"><button class="btn" onclick="doOnboard()">Create clinic</button></div>
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
    if(!r.ok){ toast(apiErr(d, "Could not create.")); return; }
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
    loadStats();
    renderTab();
  }
  function setTab(t){ TAB=t; document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x.dataset.tab===t)); renderTab(); }

  async function renderTab(){
    const body = $("tabBody"); body.innerHTML = "<div class='empty'>Loading…</div>";
    if(TAB==="bookings"){
      const r = await api("/bookings?business_id="+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML="<div class='empty'>Could not load bookings.</div>"; return; }
      const rows = await r.json();
      statsFromBookings(rows);
      body.innerHTML = rows.length ? `<div class="tablewrap"><table><thead><tr><th>Patient</th><th>Date</th><th>Time</th><th>Phone</th><th>Reason</th></tr></thead>
        <tbody>${rows.map(b=>`<tr><td>${who(b.patient_name)}</td><td class="num">${esc(b.date)}</td><td class="num">${esc(b.time)}</td><td class="num">${esc(b.phone)}</td><td>${esc(b.reason)}</td></tr>`).join("")}</tbody></table></div>`
        : estate("📅","No bookings yet","Share your widget link so customers can book.");
    } else if(TAB==="leads"){
      const r = await api("/leads?business_id="+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML="<div class='empty'>Could not load leads.</div>"; return; }
      const rows = await r.json();
      $("statLeads").textContent = rows.length;
      body.innerHTML = rows.length ? `<div class="tablewrap"><table><thead><tr><th>Name</th><th>Phone</th><th>Interest</th><th>Notes</th></tr></thead>
        <tbody>${rows.map(l=>`<tr><td>${who(l.name)}</td><td class="num">${esc(l.phone)}</td><td>${l.interest?`<span class="chip new">${esc(l.interest)}</span>`:""}</td><td>${esc(l.notes)}</td></tr>`).join("")}</tbody></table></div>`
        : estate("📥","No leads yet","Every enquiry the agent captures will land here.");
    } else if(TAB==="settings"){
      const r = await api("/manage/"+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML="<div class='empty'>Could not load settings.</div>"; return; }
      const b = await r.json();
      body.innerHTML = `<h3>Settings</h3>
        <div class="row2"><div><label>Name</label><input id="s_name" value="${esc(b.name)}"></div>
        <div><label>Type</label><input id="s_type" value="${esc(b.type)}"></div></div>
        <label>Vertical (drives the agent's behaviour)</label>
        <select id="s_vertical"><option value="clinic">clinic</option><option value="salon">salon</option><option value="real_estate">real_estate</option><option value="general">general</option></select>
        <label>Tone</label><input id="s_tone" value="${esc(b.tone)}">
        <label>Hours (display)</label><input id="s_hours" value="${esc(b.hours)}">
        <label>Services</label><input id="s_services" value="${esc(b.services)}">
        <label>FAQ / knowledge the agent can use</label><textarea id="s_faq" rows="4">${esc(b.faq)}</textarea>
        <div class="row2"><div><label>Open hour (0-23)</label><input id="s_open" type="number" min="0" max="23" value="${esc(b.open_hour)}"></div>
        <div><label>Close hour (1-24)</label><input id="s_close" type="number" min="1" max="24" value="${esc(b.close_hour)}"></div>
        <div><label>Slot mins (5-240)</label><input id="s_slot" type="number" min="5" max="240" value="${esc(b.slot_minutes)}"></div></div>
        <div style="margin-top:18px"><button class="btn" onclick="saveSettings()">Save changes</button></div>`;
      $("s_vertical").value = b.vertical || "general";
    } else {
      const url = location.origin + "/widget?business_id=" + encodeURIComponent(CURRENT);
      body.innerHTML = `<h3>Patient widget</h3>
        <div class="note">Share this link with patients, or embed it on the clinic's site.</div>
        <div class="keybox">${esc(url)}</div>
        <div style="margin:14px 0"><a href="${esc(url)}" target="_blank"><button class="btn">Open widget ↗</button></a></div>
        <label>Embed snippet</label>
        <div class="keybox">&lt;iframe src="${esc(url)}" style="width:380px;height:560px;border:0;border-radius:16px"&gt;&lt;/iframe&gt;</div>`;
    }
  }

  async function saveSettings(){
    const body = { name:val("s_name"), type:val("s_type"), tone:val("s_tone"), hours:val("s_hours"),
      services:val("s_services"), faq:val("s_faq"), open_hour:+val("s_open"), close_hour:+val("s_close"),
      slot_minutes:+val("s_slot"), vertical:val("s_vertical") };
    const r = await api("/manage/"+encodeURIComponent(CURRENT), { method:"POST", body: JSON.stringify(body) });
    if(r.ok){ toast("Saved ✓"); return; }
    let d=null; try{ d = await r.json(); }catch(e){}
    toast(apiErr(d, "Save failed"));
  }
</script>
</body>
</html>"""
