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
    --canvas:#faf9f6; --surface:#f7f5f1; --surface-2:#f1eee7; --card:#ffffff;
    --hairline:#e6e1d8; --hairline-2:#d5cec1; --ink:#0d1b26; --body:#46565f; --muted:#7a8892;
    --accent:#0d1b26; --accent-deep:#1b3340; --accent-soft:#f3e9d7;
    --gold:#b8863b; --gold-deep:#8a6224;
    --ok:#147a3d; --ok-soft:#e8f7ee; --danger:#c02543;
    --focus:rgba(184,134,59,.35);
    --shadow-card:0 0 0 1px rgba(23,21,31,.04),0 1px 1px rgba(13,27,38,.03),0 2px 4px rgba(13,27,38,.04),0 8px 16px -4px rgba(13,27,38,.06);
    --shadow-float:0 1px 1px rgba(13,27,38,.03),0 8px 16px -4px rgba(13,27,38,.06),0 24px 32px -8px rgba(13,27,38,.12);
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;
    font-feature-settings:'cv11','ss01';-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
    color:var(--ink);background:var(--canvas);font-size:16px;line-height:1.55}
  ::selection{background:rgba(184,134,59,.22)}
  :focus-visible{outline:2px solid var(--focus);outline-offset:2px}
  .hidden{display:none !important}
  .visually-hidden{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
  h3{font-size:19px;font-weight:600;letter-spacing:-.015em;margin:0 0 4px}
  .lead{font-size:14px;color:var(--muted);margin:0 0 10px}
  /* buttons */
  button{font:inherit;cursor:pointer;border:0;background:none;color:inherit}
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 22px;border-radius:999px;
    font-size:14.5px;font-weight:600;background:var(--accent);color:#fff;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 1px 2px rgba(13,27,38,.24);transition:background .15s,transform .15s}
  .btn:hover{background:var(--accent-deep);transform:translateY(-1px)}
  .btn:active{transform:translateY(0)}
  .btn.ghost{background:var(--card);color:var(--body);border:1px solid var(--hairline-2);box-shadow:none}
  .btn.ghost:hover{background:var(--surface);color:var(--ink);transform:none}
  /* forms */
  input,textarea,select{font:inherit;font-size:14.5px;width:100%;padding:10px 12px;border:1px solid var(--hairline-2);
    border-radius:8px;outline:none;background:var(--card);color:var(--ink);transition:border-color .15s,box-shadow .15s}
  input::placeholder,textarea::placeholder{color:#9aa6ae}
  input:focus,textarea:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--focus)}
  label{display:block;font-size:13px;font-weight:500;color:var(--body);margin:14px 0 6px}
  .card{background:var(--card);border:1px solid var(--hairline);border-radius:12px;box-shadow:var(--shadow-card)}
  /* real-estate agency profile card (owner's view) — the AI's understanding, surfaced */
  .profile-card{margin-bottom:18px;padding:16px 18px}
  .prof-head{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin-bottom:14px}
  .prof-name{font-size:17px;font-weight:700;letter-spacing:-.01em}
  .prof-orn{font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
    color:var(--gold-deep);background:var(--accent-soft);border:1px solid #e7d3ad;border-radius:6px;padding:3px 8px}
  .prof-focus{font-size:12.5px;color:var(--muted);margin-left:auto}
  .prof-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px 20px}
  .prof-lbl{display:block;font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:600;margin-bottom:6px}
  .prof-val{font-size:14px;color:var(--ink);line-height:1.5}
  .prof-tags{display:flex;flex-wrap:wrap;gap:6px}
  .prof-tag{font-size:12.5px;color:var(--body);background:var(--surface);border:1px solid var(--hairline);border-radius:999px;padding:3px 10px}
  /* form groups (stepped-feel onboarding + settings) */
  .fgroup{margin-top:28px;padding-top:24px;border-top:1px solid var(--surface-2)}
  .fgroup.first{margin-top:12px;padding-top:0;border-top:0}
  .fghead{display:flex;align-items:center;gap:10px}
  .fgnum{flex:none;width:24px;height:24px;border-radius:50%;background:var(--accent-soft);color:var(--gold-deep);
    display:inline-flex;align-items:center;justify-content:center;font-size:12.5px;font-weight:600;font-variant-numeric:tabular-nums}
  .fgtitle{font-size:15px;font-weight:600;letter-spacing:-.01em}
  .fgwhy{font-size:13px;color:var(--muted);margin:5px 0 0 34px}
  /* login */
  #login{position:relative;min-height:100vh;display:grid;place-items:center;padding:20px;overflow:hidden}
  .hero-glow{position:absolute;inset:-20% -10% auto;height:70%;
    background:radial-gradient(38% 45% at 22% 30%,rgba(184,134,59,.22),transparent 70%),
      radial-gradient(30% 40% at 68% 20%,rgba(255,158,122,.16),transparent 70%);
    filter:blur(60px);pointer-events:none;opacity:.55}
  #login .card{position:relative;padding:32px 28px;width:100%;max-width:400px;box-shadow:var(--shadow-float)}
  .wordmark{font-size:17px;font-weight:700;letter-spacing:-.015em;
    text-decoration:none;color:var(--ink);display:inline-block}
  a.wordmark:hover{opacity:.75}
  .wordmark span{color:var(--gold-deep)}
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
    font-size:14px;font-weight:600;color:var(--gold-deep);background:var(--accent-soft);transition:background .15s}
  .onboard-row:hover{background:#ead9bd}
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
  /* calendar view — the owner reads bookings as a diary, not a spreadsheet */
  .calsub{display:flex;align-items:center;gap:16px;flex-wrap:wrap;background:var(--card);
    border:1px solid var(--hairline);border-radius:12px;padding:16px 18px;margin-bottom:18px;
    box-shadow:var(--shadow-card)}
  .calsub-h{flex:1;min-width:260px}
  .calsub-h b{display:block;font-size:14.5px;font-weight:650;color:var(--ink)}
  .calsub-h span{display:block;font-size:13px;color:var(--muted);margin-top:3px;line-height:1.5}
  .calsub-a{flex:none}
  .calsub #calUrlBox{flex-basis:100%}
  .calsub .note{font-size:12px;color:var(--muted);margin-top:7px}
  .calwrap{display:flex;flex-direction:column;gap:14px}
  .calday{background:var(--card);border:1px solid var(--hairline);border-radius:12px;
    overflow:hidden;box-shadow:var(--shadow-card)}
  .calday.is-today{border-color:var(--gold)}
  .caldate{display:flex;align-items:center;gap:9px;padding:11px 16px;background:var(--surface);
    border-bottom:1px solid var(--hairline)}
  .caldate b{font-size:14.5px;font-weight:650;color:var(--ink)}
  .caldate span{font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums}
  .todaytag{font-style:normal;font-size:10.5px;font-weight:700;letter-spacing:.06em;
    text-transform:uppercase;padding:2px 7px;border-radius:5px;background:var(--accent-soft);color:var(--gold-deep)}
  .calslots{display:flex;flex-direction:column}
  .calslot{display:grid;grid-template-columns:88px 1fr auto auto;align-items:center;gap:14px;
    padding:12px 16px;border-top:1px solid var(--surface-2)}
  .calslot:first-child{border-top:0}
  .ctime{font-size:14px;font-weight:650;color:var(--ink);font-variant-numeric:tabular-nums}
  .cwho b{display:block;font-size:14px;font-weight:600;color:var(--ink)}
  .cwho span{display:block;font-size:12.5px;color:var(--muted)}
  .cphone{font-size:13px;color:var(--muted);white-space:nowrap}
  .cadd{font-size:12.5px;font-weight:600;color:var(--gold-deep);text-decoration:none;white-space:nowrap;
    border:1px solid var(--hairline-2);padding:6px 11px;border-radius:8px;transition:background .15s}
  .cadd:hover{background:var(--accent-soft);border-color:var(--gold)}
  @media (max-width:640px){
    .calslot{grid-template-columns:70px 1fr;row-gap:6px}
    .cphone,.cadd{grid-column:2}
  }
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
    <a class="wordmark" href="/" title="Back to the site">Reception<span>AI</span></a>
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
    <a class="wordmark" href="/" title="Back to the site">Reception<span>AI</span></a>
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
      <div id="profileCard" class="card panel profile-card hidden"></div>
      <div class="tabs" role="tablist" aria-label="Dashboard sections">
        <button class="tab active" role="tab" aria-selected="true" data-tab="bookings" onclick="setTab('bookings')">Bookings</button>
        <button class="tab" role="tab" aria-selected="false" data-tab="leads" onclick="setTab('leads')">Leads</button>
        <button class="tab" role="tab" aria-selected="false" data-tab="chats" onclick="setTab('chats')">Conversations</button>
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

      <div class="fgroup first" style="background:var(--accent-soft);border-color:#ded4ff">
        <div class="fghead"><span class="fgnum">✨</span><span class="fgtitle">Start from their website</span></div>
        <p class="fgwhy">Paste the business's site and the form below fills itself — then just review and edit.</p>
        <div style="display:flex;gap:10px;align-items:flex-end">
          <div style="flex:1"><label for="o_url">Website</label><input id="o_url" placeholder="https://thebusiness.com"></div>
          <button class="btn" type="button" id="importBtn" onclick="doImport()" style="flex:none">Import</button>
        </div>
        <label for="o_desc">No website? Describe the business instead <span class="soft">(rough notes are fine)</span></label>
        <textarea id="o_desc" rows="2" placeholder="Barbershop in Karama. Fades 60 AED, beard 40. Barbers Tony and Ali. Open 10am–10pm, Fri from 2pm."></textarea>
      </div>

      <div class="fgroup">
        <div class="fghead"><span class="fgnum">1</span><span class="fgtitle">The basics</span></div>
        <p class="fgwhy">How the receptionist introduces itself — and how it behaves.</p>
        <div class="row2"><div><label for="o_id">Business ID <span class="soft">(lowercase-and-dashes, permanent)</span></label><input id="o_id" placeholder="velvet-hair"></div>
        <div><label for="o_name">Business name</label><input id="o_name" placeholder="Velvet Hair Studio"></div></div>
        <div class="row2"><div><label for="o_type">What kind of business?</label><input id="o_type" placeholder="hair salon"></div>
        <div><label for="o_vertical">Vertical <span class="soft">(tunes how it books &amp; follows up)</span></label>
        <select id="o_vertical" onchange="toggleOnboardRE()"><option value="real_estate">Real estate</option><option value="general">General</option><option value="clinic">Clinic</option><option value="salon">Salon &amp; spa</option></select></div></div>
        <label for="o_tone">How should it sound?</label><input id="o_tone" placeholder="warm and friendly">
      </div>

      <div class="fgroup">
        <div class="fghead"><span class="fgnum">2</span><span class="fgtitle">What customers can book</span></div>
        <p class="fgwhy">This drives real availability — the agent only ever offers genuinely free slots.</p>
        <label for="o_services">Services</label><input id="o_services" placeholder="checkups, cleanings, whitening…">
        <label for="o_services_rows">Service menu <span class="soft">(optional — one per line: name | minutes | price)</span></label>
        <textarea id="o_services_rows" rows="3" placeholder="skin fade | 45 | 80 AED&#10;beard trim | 15 | 30 AED"></textarea>
        <p class="note">Menu lines drive real appointment lengths and the exact prices the agent quotes; the Services line above stays as friendly descriptive copy.</p>
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
        <label for="o_staff">Team &amp; specialties <span class="soft">(for real estate: agents + their areas &amp; languages)</span></label>
        <input id="o_staff" placeholder="Omar — Marina, EN/AR · Jessica — Dubai Hills, EN">
      </div>

      <div class="fgroup" id="o_re_group">
        <div class="fghead"><span class="fgnum">🏢</span><span class="fgtitle">Real-estate profile</span></div>
        <p class="fgwhy">So the agent understands your agency — it answers area questions honestly, routes to the right agent, and can state your RERA registration for trust.</p>
        <label for="o_areas">Areas / communities you cover</label>
        <input id="o_areas" placeholder="JVC, Dubai Marina, Downtown, Business Bay">
        <div class="row2"><div><label for="o_focus">Focus <span class="soft">(sale / rent / off-plan)</span></label>
        <input id="o_focus" placeholder="Secondary sales + rentals; some off-plan"></div>
        <div><label for="o_orn">RERA ORN <span class="soft">(broker reg. number)</span></label>
        <input id="o_orn" placeholder="12345"></div></div>
        <label for="o_languages">Languages your team speaks</label>
        <input id="o_languages" placeholder="English, Arabic, Hindi">
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
        <div class="row2"><div><label for="o_transfer">Transfer number <span class="soft">(shared when a caller asks for a human)</span></label>
        <input id="o_transfer" placeholder="+971 50 123 4567"></div>
        <div><label for="o_afterhours">When you're closed, the agent should…</label>
        <select id="o_afterhours"><option value="take_message">Take a message (name + number for a callback)</option><option value="book_only">Keep booking — staff confirm when you open</option><option value="info_only">Answer questions only — no bookings</option></select></div></div>
      </div>

      <div class="fgroup">
        <div class="fghead"><span class="fgnum">5</span><span class="fgtitle">Anything else it should know</span></div>
        <p class="fgwhy">Prices, insurance, offers, parking — the agent answers from this knowledge.</p>
        <label for="o_faq">FAQ / extra knowledge</label><textarea id="o_faq" rows="3" placeholder="Prices, insurance, loyalty program…"></textarea>
      </div>

      <div style="margin-top:24px"><button class="btn" onclick="doOnboard()">Create business</button></div>
      <p class="note">Creating a business generates its API key. The key is shown once — copy it right away.</p>
      <div id="onboardResult"></div>`;
    toggleOnboardRE();
  }
  // The Real-estate profile group only makes sense for a real-estate vertical.
  function toggleOnboardRE(){
    const g = $("o_re_group"); if(!g) return;
    g.style.display = (val("o_vertical")==="real_estate") ? "" : "none";
  }
  function toggleSettingsRE(){
    const g = $("s_re_group"); if(!g) return;
    g.style.display = (val("s_vertical")==="real_estate") ? "" : "none";
  }
  async function doImport(){
    const url = val("o_url").trim(), desc = val("o_desc").trim();
    if(!url && !desc){ toast("Paste their website — or describe the business below."); return; }
    const btn = $("importBtn"); btn.disabled = true; btn.textContent = "Reading…";
    try{
      const r = await api("/onboarding/import", { method:"POST", body: JSON.stringify({url, description: desc}) });
      const d = await r.json();
      if(!r.ok){ toast(apiErr(d, "Couldn't read that website.")); return; }
      // Prefill everything — the human reviews and edits before creating.
      const map = { name:"o_name", type:"o_type", tone:"o_tone", hours:"o_hours", services:"o_services",
        staff:"o_staff", location:"o_location", policies:"o_policies", faq:"o_faq",
        areas_covered:"o_areas", deal_focus:"o_focus", languages:"o_languages", orn:"o_orn" };
      for(const k in map){ if(d[k]) $(map[k]).value = d[k]; }
      if(d.open_hour != null) $("o_open").value = d.open_hour;
      if(d.close_hour != null) $("o_close").value = d.close_hour;
      if(d.vertical) $("o_vertical").value = d.vertical;
      toggleOnboardRE();  // reveal the RE group if the import detected real estate
      if(d.name && !val("o_id")) $("o_id").value = d.name.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,40);
      toast("Imported — review every field, then create ✨");
    } catch(e){ toast("Couldn't read that website."); }
    finally { btn.disabled = false; btn.textContent = "Import"; }
  }

  // "name | minutes | price" textarea lines -> [{name, duration_min, price}].
  // null = a malformed line (better to say so up front than lose their menu
  // to a server-side 422 after everything else already saved).
  function parseServiceRows(text){
    const rows=[];
    for(const line of String(text||"").split("\\n")){
      const t=line.trim(); if(!t) continue;
      const p=t.split("|").map(x=>x.trim());
      const mins=parseInt(p[1],10);
      if(!p[0] || !isFinite(mins)) return null;
      rows.push({name:p[0], duration_min:mins, price:p[2]||""});
    }
    return rows;
  }
  function serviceRowsText(rows){
    return (rows||[]).map(s=>s.name+" | "+s.duration_min+(s.price?" | "+s.price:"")).join("\\n");
  }
  // Listings lines: title | area | bedrooms | price | sale or rent | permit | notes.
  // Only the title is required — owners fill what they have. The permit is the
  // Trakheesi/Madhmoun number; a listing without one can't be advertised.
  function parseListingRows(text){
    const rows=[];
    for(const line of String(text||"").split("\\n")){
      const t=line.trim(); if(!t) continue;
      const p=t.split("|").map(x=>x.trim());
      if(!p[0]) return null;
      rows.push({title:p[0], area:p[1]||"", bedrooms:p[2]||"", price:p[3]||"", purpose:p[4]||"", permit_number:p[5]||"", notes:p[6]||""});
    }
    return rows;
  }
  function listingRowsText(rows){
    return (rows||[]).map(l=>[l.title,l.area,l.bedrooms,l.price,l.purpose,l.permit_number,l.notes].join(" | ")
      .replace(/( \\|)+ *$/,"")).join("\\n");
  }

  async function doOnboard(){
    const body = { id:val("o_id").trim(), name:val("o_name").trim(), type:val("o_type").trim(),
      tone:val("o_tone").trim()||"warm and professional", hours:val("o_hours").trim(), services:val("o_services").trim(),
      faq:val("o_faq").trim(), staff:val("o_staff").trim(), location:val("o_location").trim(),
      policies:val("o_policies").trim(), open_hour:+val("o_open"), close_hour:+val("o_close"), slot_minutes:+val("o_slot"),
      min_notice_hours:+val("o_notice"), max_advance_days:+val("o_advance"), buffer_min:+val("o_buffer"),
      notify_email:val("o_notify").trim(), vertical:val("o_vertical"),
      transfer_number:val("o_transfer").trim(), after_hours_mode:val("o_afterhours"),
      areas_covered:val("o_areas").trim(), deal_focus:val("o_focus").trim(),
      languages:val("o_languages").trim(), orn:val("o_orn").trim() };
    if(!body.id||!body.name||!body.type){ toast("ID, name and type are required."); return; }
    const svcRows = parseServiceRows(val("o_services_rows"));
    if(svcRows===null){ toast("Service menu: each line needs 'name | minutes' (price optional)."); return; }
    const r = await api("/admin/businesses", { method:"POST", body: JSON.stringify(body) });
    const d = await r.json();
    if(!r.ok){ toast(apiErr(d, "Could not create the business.")); return; }
    // The menu has its own endpoint (replace semantics) — posted only after
    // the business exists, and only when the owner actually typed rows.
    if(svcRows.length){
      const rs = await api("/manage/"+encodeURIComponent(body.id)+"/services",
        { method:"POST", body: JSON.stringify({services: svcRows}) });
      if(!rs.ok) toast("Created — but the service menu didn't save. Fix it in Settings.");
    }
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
    renderProfile();
    renderTab();
  }

  // The real-estate agency profile, surfaced at the top of the owner's view —
  // the same facts the AI is grounded in (areas, focus, languages, ORN, agents).
  // Real-estate tenants only; other verticals just don't show the card.
  async function renderProfile(){
    const card = $("profileCard"); card.classList.add("hidden"); card.innerHTML = "";
    const forBiz = CURRENT;
    try{
      const r = await api("/manage/"+encodeURIComponent(forBiz));
      if(!r.ok || forBiz !== CURRENT) return;
      const b = await r.json();
      if((b.vertical||"") !== "real_estate") return;
      const has = [b.orn,b.areas_covered,b.languages,b.deal_focus,b.staff].some(x=>(x||"").trim());
      if(!has) return;  // an RE tenant with nothing filled in yet — nothing to show
      const tags = s => (s||"").split(/[,·]/).map(x=>x.trim()).filter(Boolean)
        .map(x=>`<span class="prof-tag">${esc(x)}</span>`).join("");
      const cells = [];
      if((b.areas_covered||"").trim()) cells.push(`<div><span class="prof-lbl">Areas covered</span><div class="prof-tags">${tags(b.areas_covered)}</div></div>`);
      if((b.languages||"").trim()) cells.push(`<div><span class="prof-lbl">Languages</span><div class="prof-tags">${tags(b.languages)}</div></div>`);
      if((b.staff||"").trim()) cells.push(`<div><span class="prof-lbl">Agents</span><div class="prof-val">${esc(b.staff)}</div></div>`);
      card.innerHTML =
        `<div class="prof-head"><span class="prof-name">${esc(b.name)}</span>`
        + ((b.orn||"").trim() ? `<span class="prof-orn">RERA ORN ${esc(b.orn)}</span>` : "")
        + ((b.deal_focus||"").trim() ? `<span class="prof-focus">${esc(b.deal_focus)}</span>` : "")
        + `</div>`
        + (cells.length ? `<div class="prof-grid">${cells.join("")}</div>` : "");
      card.classList.remove("hidden");
    }catch(e){}
  }
  function setTab(t){
    TAB=t;
    document.querySelectorAll(".tab").forEach(x=>{ const on=x.dataset.tab===t; x.classList.toggle("active",on); x.setAttribute("aria-selected", on?"true":"false"); });
    renderTab();
  }

  // ── calendar view helpers ───────────────────────────────────────────────
  function minutesOf(t){
    const m = String(t||"").trim().toUpperCase().match(/^(\\d{1,2})(?::(\\d{2}))?\\s*(AM|PM)?$/);
    if(!m) return 0;
    let h = +m[1]; const mins = +(m[2]||0), suf = m[3];
    if(suf==="AM" && h===12) h = 0;
    if(suf==="PM" && h!==12) h += 12;
    return h*60 + mins;
  }
  function dayName(d){
    const dt = new Date(d + "T00:00:00");
    return isNaN(dt) ? d : dt.toLocaleDateString(undefined,{weekday:"long"});
  }
  function prettyDate(d){
    const dt = new Date(d + "T00:00:00");
    return isNaN(dt) ? d : dt.toLocaleDateString(undefined,{day:"numeric",month:"short"});
  }

  // The .ics endpoint is API-key protected, so a plain <a href> can't fetch it —
  // pull it with the key, then hand the browser a blob to open in its calendar.
  async function addToCal(ev, bookingId){
    ev.preventDefault();
    const r = await api("/manage/"+encodeURIComponent(CURRENT)+"/bookings/"+bookingId+".ics");
    if(!r.ok){ toast("Couldn't build the calendar invite."); return; }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "viewing-" + bookingId + ".ics";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(()=>URL.revokeObjectURL(url), 4000);
    toast("Invite downloaded — open it to add it to your calendar.");
  }

  function calSubscribeBox(){
    return `<div class="calsub">
      <div class="calsub-h">
        <b>See these in your own calendar</b>
        <span>Get one link, paste it into Google Calendar (Other calendars → From URL) — every booking appears automatically. Works with Outlook and Apple too.</span>
      </div>
      <div class="calsub-a">
        <button class="btn ghost" onclick="makeCalUrl()">Get my calendar link</button>
      </div>
      <div id="calUrlBox" class="hidden">
        <div class="keybox" id="calUrl"></div>
        <p class="note">Anyone with this link can see your bookings — keep it private.
          Generating a new link cancels the old one.</p>
      </div>
    </div>`;
  }

  async function makeCalUrl(){
    const r = await api("/manage/"+encodeURIComponent(CURRENT)+"/calendar-token", {method:"POST"});
    if(!r.ok){ toast("Couldn't create the calendar link."); return; }
    const d = await r.json();
    $("calUrl").textContent = d.url;
    $("calUrlBox").classList.remove("hidden");
    try { await navigator.clipboard.writeText(d.url); toast("Link copied — paste it into Google Calendar."); }
    catch(e){ toast("Link ready — copy it into Google Calendar."); }
  }

  function convChannel(cid){ return String(cid||"").startsWith("wa-") ? "WhatsApp" : "Web"; }
  function convWho(cid){
    const s = String(cid||"");
    if(s.startsWith("wa-")) return "+" + s.slice(3);   // wa-971… -> +971…
    return "Web visitor";
  }
  async function openThread(cid){
    const body = $("tabBody"); body.innerHTML = skel();
    const base = "/manage/"+encodeURIComponent(CURRENT)+"/conversations/"+encodeURIComponent(cid);
    const [r, sr] = await Promise.all([api(base), api(base+"/status")]);
    if(!r.ok){ body.innerHTML = estate("⚠️","Couldn't open the conversation","Go back and try again."); return; }
    const msgs = await r.json();
    const paused = sr.ok ? (await sr.json()).ai_paused : false;
    const bubbles = msgs.map(m=>{
      const mine = m.role !== "user";  // the AI/business side
      const style = "max-width:72%;margin:6px 0;padding:9px 13px;border-radius:14px;white-space:pre-wrap;"
        + (mine ? "background:var(--accent-soft);margin-left:auto;border-bottom-right-radius:4px"
                : "background:#f1f1f4;border-bottom-left-radius:4px");
      return `<div style="${style}">${esc(m.text)}</div>`;
    }).join("");
    // When a human has taken the thread over the AI is silent — show a banner and
    // a "Hand back to AI" button; otherwise a hint that replying takes it over.
    const banner = paused
      ? `<div style="margin:8px 2px;padding:8px 11px;border-radius:10px;background:#fff5e6;color:#8a5a00;font-size:13px">
           ✋ You're handling this conversation — the AI is paused.
           <button class="btn ghost" style="margin-left:8px;padding:3px 9px" onclick="resumeThread('${esc(cid)}')">Hand back to AI</button>
         </div>`
      : `<div style="margin:8px 2px;color:var(--muted);font-size:12px">The AI is answering this thread. Send a reply to take it over.</div>`;
    body.innerHTML = `<button class="btn ghost" onclick="renderTab()">← Back to conversations</button>
      <div style="margin:10px 2px;color:var(--muted);font-size:13px">${esc(convWho(cid))} · ${esc(convChannel(cid))}</div>
      ${banner}
      <div style="display:flex;flex-direction:column">${bubbles || "<div class='empty'>No messages.</div>"}</div>
      <div style="display:flex;gap:8px;margin-top:12px">
        <input id="replyText" type="text" placeholder="Type a reply…" style="flex:1;padding:9px 12px;border:1px solid var(--line,#ddd);border-radius:10px"
               onkeydown="if(event.key==='Enter')sendReply('${esc(cid)}')">
        <button class="btn" onclick="sendReply('${esc(cid)}')">Send</button>
      </div>`;
  }

  async function sendReply(cid){
    const input = $("replyText"); const text = (input.value||"").trim();
    if(!text){ return; }
    input.disabled = true;
    const r = await api("/manage/"+encodeURIComponent(CURRENT)+"/conversations/"+encodeURIComponent(cid)+"/reply",
      {method:"POST", body: JSON.stringify({text})});
    if(!r.ok){ const d = await r.json().catch(()=>null); toast(apiErr(d,"Couldn't send the reply.")); input.disabled=false; return; }
    const d = await r.json();
    if(cid.startsWith("wa-") && !d.delivered){ toast("Saved — but WhatsApp delivery failed (check the channel)."); }
    else { toast("Sent — you're handling this thread now."); }
    openThread(cid);  // refresh: shows the new bubble + the paused banner
  }

  async function resumeThread(cid){
    const r = await api("/manage/"+encodeURIComponent(CURRENT)+"/conversations/"+encodeURIComponent(cid)+"/resume",
      {method:"POST"});
    if(!r.ok){ toast("Couldn't hand back to the AI."); return; }
    toast("Handed back — the AI is answering again.");
    openThread(cid);
  }

  async function renderTab(){
    const body = $("tabBody"); body.innerHTML = skel();
    if(TAB==="bookings"){
      const r = await api("/bookings?business_id="+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML = estate("⚠️","Couldn't load bookings","Check your connection and switch tabs to retry."); return; }
      const rows = await r.json();
      loadStats();
      if(!rows.length){
        body.innerHTML = calSubscribeBox() + estate("📅","No bookings yet","Share your chat link — every appointment the receptionist books lands here, in real time.");
        return;
      }
      // Group by day so the owner reads it as a diary, not a spreadsheet — this
      // is the "can I see my calendar?" answer, and it demos far better.
      const byDay = {};
      rows.forEach(b => { (byDay[b.date] = byDay[b.date] || []).push(b); });
      const days = Object.keys(byDay).sort();
      const today = new Date().toISOString().slice(0,10);
      const cal = days.map(d => {
        const items = byDay[d].slice().sort((a,b)=> minutesOf(a.time) - minutesOf(b.time));
        return `<div class="calday${d===today?" is-today":""}">
          <div class="caldate"><b>${esc(dayName(d))}</b><span>${esc(prettyDate(d))}</span>
            ${d===today?'<em class="todaytag">Today</em>':""}</div>
          <div class="calslots">${items.map(b=>`
            <div class="calslot">
              <div class="ctime">${esc(b.time)}</div>
              <div class="cwho"><b>${who(b.patient_name)}</b>${b.reason?`<span>${esc(b.reason)}</span>`:""}</div>
              <div class="cphone num">${esc(b.phone||"")}</div>
              <a class="cadd" href="#" onclick="addToCal(event, ${Number(b.id)})" title="Add to your calendar">+ Calendar</a>
            </div>`).join("")}</div>
        </div>`;
      }).join("");
      body.innerHTML = calSubscribeBox() + `<div class="calwrap">${cal}</div>`;
    } else if(TAB==="leads"){
      const r = await api("/leads?business_id="+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML = estate("⚠️","Couldn't load leads","Check your connection and switch tabs to retry."); return; }
      const rows = await r.json();
      loadStats();
      body.innerHTML = rows.length ? `<div class="tablewrap"><table><thead><tr><th>Name</th><th>Phone</th><th>Interest</th><th>Notes</th></tr></thead>
        <tbody>${rows.map(l=>`<tr><td>${who(l.name)}</td><td class="num">${esc(l.phone)}</td><td>${l.interest?`<span class="chip new">${esc(l.interest)}</span>`:""}</td><td>${esc(l.notes)}</td></tr>`).join("")}</tbody></table></div>`
        : estate("📥","No leads yet","When someone isn't ready to book, the receptionist captures their name and number — you'll see them here.");
    } else if(TAB==="chats"){
      const r = await api("/manage/"+encodeURIComponent(CURRENT)+"/conversations");
      if(!r.ok){ body.innerHTML = estate("⚠️","Couldn't load conversations","Check your connection and switch tabs to retry."); return; }
      const rows = await r.json();
      body.innerHTML = rows.length ? `<div class="tablewrap"><table><thead><tr><th>Who</th><th>Channel</th><th>Last message</th><th>Msgs</th></tr></thead>
        <tbody>${rows.map(c=>`<tr style="cursor:pointer" onclick="openThread('${esc(c.conversation_id)}')"><td>${esc(convWho(c.conversation_id))}</td><td>${esc(convChannel(c.conversation_id))}</td><td>${esc((c.last_text||"").slice(0,70))}</td><td class="num">${esc(c.messages)}</td></tr>`).join("")}</tbody></table></div>`
        : estate("💬","No conversations yet","When customers chat on your widget or WhatsApp, every thread lands here — tap one to read the whole conversation.");
    } else if(TAB==="settings"){
      const r = await api("/manage/"+encodeURIComponent(CURRENT));
      if(!r.ok){ body.innerHTML = estate("⚠️","Couldn't load settings","Check your connection and switch tabs to retry."); return; }
      const b = await r.json();
      const svcText = serviceRowsText(b.services_rows);
      const lstText = listingRowsText(b.listings_rows);
      body.innerHTML = `<h3>Settings</h3>
        <p class="lead">Everything the receptionist knows about this business. Changes apply to the very next conversation.</p>

        <div class="fgroup first">
          <div class="fghead"><span class="fgtitle">Identity</span></div>
          <div class="row2"><div><label for="s_name">Business name</label><input id="s_name" value="${esc(b.name)}"></div>
          <div><label for="s_type">Business type</label><input id="s_type" value="${esc(b.type)}"></div></div>
          <label for="s_vertical">Vertical <span class="soft">(tunes how the agent books &amp; follows up)</span></label>
          <select id="s_vertical" onchange="toggleSettingsRE()"><option value="clinic">Clinic</option><option value="salon">Salon &amp; spa</option><option value="real_estate">Real estate</option><option value="general">General</option></select>
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
          <div class="fghead"><span class="fgtitle">Services &amp; prices</span></div>
          <label for="s_services_rows">Service menu <span class="soft">(one per line: name | minutes | price)</span></label>
          <textarea id="s_services_rows" rows="4" placeholder="skin fade | 45 | 80 AED&#10;beard trim | 15 | 30 AED">${esc(svcText)}</textarea>
          <p class="note">Menu lines drive real appointment lengths and the exact prices the agent quotes. The Services field above stays as friendly descriptive copy.</p>
        </div>

        <div class="fgroup">
          <div class="fghead"><span class="fgtitle">Property listings <span class="soft">(real estate)</span></span></div>
          <label for="s_listings_rows">Live listings <span class="soft">(one per line: title | area | bedrooms | price | sale or rent | permit | notes)</span></label>
          <textarea id="s_listings_rows" rows="4" placeholder="2BR apartment, Bloom Towers | JVC | 2 | 1.2M | sale | 7129XYZ | ready, near park&#10;1BR, Marina Gate | Dubai Marina | 1 | 95k/yr | rent | |">${esc(lstText)}</textarea>
          <p class="note">The permit is the Trakheesi/Madhmoun number — a listing without one can't be legally advertised, so the agent won't quote its price. You can also bulk-import from a CSV, XML feed, or Reelly via the API.</p>
          <p class="note">The agent shortlists ONLY from these — a caller's budget and area get matched to real properties, never invented ones. Update it whenever your inventory changes.</p>
        </div>

        <div class="fgroup">
          <div class="fghead"><span class="fgtitle">Human handoff &amp; after-hours</span></div>
          <label for="s_transfer">Transfer number <span class="soft">(shared when a caller asks for a human — empty = take a message)</span></label>
          <input id="s_transfer" value="${esc(b.transfer_number)}" placeholder="+971 50 123 4567">
          <label for="s_afterhours">When you're closed, the agent should…</label>
          <select id="s_afterhours"><option value="take_message">Take a message (name + number for a callback)</option><option value="book_only">Keep booking — staff confirm when you open</option><option value="info_only">Answer questions only — no bookings</option></select>
          <label for="s_whatsapp">WhatsApp phone_number_id <span class="soft">(from Meta's Cloud API — empty = WhatsApp off)</span></label>
          <input id="s_whatsapp" value="${esc(b.whatsapp_phone_id)}" placeholder="123456789012345">
          <label for="s_review">Google review link <span class="soft">(clients get this after a visit — empty = off)</span></label>
          <input id="s_review" value="${esc(b.google_review_url)}" placeholder="https://g.page/r/…/review">
        </div>

        <div class="fgroup">
          <div class="fghead"><span class="fgtitle">Team, location &amp; policies</span></div>
          <label for="s_staff">Team &amp; specialties <span class="soft">(real estate: agents + their areas &amp; languages)</span></label><input id="s_staff" value="${esc(b.staff)}" placeholder="Omar — Marina, EN/AR · Jessica — Dubai Hills, EN">
          <label for="s_location">Location &amp; directions</label><input id="s_location" value="${esc(b.location)}" placeholder="Area, landmark, parking">
          <label for="s_policies">Policies</label><textarea id="s_policies" rows="2" placeholder="Cancellations, walk-ins, payments">${esc(b.policies)}</textarea>
          <label for="s_notify">Owner email for instant alerts <span class="soft">(every booking &amp; lead)</span></label>
          <input id="s_notify" type="email" value="${esc(b.notify_email)}" placeholder="owner@business.com">
        </div>

        <div class="fgroup" id="s_re_group">
          <div class="fghead"><span class="fgtitle">Real-estate profile <span class="soft">(what the AI knows about your agency)</span></span></div>
          <label for="s_areas">Areas / communities covered</label>
          <input id="s_areas" value="${esc(b.areas_covered)}" placeholder="JVC, Dubai Marina, Downtown, Business Bay">
          <div class="row2"><div><label for="s_focus">Focus <span class="soft">(sale / rent / off-plan)</span></label>
          <input id="s_focus" value="${esc(b.deal_focus)}" placeholder="Secondary sales + rentals; some off-plan"></div>
          <div><label for="s_orn">RERA ORN <span class="soft">(broker reg. number)</span></label>
          <input id="s_orn" value="${esc(b.orn)}" placeholder="12345"></div></div>
          <label for="s_languages">Languages the team speaks</label>
          <input id="s_languages" value="${esc(b.languages)}" placeholder="English, Arabic, Hindi">
        </div>

        <div class="fgroup">
          <div class="fghead"><span class="fgtitle">Knowledge</span></div>
          <label for="s_faq">FAQ / extra knowledge the agent can use</label><textarea id="s_faq" rows="4">${esc(b.faq)}</textarea>
        </div>

        <div style="margin-top:22px"><button class="btn" onclick="saveSettings()">Save changes</button></div>`;
      $("s_vertical").value = b.vertical || "general";
      $("s_afterhours").value = b.after_hours_mode || "take_message";
      toggleSettingsRE();
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
      notify_email:val("s_notify").trim(),
      transfer_number:val("s_transfer").trim(), after_hours_mode:val("s_afterhours"),
      whatsapp_phone_id:val("s_whatsapp").trim(), google_review_url:val("s_review").trim(),
      areas_covered:val("s_areas").trim(), deal_focus:val("s_focus").trim(),
      languages:val("s_languages").trim(), orn:val("s_orn").trim() };
    // Validate the menu and listings BEFORE saving anything, so a typo'd line
    // can't leave settings saved but the sheet silently unchanged.
    const svcRows = parseServiceRows(val("s_services_rows"));
    if(svcRows===null){ toast("Service menu: each line needs 'name | minutes' (price optional)."); return; }
    const lstRows = parseListingRows(val("s_listings_rows"));
    if(lstRows===null){ toast("Listings: each line needs at least a title before the first |."); return; }
    const r = await api("/manage/"+encodeURIComponent(CURRENT), { method:"POST", body: JSON.stringify(body) });
    if(!r.ok){
      let d=null; try{ d = await r.json(); }catch(e){}
      toast(apiErr(d, "Couldn't save — please try again")); return;
    }
    // Replace semantics: an emptied textarea deliberately clears the sheet.
    const rs = await api("/manage/"+encodeURIComponent(CURRENT)+"/services",
      { method:"POST", body: JSON.stringify({services: svcRows}) });
    if(!rs.ok){
      let d=null; try{ d = await rs.json(); }catch(e){}
      toast(apiErr(d, "Saved — but the service menu didn't. Check its lines.")); return;
    }
    const rl = await api("/manage/"+encodeURIComponent(CURRENT)+"/listings",
      { method:"POST", body: JSON.stringify({listings: lstRows}) });
    if(!rl.ok){
      let d=null; try{ d = await rl.json(); }catch(e){}
      toast(apiErr(d, "Saved — but the listings didn't. Check their lines.")); return;
    }
    toast("Settings saved — live from the next conversation");
  }
</script>
</body>
</html>"""
