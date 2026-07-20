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
  .brand{display:flex;align-items:center;gap:10px;min-width:0;text-decoration:none;color:inherit;
    border-radius:8px;padding:2px;transition:opacity .15s}
  .brand:hover{opacity:.8}
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
  .reset{display:inline-flex;align-items:center;font-size:13px;font-weight:500;color:#c8dbe4;
    border:1px solid var(--ink-line);text-decoration:none;
    padding:6px 13px;border-radius:8px;transition:background .15s}
  .reset:hover{background:rgba(255,255,255,.07);color:#fff}
  .reset.gold{border-color:var(--brass);color:var(--brass-bright)}
  .reset.gold:hover{background:rgba(213,162,76,.12);color:#fff}
  /* language toggle — the whole customer side switches EN / العربية (RTL) */
  .langtog{display:inline-flex;gap:2px;background:rgba(255,255,255,.06);border:1px solid var(--ink-line);border-radius:8px;padding:2px}
  .langtog button{font:inherit;font-size:12.5px;font-weight:600;color:#c8dbe4;padding:5px 11px;border-radius:6px;line-height:1;transition:background .15s,color .15s}
  .langtog button.on{background:var(--brass);color:#1a1206}
  #left.ar{direction:rtl}
  @media (max-width:640px){ .live,.reset.gold{display:none} }

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
  .chip:disabled{opacity:.45;pointer-events:none}
  /* auto-tour bar — plays the winning sequence itself, so on a call it runs
     hands-free instead of the seller typing. Frames the whole thing as after-hours. */
  .tourbar{flex:none;display:flex;flex-wrap:wrap;align-items:center;gap:10px 13px;padding:10px 22px 2px}
  .tourbtn{flex:none;display:inline-flex;align-items:center;gap:7px;font-size:13px;font-weight:600;
    padding:8px 15px;border-radius:999px;white-space:nowrap;
    background:linear-gradient(150deg,var(--brass-bright),var(--brass));color:#1a1206;
    box-shadow:0 6px 16px -9px rgba(184,134,59,.75);transition:filter .15s,transform .1s}
  .tourbtn:hover{filter:brightness(1.06)} .tourbtn:active{transform:scale(.96)}
  .tourbtn.running{background:#fff;color:var(--body);border:1px solid var(--hairline-2);box-shadow:none}
  .tframe{font-size:12.5px;color:var(--muted);line-height:1.4;flex:1;min-width:160px}
  .tframe b{color:var(--body);font-weight:600}
  form{flex:none;display:flex;align-items:flex-end;gap:10px;padding:12px 22px 18px;
    border-top:1px solid var(--hairline);background:var(--card)}
  #m{flex:1;border:1px solid var(--hairline-2);border-radius:11px;outline:none;resize:none;
    background:var(--paper);color:var(--text);font:inherit;font-size:15px;padding:11px 13px;max-height:110px}
  #m:focus{border-color:var(--brass);background:#fff}
  #send{width:42px;height:42px;flex:none;border-radius:11px;display:grid;place-items:center;
    background:var(--hairline-2);transition:background .15s,transform .1s}
  #send.on{background:var(--ink)} #send.on:hover{background:var(--ink-3)}
  #send:active{transform:scale(.95)}
  /* Icon follows state — white on the inactive tan fill is ~1.6:1 and reads as a
     broken control rather than a waiting one. */
  #send svg{width:17px;height:17px;fill:var(--muted);transition:fill .15s}
  #send.on svg{fill:#fff}

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

  /* mobile: ONE panel at a time via a tab switcher — a fixed 50/50 split crams
     the chat and the ops feed into unusable slivers on a phone */
  .mtabs{display:none;flex:none;gap:6px;padding:8px 14px;background:var(--ink);border-bottom:1px solid var(--ink-line)}
  .mtab{flex:1;display:inline-flex;align-items:center;justify-content:center;gap:7px;font:inherit;
    font-size:13.5px;font-weight:600;color:#c8dbe4;padding:9px 10px;border-radius:9px;cursor:pointer;
    border:1px solid var(--ink-line);background:rgba(255,255,255,.04);transition:background .15s,color .15s}
  .mtab.active{background:var(--brass);color:#1a1206;border-color:var(--brass)}
  .mtab-badge{font-family:var(--mono);font-size:11px;min-width:18px;text-align:center;padding:1px 5px;
    border-radius:999px;background:rgba(255,255,255,.18);color:inherit}
  .mtab.active .mtab-badge{background:rgba(0,0,0,.16)}
  @keyframes mtabpulse{0%{box-shadow:0 0 0 0 rgba(213,162,76,.55)}100%{box-shadow:0 0 0 11px rgba(213,162,76,0)}}
  .mtab.pulse{animation:mtabpulse .9s ease-out}
  @media (max-width:900px){
    .mtabs{display:flex}
    #split{display:block}
    #left,#right{height:100%;min-height:0}
    #left{border-right:0}
    #split[data-m="left"] #right{display:none}
    #split[data-m="right"] #left{display:none}
  }
  @media (prefers-reduced-motion:reduce){*{animation:none !important;transition:none !important}}
</style>
</head>
<body>
<div id="shell">
  <div class="topbar">
    <a class="brand" href="/" title="Back to ReceptionAI">
      <div class="mark" id="mark">R</div>
      <div style="min-width:0">
        <div class="bizname" id="bizname">Loading…</div>
        <div class="bizsub" id="bizsub">live demo</div>
      </div>
    </a>
    <div class="grow"></div>
    <div class="live"><span class="pulse"></span><span data-i18n="live">Live — not a recording</span></div>
    <div class="langtog" role="group" aria-label="Language">
      <button type="button" data-lang="en" class="on">EN</button>
      <button type="button" data-lang="ar" lang="ar">ع</button>
    </div>
    <!-- The last beat of the pitch: the lead you just watched it capture is
         waiting in the owner's dashboard. Without this the demo dead-ends. -->
    <a class="reset gold" href="/dashboard" target="_blank" rel="noopener" data-i18n="ownerView">Owner's view ↗</a>
    <button class="reset" id="reset" data-i18n="reset">Reset</button>
  </div>

  <div class="mtabs" role="tablist" aria-label="View">
    <button class="mtab active" type="button" data-m="left">💬 <span data-i18n="mtabChat">Chat</span></button>
    <button class="mtab" type="button" data-m="right">📊 <span data-i18n="mtabWork">Activity</span> <b class="mtab-badge" id="mtabCount">0</b></button>
  </div>

  <div id="split" data-m="left">
    <!-- LEFT: the buyer -->
    <div id="left">
      <div class="lhead">
        <div class="eyebrow" data-i18n="lheadEye">You are the buyer</div>
        <h2 data-i18n="lheadH2">Talk to it like a customer would</h2>
        <p data-i18n="lheadP">Ask about a property, give your budget, book a viewing.</p>
      </div>
      <div id="chat" role="log" aria-live="polite"></div>
      <div class="tourbar">
        <button class="tourbtn" id="tour" type="button">▶ Watch it run</button>
        <span class="tframe" data-i18n-html="tframe"><b>It's 11 PM — your team's offline.</b> Play it hands-free, or type as the buyer.</span>
      </div>
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
        <div class="eyebrow" data-i18n="rheadEye">What the agent is doing</div>
        <h2 data-i18n="rheadH2">Every action, as it happens</h2>
        <p data-i18n="rheadP">Not a chatbot — an operator working your business.</p>
        <div class="ground" id="ground"></div>
      </div>
      <div id="feed">
        <div class="empty" id="empty">
          <div class="big">◇</div>
          Send a message on the left.<br>Every real action the agent takes appears here.
        </div>
      </div>
      <div class="tally">
        <div class="tcell"><b id="tLeads">0</b><span data-i18n="tallyLeads">Leads</span></div>
        <div class="tcell"><b id="tQual">0</b><span data-i18n="tallyQual">Qualified</span></div>
        <div class="tcell"><b id="tBook">0</b><span data-i18n="tallyBook">Booked</span></div>
        <div class="tcell"><b id="tActs">0</b><span data-i18n="tallyActs">Actions</span></div>
      </div>
    </div>
  </div>
</div>

<script>
  const params = new URLSearchParams(location.search);
  const bizId = params.get("business_id") || "skyline-realty";
  const chat = document.getElementById("chat"), feed = document.getElementById("feed");
  const f = document.getElementById("f"), m = document.getElementById("m"), send = document.getElementById("send");
  const mSplit = document.getElementById("split");
  let convId = newConv();
  let n = { leads: 0, qual: 0, book: 0, acts: 0 };

  // ── i18n: the demo runs FULLY in English or Arabic (RTL) ───────────────
  // The buyer-side chat, the prompt chips, the greeting, the 8-turn tour, the
  // console labels and the event titles all switch language; picking العربية
  // flips the customer side to right-to-left. The AI mirrors the caller's
  // language on its own, so an Arabic tour gets Arabic replies for free.
  const L = {
    en: {
      live: "Live — not a recording", ownerView: "Owner's view ↗", reset: "Reset",
      lheadEye: "You are the buyer", lheadH2: "Talk to it like a customer would",
      lheadP: "Ask about a property, give your budget, book a viewing.",
      tourRun: "▶ Watch it run", tourStopLbl: "■ Stop",
      tframe: "<b>It's 11 PM — your team's offline.</b> Play it hands-free, or type as the buyer.",
      placeholder: "Type as the buyer…",
      rheadEye: "What the agent is doing", rheadH2: "Every action, as it happens",
      rheadP: "Not a chatbot — an operator working your business.",
      empty: "Send a message on the left.<br>Every real action the agent takes appears here.",
      greet: "Hi! I'm the AI assistant here — I can answer questions, match you to a property, book a viewing, or get you a human. How can I help?",
      tallyLeads: "Leads", tallyQual: "Qualified", tallyBook: "Booked", tallyActs: "Actions",
      mtabChat: "Chat", mtabWork: "Activity",
      ground: { listings: "Listings", permitted: "Permitted", noPermit: "No permit", services: "Services" },
      events: {},  // English titles pass through unchanged
      tour: {
        real_estate: [
          "Hi, I saw a 2-bedroom in JVC — is it still available?",
          "What's the rent, and does it have parking?",
          "My budget's around 95k a year, moving next month",
          "It's just me and my wife — we'd pay cash",
          "What about the 3-bedroom in JVC?",
          "Let's view the 2-bed. Can I do Thursday at 4pm?",
          "Actually, could we make it 5pm instead?",
          "Perfect. Could a human agent call me about the paperwork?",
        ],
        general: [
          "Hi — what are your opening hours?",
          "I'd like to book an appointment",
          "Does Thursday at 4pm work?",
          "Could a human call me to confirm?",
        ],
      },
      chips: {
        real_estate: [
          "Hi, I saw a 2-bedroom in JVC — what's the price?",
          "Budget is 1.5M, cash, moving next month",
          "What about the 3-bedroom in JVC?",
          "Can I view it Thursday at 4pm?",
          "Can a human call me?",
        ],
        general: ["What are your hours?", "I'd like to book an appointment", "How much does it cost?", "Can a human call me?"],
      },
    },
    ar: {
      live: "مباشر — ليس تسجيلاً", ownerView: "شاشة المالك ↗", reset: "إعادة",
      lheadEye: "أنت المشتري", lheadH2: "تحدّث معه كأنك عميل",
      lheadP: "اسأل عن عقار، اذكر ميزانيتك، احجز معاينة.",
      tourRun: "▶ شغّله تلقائياً", tourStopLbl: "■ إيقاف",
      tframe: "<b>الساعة ١١ مساءً — فريقك غير متاح.</b> شغّله تلقائياً، أو اكتب كأنك المشتري.",
      placeholder: "اكتب كأنك المشتري…",
      rheadEye: "ماذا يفعل الوكيل", rheadH2: "كل إجراء، لحظة حدوثه",
      rheadP: "ليس مجرد بوت — بل موظف يدير عملك.",
      empty: "أرسل رسالة على اليمين.<br>كل إجراء حقيقي يقوم به الوكيل يظهر هنا.",
      greet: "مرحباً! أنا المساعد الذكي هنا — أقدر أجاوب على أسئلتك، أرشّح لك عقاراً، أحجز معاينة، أو أوصلك بموظف. كيف أقدر أساعدك؟",
      tallyLeads: "عملاء", tallyQual: "مؤهّلون", tallyBook: "محجوز", tallyActs: "إجراءات",
      mtabChat: "المحادثة", mtabWork: "النشاط",
      ground: { listings: "العقارات", permitted: "بترخيص", noPermit: "بدون ترخيص", services: "الخدمات" },
      events: {
        "Lead captured": "تم تسجيل العميل",
        "Qualified & scored": "تم التأهيل والتقييم",
        "Checked the calendar": "تم فحص المواعيد",
        "Viewing booked": "تم حجز المعاينة",
        "Slot unavailable — no double-booking": "الموعد محجوز — لا ازدواج في الحجز",
        "Appointment moved": "تم تعديل الموعد",
        "Appointment cancelled": "تم إلغاء الموعد",
        "Appointment confirmed": "تم تأكيد الموعد",
        "Recognised the caller": "تم التعرّف على العميل",
        "Checked caller history": "تم فحص سجل العميل",
        "Remembered for next time": "تم الحفظ للمرة القادمة",
        "Looked up their appointments": "تم البحث عن مواعيده",
        "Handed to a human": "تم التحويل لموظف",
        "Do-not-contact recorded": "تم تسجيل عدم التواصل",
      },
      tour: {
        real_estate: [
          "مرحبا، شفت شقة غرفتين في JVC — لسه متاحة؟",
          "كم الإيجار؟ وفيه موقف سيارة؟",
          "ميزانيتي حوالي ٩٥ ألف بالسنة، وناوي أنتقل الشهر الجاي",
          "أنا وزوجتي بس، والدفع كاش",
          "وش عندكم بـ ٣ غرف في JVC؟",
          "تمام، أبي أعاين شقة الغرفتين. ممكن الخميس الساعة ٤؟",
          "بصراحة، ممكن نخليها ٥ بدل ٤؟",
          "ممتاز. ممكن موظف بشري يتصل فيني بخصوص الأوراق؟",
        ],
        general: [
          "مرحبا، متى مواعيد العمل عندكم؟",
          "أبي أحجز موعد",
          "يناسبني الخميس الساعة ٤؟",
          "ممكن موظف بشري يتصل فيني؟",
        ],
      },
      chips: {
        real_estate: [
          "مرحبا، شفت شقة غرفتين في JVC — كم السعر؟",
          "ميزانيتي ٩٥ ألف بالسنة، كاش، وناوي أنتقل الشهر الجاي",
          "وش عندكم ٣ غرف في JVC؟",
          "ممكن أعاين الخميس الساعة ٤؟",
          "أبي أكلّم موظف بشري",
        ],
        general: ["متى مواعيد العمل؟", "أبي أحجز موعد", "كم التكلفة؟", "ممكن موظف بشري يتصل فيني؟"],
      },
    },
  };

  let lang = "en", vertical = "general", ctx = null;
  let tourList = L.en.tour.general, touring = false, tourStop = false;
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  function newConv() {
    return "demo-" + (self.crypto && crypto.randomUUID ? crypto.randomUUID()
      : Math.random().toString(36).slice(2) + Date.now().toString(36));
  }
  function esc(s){ return (s==null?"":String(s)); }

  // ── grounding: prove the agent runs on THEIR data ──────────────────────
  fetch("/demo/context?business_id=" + encodeURIComponent(bizId))
    .then(r => r.ok ? r.json() : null).then(c => {
      if (!c) return;
      ctx = c; vertical = c.vertical || "general";
      document.getElementById("bizname").textContent = c.name;
      document.getElementById("bizsub").textContent = (c.type || c.vertical || "").toString();
      document.getElementById("mark").textContent = (c.name || "R").trim().charAt(0).toUpperCase();
      document.title = c.name + " · Live demo";
      refreshLangDependent();
    }).catch(() => { vertical = "general"; refreshLangDependent(); });

  function renderGround() {
    if (!ctx) return;
    const t = L[lang], cells = [];
    if (ctx.listings) {
      cells.push([t.ground.listings, ctx.listings, false]);
      cells.push([t.ground.permitted, ctx.listings_permitted, false]);
      if (ctx.listings_unpermitted) cells.push([t.ground.noPermit, ctx.listings_unpermitted, true]);
    }
    if (ctx.services) cells.push([t.ground.services, ctx.services, false]);
    document.getElementById("ground").innerHTML = cells.map(([label, val, warn]) =>
      `<div class="gcell ${warn?"warn":""}"><b>${esc(val)}</b><span>${esc(label)}</span></div>`
    ).join("");
  }

  // Prompt chips walk a prospect into the selling moments (real price →
  // qualify → the 3BR trips the permit refusal → a booked viewing), in the
  // chosen language. These MUST match the seeded inventory or the demo misses.
  function setChips() {
    const list = L[lang].chips[vertical] || L[lang].chips.general;
    const box = document.getElementById("chips");
    box.innerHTML = "";
    list.forEach(txt => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "chip"; b.textContent = txt;
      b.addEventListener("click", () => { m.value = txt; f.requestSubmit(); });
      box.appendChild(b);
    });
  }

  function refreshLangDependent() {
    renderGround(); setChips();
    tourList = L[lang].tour[vertical] || L[lang].tour.general;
  }

  // Flip the whole customer side to a language (Arabic = RTL) and restart clean.
  function applyLang(next) {
    lang = next;
    const t = L[lang];
    document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t[el.dataset.i18n]; });
    document.querySelectorAll("[data-i18n-html]").forEach(el => { el.innerHTML = t[el.dataset.i18nHtml]; });
    m.placeholder = t.placeholder;
    document.getElementById("left").classList.toggle("ar", lang === "ar");
    document.querySelectorAll(".langtog button").forEach(b => b.classList.toggle("on", b.dataset.lang === lang));
    if (!touring) document.getElementById("tour").textContent = t.tourRun;
    refreshLangDependent();
    doReset(false);
  }
  document.querySelectorAll(".langtog button").forEach(b =>
    b.addEventListener("click", () => { if (b.dataset.lang !== lang) applyLang(b.dataset.lang); }));

  // mobile: the tab switcher chooses which panel fills the screen (a 50/50 split
  // is unusable on a phone). Desktop shows both side by side and ignores this.
  document.querySelectorAll(".mtab").forEach(b =>
    b.addEventListener("click", () => {
      document.querySelectorAll(".mtab").forEach(x => x.classList.toggle("active", x === b));
      mSplit.setAttribute("data-m", b.dataset.m);
      b.classList.remove("pulse");
    }));

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
  function greet() { row(L[lang].greet, "ai"); }

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
    const rawTitle = ev.title || ev.kind || "";
    const b = document.createElement("b"); b.textContent = L[lang].events[rawTitle] || rawTitle;
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
    // mobile: count the Activity tab's badge and nudge it if the viewer is on Chat
    const mc = document.getElementById("mtabCount");
    if (mc) mc.textContent = n.acts;
    if (mSplit.getAttribute("data-m") === "left") {
      const rt = document.querySelector('.mtab[data-m="right"]');
      if (rt) { rt.classList.remove("pulse"); void rt.offsetWidth; rt.classList.add("pulse"); }
    }
  }

  function grow() { m.style.height = "auto"; m.style.height = Math.min(m.scrollHeight, 110) + "px"; }
  function sync() { send.classList.toggle("on", m.value.trim().length > 0); }
  m.addEventListener("input", () => { grow(); sync(); });
  m.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); f.requestSubmit(); }
  });

  // One turn, choreographed so the two panels move TOGETHER: post the buyer's
  // line, keep the typing dots up on the left while the right-hand work feed
  // streams in FIRST (the agent visibly working), then drop the reply. The
  // console is seen to drive the answer instead of trailing it.
  async function sendMessage(text) {
    row(text, "me"); send.disabled = true;
    const tr = typing();
    try {
      const res = await fetch("/demo/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: convId, business_id: bizId })
      });
      const data = await res.json();
      const evs = data.events || [];
      for (const ev of evs) { addEvent(ev); await sleep(430); }  // work streams while it "thinks"
      if (evs.length) await sleep(260);                          // a beat, then the reply lands
      tr.remove();
      row(data.reply || "Sorry — something went wrong. Please try again.", "ai");
    } catch (err) {
      tr.remove(); row("Network error — please try again.", "ai");
    } finally { send.disabled = false; }
  }

  f.addEventListener("submit", async e => {
    e.preventDefault();
    if (touring) return;  // the tour drives the chat; ignore manual sends mid-tour
    const text = m.value.trim(); if (!text) return;
    m.value = ""; grow(); sync();
    await sendMessage(text);
    sync(); m.focus();
  });

  // ── the tour: fire the sequence itself, pausing for each turn's feed ────
  async function runTour() {
    if (touring) { tourStop = true; return; }  // second click = stop
    doReset(false);                            // clean slate + greeting
    touring = true; tourStop = false;
    const btn = document.getElementById("tour");
    btn.classList.add("running"); btn.textContent = L[lang].tourStopLbl;
    m.disabled = true;
    document.querySelectorAll(".chip").forEach(c => c.disabled = true);
    try {
      for (const line of tourList) {
        if (tourStop) break;
        await sleep(populated() ? 1700 : 600);  // read the previous reply first
        if (tourStop) break;
        await sendMessage(line);                 // streams its own work + reply
      }
    } finally {
      touring = false; tourStop = false;
      btn.classList.remove("running"); btn.textContent = L[lang].tourRun;
      m.disabled = false;
      document.querySelectorAll(".chip").forEach(c => c.disabled = false);
      sync(); m.focus();
    }
  }
  function populated() { return chat.querySelectorAll(".row.me").length > 0; }
  document.getElementById("tour").addEventListener("click", runTour);

  function doReset(focus = true) {
    tourStop = true;  // stop any running tour
    convId = newConv();
    chat.innerHTML = "";
    feed.innerHTML = '<div class="empty" id="empty"><div class="big">◇</div>' + L[lang].empty + '</div>';
    n = { leads: 0, qual: 0, book: 0, acts: 0 };
    ["tLeads","tQual","tBook","tActs","mtabCount"].forEach(id => document.getElementById(id).textContent = "0");
    greet(); if (focus) m.focus();
  }
  document.getElementById("reset").addEventListener("click", () => doReset(true));

  applyLang("en"); grow(); sync(); m.focus();
</script>
</body>
</html>"""
