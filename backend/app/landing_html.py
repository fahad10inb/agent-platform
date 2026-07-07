"""The public landing page served at / — the front door of the product.

Same pattern as widget_html.py / dashboard_html.py: one self-contained HTML
string served by the backend, no separate frontend deploy, vanilla CSS/JS.

Conversion story (top to bottom): hero with the differentiator — a receptionist
that REMEMBERS every customer — and a live demo with an industry selector
(salon / clinic / real estate, all real seed businesses); proof beats for
memory and booking; how-it-works; benefit-first feature grid; a trust/security
section grounded in real guarantees (per-business isolation, identity
verification, DB-level double-booking protection); a founder's-promise card in
place of testimonials we don't have yet; honest founding-customer pricing with
no invented numbers; FAQ; final CTA. No fake logos, metrics or reviews.
"""

LANDING_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ReceptionAI — the AI receptionist that remembers every customer</title>
<meta name="description" content="A bilingual AI receptionist for salons, clinics and agencies in the UAE. It answers in seconds 24/7, books real appointments, captures every lead, and greets returning customers by name — in English and Arabic.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root{
    --canvas:#fdfdff; --surface:#f7f6fb; --surface-2:#f1effa; --card:#ffffff;
    --hairline:#e9e7f2; --hairline-2:#dcd8ea; --ink:#16141d; --body:#4c4a58; --muted:#716e80;
    --accent:#7c5cff; --accent-deep:#6847e6; --accent-soft:#efeaff;
    --ok:#147a3d; --ok-soft:#e8f7ee;
    --focus:rgba(124,92,255,.35);
    --shadow-card:0 0 0 1px rgba(23,21,31,.04),0 1px 1px rgba(46,26,110,.03),0 2px 4px rgba(46,26,110,.04),0 8px 16px -4px rgba(46,26,110,.06);
    --shadow-float:0 1px 1px rgba(46,26,110,.03),0 8px 16px -4px rgba(46,26,110,.06),0 24px 32px -8px rgba(46,26,110,.12);
  }
  *{margin:0;padding:0;box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{
    font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;
    font-feature-settings:'cv11','ss01';
    -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
    color:var(--ink);background:var(--canvas);font-size:16px;line-height:1.55;
  }
  ::selection{background:rgba(124,92,255,.22)}
  :focus-visible{outline:2px solid var(--focus);outline-offset:2px}
  .container{max-width:1120px;margin:0 auto;padding:0 24px}
  section{padding:96px 0;scroll-margin-top:72px}
  h1{font-size:clamp(38px,5.2vw,64px);font-weight:600;line-height:1.06;letter-spacing:-.035em}
  h2{font-size:clamp(28px,3.4vw,42px);font-weight:600;line-height:1.12;letter-spacing:-.025em}
  h3{font-size:19px;font-weight:600;letter-spacing:-.015em}
  .eyebrow{font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:var(--accent-deep);margin-bottom:14px}
  .subhead{font-size:16.5px;color:var(--muted);margin-top:14px;max-width:620px}
  .center .subhead{margin-left:auto;margin-right:auto}
  .grad{background:linear-gradient(90deg,var(--accent),#a86bff);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:transparent}
  .num{font-variant-numeric:tabular-nums}
  /* buttons */
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:13px 24px;border-radius:999px;
    font:inherit;font-size:15px;font-weight:600;text-decoration:none;border:0;cursor:pointer;
    transition:background .15s,transform .15s,border-color .15s,box-shadow .15s}
  .btn-primary{background:var(--accent);color:#fff;box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 1px 2px rgba(46,26,110,.24)}
  .btn-primary:hover{background:var(--accent-deep);transform:translateY(-1px)}
  .btn-secondary{background:var(--card);color:var(--ink);border:1px solid var(--hairline-2)}
  .btn-secondary:hover{border-color:#c9c2e2;transform:translateY(-1px)}
  /* nav */
  #nav{position:fixed;top:0;left:0;right:0;height:60px;z-index:50;transition:background .2s,border-color .2s}
  #nav.scrolled{background:rgba(253,253,255,.84);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid var(--hairline)}
  .nav-inner{max-width:1120px;margin:0 auto;padding:0 24px;height:60px;display:flex;align-items:center;gap:28px}
  .logo{font-size:16px;font-weight:700;letter-spacing:-.015em;color:var(--ink);text-decoration:none}
  .logo span{color:var(--accent-deep)}
  .nav-links{display:flex;gap:22px;margin-left:8px}
  .nav-links a{font-size:14px;font-weight:500;color:var(--body);text-decoration:none}
  .nav-links a:hover{color:var(--ink)}
  .nav-spacer{flex:1}
  .nav-ghost{font-size:14px;font-weight:500;color:var(--body);text-decoration:none;padding:8px 12px;border-radius:999px}
  .nav-ghost:hover{color:var(--ink);background:var(--surface)}
  #nav .btn{padding:9px 18px;font-size:14px}
  /* hero */
  .hero-glow{position:absolute;inset:-20% -10% auto;height:70%;
    background:radial-gradient(38% 45% at 22% 30%,rgba(124,92,255,.22),transparent 70%),
      radial-gradient(30% 40% at 68% 20%,rgba(255,158,122,.16),transparent 70%);
    filter:blur(60px);pointer-events:none}
  .hero{position:relative;overflow:hidden;padding:148px 0 96px}
  .hero-grid{position:relative;display:grid;grid-template-columns:1.02fr .98fr;gap:56px;align-items:start}
  .hero .sub{font-size:18px;color:var(--body);margin-top:20px;max-width:480px}
  .cta-row{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}
  .micro{font-size:13px;color:var(--muted);margin-top:14px}
  /* industry selector + demo */
  .ind-tabs{display:inline-flex;gap:2px;background:var(--surface);border:1px solid var(--hairline);border-radius:999px;padding:4px}
  .ind-tab{font:inherit;font-size:13.5px;font-weight:500;padding:7px 16px;border:0;border-radius:999px;cursor:pointer;
    background:transparent;color:var(--muted);transition:color .15s,background .15s,box-shadow .15s}
  .ind-tab:hover{color:var(--ink)}
  .ind-tab[aria-selected="true"]{background:var(--card);color:var(--ink);font-weight:600;box-shadow:var(--shadow-card)}
  .ind-line{font-size:13.5px;color:var(--muted);margin:10px 2px 12px;min-height:21px}
  .demo-frame{background:var(--card);border:1px solid var(--hairline);border-radius:16px;box-shadow:var(--shadow-float);overflow:hidden}
  .titlebar{display:flex;gap:6px;padding:11px 14px;border-bottom:1px solid var(--hairline);background:var(--surface)}
  .titlebar span{width:10px;height:10px;border-radius:50%;border:1px solid var(--hairline);background:var(--card)}
  .demo-frame iframe{display:block;width:100%;height:500px;border:0}
  /* ribbon */
  .ribbon-sec{padding:0 0 96px}
  .ribbon{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--hairline);border-radius:12px;background:var(--card);box-shadow:var(--shadow-card)}
  .ribbon div{padding:20px 18px;font-size:14px;font-weight:500;color:var(--body);text-align:center;border-left:1px solid var(--hairline)}
  .ribbon div:first-child{border-left:0}
  /* problem band */
  .band{background:var(--surface);border-top:1px solid var(--hairline);border-bottom:1px solid var(--hairline)}
  .band .lede{font-size:17px;color:var(--body);max-width:640px;margin-top:16px}
  /* conversation vignettes (memory duo + booking beat) */
  .duo{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:44px}
  .convo{background:var(--card);border:1px solid var(--hairline);border-radius:14px;box-shadow:var(--shadow-card);overflow:hidden;display:flex;flex-direction:column}
  .chead{display:flex;align-items:center;gap:8px;padding:11px 18px;border-bottom:1px solid var(--hairline);font-size:13px;font-weight:600;letter-spacing:.01em}
  .convo.plain .chead{color:var(--muted);background:var(--surface)}
  .convo.ours .chead{color:var(--accent-deep);background:var(--accent-soft)}
  .cbody{padding:18px;display:flex;flex-direction:column;gap:7px;flex:1}
  .cfoot{padding:11px 18px;border-top:1px solid var(--hairline);font-size:13px;color:var(--muted)}
  .vb{max-width:82%;padding:9px 13px;border-radius:14px;font-size:13.5px;line-height:1.45}
  .vb.user{align-self:flex-end;background:linear-gradient(135deg,#8f6fff,var(--accent-deep));color:#fff;border-bottom-right-radius:5px}
  .vb.agent{align-self:flex-start;background:var(--surface-2);color:var(--ink);border-bottom-left-radius:5px}
  .convo.plain .vb.user{background:#5d5a6c}
  .convo.plain .vb.agent{background:var(--surface);color:var(--body)}
  /* mini dashboard table */
  .vtable{border:1px solid var(--hairline);border-radius:10px;overflow:hidden}
  .vrow{display:flex;align-items:center;gap:10px;padding:10px 12px;font-size:13px;border-bottom:1px solid var(--hairline);background:var(--card)}
  .vrow:last-child{border-bottom:0}
  .vrow .t{font-variant-numeric:tabular-nums;color:var(--muted);width:44px;flex:none}
  .vrow .g{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .vrow.hot{background:#fbfaff}
  .chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:500;padding:3px 10px;border-radius:999px;white-space:nowrap}
  .chip::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor}
  .chip.confirmed{background:var(--ok-soft);color:var(--ok)}
  .chip.new{background:var(--accent-soft);color:var(--accent-deep)}
  .locknote{display:flex;gap:10px;margin-top:16px;padding:12px 14px;border:1px solid var(--hairline);border-radius:10px;
    background:var(--surface);font-size:13px;color:var(--body);align-items:flex-start}
  .locknote svg{width:16px;height:16px;flex:none;margin-top:2px;color:var(--accent-deep)}
  /* how it works */
  .steps{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:44px}
  .step{background:var(--card);border:1px solid var(--hairline);border-radius:12px;box-shadow:var(--shadow-card);padding:24px}
  .step .n{width:32px;height:32px;border-radius:50%;background:var(--accent-soft);color:var(--accent-deep);
    display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:600;margin-bottom:14px;font-variant-numeric:tabular-nums}
  .step h3{margin-bottom:6px}
  .step p{font-size:14.5px;color:var(--body)}
  /* bento */
  .bento{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:44px}
  .bcard{background:var(--card);border:1px solid var(--hairline);border-radius:12px;box-shadow:var(--shadow-card);padding:24px;display:flex;flex-direction:column}
  .bcard h3{margin-bottom:6px}
  .bcard p{font-size:14.5px;color:var(--body)}
  .bcard.wide{grid-column:span 2}
  .vchat{display:flex;flex-direction:column;gap:6px;margin-top:18px}
  .bcard .vtable{margin-top:18px}
  .kpis{display:flex;gap:10px;margin-top:18px;flex-wrap:wrap}
  .kpi-pill{flex:1;min-width:110px;border:1px solid var(--hairline);border-radius:10px;padding:10px 14px;background:var(--surface)}
  .kpi-pill b{display:block;font-size:20px;font-weight:600;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
  .kpi-pill span{font-size:12px;color:var(--muted)}
  /* trust trio */
  .trio{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:44px}
  .tcard{background:var(--card);border:1px solid var(--hairline);border-radius:12px;box-shadow:var(--shadow-card);padding:24px}
  .tico{width:40px;height:40px;border-radius:10px;background:var(--accent-soft);color:var(--accent-deep);
    display:grid;place-items:center;margin-bottom:16px}
  .tico svg{width:20px;height:20px}
  .tcard h3{margin-bottom:6px}
  .tcard p{font-size:14.5px;color:var(--body)}
  /* founder's promise */
  .promise{max-width:720px;margin:44px auto 0;background:var(--card);border:1px solid var(--hairline);border-radius:16px;
    box-shadow:var(--shadow-card);padding:36px 36px 30px}
  .promise .plede{font-size:16.5px;color:var(--body)}
  .promise ul{list-style:none;margin:22px 0 0;display:flex;flex-direction:column;gap:12px}
  .promise li{display:flex;gap:11px;font-size:15px;color:var(--body)}
  .promise li::before{content:"✓";color:var(--accent-deep);font-weight:600;flex:none}
  .sig{margin-top:24px;padding-top:18px;border-top:1px solid var(--hairline);font-size:13.5px;color:var(--muted)}
  /* pricing */
  .tiers{display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:860px;margin:44px auto 0}
  .tier{background:var(--card);border:1px solid var(--hairline);border-radius:16px;box-shadow:var(--shadow-card);
    padding:28px;display:flex;flex-direction:column;position:relative}
  .tier.featured{border-color:#cdbfff;box-shadow:var(--shadow-float)}
  .tbadge{position:absolute;top:-11px;left:24px;background:var(--accent);color:#fff;font-size:11.5px;font-weight:600;
    letter-spacing:.04em;text-transform:uppercase;padding:3px 11px;border-radius:999px}
  .tname{font-size:18px;font-weight:600;letter-spacing:-.015em}
  .tfor{font-size:13.5px;color:var(--muted);margin-top:2px}
  .tprice{margin-top:20px;font-size:22px;font-weight:600;letter-spacing:-.02em}
  .tnote{font-size:13px;color:var(--muted);margin-top:3px}
  .tier ul{list-style:none;margin:20px 0 24px;display:flex;flex-direction:column;gap:9px}
  .tier li{display:flex;gap:10px;font-size:14px;color:var(--body)}
  .tier li::before{content:"✓";color:var(--accent-deep);font-weight:600;flex:none}
  .tier .btn{margin-top:auto}
  .pfoot{text-align:center;font-size:13.5px;color:var(--muted);max-width:560px;margin:28px auto 0}
  /* faq */
  .faq{max-width:720px;margin:44px auto 0;border-top:1px solid var(--hairline)}
  details{border-bottom:1px solid var(--hairline)}
  summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:16px;
    padding:18px 4px;font-size:16px;font-weight:600;letter-spacing:-.01em}
  summary::-webkit-details-marker{display:none}
  summary::after{content:"+";font-size:20px;font-weight:400;color:var(--muted);transition:transform .2s;flex:none}
  details[open] summary::after{transform:rotate(45deg)}
  details p{font-size:15px;color:var(--body);padding:0 4px 18px;max-width:640px}
  /* final cta */
  .final{position:relative;overflow:hidden;text-align:center}
  .final h2{max-width:680px;margin:0 auto}
  .final .subhead{margin-left:auto;margin-right:auto}
  .final .cta-row{justify-content:center;margin-top:32px}
  .final .container{position:relative}
  /* footer */
  footer{background:var(--surface);border-top:1px solid var(--hairline);padding:36px 0}
  .foot-grid{display:flex;align-items:center;gap:24px;flex-wrap:wrap}
  .foot-links{display:flex;gap:20px;flex:1;justify-content:center;flex-wrap:wrap}
  .foot-links a{font-size:14px;color:var(--body);text-decoration:none}
  .foot-links a:hover{color:var(--ink)}
  .foot-note{font-size:13px;color:var(--muted)}
  /* section header helpers */
  .sechead{max-width:720px}
  .sechead.center{margin:0 auto;text-align:center}
  /* scroll reveal */
  .reveal{opacity:0;transform:translateY(14px);
    transition:opacity .6s cubic-bezier(.16,1,.3,1),transform .6s cubic-bezier(.16,1,.3,1)}
  .reveal.in{opacity:1;transform:none}
  @media (prefers-reduced-motion: reduce){
    html{scroll-behavior:auto}
    .reveal{opacity:1;transform:none;transition:none}
    .btn,#nav,.ind-tab{transition:none}
  }
  /* responsive */
  @media(max-width:960px){
    .hero{padding-top:118px}
    .hero-grid{grid-template-columns:1fr;gap:40px}
    .steps,.bento,.trio{grid-template-columns:1fr 1fr}
    .ribbon{grid-template-columns:1fr 1fr}
    .ribbon div:nth-child(3){border-left:0;border-top:1px solid var(--hairline)}
    .ribbon div:nth-child(4){border-top:1px solid var(--hairline)}
    .nav-links{display:none}
    .duo{grid-template-columns:1fr}
  }
  @media(max-width:640px){
    section{padding:72px 0}
    .steps,.bento,.trio,.tiers{grid-template-columns:1fr}
    .bcard.wide{grid-column:auto}
    .ribbon{grid-template-columns:1fr}
    .ribbon div{border-left:0;border-top:1px solid var(--hairline);text-align:left}
    .ribbon div:first-child{border-top:0}
    .nav-ghost{display:none}
    .demo-frame iframe{height:440px}
    .promise{padding:26px 22px}
  }
</style>
</head>
<body>

<header id="nav">
  <div class="nav-inner">
    <a class="logo" href="/">Reception<span>AI</span></a>
    <nav class="nav-links" aria-label="Primary">
      <a href="#product">Product</a>
      <a href="#how">How it works</a>
      <a href="#pricing">Pricing</a>
      <a href="#faq">FAQ</a>
    </nav>
    <span class="nav-spacer"></span>
    <a class="nav-ghost" href="/dashboard">Sign in</a>
    <a class="btn btn-primary" href="/widget?business_id=bright-smile">Try the demo</a>
  </div>
</header>

<section class="hero">
  <div class="hero-glow"></div>
  <div class="container hero-grid">
    <div>
      <p class="eyebrow">AI receptionist for salons, clinics &amp; agencies — English + العربية</p>
      <h1>The AI receptionist that <span class="grad">remembers</span> every customer</h1>
      <p class="sub">It answers in seconds at any hour, books real appointments straight into your
        calendar, and greets returning customers by name — in English or Arabic.</p>
      <div class="cta-row">
        <a class="btn btn-primary" href="/widget?business_id=bright-smile" target="_blank" rel="noopener">See it answer your customers</a>
        <a class="btn btn-secondary" href="#how">How it works</a>
      </div>
      <p class="micro">No signup. Pick your industry and chat with a live demo business →</p>
    </div>
    <div>
      <div class="ind-tabs" role="tablist" aria-label="Choose an industry demo">
        <button class="ind-tab" role="tab" aria-selected="true" data-biz="velvet-hair"
          data-line="Remembers every regular — their usual service, their favourite stylist, their last visit.">Salon</button>
        <button class="ind-tab" role="tab" aria-selected="false" data-biz="bright-smile"
          data-line="Fills your calendar with real appointments and answers insurance questions at 2am.">Clinic</button>
        <button class="ind-tab" role="tab" aria-selected="false" data-biz="skyline-realty"
          data-line="Never lets a buyer go cold — budget, area and phone number captured while you sleep.">Real estate</button>
      </div>
      <p class="ind-line" id="indLine">Remembers every regular — their usual service, their favourite stylist, their last visit.</p>
      <div class="demo-frame">
        <div class="titlebar"><span></span><span></span><span></span></div>
        <iframe id="demoFrame" src="/widget?business_id=velvet-hair" title="Live demo — chat with the receptionist" loading="lazy"></iframe>
      </div>
    </div>
  </div>
</section>

<section class="ribbon-sec">
  <div class="container reveal">
    <div class="ribbon">
      <div>Answers in seconds, 24/7</div>
      <div>English + Arabic</div>
      <div>Double-booking impossible</div>
      <div>Every customer remembered</div>
    </div>
  </div>
</section>

<section class="band">
  <div class="container reveal">
    <div class="sechead">
      <p class="eyebrow">Why it exists</p>
      <h2>A missed message is a lost booking.</h2>
      <p class="lede">Front desks close at night, get slammed at noon, and can't answer two chats at
        once — so customers quietly book somewhere else. ReceptionAI answers every message the
        moment it arrives, books straight into your calendar, and hands your team a tidy list of
        bookings and leads instead of a pile of missed calls.</p>
    </div>
  </div>
</section>

<section id="memory">
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">The difference</p>
      <h2>Your regulars aren't strangers.<br>Most chatbots treat them like strangers.</h2>
      <p class="subhead">ReceptionAI keeps a memory per customer, per business — preferences, past
        visits, favourite staff — and uses it the way a great front desk would.</p>
    </div>
    <div class="duo">
      <div class="convo plain reveal">
        <div class="chead">A typical chatbot</div>
        <div class="cbody" aria-label="Example conversation with a typical chatbot">
          <div class="vb user">hi, it's Layla — can I come in thursday?</div>
          <div class="vb agent">Hello! Which service would you like to book? Please provide your full name and phone number.</div>
          <div class="vb user">…the same as always?</div>
          <div class="vb agent">I'm sorry, I don't have that information.</div>
        </div>
        <div class="cfoot">Every visit starts from zero — and your regular feels like a number.</div>
      </div>
      <div class="convo ours reveal">
        <div class="chead">Your ReceptionAI front desk</div>
        <div class="cbody" aria-label="Example conversation with ReceptionAI">
          <div class="vb user">hi, it's Layla — can I come in thursday?</div>
          <div class="vb agent">Welcome back, Layla! Your usual blow-dry with Rana? She has 6:00 pm free on Thursday.</div>
          <div class="vb user">perfect 💜</div>
          <div class="vb agent">Booked — Thursday, 6:00 pm with Rana. See you then!</div>
        </div>
        <div class="cfoot">Remembered automatically after her first visit — no forms, no lookup.</div>
      </div>
    </div>
  </div>
</section>

<section id="booking" class="band">
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">Real bookings</p>
      <h2>From chat to a confirmed slot — no human in the loop</h2>
      <p class="subhead">Not a "we'll call you back". A real appointment, checked against your real
        availability, sitting in your dashboard seconds later.</p>
    </div>
    <div class="duo">
      <div class="convo ours reveal">
        <div class="chead">The conversation</div>
        <div class="cbody" aria-label="Example booking conversation">
          <div class="vb user">do you have anything tomorrow afternoon?</div>
          <div class="vb agent">Tomorrow I have 2:00, 3:30 or 5:00 pm free — which suits you?</div>
          <div class="vb user">3:30. It's Omar — 050 123 4567</div>
          <div class="vb agent">Done — tomorrow at 3:30 pm. See you then, Omar!</div>
        </div>
      </div>
      <div class="convo plain reveal">
        <div class="chead">Your dashboard, seconds later</div>
        <div class="cbody">
          <div class="vtable" aria-hidden="true">
            <div class="vrow"><span class="t">10:00</span><span class="g">Sara M. — cleaning</span><span class="chip confirmed">confirmed</span></div>
            <div class="vrow"><span class="t">11:30</span><span class="g">Fatima R. — check-up</span><span class="chip confirmed">confirmed</span></div>
            <div class="vrow hot"><span class="t">15:30</span><span class="g">Omar K. — appointment</span><span class="chip new">new</span></div>
          </div>
          <div class="locknote">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>
            <span>The moment a slot is confirmed, the database locks it. Two customers can never
              hold the same time — it's a constraint, not a promise.</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<section id="how">
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">How it works</p>
      <h2>Live in an afternoon</h2>
      <p class="subhead">Three steps — no code, no new phone system, no training period.</p>
    </div>
    <div class="steps">
      <div class="step reveal"><div class="n">1</div>
        <h3>Tell us about your business</h3>
        <p>Name, hours, services, team, house policies, FAQs. One form is the whole onboarding.</p></div>
      <div class="step reveal"><div class="n">2</div>
        <h3>Put the chat where customers are</h3>
        <p>One link or one iframe line — your website, Instagram bio, or WhatsApp auto-reply.</p></div>
      <div class="step reveal"><div class="n">3</div>
        <h3>Watch bookings &amp; leads roll in</h3>
        <p>The dashboard fills up in real time — including an estimate of the staff hours you saved.</p></div>
    </div>
  </div>
</section>

<section id="product">
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">Product</p>
      <h2>Everything a great receptionist does</h2>
      <p class="subhead">With a perfect memory, in two languages, at four in the morning.</p>
    </div>
    <div class="bento">
      <div class="bcard wide reveal">
        <h3>Greets returning customers like a real receptionist</h3>
        <p>Preferences, past visits and usual services are saved automatically and recalled the
          moment a returning customer says their name — so your regulars feel known, not processed.</p>
        <div class="vchat" aria-hidden="true">
          <div class="vb user">hi, it's Layla — can I come in thursday?</div>
          <div class="vb agent">Layla! Your usual blow-dry with Rana? 6pm is free 💜</div>
        </div>
      </div>
      <div class="bcard reveal">
        <h3>Real appointments, not callback requests</h3>
        <p>It offers only genuinely free slots from your own working hours — and a database
          guarantee means one slot is never sold twice.</p>
        <div class="vtable" aria-hidden="true">
          <div class="vrow"><span class="t">10:00</span><span class="g">Sara M. — cleaning</span><span class="chip confirmed">confirmed</span></div>
          <div class="vrow"><span class="t">16:00</span><span class="g">Layla A. — blow-dry</span><span class="chip new">new</span></div>
        </div>
      </div>
      <div class="bcard reveal">
        <h3>Recommends the right person</h3>
        <p>Tell it who's on your team and what they're great at. When a customer asks for "someone
          good with balayage", it suggests the right stylist by name.</p>
      </div>
      <div class="bcard reveal">
        <h3>Applies your house rules</h3>
        <p>Cancellation windows, walk-in policy, deposits, payment methods — it answers with your
          policies, consistently, so your staff never has to be the bad guy.</p>
      </div>
      <div class="bcard reveal">
        <h3>Speaks your customers' language</h3>
        <p>English or Arabic — it replies in whichever the customer uses, and switches the moment
          they switch.</p>
        <div class="vchat" aria-hidden="true">
          <div class="vb agent" dir="rtl" lang="ar">أهلاً! كيف أقدر أساعدك اليوم؟</div>
        </div>
      </div>
      <div class="bcard reveal">
        <h3>Never loses a lead</h3>
        <p>When someone isn't ready to book, their name, number and interest are captured as a lead
          in your dashboard — not lost in a chat log.</p>
        <div class="vtable" aria-hidden="true">
          <div class="vrow"><span class="g">Fatima R. — 2-bed, Marina</span><span class="chip new">new</span></div>
        </div>
      </div>
      <div class="bcard wide reveal">
        <h3>Shows you what it's worth</h3>
        <p>The owner dashboard tracks conversations, bookings, leads — and estimates the staff
          hours saved, so you can see the return, not just the activity.</p>
        <div class="kpis" aria-hidden="true">
          <div class="kpi-pill"><b>—</b><span>Bookings · 30 days</span></div>
          <div class="kpi-pill"><b>—</b><span>Leads · 30 days</span></div>
          <div class="kpi-pill"><b>—</b><span>Staff hours saved</span></div>
        </div>
      </div>
      <div class="bcard reveal">
        <h3>Sounds like <em>your</em> front desk</h3>
        <p>Your name, your tone, your services, your FAQs. Warm and human, never scripted — care
          first, logistics second.</p>
      </div>
    </div>
  </div>
</section>

<section id="trust" class="band">
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">Security &amp; trust</p>
      <h2>Built to be trusted with your customers</h2>
      <p class="subhead">The boring guarantees matter most. These aren't policies — they're how the
        system is built.</p>
    </div>
    <div class="trio">
      <div class="tcard reveal">
        <div class="tico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg></div>
        <h3>Your data is yours alone</h3>
        <p>Every business runs isolated behind its own private key. Your customers, bookings and
          memory are never shared with — or visible to — any other business.</p>
      </div>
      <div class="tcard reveal">
        <div class="tico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l7 3v5c0 4.6-3 8.4-7 10-4-1.6-7-5.4-7-10V6l7-3z"/><path d="M9 11.5l2 2 4-4"/></svg></div>
        <h3>Identity before information</h3>
        <p>Typing a name into a chat reveals nothing. Appointment details unlock only after the
          caller confirms the phone number on file — so nobody can fish for your customers' visits.</p>
      </div>
      <div class="tcard reveal">
        <div class="tico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 9.5h17M8 3v4M16 3v4M9.5 14.5l2 2 3.5-3.5"/></svg></div>
        <h3>Double-booking is impossible</h3>
        <p>One slot, one customer — enforced by a database constraint, not a line in a prompt. Your
          calendar stays clean even when two people ask for the same time at once.</p>
      </div>
    </div>
  </div>
</section>

<section id="promise">
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">A note from the builder</p>
      <h2>No fake logos. No invented numbers.</h2>
    </div>
    <div class="promise reveal">
      <p class="plede">ReceptionAI is new, and we won't pretend otherwise. This space is reserved
        for our founding customers' words — until they're here, you get our promise instead:</p>
      <ul>
        <li>We set it up with you, personally — you talk, we type.</li>
        <li>You get a direct line to the person who built it, not a ticket queue.</li>
        <li>We'll tell you plainly what it can't do — before you pay, not after.</li>
        <li>Founding customers shape the roadmap. Ask for what you need.</li>
      </ul>
      <p class="sig">— The ReceptionAI team · Dubai, UAE</p>
    </div>
  </div>
</section>

<section id="pricing" class="band">
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">Founding customer pricing</p>
      <h2>Early access, honest terms</h2>
      <p class="subhead">We're onboarding a small number of founding businesses. Join now and your
        rate is locked — it never goes up while you stay.</p>
    </div>
    <div class="tiers">
      <div class="tier reveal">
        <div class="tname">Starter</div>
        <div class="tfor">For a single location</div>
        <div class="tprice">Founding rate</div>
        <div class="tnote">Locked in for as long as you stay</div>
        <ul>
          <li>24/7 chat receptionist on your site &amp; socials</li>
          <li>Real bookings with double-booking protection</li>
          <li>Lead capture with names &amp; numbers</li>
          <li>Customer memory — regulars greeted by name</li>
          <li>English + Arabic</li>
          <li>Owner dashboard with hours-saved tracking</li>
        </ul>
        <a class="btn btn-secondary" href="/widget?business_id=bright-smile" target="_blank" rel="noopener">Try the live demo</a>
      </div>
      <div class="tier featured reveal">
        <span class="tbadge">Founding customers</span>
        <div class="tname">Growth</div>
        <div class="tfor">For multiple locations or high volume</div>
        <div class="tprice">Founding rate</div>
        <div class="tnote">Locked in for as long as you stay</div>
        <ul>
          <li>Everything in Starter</li>
          <li>A receptionist per location — data isolated for each</li>
          <li>Higher conversation volume</li>
          <li>Priority, founder-level support</li>
          <li>Onboarding done with you, personally</li>
        </ul>
        <a class="btn btn-primary" href="/widget?business_id=velvet-hair" target="_blank" rel="noopener">Start with the demo</a>
      </div>
    </div>
    <p class="pfoot">Final pricing is being set with our founding customers — early businesses lock
      in their rate before public launch. No long-term contracts.</p>
  </div>
</section>

<!-- Fair billing: the market's loudest complaint is billing betrayal (charged
     after cancelling, spam calls billed, silence billed as "resolutions") —
     so the pledge goes on the page, in writing, before billing even exists. -->
<section id="fair-billing">
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">Fair billing</p>
      <h2>Fair billing, in writing</h2>
      <p class="subhead">Paid plans aren't live yet — which is exactly why we're putting the rules
        in writing first. When paid plans launch, these three are the contract.</p>
    </div>
    <div class="trio">
      <div class="tcard reveal">
        <div class="tico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5h16l-6 7v6l-4 2v-8L4 5z"/></svg></div>
        <h3>Spam and one-line drive-bys are never counted.</h3>
        <p>A conversation only counts once a customer actually engages. Your dashboard's numbers
          already work this way today — junk never inflates them, so it can never inflate a bill.</p>
      </div>
      <div class="tcard reveal">
        <div class="tico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1.5 12S5.5 5 12 5s10.5 7 10.5 7-4 7-10.5 7S1.5 12 1.5 12z"/><circle cx="12" cy="12" r="3"/></svg></div>
        <h3>Your usage meter is always visible on your dashboard.</h3>
        <p>Day-by-day counts, updated as they happen — you see exactly what we see. No surprise
          invoice can exist when the meter is on your screen all month.</p>
      </div>
      <div class="tcard reveal">
        <div class="tico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg></div>
        <h3>Cancel anytime — one click, no email maze.</h3>
        <p>No retention scripts, no "call us to discuss", no billing that outlives the goodbye.
          Leaving should be as easy as joining, or the joining was a trap.</p>
      </div>
    </div>
  </div>
</section>

<section id="faq">
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">FAQ</p>
      <h2>Honest answers</h2>
      <p class="subhead">What it does — and what it doesn't.</p>
    </div>
    <div class="faq reveal">
      <details>
        <summary>What does it actually do?</summary>
        <p>It answers your customers' chat messages 24/7, books real appointments against your
          working hours, captures enquiries as leads, and remembers returning customers — their
          preferences, usual services and past visits — per business.</p>
      </details>
      <details>
        <summary>How long does setup take?</summary>
        <p>One form: your name, hours, services, team, policies and FAQs. Most businesses are live
          the same afternoon. No code, no new phone system, and nothing changes about how you work.</p>
      </details>
      <details>
        <summary>Does it speak Arabic?</summary>
        <p>Yes. It replies in the customer's language — English or Arabic — and switches
          mid-conversation when they do.</p>
      </details>
      <details>
        <summary>How do bookings work? Can it double-book us?</summary>
        <p>You set your opening hours and slot length once. The agent offers only genuinely free
          slots, and a database constraint guarantees a slot can never be booked twice — even if two
          customers ask for the same time at the same moment. Bookings, reschedules and
          cancellations all land in your dashboard.</p>
      </details>
      <details>
        <summary>What happens when it can't help?</summary>
        <p>It doesn't bluff and it doesn't pretend to be human. When a conversation needs a person,
          it captures the customer's name, number and what they need as a lead, so your team can
          follow up directly.</p>
      </details>
      <details>
        <summary>Where does my customers' data live?</summary>
        <p>Each business's conversations, bookings, leads and memory are isolated behind that
          business's own API key. Nothing is shared or mixed between businesses, and appointment
          details are only revealed after the caller verifies the phone number on file.</p>
      </details>
      <details>
        <summary>What does it cost?</summary>
        <p>We're finalising pricing with our founding customers — simple monthly tiers, no long-term
          contracts. Founding businesses lock in their rate before public launch and it never goes
          up while they stay.</p>
      </details>
      <details>
        <summary>Will spam or junk messages count against me?</summary>
        <p>Never. A conversation only counts once a customer sends a second message — spam and
          one-line drive-bys are excluded from your numbers today, and will be excluded from any
          bill when paid plans launch. Your usage meter stays visible on your dashboard, and
          cancelling will always be one click. That's the fair-billing pledge, in writing.</p>
      </details>
    </div>
  </div>
</section>

<section class="final">
  <div class="hero-glow"></div>
  <div class="container reveal">
    <h2>Right now, someone is messaging a business that won't answer until morning.</h2>
    <p class="subhead">Make sure it isn't yours.</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="/widget?business_id=bright-smile" target="_blank" rel="noopener">See it answer your customers</a>
      <a class="btn btn-secondary" href="/dashboard">Open the dashboard</a>
    </div>
  </div>
</section>

<footer>
  <div class="container foot-grid">
    <a class="logo" href="/">Reception<span>AI</span></a>
    <nav class="foot-links" aria-label="Footer">
      <a href="/widget?business_id=bright-smile">Clinic demo</a>
      <a href="/widget?business_id=velvet-hair">Salon demo</a>
      <a href="/widget?business_id=skyline-realty">Real estate demo</a>
      <a href="/dashboard">Dashboard</a>
    </nav>
    <span class="foot-note">Made for the UAE 🇦🇪</span>
  </div>
</footer>

<noscript><style>.reveal{opacity:1;transform:none}</style></noscript>
<script>
  // sticky nav: transparent over the hero, frosted after 24px of scroll
  const nav = document.getElementById("nav");
  const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 24);
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // industry selector — swaps the live demo iframe + one benefit line
  const frame = document.getElementById("demoFrame");
  const line = document.getElementById("indLine");
  document.querySelectorAll(".ind-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".ind-tab").forEach(t => t.setAttribute("aria-selected", t === tab ? "true" : "false"));
      line.textContent = tab.dataset.line;
      frame.src = "/widget?business_id=" + encodeURIComponent(tab.dataset.biz);
    });
  });

  // scroll reveal — one observer, unobserve after entry, reduced-motion handled in CSS
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }
  }, { threshold: .12, rootMargin: "0px 0px -8% 0px" });
  document.querySelectorAll(".reveal").forEach(el => io.observe(el));
</script>
</body>
</html>"""
