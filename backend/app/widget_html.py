"""
The patient-facing chat widget — a single, self-contained, polished HTML page
served by the backend itself (no separate frontend deploy). A clinic links to:

    https://<your-app>/widget?business_id=bright-smile

The page reads business_id from the URL, fetches the clinic's display name for
the header, makes its own conversation id, and POSTs each message to /chat.
The conversation is the product, so the UI is intentionally refined: a glowing
assistant orb, soft message animations, and a real typing indicator.
"""

WIDGET_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>Reception</title>
<style>
  :root{
    --accent1:#14b8a6; --accent2:#0d9488; --accent-deep:#0f766e;
    --ink:#0f172a; --muted:#64748b; --line:#e6ebf0;
    --ai-bg:#ffffff; --page:#eef2f6;
  }
  *{box-sizing:border-box; -webkit-tap-highlight-color:transparent;}
  html,body{margin:0; height:100%; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:
      radial-gradient(1200px 600px at 50% -10%, #e7f4f2 0%, transparent 60%),
      linear-gradient(180deg,#eef2f6 0%,#e9eef3 100%);
    color:var(--ink);}
  #app{display:flex; flex-direction:column; height:100%; max-width:560px; margin:0 auto;
    background:rgba(255,255,255,.55); backdrop-filter:blur(8px);
    box-shadow:0 10px 40px rgba(15,23,42,.10);}
  /* header */
  header{position:relative; display:flex; align-items:center; gap:12px; padding:16px 18px; color:#fff;
    background:linear-gradient(135deg,var(--accent1),var(--accent-deep));
    box-shadow:0 6px 20px rgba(13,148,136,.30);}
  .orb{width:38px;height:38px;border-radius:50%;flex:none;position:relative;
    background:radial-gradient(circle at 32% 30%, #ffffff 0%, #c9fff6 18%, var(--accent1) 55%, var(--accent-deep) 100%);
    box-shadow:0 0 0 3px rgba(255,255,255,.25), 0 4px 14px rgba(0,0,0,.18);
    animation:breathe 4s ease-in-out infinite;}
  @keyframes breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}
  .htext{line-height:1.2;}
  .htext b{font-size:16px; font-weight:650; letter-spacing:.2px;}
  .status{display:flex; align-items:center; gap:6px; font-size:12px; opacity:.92; margin-top:3px;}
  .dot{width:7px;height:7px;border-radius:50%;background:#7dffd6;box-shadow:0 0 8px #7dffd6;}
  /* chat */
  #chat{flex:1; overflow-y:auto; padding:20px 16px 8px; display:flex; flex-direction:column; gap:12px; scroll-behavior:smooth;}
  .row{display:flex; align-items:flex-end; gap:8px; max-width:88%;}
  .row.me{align-self:flex-end; flex-direction:row-reverse;}
  .row.ai{align-self:flex-start;}
  .av{width:26px;height:26px;border-radius:50%;flex:none;
    background:radial-gradient(circle at 32% 30%, #ffffff 0%, #c9fff6 20%, var(--accent1) 60%, var(--accent-deep) 100%);
    box-shadow:0 2px 6px rgba(13,148,136,.35);}
  .b{padding:11px 15px; border-radius:18px; line-height:1.45; white-space:pre-wrap; word-wrap:break-word; font-size:15px;
    animation:pop .28s cubic-bezier(.2,.8,.2,1);}
  @keyframes pop{from{opacity:0; transform:translateY(8px) scale(.98)} to{opacity:1; transform:none}}
  .me .b{background:linear-gradient(135deg,var(--accent1),var(--accent2)); color:#fff; border-bottom-right-radius:6px;
    box-shadow:0 4px 14px rgba(13,148,136,.28);}
  .ai .b{background:var(--ai-bg); color:var(--ink); border:1px solid var(--line); border-bottom-left-radius:6px;
    box-shadow:0 3px 12px rgba(15,23,42,.06);}
  /* typing */
  .typing{display:flex; gap:5px; padding:14px 16px;}
  .typing span{width:7px;height:7px;border-radius:50%;background:var(--muted);opacity:.55;animation:blink 1.3s infinite;}
  .typing span:nth-child(2){animation-delay:.18s} .typing span:nth-child(3){animation-delay:.36s}
  @keyframes blink{0%,60%,100%{transform:translateY(0);opacity:.35}30%{transform:translateY(-5px);opacity:.9}}
  /* input */
  form{display:flex; align-items:center; gap:10px; padding:12px 14px calc(12px + env(safe-area-inset-bottom));
    background:rgba(255,255,255,.85); border-top:1px solid var(--line);}
  #m{flex:1; padding:13px 16px; border:1px solid #d7dee4; border-radius:24px; font-size:15px; outline:none; background:#fff;
    transition:border-color .15s, box-shadow .15s;}
  #m:focus{border-color:var(--accent1); box-shadow:0 0 0 4px rgba(20,184,166,.14);}
  #send{width:46px;height:46px;flex:none;border:none;border-radius:50%;cursor:pointer; display:grid; place-items:center;
    background:linear-gradient(135deg,var(--accent1),var(--accent-deep)); box-shadow:0 6px 16px rgba(13,148,136,.35);
    transition:transform .12s, opacity .15s;}
  #send:active{transform:scale(.92)}
  #send:disabled{opacity:.45; cursor:default;}
  #send svg{width:20px;height:20px;fill:#fff;}
  .foot{text-align:center; font-size:11px; color:var(--muted); padding:0 0 8px; opacity:.7;}
</style>
</head>
<body>
<div id="app">
  <header>
    <div class="orb"></div>
    <div class="htext">
      <b id="title">Reception</b>
      <div class="status"><span class="dot"></span><span id="sub">online</span></div>
    </div>
  </header>
  <div id="chat"></div>
  <form id="f" autocomplete="off">
    <input id="m" placeholder="Type your message…" autocomplete="off" enterkeyhint="send">
    <button id="send" type="submit" aria-label="Send">
      <svg viewBox="0 0 24 24"><path d="M3 11l18-8-8 18-2.5-7.5L3 11z"/></svg>
    </button>
  </form>
  <div class="foot">AI assistant · replies are automated</div>
</div>
<script>
  const params = new URLSearchParams(location.search);
  const businessId = params.get("business_id") || "bright-smile";
  const convId = "web-" + Math.random().toString(36).slice(2);
  const chat = document.getElementById("chat");
  const f = document.getElementById("f");
  const m = document.getElementById("m");
  const send = document.getElementById("send");

  // Pull the real business name for the header (public endpoint; falls back quietly).
  fetch("/business/" + encodeURIComponent(businessId)).then(r => r.ok ? r.json() : null).then(biz => {
    if (biz && biz.name) { document.getElementById("title").textContent = biz.name; document.title = biz.name; }
    document.getElementById("sub").textContent = (biz && biz.name) ? "online" : businessId;
  }).catch(() => {});

  function row(text, who) {
    const r = document.createElement("div");
    r.className = "row " + who;
    if (who === "ai") { const a = document.createElement("div"); a.className = "av"; r.appendChild(a); }
    const b = document.createElement("div"); b.className = "b"; b.textContent = text;
    r.appendChild(b);
    chat.appendChild(r); chat.scrollTop = chat.scrollHeight;
    return b;
  }

  function typingRow() {
    const r = document.createElement("div"); r.className = "row ai";
    const a = document.createElement("div"); a.className = "av"; r.appendChild(a);
    const t = document.createElement("div"); t.className = "b typing";
    t.innerHTML = "<span></span><span></span><span></span>";
    r.appendChild(t); chat.appendChild(r); chat.scrollTop = chat.scrollHeight;
    return r;
  }

  row("Hi! How can I help you today?", "ai");
  m.focus();

  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = m.value.trim();
    if (!text) return;
    row(text, "me");
    m.value = "";
    send.disabled = true;
    const tr = typingRow();
    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: convId, business_id: businessId }),
      });
      const data = await res.json();
      tr.remove();
      row(data.reply || "Sorry, something went wrong — please try again.", "ai");
    } catch (err) {
      tr.remove();
      row("Network error — please try again.", "ai");
    } finally {
      send.disabled = false;
      m.focus();
    }
  });
</script>
</body>
</html>"""
