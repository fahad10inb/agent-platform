"""
The live demo page — the thing that actually sells the product.

Left: the buyer's chat (the same /chat brain, via /demo/chat).
Right: a dark operations console streaming what the agent ACTUALLY did that turn —
lead captured, qualified, scored A/B/C, calendar checked, unpermitted price
withheld, viewing booked. Every row comes from a tool the model really executed;
nothing here is a scripted animation.

Design: ink + brass, not the generic "AI purple". This is sold to property people
— it should read as premium, Gulf, and serious about money, not as a chatbot toy.
"""

DEMO_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Live demo · ReceptionAI</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{
    --ink:#0d1b26; --ink-2:#122530; --ink-3:#1b3340; --ink-line:#24404e;
    --paper:#f7f5f1; --card:#ffffff; --hairline:#e6e1d8; --hairline-2:#d5cec1;
    --text:#16232b; --body:#46565f; --muted:#7a8892;
    --brass:#b8863b; --brass-bright:#d5a24c; --brass-soft:#f3e9d7;
    --ok:#2e7d53; --ok-soft:#e6f2ea;
    --hot:#c2571f; --hot-soft:#fbeade;
    --warn:#a8741c; --warn-soft:#f8eeda;
    --info:#5b7385;
    --sans:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;
    --mono:'JetBrains Mono',ui-monospace,'SF Mono',Consolas,monospace;
    --shadow:0 1px 2px rgba(13,27,38,.05),0 8px 24px -10px rgba(13,27,38,.16);
  }
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{margin:0;height:100%}
  body{font-family:var(--sans);background:var(--paper);color:var(--text);
    font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}
  :focus-visible{outline:2px solid var(--brass);outline-offset:2px}
  button{font:inherit;cursor:pointer;border:0;background:none;color:inherit}

  /* ── shell ─────────────────────────────────────────────────────────── */
  #shell{display:flex;flex-direction:column;height:100dvh}
  .topbar{flex:none;display:flex;align-items:center;gap:14px;padding:12px 20px;
    background:var(--ink);color:#fff;border-bottom:1px solid var(--ink-line)}
  .brand{display:flex;align-items:center;gap:10px;min-width:0}
  .mark{width:30px;height:30px;flex:none;border-radius:7px;display:grid;place-items:center;
    background:linear-gradient(150deg,var(--brass-bright),var(--brass));color:#1a1206;
    font-weight:700;font-size:14px;letter-spacing:-.02em}
  .bizname{font-weight:600;font-size:15.5px;letter-spacing:-.01em;white-space:nowrap;
    overflow:hidden;text-overflow:ellipsis}
  .bizsub{font-family:var(--mono);font-size:11px;color:#8fa5b1;letter-spacing:.04em;text-transform:uppercase}
  .grow{flex:1}
  .live{display:flex;align-items:center;gap:7px;font-family:var(--mono);font-size:11px;
    letter-spacing:.1em;text-transform:uppercase;color:#c8dbe4;
    background:rgba(255,255,255,.06);border:1px solid var(--ink-line);padding:5px 10px;border-radius:999px}
  .pulse{width:7px;height:7px;border-radius:50%;background:#3fcf7f;animation:pulse 1.8s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
  .reset{font-size:13px;font-weight:500;color:#c8dbe4;border:1px solid var(--ink-line);
    padding:6px 13px;border-radius:8px;transition:background .15s}
  .reset:hover{background:rgba(255,255,255,.07);color:#fff}

  /* ── split ─────────────────────────────────────────────────────────── */
  #split{flex:1;display:grid;grid-template-columns:minmax(0,5fr) minmax(0,6fr);min-height:0}

  /* ── left: the chat ────────────────────────────────────────────────── */
  #left{display:flex;flex-direction:column;min-height:0;background:var(--paper);
    border-right:1px solid var(--hairline)}
  .lhead{flex:none;padding:16px 22px 12px}
  .eyebrow{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;
    color:var(--brass);font-weight:500}
  .lhead h2{margin:5px 0 0;font-size:17px;font-weight:600;letter-spacing:-.015em}
  .lhead p{margin:3px 0 0;font-size:13.5px;color:var(--muted)}
  #chat{flex:1;overflow-y:auto;padding:8px 22px 16px;display:flex;flex-direction:column}
  .row{display:flex;margin-top:14px}
  .row:first-child{margin-top:0}
  .row.me{justify-content:flex-end}
  .b{max-width:84%;padding:11px 15px;border-radius:14px;font-size:15px;line-height:1.5;
    white-space:pre-wrap;word-wrap:break-word;animation:in .22s cubic-bezier(.16,1,.3,1)}
  @keyframes in{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
  .ai .b{background:var(--card);border:1px solid var(--hairline);border-bottom-left-radius:5px;
    box-shadow:var(--shadow)}
  .me .b{background:var(--ink);color:#f2f6f8;border-bottom-right-radius:5px}
  .typing{display:flex;gap:5px;padding:14px 15px}
  .typing i{width:6px;height:6px;border-radius:50%;background:var(--muted);animation:blink 1.2s infinite}
  .typing i:nth-child(2){animation-delay:.15s} .typing i:nth-child(3){animation-delay:.3s}
  @keyframes blink{0%,80%,100%{opacity:.22}40%{opacity:1}}
  /* prompt chips — these drive the demo to the moments that sell */
  .chips{display:flex;flex-wrap:wrap;gap:7px;padding:0 22px 12px;flex:none}
  .chip{font-size:12.5px;font-weight:500;padding:7px 12px;border-radius:999px;
    border:1px solid var(--hairline-2);background:var(--card);color:var(--body);
    transition:border-color .15s,color .15s,background .15s}
  .chip:hover{border-color:var(--brass);color:var(--brass);background:var(--brass-soft)}
  form{flex:none;display:flex;align-items:flex-end;gap:10px;padding:12px 22px 18px;
    border-top:1px solid var(--hairline);background:var(--card)}
  #m{flex:1;border:1px solid var(--hairline-2);border-radius:11px;outline:none;resize:none;
    background:var(--paper);color:var(--text);font:inherit;font-size:15px;padding:11px 13px;max-height:110px}
  #m:focus{border-color:var(--brass);background:#fff}
  #send{width:42px;height:42px;flex:none;border-radius:11px;display:grid;place-items:center;
    background:var(--hairline-2);transition:background .15s,transform .1s}
  #send.on{background:var(--ink)} #send.on:hover{background:var(--ink-3)}
  #send:active{transform:scale(.95)}
  #send svg{width:17px;height:17px;fill:#fff}

  /* ── right: the operations console ─────────────────────────────────── */
  #right{display:flex;flex-direction:column;min-height:0;background:var(--ink);color:#dce8ee}
  .rhead{flex:none;padding:16px 22px;border-bottom:1px solid var(--ink-line)}
  .rhead .eyebrow{color:var(--brass-bright)}
  .rhead h2{margin:5px 0 0;font-size:17px;font-weight:600;color:#fff;letter-spacing:-.015em}
  .rhead p{margin:3px 0 0;font-size:13.5px;color:#8fa5b1}
  /* grounding strip — proves the agent works off THEIR data */
  .ground{display:flex;flex-wrap:wrap;gap:8px;margin-top:13px}
  .gcell{border:1px solid var(--ink-line);background:rgba(255,255,255,.03);border-radius:9px;
    padding:8px 12px;min-width:96px}
  .gcell b{display:block;font-size:17px;font-weight:650;color:#fff;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
  .gcell span{font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#7e97a5}
  .gcell.warn b{color:var(--brass-bright)}

  #feed{flex:1;overflow-y:auto;padding:16px 22px 22px}
  .empty{margin-top:32px;text-align:center;color:#6e8794;font-size:14px;line-height:1.6;padding:0 20px}
  .empty .big{font-size:26px;margin-bottom:10px;opacity:.5}
  .ev{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid rgba(255,255,255,.05);
    animation:evin .3s cubic-bezier(.16,1,.3,1)}
  @keyframes evin{from{opacity:0;transform:translateX(10px)}to{opacity:1;transform:none}}
  .ev .rail{width:3px;flex:none;border-radius:3px;background:var(--info)}
  .ev.ok .rail{background:#3fcf7f} .ev.hot .rail{background:#ff8a4c}
  .ev.warn .rail{background:var(--brass-bright)} .ev.info .rail{background:#5d7d8f}
  .ev .body{min-width:0;flex:1}
  .ev .t{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .ev .t b{font-size:14.5px;font-weight:600;color:#fff;letter-spacing:-.005em}
  .ev .d{font-family:var(--mono);font-size:12px;color:#8fa5b1;margin-top:3px;word-break:break-word;line-height:1.5}
  .ev .ts{font-family:var(--mono);font-size:10.5px;color:#5d7785;flex:none}
  .badge{font-family:var(--mono);font-size:10.5px;font-weight:600;letter-spacing:.06em;
    padding:2px 7px;border-radius:5px;background:rgba(255,255,255,.1);color:#cfe0e8}
  .ev.hot .badge{background:#ff8a4c;color:#2a1305}
  .ev.warn .badge{background:var(--brass-bright);color:#2a1d05}
  /* running tally */
  .tally{flex:none;display:flex;gap:0;border-top:1px solid var(--ink-line)}
  .tcell{flex:1;padding:11px 14px;text-align:center;border-left:1px solid var(--ink-line)}
  .tcell:first-child{border-left:0}
  .tcell b{display:block;font-size:18px;font-weight:650;color:#fff;font-variant-numeric:tabular-nums}
  .tcell span{font-family:var(--mono);font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:#7e97a5}

  @media (max-width:900px){
    #split{grid-template-columns:1fr;grid-template-rows:minmax(0,1fr) minmax(0,1fr)}
    #left{border-right:0;border-bottom:1px solid var(--hairline)}
  }
  @media (prefers-reduced-motion:reduce){*{animation:none !important;transition:none !important}}
</style>
</head>
<body>
<div id="shell">
  <div class="topbar">
    <div class="brand">
      <div class="mark" id="mark">R</div>
      <div style="min-width:0">
        <div class="bizname" id="bizname">Loading…</div>
        <div class="bizsub" id="bizsub">live demo</div>
      </div>
    </div>
    <div class="grow"></div>
    <div class="live"><span class="pulse"></span>Live — not a recording</div>
    <button class="reset" id="reset">Reset</button>
  </div>

  <div id="split">
    <!-- LEFT: the buyer -->
    <div id="left">
      <div class="lhead">
        <div class="eyebrow">You are the buyer</div>
        <h2>Talk to it like a customer would</h2>
        <p>Ask about a property, give your budget, book a viewing.</p>
      </div>
      <div id="chat" role="log" aria-live="polite"></div>
      <div class="chips" id="chips"></div>
      <form id="f" autocomplete="off">
        <textarea id="m" rows="1" placeholder="Type as the buyer…" aria-label="Message"></textarea>
        <button id="send" type="submit" aria-label="Send">
          <svg viewBox="0 0 24 24"><path d="M3 11l18-8-8 18-2.5-7.5L3 11z"/></svg>
        </button>
      </form>
    </div>

    <!-- RIGHT: the machine -->
    <div id="right">
      <div class="rhead">
        <div class="eyebrow">What the agent is doing</div>
        <h2>Every action, as it happens</h2>
        <p>Not a chatbot — an operator working your business.</p>
        <div class="ground" id="ground"></div>
      </div>
      <div id="feed">
        <div class="empty" id="empty">
          <div class="big">◇</div>
          Send a message on the left.<br>Every real action the agent takes appears here.
        </div>
      </div>
      <div class="tally">
        <div class="tcell"><b id="tLeads">0</b><span>Leads</span></div>
        <div class="tcell"><b id="tQual">0</b><span>Qualified</span></div>
        <div class="tcell"><b id="tBook">0</b><span>Booked</span></div>
        <div class="tcell"><b id="tActs">0</b><span>Actions</span></div>
      </div>
    </div>
  </div>
</div>

<script>
  const params = new URLSearchParams(location.search);
  const bizId = params.get("business_id") || "skyline-realty";
  const chat = document.getElementById("chat"), feed = document.getElementById("feed");
  const f = document.getElementById("f"), m = document.getElementById("m"), send = document.getElementById("send");
  let convId = newConv();
  let n = { leads: 0, qual: 0, book: 0, acts: 0 };

  function newConv() {
    return "demo-" + (self.crypto && crypto.randomUUID ? crypto.randomUUID()
      : Math.random().toString(36).slice(2) + Date.now().toString(36));
  }
  function esc(s){ return (s==null?"":String(s)); }

  // ── grounding: prove the agent runs on THEIR data ──────────────────────
  fetch("/demo/context?business_id=" + encodeURIComponent(bizId))
    .then(r => r.ok ? r.json() : null).then(c => {
      if (!c) return;
      document.getElementById("bizname").textContent = c.name;
      document.getElementById("bizsub").textContent = (c.type || c.vertical || "").toString();
      const initial = (c.name || "R").trim().charAt(0).toUpperCase();
      document.getElementById("mark").textContent = initial;
      document.title = c.name + " · Live demo";
      const g = document.getElementById("ground");
      const cells = [];
      if (c.listings) {
        cells.push(["Listings", c.listings, false]);
        cells.push(["Permitted", c.listings_permitted, false]);
        if (c.listings_unpermitted) cells.push(["No permit", c.listings_unpermitted, true]);
      }
      if (c.services) cells.push(["Services", c.services, false]);
      g.innerHTML = cells.map(([label, val, warn]) =>
        `<div class="gcell ${warn?"warn":""}"><b>${esc(val)}</b><span>${esc(label)}</span></div>`
      ).join("");
      setChips(c.vertical);
    }).catch(() => setChips("general"));

  // Prompts curated to walk a prospect straight into the moments that sell —
  // in order: a real price from real inventory, qualification + an A score, the
  // PERMIT REFUSAL (chip 3 hits the unpermitted listing on purpose), a booked
  // viewing. These MUST match the seeded inventory or the demo opens on a miss.
  function setChips(vertical) {
    const re = [
      "Hi, I saw a 2-bedroom in JVC — what's the price?",
      "Budget is 1.5M, cash, I want to move next month",
      "What about the 3-bedroom in JVC?",
      "Can I view it Thursday at 4pm?",
      "أبحث عن شقة في دبي مارينا",
    ];
    const general = [
      "What are your hours?",
      "I'd like to book an appointment",
      "How much does it cost?",
      "أتحدث العربية",
    ];
    const list = (vertical === "real_estate") ? re : general;
    const box = document.getElementById("chips");
    box.innerHTML = "";
    list.forEach(t => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "chip"; b.textContent = t;
      b.addEventListener("click", () => { m.value = t; f.requestSubmit(); });
      box.appendChild(b);
    });
  }

  // ── chat ───────────────────────────────────────────────────────────────
  function row(text, who) {
    const r = document.createElement("div"); r.className = "row " + who;
    const b = document.createElement("div"); b.className = "b"; b.textContent = text;
    r.appendChild(b); chat.appendChild(r); chat.scrollTop = chat.scrollHeight; return r;
  }
  function typing() {
    const r = document.createElement("div"); r.className = "row ai";
    const t = document.createElement("div"); t.className = "b typing";
    t.innerHTML = "<i></i><i></i><i></i>";
    r.appendChild(t); chat.appendChild(r); chat.scrollTop = chat.scrollHeight; return r;
  }
  function greet() {
    row("Hi! I'm the AI assistant here — I can answer questions, match you to a property, book a viewing, or get you a human. How can I help?", "ai");
  }

  // ── the feed: real executed work, never a scripted animation ───────────
  function stamp() {
    const d = new Date();
    return String(d.getHours()).padStart(2,"0") + ":" + String(d.getMinutes()).padStart(2,"0")
      + ":" + String(d.getSeconds()).padStart(2,"0");
  }
  function addEvent(ev) {
    const empty = document.getElementById("empty");
    if (empty) empty.remove();
    const el = document.createElement("div");
    el.className = "ev " + (ev.tone || "info");
    const rail = document.createElement("div"); rail.className = "rail";
    const body = document.createElement("div"); body.className = "body";
    const t = document.createElement("div"); t.className = "t";
    const b = document.createElement("b"); b.textContent = ev.title || ev.kind;
    t.appendChild(b);
    if (ev.badge) { const g = document.createElement("span"); g.className = "badge"; g.textContent = ev.badge; t.appendChild(g); }
    const grow = document.createElement("div"); grow.style.flex = "1"; t.appendChild(grow);
    const ts = document.createElement("span"); ts.className = "ts"; ts.textContent = stamp(); t.appendChild(ts);
    body.appendChild(t);
    if (ev.detail) { const d = document.createElement("div"); d.className = "d"; d.textContent = ev.detail; body.appendChild(d); }
    el.appendChild(rail); el.appendChild(body);
    feed.appendChild(el); feed.scrollTop = feed.scrollHeight;

    n.acts++;
    if (ev.kind === "capture_lead") n.leads++;
    if (ev.kind === "qualify_lead") n.qual++;
    if (ev.kind === "book_appointment" && ev.tone === "ok") n.book++;
    document.getElementById("tLeads").textContent = n.leads;
    document.getElementById("tQual").textContent = n.qual;
    document.getElementById("tBook").textContent = n.book;
    document.getElementById("tActs").textContent = n.acts;
  }

  function grow() { m.style.height = "auto"; m.style.height = Math.min(m.scrollHeight, 110) + "px"; }
  function sync() { send.classList.toggle("on", m.value.trim().length > 0); }
  m.addEventListener("input", () => { grow(); sync(); });
  m.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); f.requestSubmit(); }
  });

  f.addEventListener("submit", async e => {
    e.preventDefault();
    const text = m.value.trim(); if (!text) return;
    row(text, "me"); m.value = ""; grow(); sync(); send.disabled = true;
    const tr = typing();
    try {
      const res = await fetch("/demo/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: convId, business_id: bizId })
      });
      const data = await res.json();
      tr.remove();
      row(data.reply || "Sorry — something went wrong. Please try again.", "ai");
      (data.events || []).forEach((ev, i) => setTimeout(() => addEvent(ev), i * 260));
    } catch (err) {
      tr.remove(); row("Network error — please try again.", "ai");
    } finally { send.disabled = false; sync(); m.focus(); }
  });

  document.getElementById("reset").addEventListener("click", () => {
    convId = newConv();
    chat.innerHTML = ""; feed.innerHTML = '<div class="empty" id="empty"><div class="big">◇</div>Send a message on the left.<br>Every real action the agent takes appears here.</div>';
    n = { leads: 0, qual: 0, book: 0, acts: 0 };
    ["tLeads","tQual","tBook","tActs"].forEach(id => document.getElementById(id).textContent = "0");
    greet(); m.focus();
  });

  greet(); grow(); sync(); m.focus();
</script>
</body>
</html>"""
