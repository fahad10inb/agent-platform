"""
The patient/customer-facing chat widget — a single self-contained HTML page
served by the backend (no separate frontend deploy). A business links to:

    https://<your-app>/widget?business_id=<id>

It renders full-bleed inside an iframe embed and as a centered floating card
when opened standalone on a wide screen. The page reads business_id from the
URL, fetches the business's name for the header, and POSTs each message to
/chat with a random per-load conversation_id. All message text is rendered
via textContent (XSS-safe); a network failure adds an error row.
"""

WIDGET_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reception</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root{
    --canvas:#fdfdff; --surface:#f7f6fb; --surface-2:#f1effa; --card:#ffffff;
    --hairline:#e9e7f2; --hairline-2:#dcd8ea; --ink:#16141d; --body:#4c4a58; --muted:#716e80;
    --accent:#7c5cff; --accent-deep:#6847e6; --accent-soft:#efeaff;
    --focus:rgba(124,92,255,.35);
    --shadow-card:0 0 0 1px rgba(23,21,31,.04),0 1px 1px rgba(46,26,110,.03),0 2px 4px rgba(46,26,110,.04),0 8px 16px -4px rgba(46,26,110,.06);
    --shadow-float:0 1px 1px rgba(46,26,110,.03),0 8px 16px -4px rgba(46,26,110,.06),0 24px 32px -8px rgba(46,26,110,.12);
  }
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{margin:0;height:100%}
  body{font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;
    font-feature-settings:'cv11','ss01';-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
    background:var(--canvas);color:var(--ink);font-size:16px;line-height:1.55}
  ::selection{background:rgba(124,92,255,.22)}
  :focus-visible{outline:2px solid var(--focus);outline-offset:2px}
  /* full-bleed by default (iframe embeds); floating card when standalone on wide screens */
  #app{display:flex;flex-direction:column;height:100dvh;background:var(--card)}
  @media(min-width:560px){
    body{display:grid;place-items:center}
    #app{width:420px;height:min(92dvh,760px);border-radius:16px;overflow:hidden;
      border:1px solid var(--hairline);box-shadow:var(--shadow-float)}
  }
  /* header */
  header{display:flex;align-items:center;gap:12px;padding:14px 16px;flex:none;
    background:linear-gradient(135deg,#8f6fff,#6847e6);color:#fff}
  .avatar{width:36px;height:36px;border-radius:50%;flex:none;display:grid;place-items:center;
    background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.3);font-size:15px;font-weight:600}
  .htext{min-width:0}
  .htext b{display:block;font-size:16px;font-weight:600;letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .status{display:flex;align-items:center;gap:6px;font-size:12px;color:rgba(255,255,255,.85);margin-top:1px}
  .dot{width:8px;height:8px;border-radius:50%;background:#2fbf62;box-shadow:0 0 0 1.5px #fff;flex:none}
  /* chat */
  #chat{flex:1;overflow-y:auto;padding:18px 16px;display:flex;flex-direction:column}
  .row{display:flex;margin-top:16px}
  .row:first-child{margin-top:0}
  .row.me{justify-content:flex-end}
  .row.me + .row.me{margin-top:4px}
  .row.ai + .row.ai{margin-top:4px}
  .b{max-width:78%;padding:10px 14px;border-radius:16px;font-size:15px;line-height:1.45;
    white-space:pre-wrap;word-wrap:break-word;animation:msgin .18s cubic-bezier(.16,1,.3,1)}
  @keyframes msgin{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
  .ai .b{background:var(--surface-2);color:var(--ink);border-bottom-left-radius:6px}
  .me .b{background:linear-gradient(135deg,#8f6fff,#6847e6);color:#fff;border-bottom-right-radius:6px}
  /* typing indicator */
  .typing{display:flex;gap:5px;padding:13px 14px}
  .typing span{width:6px;height:6px;border-radius:50%;background:var(--muted);animation:blink 1.2s infinite}
  .typing span:nth-child(2){animation-delay:.15s}
  .typing span:nth-child(3){animation-delay:.3s}
  @keyframes blink{0%,80%,100%{opacity:.25}40%{opacity:1}}
  /* quick-reply starter chips */
  .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
  .chipbtn{font:inherit;font-size:13px;font-weight:500;padding:8px 14px;border-radius:999px;cursor:pointer;
    border:1px solid var(--hairline);background:var(--card);color:var(--accent-deep);
    transition:background .15s,border-color .15s}
  .chipbtn:hover{background:var(--accent-soft);border-color:#ded4ff}
  /* input bar */
  form{display:flex;align-items:flex-end;gap:10px;flex:none;background:var(--card);
    padding:10px 12px calc(10px + env(safe-area-inset-bottom));border-top:1px solid var(--hairline)}
  #m{flex:1;border:0;outline:none;resize:none;background:transparent;color:var(--ink);
    font:inherit;font-size:15px;line-height:1.4;padding:9px 4px;max-height:96px}
  #m::placeholder{color:var(--muted)}
  #send{width:40px;height:40px;flex:none;border:0;border-radius:999px;cursor:pointer;display:grid;place-items:center;
    background:var(--muted);transition:background .15s,transform .12s}
  #send.ready{background:var(--accent)}
  #send.ready:hover{background:var(--accent-deep)}
  #send:active{transform:scale(.94)}
  #send:disabled{opacity:.5;cursor:default}
  #send svg{width:18px;height:18px;fill:#fff}
  .foot{flex:none;text-align:center;font-size:11px;color:var(--muted);padding:0 0 8px;background:var(--card)}
  .foot a{color:var(--muted);text-decoration:none}
  .foot a b{font-weight:600;color:var(--body)}
  .foot a:hover b{color:var(--accent-deep)}
  @media (prefers-reduced-motion: reduce){
    *{animation:none !important;transition:none !important}
    .typing span{opacity:.6}
  }
</style>
</head>
<body>
<div id="app">
  <header>
    <div class="avatar" id="avatar">R</div>
    <div class="htext">
      <b id="title">Reception</b>
      <div class="status"><span class="dot"></span><span id="sub">Online — replies in seconds</span></div>
    </div>
  </header>
  <div id="chat" role="log" aria-live="polite" aria-label="Conversation"></div>
  <form id="f" autocomplete="off">
    <textarea id="m" placeholder="Type your message…" rows="1" enterkeyhint="send" aria-label="Type your message"></textarea>
    <button id="send" type="submit" aria-label="Send"><svg viewBox="0 0 24 24"><path d="M3 11l18-8-8 18-2.5-7.5L3 11z"/></svg></button>
  </form>
  <div class="foot"><a href="/" target="_blank" rel="noopener">Powered by <b>ReceptionAI</b></a></div>
</div>
<script>
  const params = new URLSearchParams(location.search);
  const businessId = params.get("business_id") || "bright-smile";
  // A conversation SURVIVES page reloads (industry-standard widget behavior):
  // one random unguessable id per business, kept in localStorage.
  const convKey = "receptionai_conv_" + businessId;
  let convId = null;
  try { convId = localStorage.getItem(convKey); } catch (e) {}
  if (!convId) {
    convId = "web-" + (self.crypto && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2) + Date.now().toString(36));
    try { localStorage.setItem(convKey, convId); } catch (e) {}
  }
  const chat = document.getElementById("chat"), f = document.getElementById("f"), m = document.getElementById("m"), send = document.getElementById("send");

  fetch("/business/" + encodeURIComponent(businessId)).then(r => r.ok ? r.json() : null).then(biz => {
    if (biz && biz.name) {
      document.getElementById("title").textContent = biz.name;
      document.title = biz.name;
      const initial = biz.name.trim().charAt(0).toUpperCase();
      if (initial) document.getElementById("avatar").textContent = initial;
    } else {
      document.getElementById("sub").textContent = businessId;
    }
  }).catch(() => {});

  function row(text, who) {
    const r = document.createElement("div"); r.className = "row " + who;
    const b = document.createElement("div"); b.className = "b"; b.textContent = text;
    r.appendChild(b); chat.appendChild(r); chat.scrollTop = chat.scrollHeight; return b;
  }
  function typingRow() {
    const r = document.createElement("div"); r.className = "row ai";
    const t = document.createElement("div"); t.className = "b typing"; t.innerHTML = "<span></span><span></span><span></span>";
    r.appendChild(t); chat.appendChild(r); chat.scrollTop = chat.scrollHeight; return r;
  }

  // auto-grow textarea (capped ~4 lines) + send-button state
  function grow() { m.style.height = "auto"; m.style.height = Math.min(m.scrollHeight, 96) + "px"; }
  function syncSend() { send.classList.toggle("ready", m.value.trim().length > 0); }
  m.addEventListener("input", () => { grow(); syncSend(); });
  m.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); f.requestSubmit(); }
  });

  function freshStart() {
    row("Hi! How can I help you today?", "ai");
    // quick-reply starter chips — purely visual, removed after the first message
    const chipBox = document.createElement("div");
    chipBox.id = "chips"; chipBox.className = "chips";
    ["Book an appointment", "What are your hours?", "أتحدث العربية"].forEach(t => {
      const c = document.createElement("button");
      c.type = "button"; c.className = "chipbtn"; c.textContent = t;
      c.addEventListener("click", () => { m.value = t; f.requestSubmit(); });
      chipBox.appendChild(c);
    });
    chat.appendChild(chipBox);
  }

  // Restore the conversation after a reload; fresh greeting only when there
  // is genuinely nothing to restore (or history is unreachable).
  fetch("/chat/history?business_id=" + encodeURIComponent(businessId) + "&conversation_id=" + encodeURIComponent(convId))
    .then(r => r.ok ? r.json() : [])
    .then(hist => {
      if (Array.isArray(hist) && hist.length) {
        hist.forEach(t => row(t.text, t.role === "user" ? "me" : "ai"));
      } else { freshStart(); }
    })
    .catch(() => freshStart());

  grow(); syncSend(); m.focus();

  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = m.value.trim(); if (!text) return;
    const chips = document.getElementById("chips"); if (chips) chips.remove();
    row(text, "me"); m.value = ""; grow(); syncSend(); send.disabled = true;
    const tr = typingRow();
    try {
      const res = await fetch("/chat", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: convId, business_id: businessId }) });
      const data = await res.json();
      tr.remove(); row(data.reply || "Sorry, something went wrong — please try again.", "ai");
    } catch (err) { tr.remove(); row("Network error — please try again.", "ai"); }
    finally { send.disabled = false; syncSend(); m.focus(); }
  });
</script>
</body>
</html>"""
