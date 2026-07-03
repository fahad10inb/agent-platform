"""The public landing page served at / — the front door of the product.

Same pattern as widget_html.py / dashboard_html.py: one self-contained HTML
string served by the backend, no separate frontend deploy. 2026 visual
language: near-white canvas, Inter, hairline cards with layered violet-tinted
shadows, a single hero gradient glow (reprised once in the final CTA band).
The pitch leads with the differentiator — a receptionist that REMEMBERS every
customer — with a live widget demo embedded right in the hero. Honest content
only: no invented metrics, logos, testimonials or pricing.
"""

LANDING_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ReceptionAI — the receptionist that remembers every customer</title>
<meta name="description" content="A bilingual AI receptionist for UAE clinics, salons and agencies. Books appointments 24/7, remembers every caller, and captures every lead — in English and Arabic.">
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
  h1{font-size:clamp(40px,5.5vw,68px);font-weight:600;line-height:1.05;letter-spacing:-.035em}
  h2{font-size:clamp(30px,3.5vw,44px);font-weight:600;line-height:1.12;letter-spacing:-.025em}
  h3{font-size:20px;font-weight:600;letter-spacing:-.015em}
  .eyebrow{font-size:13px;font-weight:500;text-transform:uppercase;letter-spacing:.06em;color:var(--accent);margin-bottom:14px}
  .subhead{font-size:16px;color:var(--muted);margin-top:12px}
  .grad{background:linear-gradient(90deg,var(--accent),#b06bff);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:transparent}
  .num{font-variant-numeric:tabular-nums}
  /* buttons */
  .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 22px;border-radius:999px;
    font-size:15px;font-weight:600;text-decoration:none;border:0;cursor:pointer;
    transition:background .15s,transform .15s,border-color .15s}
  .btn-primary{background:var(--accent);color:#fff;box-shadow:inset 0 1px 0 rgba(255,255,255,.18)}
  .btn-primary:hover{background:var(--accent-deep);transform:translateY(-1px)}
  .btn-secondary{background:var(--card);color:var(--ink);border:1px solid var(--hairline)}
  .btn-secondary:hover{border-color:#d8d3ea;transform:translateY(-1px)}
  /* nav */
  #nav{position:fixed;top:0;left:0;right:0;height:60px;z-index:50;transition:background .2s,border-color .2s}
  #nav.scrolled{background:rgba(253,253,255,.8);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid var(--hairline)}
  .nav-inner{max-width:1120px;margin:0 auto;padding:0 24px;height:60px;display:flex;align-items:center;gap:28px}
  .logo{font-size:16px;font-weight:700;letter-spacing:-.015em;color:var(--ink);text-decoration:none}
  .logo span{color:var(--accent)}
  .nav-links{display:flex;gap:22px;margin-left:8px}
  .nav-links a{font-size:14px;font-weight:500;color:var(--body);text-decoration:none}
  .nav-links a:hover{color:var(--ink)}
  .nav-spacer{flex:1}
  .nav-ghost{font-size:14px;font-weight:500;color:var(--body);text-decoration:none;padding:8px 12px;border-radius:999px}
  .nav-ghost:hover{color:var(--ink);background:var(--surface)}
  #nav .btn{padding:9px 18px;font-size:14px}
  /* hero */
  .hero-glow{position:absolute;inset:-20% -10% auto;height:70%;
    background:radial-gradient(38% 45% at 22% 30%,rgba(124,92,255,.28),transparent 70%),
      radial-gradient(30% 40% at 68% 20%,rgba(255,158,122,.25),transparent 70%),
      radial-gradient(28% 35% at 85% 55%,rgba(255,122,198,.16),transparent 70%);
    filter:blur(60px);pointer-events:none}
  .hero{position:relative;overflow:hidden;padding:150px 0 96px}
  .hero-grid{position:relative;display:grid;grid-template-columns:1.02fr .98fr;gap:48px;align-items:center}
  .hero .sub{font-size:18px;color:var(--body);margin-top:20px;max-width:480px}
  .cta-row{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}
  .micro{font-size:13px;color:var(--muted);margin-top:14px}
  .demo-frame{background:var(--card);border:1px solid var(--hairline);border-radius:16px;box-shadow:var(--shadow-float);overflow:hidden}
  .titlebar{display:flex;gap:6px;padding:11px 14px;border-bottom:1px solid var(--hairline);background:var(--surface)}
  .titlebar span{width:10px;height:10px;border-radius:50%;border:1px solid var(--hairline);background:var(--card)}
  .demo-frame iframe{display:block;width:100%;height:520px;border:0}
  /* ribbon */
  .ribbon-sec{padding:0 0 96px}
  .ribbon{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--hairline);border-radius:12px;background:var(--card);box-shadow:var(--shadow-card)}
  .ribbon div{padding:20px 18px;font-size:14px;font-weight:500;color:var(--body);text-align:center;border-left:1px solid var(--hairline)}
  .ribbon div:first-child{border-left:0}
  /* problem band */
  .band{background:var(--surface);border-top:1px solid var(--hairline);border-bottom:1px solid var(--hairline)}
  .band .lede{font-size:17px;color:var(--body);max-width:640px;margin-top:16px}
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
  .vb{max-width:78%;padding:9px 13px;border-radius:14px;font-size:13.5px;line-height:1.45}
  .vb.user{align-self:flex-end;background:linear-gradient(135deg,#8f6fff,var(--accent-deep));color:#fff;border-bottom-right-radius:5px}
  .vb.agent{align-self:flex-start;background:#f1eff8;color:var(--ink);border-bottom-left-radius:5px}
  .vtable{margin-top:18px;border:1px solid var(--hairline);border-radius:10px;overflow:hidden}
  .vrow{display:flex;align-items:center;gap:10px;padding:9px 12px;font-size:13px;border-bottom:1px solid var(--hairline)}
  .vrow:last-child{border-bottom:0}
  .vrow .t{font-variant-numeric:tabular-nums;color:var(--muted);width:42px;flex:none}
  .vrow .g{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .vkey{margin-top:18px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;color:var(--accent-deep);
    background:var(--surface);border:1px solid var(--hairline);border-radius:8px;padding:8px 12px;align-self:flex-start}
  .chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:500;padding:3px 10px;border-radius:999px;white-space:nowrap}
  .chip::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor}
  .chip.confirmed{background:#e8f7ee;color:#147a3d}
  .chip.new{background:var(--accent-soft);color:var(--accent-deep)}
  /* industries */
  .pills{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:36px}
  .pill{background:var(--card);border:1px solid var(--hairline);border-radius:999px;padding:9px 20px;font-size:14.5px;font-weight:500;color:var(--body);box-shadow:var(--shadow-card)}
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
  .final .btn{margin-top:32px}
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
    .btn,#nav{transition:none}
  }
  /* responsive */
  @media(max-width:960px){
    .hero{padding-top:120px}
    .hero-grid{grid-template-columns:1fr;gap:40px}
    .steps,.bento{grid-template-columns:1fr 1fr}
    .ribbon{grid-template-columns:1fr 1fr}
    .ribbon div:nth-child(3){border-left:0;border-top:1px solid var(--hairline)}
    .ribbon div:nth-child(4){border-top:1px solid var(--hairline)}
    .nav-links{display:none}
  }
  @media(max-width:640px){
    section{padding:72px 0}
    .steps,.bento{grid-template-columns:1fr}
    .bcard.wide{grid-column:auto}
    .ribbon{grid-template-columns:1fr}
    .ribbon div{border-left:0;border-top:1px solid var(--hairline);text-align:left}
    .ribbon div:first-child{border-top:0}
    .nav-ghost{display:none}
    .demo-frame iframe{height:460px}
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
      <a href="#faq">FAQ</a>
    </nav>
    <span class="nav-spacer"></span>
    <a class="nav-ghost" href="/dashboard">Dashboard</a>
    <a class="btn btn-primary" href="/widget?business_id=bright-smile">Try the demo</a>
  </div>
</header>

<section class="hero">
  <div class="hero-glow"></div>
  <div class="container hero-grid">
    <div>
      <p class="eyebrow">AI receptionist for UAE clinics, salons &amp; agencies — English + العربية</p>
      <h1>The AI receptionist that <span class="grad">remembers</span> every customer</h1>
      <p class="sub">It greets returning customers by name, knows their usual service, and books
        them in one message — around the clock, in English or Arabic.</p>
      <div class="cta-row">
        <a class="btn btn-primary" href="/widget?business_id=bright-smile">Try the live demo</a>
        <a class="btn btn-secondary" href="/widget?business_id=velvet-hair">See the salon demo</a>
      </div>
      <p class="micro">No signup — chat with a demo business in seconds.</p>
    </div>
    <div class="demo-frame">
      <div class="titlebar"><span></span><span></span><span></span></div>
      <iframe src="/widget?business_id=velvet-hair" title="Live demo — chat with the salon receptionist" loading="lazy"></iframe>
    </div>
  </div>
</section>

<section class="ribbon-sec">
  <div class="container reveal">
    <div class="ribbon">
      <div>Answers instantly, 24/7</div>
      <div>English + Arabic</div>
      <div>Real bookings, zero double-slots</div>
      <div>Every caller remembered</div>
    </div>
  </div>
</section>

<section class="band">
  <div class="container reveal">
    <div class="sechead">
      <p class="eyebrow">Why it exists</p>
      <h2>A missed call is a lost booking.</h2>
      <p class="lede">Front desks close at night, get busy at noon, and can't answer two chats at
        once — so customers quietly book somewhere else. ReceptionAI answers every message the
        moment it arrives, books straight into your calendar, and hands your team a tidy list of
        bookings and leads instead of a pile of missed calls.</p>
    </div>
  </div>
</section>

<section id="how">
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">How it works</p>
      <h2>Live in an afternoon</h2>
      <p class="subhead">Three steps — no code, no new phone system.</p>
    </div>
    <div class="steps">
      <div class="step reveal"><div class="n">1</div>
        <h3>Tell us about your business</h3>
        <p>Name, hours, services, tone, FAQs. That one form is the whole onboarding.</p></div>
      <div class="step reveal"><div class="n">2</div>
        <h3>Put the chat on your site</h3>
        <p>One link or one iframe line — on your website, Instagram bio, or WhatsApp reply.</p></div>
      <div class="step reveal"><div class="n">3</div>
        <h3>Watch bookings &amp; leads roll in</h3>
        <p>The dashboard fills up in real time while the agent handles the conversations.</p></div>
    </div>
  </div>
</section>

<section id="product">
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">Product</p>
      <h2>A front desk that never forgets</h2>
      <p class="subhead">Everything a great receptionist does — with a perfect memory.</p>
    </div>
    <div class="bento">
      <div class="bcard wide reveal">
        <h3>Remembers every caller</h3>
        <p>Preferences, past visits, usual services — saved automatically and recalled the moment
          a returning customer says their name. Memory is isolated per business, always.</p>
        <div class="vchat" aria-hidden="true">
          <div class="vb user">hi, it's Layla — can I come in thursday?</div>
          <div class="vb agent">Layla! your usual blow-dry with Rana? 6pm is free 💜</div>
        </div>
      </div>
      <div class="bcard reveal">
        <h3>Real bookings</h3>
        <p>Live availability from your own working hours, with a database guarantee that one slot
          is never sold twice.</p>
        <div class="vtable" aria-hidden="true">
          <div class="vrow"><span class="t">10:00</span><span class="g">Sara M. — cleaning</span><span class="chip confirmed">confirmed</span></div>
          <div class="vrow"><span class="t">11:30</span><span class="g">Omar K. — check-up</span><span class="chip confirmed">confirmed</span></div>
          <div class="vrow"><span class="t">16:00</span><span class="g">Layla A. — blow-dry</span><span class="chip new">new</span></div>
        </div>
      </div>
      <div class="bcard reveal">
        <h3>Never loses a lead</h3>
        <p>Every enquiry becomes a captured lead — name, number, interest — waiting in your
          dashboard, not lost in a chat log.</p>
        <div class="vtable" aria-hidden="true">
          <div class="vrow"><span class="g">Fatima R. — 2-bed, Marina</span><span class="chip new">new</span></div>
        </div>
      </div>
      <div class="bcard reveal">
        <h3>Bilingual by nature</h3>
        <p>Answers in the customer's language — English or Arabic — and switches the moment
          they switch.</p>
        <div class="vchat" aria-hidden="true">
          <div class="vb agent" dir="rtl" lang="ar">أهلاً! كيف أقدر أساعدك اليوم؟</div>
        </div>
      </div>
      <div class="bcard reveal">
        <h3>Sounds like YOUR front desk</h3>
        <p>Each business gets its own persona — name, tone, services, FAQs. Warm and human, never
          scripted. Care first, logistics second.</p>
      </div>
      <div class="bcard reveal">
        <h3>Private by default</h3>
        <p>Every business's data lives behind its own key. Your customers, your bookings, your
          memory — never shared, never mixed.</p>
        <div class="vkey" aria-hidden="true">X-API-Key · one per business</div>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="container">
    <div class="sechead center reveal">
      <p class="eyebrow">Industries</p>
      <h2>Built for the front desk you already run</h2>
      <p class="subhead">Verticals tune how the agent books, captures and follows up.</p>
    </div>
    <div class="pills reveal">
      <span class="pill">Clinics</span>
      <span class="pill">Salons &amp; spas</span>
      <span class="pill">Real estate</span>
      <span class="pill">Home services</span>
      <span class="pill">Any small business</span>
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
        <summary>Does it speak Arabic?</summary>
        <p>Yes. It replies in the customer's language — English or Arabic — and switches
          mid-conversation when they do.</p>
      </details>
      <details>
        <summary>How do bookings work?</summary>
        <p>You set your opening hours and slot length once. The agent offers only genuinely free
          slots, and a database constraint guarantees a slot can never be booked twice. Bookings,
          reschedules and cancellations all land in your dashboard.</p>
      </details>
      <details>
        <summary>Can it hand off to a human?</summary>
        <p>It doesn't pretend to be one. When a conversation needs a person, it captures the
          customer's name, number and what they need as a lead, so your team can follow up
          directly.</p>
      </details>
      <details>
        <summary>Where does my data live?</summary>
        <p>Each business's conversations, bookings, leads and memory are isolated behind that
          business's own API key. Nothing is shared or mixed between businesses.</p>
      </details>
    </div>
  </div>
</section>

<section class="final">
  <div class="hero-glow"></div>
  <div class="container reveal">
    <h2>Give your business a front desk that never sleeps.</h2>
    <a class="btn btn-primary" href="/widget?business_id=bright-smile">Try the live demo</a>
  </div>
</section>

<footer>
  <div class="container foot-grid">
    <a class="logo" href="/">Reception<span>AI</span></a>
    <nav class="foot-links" aria-label="Footer">
      <a href="/widget?business_id=bright-smile">Clinic demo</a>
      <a href="/widget?business_id=velvet-hair">Salon demo</a>
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
