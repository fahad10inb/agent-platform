"""
The shareable "watch it work" story page — the sales TRAILER.

Served at /watch. The link an owner gets in a cold WhatsApp/DM opens THIS: a
self-contained, auto-playing 60-second scene of the AI handling a real after-hours
enquiry on WhatsApp — capturing the lead, qualifying it, staying DLD-compliant,
answering in Arabic, and booking the viewing — while the owner is asleep.

Why it's scripted and API-free (unlike /demo, which is the live brain): a cold
prospect taps a DM link on their phone. Render's free tier cold-starts and drops
the first request; a spinner loses them in 3 seconds. So this page ships the whole
story inline and plays instantly — no backend round-trip, works offline. /demo is
"see it run live"; /watch is the trailer that earns the click to it.

Design: committed dark "11 PM" scene, ink + brass (never AI-purple), a WhatsApp-
familiar thread beside a live receipts panel proving the invisible work. Sold to
Dubai property owners — premium, Gulf, serious about the money they're losing.
"""

STORY_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>The lead you didn't lose · ReceptionAI</title>
<meta name="description" content="At 11 PM a buyer messaged and nobody was awake. Watch the AI qualify, stay compliant, reply in Arabic, and book the viewing — on its own.">
<style>
  :root{
    --ink:#08131c; --ink-2:#0d1b26; --ink-3:#12252f; --ink-line:#22404e;
    --brass:#b8863b; --brass-bright:#d5a24c; --brass-soft:#e9c987;
    --text:#eaf1f5; --body:#b6c6d0; --muted:#7f97a4;
    --ok:#3fcf7f; --ok-deep:#1f8a55; --hot:#ff9a52; --warn:#d5a24c; --info:#6f93a6;
    /* WhatsApp-familiar chat surface (evoked, not cloned) */
    --wa-bg:#0a151d; --wa-in:#1e2b33; --wa-out:#0b4f3c; --wa-out-2:#0a6149;
    --sans:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;
    --mono:ui-monospace,'JetBrains Mono','SF Mono',Consolas,monospace;
  }
  *{box-sizing:border-box;margin:0;-webkit-tap-highlight-color:transparent}
  html,body{min-height:100%}
  body{font-family:var(--sans);color:var(--text);line-height:1.55;
    -webkit-font-smoothing:antialiased;
    background:
      radial-gradient(120% 80% at 82% -8%,#123449 0%,transparent 46%),
      radial-gradient(90% 70% at -10% 110%,#10202c 0%,transparent 50%),
      linear-gradient(180deg,#08131c,#050d14 90%);
    background-attachment:fixed}
  a{color:inherit}
  :focus-visible{outline:2px solid var(--brass-bright);outline-offset:3px;border-radius:6px}

  .wrap{max-width:1080px;margin:0 auto;padding:26px 20px 40px}
  .top{display:flex;align-items:center;gap:11px;margin-bottom:26px}
  .mark{width:34px;height:34px;border-radius:9px;flex:none;display:grid;place-items:center;
    background:linear-gradient(150deg,var(--brass-bright),var(--brass));color:#1a1206;
    font-weight:800;font-size:16px;letter-spacing:-.02em}
  .top .nm{font-weight:700;letter-spacing:-.01em;font-size:15.5px}
  .top .nm span{color:var(--brass-bright)}
  .top .grow{flex:1}
  .clock{font-family:var(--mono);font-size:12.5px;color:var(--body);
    display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.04);
    border:1px solid var(--ink-line);border-radius:999px;padding:6px 13px}
  .moon{filter:saturate(.8)}

  /* ── hero copy ─────────────────────────────────────────────────────── */
  .hero{max-width:660px;margin:0 auto 30px;text-align:center}
  .eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.22em;text-transform:uppercase;
    color:var(--brass-bright);font-weight:600}
  h1{font-size:clamp(27px,5.4vw,42px);line-height:1.08;letter-spacing:-.025em;margin:13px 0 0;
    font-weight:800;text-wrap:balance}
  h1 .glow{color:var(--brass-bright)}
  .sub{margin:15px auto 0;max-width:52ch;color:var(--body);font-size:clamp(15px,2.4vw,17px);
    text-wrap:pretty}

  /* ── stage: phone + receipts ───────────────────────────────────────── */
  .stage{display:grid;grid-template-columns:minmax(0,340px) minmax(0,1fr);
    gap:30px;align-items:start;margin-top:6px}
  @media (max-width:820px){ .stage{grid-template-columns:1fr;gap:22px;max-width:400px;margin-inline:auto} }

  /* the phone */
  .phone{position:relative;justify-self:center;width:100%;max-width:340px;
    border-radius:38px;padding:11px;background:linear-gradient(160deg,#1b2a34,#0a141b);
    box-shadow:0 40px 90px -30px rgba(0,0,0,.85),0 0 0 1px rgba(213,162,76,.16),
      inset 0 0 0 1px rgba(255,255,255,.04)}
  .screen{position:relative;border-radius:29px;overflow:hidden;background:var(--wa-bg);
    height:min(620px,74vh);min-height:480px;display:flex;flex-direction:column}
  .notch{position:absolute;top:0;left:50%;transform:translateX(-50%);z-index:6;
    width:120px;height:23px;background:#0a141b;border-radius:0 0 15px 15px}
  .sbar{flex:none;display:flex;align-items:center;justify-content:space-between;
    padding:9px 20px 5px;font-size:12px;font-weight:600;color:#cddae2;font-family:var(--mono)}
  .sbar .r{display:flex;gap:6px;align-items:center;opacity:.85}
  /* whatsapp-style header */
  .wahead{flex:none;display:flex;align-items:center;gap:10px;padding:8px 13px;
    background:var(--ink-3);border-bottom:1px solid rgba(255,255,255,.05)}
  .wahead .bk{color:#8fb0c2;font-size:20px;line-height:1}
  .wava{width:38px;height:38px;border-radius:50%;flex:none;display:grid;place-items:center;
    background:linear-gradient(150deg,var(--brass-bright),var(--brass));color:#1a1206;font-weight:800}
  .wahead .who b{display:block;font-size:14.5px;font-weight:600;letter-spacing:-.01em}
  .wahead .who .st{font-size:11.5px;color:var(--ok);display:flex;align-items:center;gap:5px}
  .wahead .who .st i{width:6px;height:6px;border-radius:50%;background:var(--ok);display:inline-block}
  .aitag{margin-left:auto;font-family:var(--mono);font-size:9.5px;letter-spacing:.08em;
    text-transform:uppercase;color:var(--brass-bright);border:1px solid rgba(213,162,76,.4);
    border-radius:6px;padding:3px 7px}

  .thread{flex:1;overflow-y:auto;padding:14px 12px 8px;display:flex;flex-direction:column;gap:4px;
    background:
      radial-gradient(60% 40% at 90% 6%,rgba(213,162,76,.05),transparent 60%),
      var(--wa-bg);scroll-behavior:smooth}
  .thread::-webkit-scrollbar{width:0}
  .day{align-self:center;font-size:10.5px;color:var(--muted);background:rgba(255,255,255,.05);
    padding:3px 11px;border-radius:8px;margin:2px 0 8px;font-family:var(--mono)}
  .msg{max-width:82%;padding:7px 10px 5px;border-radius:11px;font-size:14px;line-height:1.42;
    position:relative;animation:pop .32s cubic-bezier(.18,1,.3,1);box-shadow:0 1px 1px rgba(0,0,0,.25)}
  @keyframes pop{from{opacity:0;transform:translateY(8px) scale(.98)}to{opacity:1;transform:none}}
  .msg .tm{font-size:9.5px;color:rgba(255,255,255,.45);float:right;margin:5px 0 -2px 10px;font-family:var(--mono)}
  .msg .ar{direction:rtl;text-align:right;font-size:15px}
  .msg .gloss{display:block;font-size:11px;color:rgba(255,255,255,.5);font-style:italic;margin-top:2px}
  .in{align-self:flex-start;background:var(--wa-in);border-bottom-left-radius:4px}
  .out{align-self:flex-end;background:linear-gradient(180deg,var(--wa-out-2),var(--wa-out));
    border-bottom-right-radius:4px}
  .out .tk{color:#7fd6b3;font-size:11px;margin-left:3px}
  .typing{align-self:flex-start;background:var(--wa-in);border-bottom-left-radius:4px;
    padding:11px 13px;display:flex;gap:4px;border-radius:11px}
  .typing i{width:6px;height:6px;border-radius:50%;background:#7f97a4;animation:blink 1.2s infinite}
  .typing i:nth-child(2){animation-delay:.16s} .typing i:nth-child(3){animation-delay:.32s}
  @keyframes blink{0%,80%,100%{opacity:.25}40%{opacity:1}}
  .wabar{flex:none;display:flex;align-items:center;gap:9px;padding:9px 12px;background:var(--ink-3);
    border-top:1px solid rgba(255,255,255,.05)}
  .wabar .fake{flex:1;height:34px;border-radius:18px;background:rgba(255,255,255,.06);
    display:flex;align-items:center;padding:0 14px;color:var(--muted);font-size:13px}
  .wabar .snd{width:34px;height:34px;border-radius:50%;flex:none;display:grid;place-items:center;
    background:var(--wa-out);color:#cfeee0}

  /* the receipts / "what your AI did" panel */
  .work{align-self:stretch}
  .work .wt{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:3px}
  .work .wt h2{font-size:16px;font-weight:700;letter-spacing:-.01em}
  .work .wt .hint{font-size:12.5px;color:var(--muted)}
  .receipts{margin-top:12px;display:flex;flex-direction:column;gap:0;
    border:1px solid var(--ink-line);border-radius:14px;overflow:hidden;background:rgba(255,255,255,.02)}
  .rc{display:flex;gap:12px;padding:13px 15px;border-bottom:1px solid rgba(255,255,255,.05);
    animation:slidein .34s cubic-bezier(.16,1,.3,1)}
  .rc:last-child{border-bottom:0}
  @keyframes slidein{from{opacity:0;transform:translateX(12px)}to{opacity:1;transform:none}}
  .rc .rail{width:3px;flex:none;border-radius:3px;background:var(--info)}
  .rc.ok .rail{background:var(--ok)} .rc.hot .rail{background:var(--hot)}
  .rc.warn .rail{background:var(--brass-bright)}
  .rc .bd{flex:1;min-width:0}
  .rc .h{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .rc .h b{font-size:14px;font-weight:600}
  .rc .h .ts{margin-left:auto;font-family:var(--mono);font-size:10.5px;color:var(--muted)}
  .rc .d{font-family:var(--mono);font-size:11.5px;color:var(--body);margin-top:3px;line-height:1.5;word-break:break-word}
  .badge{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.05em;
    padding:2px 7px;border-radius:5px;background:rgba(255,255,255,.1);color:#d7e5ec}
  .rc.hot .badge{background:var(--hot);color:#2a1305}
  .rc.warn .badge{background:var(--brass-bright);color:#2a1d05}
  .rc-wait{padding:16px;text-align:center;color:var(--muted);font-size:13px;font-family:var(--mono)}

  /* the punchline card that resolves the story */
  .kicker{margin-top:16px;border:1px solid rgba(213,162,76,.35);border-radius:14px;padding:17px 18px;
    background:linear-gradient(160deg,rgba(213,162,76,.1),rgba(213,162,76,.02));
    opacity:0;transform:translateY(10px);transition:opacity .5s,transform .5s}
  .kicker.show{opacity:1;transform:none}
  .kicker .big{font-size:19px;font-weight:750;letter-spacing:-.015em}
  .kicker .big b{color:var(--brass-bright)}
  .kicker p{margin-top:6px;color:var(--body);font-size:13.5px}
  .bkg{margin-top:13px;display:flex;align-items:center;gap:12px;background:var(--ink-2);
    border:1px solid var(--ink-line);border-radius:11px;padding:12px 14px}
  .bkg .dot{width:40px;height:40px;border-radius:10px;flex:none;display:grid;place-items:center;
    background:rgba(63,207,127,.14);color:var(--ok);font-size:20px}
  .bkg .l1{font-weight:650;font-size:14.5px} .bkg .l2{font-size:12.5px;color:var(--muted);margin-top:1px}
  .bkg .rt{margin-left:auto;text-align:right;font-family:var(--mono);font-size:11px;color:var(--ok)}

  /* ── proof strip + CTAs ────────────────────────────────────────────── */
  .proof{max-width:760px;margin:34px auto 0;display:flex;flex-wrap:wrap;gap:9px;justify-content:center}
  .pchip{font-size:12.5px;color:var(--body);border:1px solid var(--ink-line);
    background:rgba(255,255,255,.03);border-radius:999px;padding:7px 13px;display:flex;gap:7px;align-items:center}
  .pchip b{color:var(--text);font-weight:600}
  .cta{max-width:760px;margin:26px auto 0;display:flex;flex-wrap:wrap;gap:12px;justify-content:center}
  .btn{display:inline-flex;align-items:center;gap:9px;font-size:15px;font-weight:650;
    padding:13px 22px;border-radius:12px;text-decoration:none;transition:transform .12s,filter .15s,background .15s}
  .btn:active{transform:scale(.97)}
  .btn.primary{background:linear-gradient(150deg,var(--brass-bright),var(--brass));color:#1a1206;
    box-shadow:0 12px 30px -12px rgba(213,162,76,.6)}
  .btn.primary:hover{filter:brightness(1.06)}
  .btn.ghost{border:1px solid var(--ink-line);color:var(--text);background:rgba(255,255,255,.03)}
  .btn.ghost:hover{background:rgba(255,255,255,.07)}
  .replay{display:block;margin:20px auto 0;background:none;border:0;color:var(--muted);
    font:inherit;font-size:13px;cursor:pointer;font-family:var(--mono)}
  .replay:hover{color:var(--brass-bright)}
  footer{margin-top:36px;text-align:center;color:var(--muted);font-size:12.5px}
  footer a{color:var(--body);text-decoration:none;font-weight:600}
  footer a:hover{color:var(--brass-bright)}

  @media (prefers-reduced-motion:reduce){*{animation:none !important;transition:none !important}
    .kicker{opacity:1;transform:none}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="mark" id="mark">R</div>
    <div class="nm">Reception<span>AI</span></div>
    <div class="grow"></div>
    <div class="clock"><span class="moon">🌙</span><span id="clk">11:04 PM</span></div>
  </div>

  <div class="hero">
    <div class="eyebrow">After hours · WhatsApp · Dubai</div>
    <h1>A buyer messaged at 11&nbsp;PM.<br>Nobody was awake.<br><span class="glow">It still got booked.</span></h1>
    <p class="sub">Watch your AI receptionist work a real enquiry end-to-end — qualify the buyer, stay DLD-compliant, reply in Arabic, and lock the viewing. On its own, while you sleep.</p>
  </div>

  <div class="stage">
    <!-- the phone -->
    <div class="phone">
      <div class="screen">
        <div class="notch"></div>
        <div class="sbar"><span id="clk2">11:04</span>
          <span class="r"><span>📶</span><span>🔋</span></span></div>
        <div class="wahead">
          <span class="bk">‹</span>
          <div class="wava">S</div>
          <div class="who"><b>Skyline Realty</b><span class="st"><i></i>online</span></div>
          <span class="aitag">AI</span>
        </div>
        <div class="thread" id="thread">
          <div class="day">TODAY</div>
        </div>
        <div class="wabar">
          <div class="fake">Message</div>
          <div class="snd">➤</div>
        </div>
      </div>
    </div>

    <!-- the invisible work -->
    <div class="work">
      <div class="wt">
        <h2>What your AI did</h2>
        <span class="hint">— the customer never saw any of this</span>
      </div>
      <div class="receipts" id="receipts">
        <div class="rc-wait" id="wait">watching the conversation…</div>
      </div>

      <div class="kicker" id="kicker">
        <div class="big">Under a minute. <b>You were asleep.</b></div>
        <p>No missed message. No lead gone to the agency that answered first. Just a booked viewing waiting in your dashboard when you wake up.</p>
        <div class="bkg">
          <div class="dot">✓</div>
          <div><div class="l1">Viewing — 2BR, JVC</div><div class="l2">Ahmed · Grade A lead · via WhatsApp</div></div>
          <div class="rt">Thu<br>4:00 PM</div>
        </div>
      </div>
    </div>
  </div>

  <div class="proof">
    <div class="pchip">🌐 <b>Arabic &amp; English</b></div>
    <div class="pchip">🛡️ <b>DLD-compliant</b> — withholds unpermitted prices</div>
    <div class="pchip">⏱️ <b>Answers in seconds</b>, 24/7</div>
    <div class="pchip">📲 <b>On WhatsApp</b> — where buyers already are</div>
  </div>

  <div class="cta">
    <a class="btn primary" href="/demo?business_id=skyline-realty">See it run live — talk to it yourself ↗</a>
    <a class="btn ghost" href="/">Set this up for your agency →</a>
  </div>
  <button class="replay" id="replay">↻ Watch it again</button>

  <footer>
    <a href="/">ReceptionAI</a> — an AI receptionist that answers, qualifies and books, day or night.
  </footer>
</div>

<script>
(() => {
  const thread = document.getElementById("thread");
  const receipts = document.getElementById("receipts");
  const wait = document.getElementById("wait");
  const kicker = document.getElementById("kicker");
  const clk = document.getElementById("clk"), clk2 = document.getElementById("clk2");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let timers = [];

  // The scene. Each step is a beat; `at` is ms from start. Nothing here calls the
  // backend — it's a curated retelling of exactly what the live /demo does.
  const SCENE = [
    { at: 400,  clock: "11:04 PM" },
    { at: 600,  typing: true },
    { at: 1600, msg: { side: "in", text: "Hi, saw the 2BR in JVC on Bayut — is it still available?", tm: "11:04 PM" } },
    { at: 2100, rc: { tone: "info", title: "Enquiry received", detail: "WhatsApp · after hours · 11:04 PM" } },
    { at: 2500, typing: true },
    { at: 3600, msg: { side: "out", text: "Hi! Yes — the 2-bed in JVC is available at AED 95,000/yr, and I've a permitted unit ready to view. May I take your name? 😊", tm: "11:04 PM", tick: true } },
    { at: 3900, rc: { tone: "ok", title: "Lead captured", detail: "new WhatsApp enquiry — 2BR JVC" } },
    { at: 4400, rc: { tone: "warn", badge: "DLD", title: "Price withheld on 1 unit", detail: "a matching listing had no DLD permit — not quoted" } },
    { at: 5300, typing: true },
    { at: 6300, msg: { side: "in", text: "Ahmed 🙂 budget's around 95k, looking to move next month", tm: "11:05 PM" } },
    { at: 6700, rc: { tone: "hot", badge: "GRADE A", title: "Qualified & scored", detail: "AED 95k · JVC · 2BR · moving in 1 month" } },
    { at: 7100, typing: true },
    { at: 8000, msg: { side: "out", text: "Perfect, Ahmed. Thursday at 4pm is free for a viewing — shall I lock it in?", tm: "11:05 PM", tick: true } },
    { at: 8300, rc: { tone: "info", title: "Calendar checked", detail: "Thursday — 3 slots free" } },
    { at: 9100, typing: true },
    { at: 10100, msg: { side: "in", ar: "تمام، الخميس ٤ العصر 👍", gloss: "(perfect — Thursday 4pm)", tm: "11:05 PM" } },
    { at: 10500, rc: { tone: "info", title: "Understood Arabic", detail: "buyer switched language — replying bilingually" } },
    { at: 10900, typing: true },
    { at: 11900, msg: { side: "out", ar: "تم الحجز ✅", text: "Booked! You'll get the confirmation and the agent's details shortly. 🔑", tm: "11:05 PM", tick: true } },
    { at: 12200, rc: { tone: "ok", badge: "BOOKED", title: "Viewing booked", detail: "Thursday 4:00 PM · confirmation sent" } },
    { at: 12300, clock: "11:05 PM" },
    { at: 13000, kicker: true },
  ];

  function typingEl() {
    const t = document.createElement("div");
    t.className = "typing"; t.dataset.typing = "1";
    t.innerHTML = "<i></i><i></i><i></i>";
    return t;
  }
  function clearTyping() {
    thread.querySelectorAll('[data-typing]').forEach(e => e.remove());
  }
  function addMsg(m) {
    clearTyping();
    const el = document.createElement("div");
    el.className = "msg " + (m.side === "out" ? "out" : "in");
    let inner = "";
    if (m.ar) inner += '<span class="ar">' + m.ar + '</span>';
    if (m.text) inner += (m.ar ? '<span style="display:block;margin-top:3px">' : '<span>') + m.text + '</span>';
    if (m.gloss) inner += '<span class="gloss">' + m.gloss + '</span>';
    inner += '<span class="tm">' + (m.tm || "") + (m.tick ? ' <span class="tk">✓✓</span>' : '') + '</span>';
    el.innerHTML = inner;
    thread.appendChild(el);
    thread.scrollTop = thread.scrollHeight;
  }
  function addReceipt(r) {
    if (wait && wait.parentNode) wait.remove();
    const el = document.createElement("div");
    el.className = "rc " + (r.tone || "info");
    const icon = r.tone === "warn" ? "⚠" : (r.tone === "info" ? "•" : "✓");
    el.innerHTML =
      '<div class="rail"></div><div class="bd"><div class="h">' +
      '<b>' + icon + '  ' + r.title + '</b>' +
      (r.badge ? '<span class="badge">' + r.badge + '</span>' : '') +
      '<span class="ts">' + stamp() + '</span></div>' +
      (r.detail ? '<div class="d">' + r.detail + '</div>' : '') +
      '</div>';
    receipts.appendChild(el);
  }
  function stamp() {
    // Cosmetic clock inside the scene — the story is 11:0x PM, not the viewer's time.
    return "11:0" + (Math.min(5, 4 + (receipts.querySelectorAll('.rc').length > 2 ? 1 : 0))) + " PM";
  }

  function run() {
    timers.forEach(clearTimeout); timers = [];
    thread.innerHTML = '<div class="day">TODAY</div>';
    receipts.innerHTML = '<div class="rc-wait" id="wait">watching the conversation…</div>';
    kicker.classList.remove("show");
    const waitEl = document.getElementById("wait");

    if (reduce) {  // no motion: render the whole resolved scene at once
      SCENE.forEach(s => { if (s.msg) addMsg(s.msg); if (s.rc) addReceipt(s.rc); });
      clk.textContent = clk2.textContent = "11:05 PM"; clk2.textContent = "11:05";
      kicker.classList.add("show");
      return;
    }
    SCENE.forEach(step => {
      timers.push(setTimeout(() => {
        if (step.clock) { clk.textContent = step.clock; clk2.textContent = step.clock.replace(" PM",""); }
        if (step.typing) { clearTyping(); thread.appendChild(typingEl()); thread.scrollTop = thread.scrollHeight; }
        if (step.msg) addMsg(step.msg);
        if (step.rc) addReceipt(step.rc);
        if (step.kicker) { clearTyping(); kicker.classList.add("show"); }
      }, step.at));
    });
  }

  document.getElementById("replay").addEventListener("click", () => {
    run(); window.scrollTo({ top: 0, behavior: "smooth" });
  });
  run();
})();
</script>
</body>
</html>"""
