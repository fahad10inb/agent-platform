"""
The patient/customer-facing chat widget — a single self-contained HTML page
served by the backend (no separate frontend deploy). A business links to:

    https://<your-app>/widget?business_id=<id>

Design: "bold gradient" (Linear/Stripe-style) — a vibrant indigo→violet→pink
backdrop with a crisp white card floating on it, violet message bubbles, sharp
modern type, and smooth micro-interactions. The page reads business_id from the
URL, fetches the business's name, and POSTs each message to /chat.
"""

WIDGET_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>Reception</title>
<style>
  :root{
    --g1:#6366f1; --g2:#8b5cf6; --g3:#ec4899;
    --ink:#1b1830; --muted:#7c7896; --line:#ece9f5; --ai:#f5f4fb;
  }
  *{box-sizing:border-box; -webkit-tap-highlight-color:transparent;}
  html,body{margin:0; height:100%; font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    background:
      radial-gradient(820px 460px at 12% -8%, #eef0ff 0%, transparent 60%),
      radial-gradient(820px 460px at 100% 108%, #fdeaf4 0%, transparent 58%),
      #f7f7fb;
    background-attachment:fixed; color:var(--ink);}
  /* the chat surface — a white card floating on a soft, light backdrop */
  #app{display:flex; flex-direction:column; height:100dvh; max-width:480px; margin:0 auto; background:#fff;
    box-shadow:0 18px 50px rgba(99,102,241,.13);}
  @media(min-width:520px){ #app{height:min(92dvh,820px); margin:4dvh auto; border-radius:24px; overflow:hidden;} }
  /* header */
  header{display:flex; align-items:center; gap:12px; padding:16px 18px; border-bottom:1px solid var(--line); position:relative;}
  header::after{content:""; position:absolute; left:0; right:0; bottom:-1px; height:3px;
    background:linear-gradient(90deg,var(--g1),var(--g2),var(--g3));}
  .orb{width:40px;height:40px;border-radius:13px;flex:none;
    background:linear-gradient(135deg,var(--g1),var(--g2) 55%,var(--g3));
    box-shadow:0 6px 18px rgba(124,58,237,.45); animation:float 4s ease-in-out infinite;}
  @keyframes float{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-3px) rotate(-3deg)}}
  .htext b{font-size:16px; font-weight:700; letter-spacing:-.01em;}
  .status{display:flex; align-items:center; gap:6px; font-size:12px; color:var(--muted); margin-top:2px;}
  .dot{width:7px;height:7px;border-radius:50%;background:#22c55e;box-shadow:0 0 8px #22c55e;}
  /* chat */
  #chat{flex:1; overflow-y:auto; padding:20px 16px 8px; display:flex; flex-direction:column; gap:11px; background:#fff;}
  .row{display:flex; align-items:flex-end; gap:8px; max-width:86%;}
  .row.me{align-self:flex-end; flex-direction:row-reverse;}
  .row.ai{align-self:flex-start;}
  .av{width:24px;height:24px;border-radius:8px;flex:none;background:linear-gradient(135deg,var(--g1),var(--g3));}
  .b{padding:11px 15px; border-radius:16px; line-height:1.45; white-space:pre-wrap; word-wrap:break-word; font-size:15px;
    animation:pop .26s cubic-bezier(.2,.8,.2,1);}
  @keyframes pop{from{opacity:0; transform:translateY(8px) scale(.98)} to{opacity:1; transform:none}}
  .me .b{background:linear-gradient(135deg,var(--g1),var(--g2)); color:#fff; border-bottom-right-radius:5px;
    box-shadow:0 4px 14px rgba(99,102,241,.20);}
  .ai .b{background:var(--ai); color:var(--ink); border-bottom-left-radius:5px;}
  .typing{display:flex; gap:5px; padding:14px 16px;}
  .typing span{width:7px;height:7px;border-radius:50%;background:var(--g2);opacity:.5;animation:blink 1.3s infinite;}
  .typing span:nth-child(2){animation-delay:.18s} .typing span:nth-child(3){animation-delay:.36s}
  @keyframes blink{0%,60%,100%{transform:translateY(0);opacity:.35}30%{transform:translateY(-5px);opacity:.95}}
  /* input */
  form{display:flex; align-items:center; gap:10px; padding:12px 14px calc(12px + env(safe-area-inset-bottom)); border-top:1px solid var(--line);}
  #m{flex:1; padding:13px 16px; border:1.5px solid var(--line); border-radius:14px; font-size:15px; outline:none; transition:border-color .15s, box-shadow .15s;}
  #m:focus{border-color:var(--g2); box-shadow:0 0 0 4px rgba(139,92,246,.16);}
  #send{width:46px;height:46px;flex:none;border:none;border-radius:14px;cursor:pointer; display:grid; place-items:center;
    background:linear-gradient(135deg,var(--g1),var(--g2)); box-shadow:0 6px 16px rgba(99,102,241,.26); transition:transform .12s,opacity .15s;}
  #send:active{transform:scale(.92)} #send:disabled{opacity:.45;cursor:default;} #send svg{width:20px;height:20px;fill:#fff;}
  .foot{text-align:center; font-size:11px; color:var(--muted); padding:0 0 8px;}
