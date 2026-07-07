"""
The management dashboard — one polished page served by the backend, for BOTH:
  • Business owners: sign in with their Business ID + api_key → see bookings,
    leads, edit settings, grab their widget link.
  • Admin (you): sign in with just the admin key → list all businesses, open any
    one, and onboard new businesses (which generates their api_key).

It's only the app shell; every data call sends the key in the X-API-Key header,
so the backend (not the page) enforces who can see what. The premium-SaaS
restyle is purely visual: same IDs, functions and API flows. Additions are
presentational only — skeleton loading rows, a copy-key button, aria/keyboard
affordances (login is a real form so Enter submits; tabs are buttons with
aria-selected), and a grouped, stepped-feel onboarding form (same o_* ids, same
single doOnboard submit).
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
    --hairline:#e9e7f2; --hairline-2:#dcd8ea; --ink:#16141d; --body:#4c4a58; --muted:#716e80;
    --accent:#7c5cff; --accent-deep:#6847e6; --accent-soft:#efeaff;
    --ok:#147a3d; --ok-soft:#e8f7ee; --danger:#c02543;
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
  .visually-hidden{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
  h3{font-size:19px;font-weight:600;letter-spacing:-.015em;margin:0 0 4px}
  .lead{font-size:14px;color:var(--muted);margin:0 0 10px}
  /* buttons */
  button{font:inherit;cursor:pointer;border:0;background:none;color:inherit}
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 22px;border-radius:999px;
    font-size:14.5px;font-weight:600;background:var(--accent);color:#fff;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 1px 2px rgba(46,26,110,.24);transition:background .15s,transform .15s}
  .btn:hover{background:var(--accent-deep);transform:translateY(-1px)}
  .btn:active{transform:translateY(0)}
  .btn.ghost{background:var(--card);color:var(--body);border:1px solid var(--hairline-2);box-shadow:none}
  .btn.ghost:hover{background:var(--surface);color:var(--ink);transform:none}
  /* forms */
  input,textarea,select{font:inherit;font-size:14.5px;width:100%;padding:10px 12px;border:1px solid var(--hairline-2);
    border-radius:8px;outline:none;background:var(--card);color:var(--ink);transition:border-color .15s,box-shadow .15s}
  input::placeholder,textarea::placeholder{color:#a3a0b0}
  input:focus,textarea:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--focus)}
  label{display:block;font-size:13px;font-weight:500;color:var(--body);margin:14px 0 6px}
  .card{background:var(--card);border:1px solid var(--hairline);border-radius:12px;box-shadow:var(--shadow-card)}
  /* form groups (stepped-feel onboarding + settings) */
  .fgroup{margin-top:28px;padding-top:24px;border-top:1px solid var(--surface-2)}
  .fgroup.first{margin-top:12px;padding-top:0;border-top:0}
  .fghead{display:flex;align-items:center;gap:10px}
  .fgnum{flex:none;width:24px;height:24px;border-radius:50%;background:var(--accent-soft);color:var(--accent-deep);
    display:inline-flex;align-items:center;justify-content:center;font-size:12.5px;font-weight:600;font-variant-numeric:tabular-nums}
  .fgtitle{font-size:15px;font-weight:600;letter-spacing:-.01em}
  .fgwhy{font-size:13px;color:var(--muted);margin:5px 0 0 34px}
  /* login */
  #login{position:relative;min-height:100vh;display:grid;place-items:center;padding:20px;overflow:hidden}
  .hero-glow{position:absolute;inset:-20% -10% auto;height:70%;
    background:radial-gradient(38% 45% at 22% 30%,rgba(124,92,255,.22),transparent 70%),
      radial-gradient(30% 40% at 68% 20%,rgba(255,158,122,.16),transparent 70%);
    filter:blur(60px);pointer-events:none;opacity:.55}
  #login .card{position:relative;padding:32px 28px;width:100%;max-width:400px;box-shadow:var(--shadow-float)}
  .wordmark{font-size:17px;font-weight:700;letter-spacing:-.015em}
  .wordmark span{color:var(--accent-deep)}
  #login h1{margin:18px 0 4px;font-size:20px;font-weight:600;letter-spacing:-.015em}
  #login .hint{margin:0 0 6px;color:var(--muted);font-size:13px}
  label .soft{font-weight:400;color:var(--muted)}
  .err{color:var(--danger);font-size:13px;margin-top:12px;min-height:16px}
  /* app shell */
  #app{display:flex;min-height:100vh;align-items:stretch}
  .side{width:240px;flex:none;background:var(--surface);border-right:1px solid var(--hairline);
    padding:18px 12px;position:sticky;top:0;height:100vh;overflow-y:auto}
  .side .wordmark{display:block;padding:4px 10px 16px}
  .onboard-row{display:block;width:100%;text-align:left;padding:10px 12px;margin-bottom:14px;border-radius:8px;
    font-size:14px;font-weight:600;color:var(--accent-deep);background:var(--accent-soft);transition:background .15s}
  .onboard-row:hover{background:#e4dcff}
  .side-label{font-size:11.5px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);
    padding:2px 12px 8px}
  .biz-item{display:flex;width:100%;text-align:left;padding:9px 12px;border-radius:8px;cursor:pointer;
    flex-direction:column;gap:1px;background:transparent;transition:background .15s}
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
  /* KPI value band — one card, six cells */
  .stats{display:grid;grid-template-columns:repeat(6,1fr);background:var(--card);border:1px solid var(--hairline);
    border-radius:12px;box-shadow:var(--shadow-card);overflow:hidden;margin-bottom:20px}
  .kpi{padding:16px 18px;border-left:1px solid var(--hairline)}
  .kpi:first-child{border-left:0}
  .klabel{display:block;font-size:12.5px;font-weight:500;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .knum{display:block;font-size:26px;font-weight:600;letter-spacing:-.015em;font-variant-numeric:tabular-nums;margin-top:2px}
  /* tabs — segmented control */
  .tabs{display:inline-flex;gap:2px;background:var(--surface);border:1px solid var(--hairline);border-radius:999px;padding:4px;margin-bottom:16px}
  .tab{padding:8px 16px;border-radius:999px;background:transparent;color:var(--muted);font-weight:500;font-size:14px;cursor:pointer;transition:color .15s,background .15s,box-shadow .15s}
  .tab:hover{color:var(--ink)}
  .tab.active{background:var(--card);color:var(--ink);font-weight:600;box-shadow:var(--shadow-card)}
  .panel{padding:24px}
  /* tables */
  .tablewrap{margin:-24px;max-height:65vh;overflow:auto;border-radius:12px}
  table{width:100%;border-collapse:collapse;font-size:14px}
  th{position:sticky;top:0;z-index:1;background:var(--card);text-align:left;padding:12px 14px;
    font-size:12.5px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
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
  .chip.confirmed{background:var(--ok-soft);color:var(--ok)}
  .chip.new{background:var(--accent-soft);color:var(--accent-deep)}
  /* empty + loading states */
  .empty{color:var(--muted);padding:28px 0;text-align:center;font-size:14px}
  .estate{text-align:center;padding:44px 20px}
  .eico{width:56px;height:56px;border-radius:50%;background:var(--accent-soft);display:inline-flex;
    align-items:center;justify-content:center;font-size:24px;margin-bottom:14px}
  .etitle{font-size:16px;font-weight:600;letter-spacing:-.01em}
  .ehint{font-size:13.5px;color:var(--muted);margin-top:4px;max-width:360px;margin-left:auto;margin-right:auto}
  .skelrow{display:flex;gap:12px;align-items:center;padding:13px 0;border-bottom:1px solid var(--surface-2)}
  .skelrow:last-child{border-bottom:0}
  .sk{height:12px;border-radius:6px;background:linear-gradient(90deg,var(--surface),var(--surface-2),var(--surface));
    background-size:200% 100%;animation:shimmer 1.4s linear infinite}
  .sk.av{width:32px;height:32px;border-radius:50%;flex:none}
  @keyframes shimmer{from{background-position:200% 0}to{background-position:-200% 0}}
  /* misc */
  .row2{display:flex;gap:12px} .row2 > div{flex:1}
  .note{font-size:13px;color:var(--muted);margin-top:6px}
  .keybox{background:var(--ink);color:#cfc3ff;padding:12px 14px;border-radius:8px;
    font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;word-break:break-all;margin-top:8px}
  .okcard{margin-top:20px;border:1px solid #bfe6cd;background:var(--ok-soft);border-radius:12px;padding:18px 20px}
  .okcard .oktitle{font-size:15px;font-weight:600;color:var(--ok)}
  .okcard .note{color:#3c5a48}
  .okrow{display:flex;gap:10px;margin-top:12px;flex-wrap:wrap;align-items:center}
  .toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:var(--ink);color:#fff;
    padding:12px 22px;border-radius:999px;font-size:14px;font-weight:500;box-shadow:var(--shadow-float);
    opacity:0;pointer-events:none;transition:opacity .2s;z-index:60}
  .toast.show{opacity:1}
  @media (prefers-reduced-motion: reduce){ *{transition:none !important;animation:none !important} }
  @media (max-width:1100px){
    .stats{grid-template-columns:repeat(3,1fr)}
    .kpi:nth-child(3n+1){border-left:0}
    .kpi:nth-child(n+4){border-top:1px solid var(--hairline)}
  }
  @media (max-width:860px){
    #app{flex-direction:column}
    .side{width:100%;height:auto;position:static;border-right:0;border-bottom:1px solid var(--hairline)}
    .main{padding:18px 20px 48px}
    .row2{flex-direction:column;gap:0}
  }
  @media (max-width:640px){
    .stats{grid-template-columns:repeat(2,1fr)}
    .kpi:nth-child(n){border-left:1px solid var(--hairline);border-top:0}
    .kpi:nth-child(2n+1){border-left:0}
    .kpi:nth-child(n+3){border-top:1px solid var(--hairline)}
    .tabs{width:100%;overflow-x:auto}
  }
</style>
</head>
<body>

<!-- LOGIN -->
<div id="login">
  <div class="hero-glow"></div>
  <div class="card">
    <div class="wordmark">Reception<span>AI</span></div>
    <h1>Sign in to your dashboard</h1>
    <p class="hint">Business owners: enter your Business ID and API key. Admin: leave Business ID blank.</p>
    <form onsubmit="event.preventDefault(); signIn()">
      <label for="bid">Business ID <span class="soft">(blank = admin)</span></label>
      <input id="bid" placeholder="e.g. bright-smile" autocomplete="off">
      <label for="key">API key</label>
      <input id="key" type="password" placeholder="Paste the key you were given" autocomplete="off">
      <div style="margin-top:20px"><button class="btn" type="submit" style="width:100%">Sign in</button></div>
    </form>
    <div class="err" id="loginErr" aria-live="polite"></div>
  </div>
</div>

<!-- APP -->
<div id="app" class="hidden">
  <div class="side hidden" id="side">
    <span class="wordmark">Reception<span>AI</span></span>
    <button class="onboard-row" onclick="showOnboard()">+ Add a business</button>
    <div class="side-label">Businesses</div>
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
        <div class="kpi"><span class="klabel">Chats today</span><span class="knum" id="mToday">–</span></div>
        <div class="kpi"><span class="klabel">Chats · 30 days</span><span class="knum" id="mChats">–</span></div>
        <div class="kpi"><span class="klabel">Questions answered</span><span class="knum" id="mMsgs">–</span></div>
        <div class="kpi"><span class="klabel">Bookings · 30 days</span><span class="knum" id="mBookings">–</span></div>
        <div class="kpi"><span class="klabel">Leads · 30 days</span><span class="knum" id="mLeads">–</span></div>
        <div class="kpi"><span class="klabel">Staff hours saved <span class="soft">(est.)</span></span><span class="knum" id="mHours">–</span></div>
      </div>
      <div class="tabs" role="tablist" aria-label="Dashboard sections">
        <button class="tab active" role="tab" aria-selected="true" data-tab="bookings" onclick="setTab('bookings')">Bookings</button>
        <button class="tab" role="tab" aria-selected="false" data-tab="leads" onclick="setTab('leads')">Leads</button>
        <button class="tab" role="tab" aria-selected="false" data-tab="settings" onclick="setTab('settings')">Settings</button>
        <button class="tab" role="tab" aria-selected="false" data-tab="widget" onclick="setTab('widget')">Widget</button>
      </div>
      <div class="card panel" id="tabBody"></div>
    </div>
    <div id="onboardPanel" class="card panel hidden"></div>
    <div id="adminHome" class="card panel hidden">
      <div class="estate"><div class="eico">🏢</div>
        <div class="etitle">Select a business</div>
        <div class="ehint">Choose a business on the left to see its bookings, leads and settings — or add a new one.</div></div>
    </div>
  </div>
</div>

<div class="toast" id="toast" role="status" aria-live="polite"></div>

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

  // ---- purely-visual helpers (initials avatars, chips, empty/loading states, KPIs) ----
  function nameHue(s){ s=String(s==null?"":s); let h=0; for(let i=0;i<s.length;i++){ h=(h*31+s.charCodeAt(i))>>>0; } return h%360; }
  function avatar(name){
    const n=String(name==null?"":name).trim()||"?"; const h=nameHue(n);
    return `<span class="wav" style="background:hsl(${h},55%,88%);color:hsl(${h},55%,35%)">${esc(n.charAt(0).toUpperCase())}</span>`;
  }
  function who(name){ return `<span class="who">${avatar(name)}<span>${esc(name)}</span></span>`; }
  function estate(ico, title, hint){
    return `<div class="estate"><div class="eico">${ico}</div><div class="etitle">${esc(title)}</div><div class="ehint">${esc(hint)}</div></div>`;
  }
  // skeleton rows shown while a tab's data is in flight (screen readers get "Loading")
  function skel(){
    let rows="";
    for(let i=0;i<4;i++){
      rows += `<div class="skelrow"><span class="sk av"></span><span class="sk" style="width:${26+i*9}%"></span><span class="sk" style="width:12%;margin-left:auto"></span></div>`;
    }
    return `<div aria-hidden="true">${rows}</div><span class="visually-hidden" role="status">Loading…</span>`;
  }
  function todayISO(){
    const t=new Date();
    return t.getFullYear()+"-"+String(t.getMonth()+1).padStart(2,"0")+"-"+String(t.getDate()).padStart(2,"0");
  }
  // The owner's value-proof row: one authorized /metrics call fills all six.
  async function loadStats(){
    const biz = CURRENT;
    ["mToday","mChats","mMsgs","mBookings","mLeads","mHours"].forEach(id => $(id).textContent="–");
    try{
      const r = await api("/metrics?business_id="+encodeURIComponent(biz));
      if(biz !== CURRENT || !r.ok) return;
      const m = await r.json();
      $("mToday").textContent = m.conversations_today;
      $("mChats").textContent = m.conversations_30d;
      $("mMsgs").textContent = m.messages_30d;
      $("mBookings").textContent = m.bookings_30d;
      $("mLeads").textContent = m.leads_30d;
      $("mHours").textContent = "~" + m.hours_saved_30d_estimate + "h";
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
      if(!r.ok){ $("loginErr").textContent = r.status===403||r.status===401 ? "That Business ID and key don't match. Check both and try again." : "Could not sign in — please try again."; return; }
      MODE="clinic"; CURRENT=bid;
      try{ sessionStorage.setItem("ra_key",key); sessionStorage.setItem("ra_bid",bid); }catch(e){}
      const biz = await r.json();
      enterApp(biz.name || bid);
      $("side").classList.add("hidden");
      openBusiness(bid, biz);
    } else {
      const r = await api("/businesses");
      if(!r.ok){ $("loginErr").textContent = r.status===503 ? "Admin access isn't configured on this server." : "That admin key isn't valid."; return; }
      MODE="admin";
      try{ sessionStorage.setItem("ra_key",key); sessionStorage.setItem("ra_bid",""); }catch(e){}
      enterApp("Admin");
      $("side").classList.remove("hidden");
      $("adminHome").classList.remove("hidden");
      renderBizList(await r.json());
    }
  }

  function enterApp(title){ $("login").classList.add("hidden"); $("app").classList.remove("hidden"); $("appTitle").textContent = title; }
  function signOut(){
    try{ sessionStorage.removeItem("ra_key"); sessionStorage.removeItem("ra_bid"); }catch(e){}
    KEY=null; MODE=null; CURRENT=null; location.reload();
  }
  // Survive F5 (industry-standard admin behavior): re-validate the stored
  // session key against the server instead of dumping the user at login.
  // sessionStorage = per-tab, cleared when the tab closes — deliberate choice
  // for a key-based login (localStorage would outlive the visit).
  (function restoreSession(){
    let k=null, b=null;
    try{ k=sessionStorage.getItem("ra_key"); b=sessionStorage.getItem("ra_bid"); }catch(e){}
    if(!k) return;
    $("key").value = k; $("bid").value = b || "";
    signIn();
  })();

  // ---- admin: list + onboard ----
  function renderBizList(list){
    const box = $("bizList");
    box.innerHTML = (list||[]).map(b =>
      `<button class="biz-item" data-id="${esc(b.id)}" onclick="openBusiness('${esc(b.id)}')">
         <b>${esc(b.name)}</b><small>${esc(b.type)} · ${esc(b.id)}</small></button>`).join("") || "<div class='empty'>No businesses yet — add your first one above.</div>";
  }
  function showOnboard(){
    CURRENT=null;
    $("bizPanel").classList.add("hidden"); $("adminHome").classList.add("hidden");
    const p = $("onboardPanel"); p.classList.remove("hidden");
    p.innerHTML = `<h3>Set up a new business</h3>
      <p class="lead">This one form is the whole onboarding — the receptionist is live the moment you create it.</p>

      <div class="fgroup first">
        <div class="fghead"><span class="fgnum">1</span><span class="fgtitle">The basics</span></div>
        <p class="fgwhy">How the receptionist introduces itself — and how it behaves.</p>
        <div class="row2"><div><label for="o_id">Business ID <span class="soft">(lowercase-and-dashes, permanent)</span></label><input id="o_id" placeholder="velvet-hair"></div>
        <div><label for="o_name">Business name</label><input id="o_name" placeholder="Velvet Hair Studio"></div></div>
        <div class="row2"><div><label for="o_type">What kind of business?</label><input id="o_type" placeholder="hair salon"></div>
        <div><label for="o_vertical">Vertical <span class="soft">(tunes how it books &amp; follows up)</span></label>
        <select id="o_vertical"><option value="general">General</option><option value="clinic">Clinic</option><option value="salon">Salon &amp; spa</option><option value="real_estate">Real estate</option></select></div></div>
        <label for="o_tone">How should it sound?</label><input id="o_tone" placeholder="warm and friendly">
      </div>

      <div class="fgroup">
        <div class="fghead"><span class="fgnum">2</span><span class="fgtitle">What customers can book</span></div>
        <p class="fgwhy">This drives real availability — the agent only ever offers genuinely free slots.</p>
        <label for="o_services">Services</label><input id="o_services" placeholder="checkups, cleanings, whitening…">
        <label for="o_hours">Opening hours <span class="soft">(as customers should hear them)</span></label><input id="o_hours" placeholder="Mon–Fri 9am–5pm">
        <div class="row2"><div><label for="o_open">Open hour <span class="soft">(0–23)</span></label><input id="o_open" type="number" min="0" max="23" value="9"></div>
        <div><label for="o_close">Close hour <span class="soft">(1–24)</span></label><input id="o_close" type="number" min="1" max="24" value="17"></div>
        <div><label for="o_slot">Slot length <span class="soft">(minutes, 5–240)</span></label><input id="o_slot" type="number" min="5" max="240" value="30"></div></div>
        <div class="row2"><div><label for="o_notice">Min notice <span class="soft">(hours)</span></label><input id="o_notice" type="number" min="0" max="72" value="1"></div>
        <div><label for="o_advance">Book ahead <span class="soft">(days)</span></label><input id="o_advance" type="number" min="1" max="365" value="60"></div>
        <div><label for="o_buffer">Buffer <span class="soft">(mins between)</span></label><input id="o_buffer" type="number" min="0" max="120" value="0"></div></div>
      </div>

      <div class="fgroup">
        <div class="fghead"><span class="fgnum">3</span><span class="fgtitle">Who's on the team?</span></div>
        <p class="fgwhy">So the AI can recommend the right person automatically when a customer asks.</p>
        <label for="o_staff">Team &amp; specialties</label>
        <input id="o_staff" placeholder="Marwan — fades specialist · Tony — classic cuts &amp; beards">
      </div>

      <div class="fgroup">
        <div class="fghead"><span class="fgnum">4</span><span class="fgtitle">Finding you &amp; house rules</span></div>
        <p class="fgwhy">It gives directions and applies your policies — so your staff never has to be the bad guy.</p>
        <label for="o_location">Location &amp; directions</label>
        <input id="o_location" placeholder="Al Barsha 1, near MoE metro exit 2 — free parking behind the building">
        <label for="o_policies">Policies <span class="soft">(cancellations, walk-ins, payments, deposits)</span></label>
        <textarea id="o_policies" rows="2" placeholder="Reschedule up to 2h before. Walk-ins welcome, bookings get priority. Cash &amp; card."></textarea>
        <label for="o_notify">Owner email for instant alerts <span class="soft">(every booking &amp; lead — leave empty to skip)</span></label>
        <input id="o_notify" type="email" placeholder="owner@business.com">
      </div>

      <div class="fgroup">
        <div class="fghead"><span class="fgnum">5</span><span class="fgtitle">Anything else it should know</span></div>
        <p class="fgwhy">Prices, insurance, offers, parking — the agent answers from this knowledge.</p>
        <label for="o_faq">FAQ / extra knowledge</label><textarea id="o_faq" rows="3" placeholder="Prices, insurance, loyalty program…"></textarea>
      </div>

      <div style="margin-top:24px"><button class="btn" onclick="doOnboard()">Create business</button></div>
      <p class="note">Creating a business generates its API key. The key is shown once — copy it right away.</p>
      <div id="onboardResult"></div>`;
  }
  async function doOnboard(){
    const body = { id:val("o_id").trim(), name:val("o_name").trim(), type:val("o_type").trim(),
      tone:val("o_tone").trim()||"warm and professional", hours:val("o_hours").trim(), services:val("o_services").trim(),
      faq:val("o_faq").trim(), staff:val("o_staff").trim(), location:val("o_location").trim(),
      policies:val("o_policies").trim(), open_hour:+val("o_open"), close_hour:+val("o_close"), slot_minutes:+val("o_slot"),
      min_notice_hours:+val("o_notice"), max_advance_days:+val("o_advance"), buffer_min:+val("o_buffer"),
      notify_email:val("o_notify").trim(), vertical:val("o_vertical") };
    if(!body.id||!body.name||!body.type){ toast("ID, name and type are required."); return; }
    const r = await api("/admin/businesses", { method:"POST", body: JSON.stringify(body) });
    const d = await r.json();
    if(!r.ok){ toast(apiErr(d, "Could not create the business.")); return; }
    $("onboardResult").innerHTML = `<div class="okcard">
      <div class="oktitle">✓ ${esc(body.name)} is live</div>
      <div class="note">This is their API key — it's shown once, so copy it now. They sign in to this dashboard with it.</div>
      <div class="keybox" id="newKey">${esc(d.api_key)}</div>
      <div class="okrow"><button class="btn ghost" onclick="copyKey()">Copy key</button></div>
      <div class="note">Customer chat link: <code>/widget?business_id=${esc(d.id)}</code></div></div>`;
    const r2 = await api("/businesses"); if(r2.ok) renderBizList(await r2.json());
  }
  function copyKey(){
    const el = $("newKey"); if(!el) return;
    try{ navigator.clipboard.writeText(el.textContent).then(()=>toast("Key copied to clipboard")); }
    catch(e){ toast("Select the key and copy it manually."); }
  }

  // ---- shared business panel ----
  async function openBusiness(id, preBiz){
    CURRENT = id; TAB = "bookings";
    $("onboardPanel").classList.add("hidden"); $("adminHome").classList.add("hidden");
    $("bizPanel").classList.remove("hidden");
    document.querySelectorAll(".biz-item").forEach(e => e.classList.toggle("active", e.dataset.id===id));
    document.querySelectorAll(".tab").forEach(t => { const on=t.dataset.tab==="bookings"; t.classList.toggle("active", on); t.setAttribute("aria-selected", on?"true":"false"); });
    loadStats();
    renderTab();
  }
  function setTab(t){
    TAB=t;
    document.querySelectorAll(".tab").forEach(x=>{ const on=x.dataset.tab===t; x.classList.toggle("active",on); x.setAttribute("aria-selected", on?"true":"false"); });
    renderTab();
  }

  async function renderTab(){
    const body = $("tabBody"); body.innerHTML = skel();
    if(TAB==="bookings"){
      const r = await api("/bookings?business_id="+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML = estate("⚠️","Couldn't load bookings","Check your connection and switch tabs to retry."); return; }
      const rows = await r.json();
      loadStats();
      body.innerHTML = rows.length ? `<div class="tablewrap"><table><thead><tr><th>Customer</th><th>Date</th><th>Time</th><th>Phone</th><th>Reason</th></tr></thead>
        <tbody>${rows.map(b=>`<tr><td>${who(b.patient_name)}</td><td class="num">${esc(b.date)}</td><td class="num">${esc(b.time)}</td><td class="num">${esc(b.phone)}</td><td>${esc(b.reason)}</td></tr>`).join("")}</tbody></table></div>`
        : estate("📅","No bookings yet","Share your chat link — every appointment the receptionist books lands here, in real time.");
    } else if(TAB==="leads"){
      const r = await api("/leads?business_id="+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML = estate("⚠️","Couldn't load leads","Check your connection and switch tabs to retry."); return; }
      const rows = await r.json();
      loadStats();
      body.innerHTML = rows.length ? `<div class="tablewrap"><table><thead><tr><th>Name</th><th>Phone</th><th>Interest</th><th>Notes</th></tr></thead>
        <tbody>${rows.map(l=>`<tr><td>${who(l.name)}</td><td class="num">${esc(l.phone)}</td><td>${l.interest?`<span class="chip new">${esc(l.interest)}</span>`:""}</td><td>${esc(l.notes)}</td></tr>`).join("")}</tbody></table></div>`
        : estate("📥","No leads yet","When someone isn't ready to book, the receptionist captures their name and number — you'll see them here.");
    } else if(TAB==="settings"){
      const r = await api("/manage/"+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML = estate("⚠️","Couldn't load settings","Check your connection and switch tabs to retry."); return; }
      const b = await r.json();
      body.innerHTML = `<h3>Settings</h3>
        <p class="lead">Everything the receptionist knows about this business. Changes apply to the very next conversation.</p>

        <div class="fgroup first">
          <div class="fghead"><span class="fgtitle">Identity</span></div>
          <div class="row2"><div><label for="s_name">Business name</label><input id="s_name" value="${esc(b.name)}"></div>
          <div><label for="s_type">Business type</label><input id="s_type" value="${esc(b.type)}"></div></div>
          <label for="s_vertical">Vertical <span class="soft">(tunes how the agent books &amp; follows up)</span></label>
          <select id="s_vertical"><option value="clinic">Clinic</option><option value="salon">Salon &amp; spa</option><option value="real_estate">Real estate</option><option value="general">General</option></select>
          <label for="s_tone">Tone</label><input id="s_tone" value="${esc(b.tone)}">
        </div>

        <div class="fgroup">
          <div class="fghead"><span class="fgtitle">Services &amp; hours</span></div>
          <label for="s_services">Services</label><input id="s_services" value="${esc(b.services)}">
          <label for="s_hours">Opening hours <span class="soft">(as customers should hear them)</span></label><input id="s_hours" value="${esc(b.hours)}">
          <div class="row2"><div><label for="s_open">Open hour <span class="soft">(0–23)</span></label><input id="s_open" type="number" min="0" max="23" value="${esc(b.open_hour)}"></div>
          <div><label for="s_close">Close hour <span class="soft">(1–24)</span></label><input id="s_close" type="number" min="1" max="24" value="${esc(b.close_hour)}"></div>
          <div><label for="s_slot">Slot length <span class="soft">(minutes)</span></label><input id="s_slot" type="number" min="5" max="240" value="${esc(b.slot_minutes)}"></div></div>
          <div class="row2"><div><label for="s_notice">Min notice <span class="soft">(hours)</span></label><input id="s_notice" type="number" min="0" max="72" value="${esc(b.min_notice_hours == null ? 1 : b.min_notice_hours)}"></div>
          <div><label for="s_advance">Book ahead <span class="soft">(days)</span></label><input id="s_advance" type="number" min="1" max="365" value="${esc(b.max_advance_days == null ? 60 : b.max_advance_days)}"></div>
          <div><label for="s_buffer">Buffer <span class="soft">(mins)</span></label><input id="s_buffer" type="number" min="0" max="120" value="${esc(b.buffer_min == null ? 0 : b.buffer_min)}"></div></div>
        </div>

        <div class="fgroup">
          <div class="fghead"><span class="fgtitle">Team, location &amp; policies</span></div>
          <label for="s_staff">Team &amp; specialties <span class="soft">(so it recommends the right person)</span></label><input id="s_staff" value="${esc(b.staff)}" placeholder="Marwan — fades · Tony — beards">
          <label for="s_location">Location &amp; directions</label><input id="s_location" value="${esc(b.location)}" placeholder="Area, landmark, parking">
          <label for="s_policies">Policies</label><textarea id="s_policies" rows="2" placeholder="Cancellations, walk-ins, payments">${esc(b.policies)}</textarea>
          <label for="s_notify">Owner email for instant alerts <span class="soft">(every booking &amp; lead)</span></label>
          <input id="s_notify" type="email" value="${esc(b.notify_email)}" placeholder="owner@business.com">
        </div>

        <div class="fgroup">
          <div class="fghead"><span class="fgtitle">Knowledge</span></div>
          <label for="s_faq">FAQ / extra knowledge the agent can use</label><textarea id="s_faq" rows="4">${esc(b.faq)}</textarea>
        </div>

        <div style="margin-top:22px"><button class="btn" onclick="saveSettings()">Save changes</button></div>`;
      $("s_vertical").value = b.vertical || "general";
    } else {
      const url = location.origin + "/widget?business_id=" + encodeURIComponent(CURRENT);
      body.innerHTML = `<h3>Your chat widget</h3>
        <p class="lead">This is where customers talk to your receptionist. Put it on your website, Instagram bio, or WhatsApp auto-reply.</p>
        <label>Direct link</label>
        <div class="keybox">${esc(url)}</div>
        <div style="margin:14px 0 22px"><a href="${esc(url)}" target="_blank" rel="noopener"><button class="btn">Open the widget ↗</button></a></div>
        <label>Embed on your website</label>
        <div class="keybox">&lt;iframe src="${esc(url)}" style="width:380px;height:560px;border:0;border-radius:16px"&gt;&lt;/iframe&gt;</div>
        <p class="note">Paste that once and the receptionist appears on the page — no other code needed.</p>`;
    }
  }

  async function saveSettings(){
    const body = { name:val("s_name"), type:val("s_type"), tone:val("s_tone"), hours:val("s_hours"),
      services:val("s_services"), faq:val("s_faq"), staff:val("s_staff"), location:val("s_location"),
      policies:val("s_policies"), open_hour:+val("s_open"), close_hour:+val("s_close"),
      slot_minutes:+val("s_slot"), vertical:val("s_vertical"),
      min_notice_hours:+val("s_notice"), max_advance_days:+val("s_advance"), buffer_min:+val("s_buffer"),
      notify_email:val("s_notify").trim() };
    const r = await api("/manage/"+encodeURIComponent(CURRENT), { method:"POST", body: JSON.stringify(body) });
    if(r.ok){ toast("Settings saved — live from the next conversation"); return; }
    let d=null; try{ d = await r.json(); }catch(e){}
    toast(apiErr(d, "Couldn't save — please try again"));
  }
</script>
</body>
</html>"""