</style>
</head>
<body>
<div id="app">
  <header>
    <div class="orb"></div>
    <div class="htext"><b id="title">Reception</b><div class="status"><span class="dot"></span><span id="sub">online</span></div></div>
  </header>
  <div id="chat"></div>
  <form id="f" autocomplete="off">
    <input id="m" placeholder="Type your message…" autocomplete="off" enterkeyhint="send">
    <button id="send" type="submit" aria-label="Send"><svg viewBox="0 0 24 24"><path d="M3 11l18-8-8 18-2.5-7.5L3 11z"/></svg></button>
  </form>
  <div class="foot">AI assistant · replies are automated</div>
</div>
<script>
  const params = new URLSearchParams(location.search);
  const businessId = params.get("business_id") || "bright-smile";
  const convId = "web-" + Math.random().toString(36).slice(2);
  const chat = document.getElementById("chat"), f = document.getElementById("f"), m = document.getElementById("m"), send = document.getElementById("send");

  fetch("/business/" + encodeURIComponent(businessId)).then(r => r.ok ? r.json() : null).then(biz => {
    if (biz && biz.name) { document.getElementById("title").textContent = biz.name; document.title = biz.name; }
    document.getElementById("sub").textContent = (biz && biz.name) ? "online" : businessId;
  }).catch(() => {});

  function row(text, who) {
    const r = document.createElement("div"); r.className = "row " + who;
    if (who === "ai") { const a = document.createElement("div"); a.className = "av"; r.appendChild(a); }
    const b = document.createElement("div"); b.className = "b"; b.textContent = text;
    r.appendChild(b); chat.appendChild(r); chat.scrollTop = chat.scrollHeight; return b;
  }
  function typingRow() {
    const r = document.createElement("div"); r.className = "row ai";
    const a = document.createElement("div"); a.className = "av"; r.appendChild(a);
    const t = document.createElement("div"); t.className = "b typing"; t.innerHTML = "<span></span><span></span><span></span>";
    r.appendChild(t); chat.appendChild(r); chat.scrollTop = chat.scrollHeight; return r;
  }

  row("Hi! How can I help you today?", "ai");
  m.focus();

  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = m.value.trim(); if (!text) return;
    row(text, "me"); m.value = ""; send.disabled = true;
    const tr = typingRow();
    try {
      const res = await fetch("/chat", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: convId, business_id: businessId }) });
      const data = await res.json();
      tr.remove(); row(data.reply || "Sorry, something went wrong — please try again.", "ai");
    } catch (err) { tr.remove(); row("Network error — please try again.", "ai"); }
    finally { send.disabled = false; m.focus(); }
  });
</script>
</body>
</html>"""
