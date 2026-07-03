"""The public landing page served at / — the front door of the product.

Same pattern as widget_html.py / dashboard_html.py: one self-contained HTML
string served by the backend, no separate frontend deploy. Visual language
matches the widget/dashboard: near-white wash, soft lavender/peach glow,
violet accents. The pitch leads with the differentiator — a receptionist
that REMEMBERS every customer — not generic "AI chatbot" claims.
"""

LANDING_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reception AI — the receptionist that remembers every customer</title>
<meta name="description" content="A bilingual AI receptionist for UAE clinics, salons and agencies. Books appointments 24/7, remembers every caller, and captures every lead — in English and Arabic.">
<style>
  :root{
    --ink:#241b3a; --muted:#6b6285; --violet:#7c5cff; --violet-deep:#5b3df5;
    --card:#ffffffcc; --line:#e9e4f6;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  body{
    font-family:ui-sans-serif,system-ui,'Segoe UI',Roboto,Arial,sans-serif;
    color:var(--ink); background:#faf9fe; line-height:1.6;
  }
  .wash{position:fixed;inset:0;z-index:-1;background:
    radial-gradient(60% 50% at 15% 0%, #efe9ff 0%, transparent 60%),
    radial-gradient(50% 40% at 90% 10%, #ffeee3 0%, transparent 55%),
    radial-gradient(45% 45% at 60% 100%, #eaf3ff 0%, transparent 60%);}
  .wrap{max-width:1000px;margin:0 auto;padding:0 24px}
  header{display:flex;align-items:center;justify-content:space-between;padding:22px 0}
  .logo{font-weight:800;letter-spacing:.2px}
  .logo span{color:var(--violet)}
  nav a{color:var(--muted);text-decoration:none;margin-left:22px;font-size:14.5px}
  nav a:hover{color:var(--ink)}
  .hero{padding:72px 0 40px;text-align:center}
  .eyebrow{display:inline-block;font-size:13px;color:var(--violet-deep);
    background:#efe9ff;border:1px solid var(--line);padding:5px 14px;border-radius:999px;margin-bottom:18px}
  h1{font-size:clamp(30px,5.4vw,52px);line-height:1.12;font-weight:800;letter-spacing:-.5px}
  h1 em{font-style:normal;background:linear-gradient(90deg,var(--violet),#b46bff);
    -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
  .sub{max-width:620px;margin:18px auto 0;color:var(--muted);font-size:17.5px}
  .cta{margin-top:30px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
  .btn{display:inline-block;padding:13px 26px;border-radius:12px;text-decoration:none;font-weight:600;font-size:15.5px}
  .btn-primary{color:#fff;background:linear-gradient(135deg,var(--violet),var(--violet-deep));
    box-shadow:0 8px 24px #7c5cff44}
  .btn-primary:hover{filter:brightness(1.06)}
  .btn-ghost{color:var(--violet-deep);border:1.5px solid #d9cffa;background:#fff}
  .demo-note{margin-top:12px;font-size:13px;color:var(--muted)}
  .chatline{max-width:560px;margin:46px auto 0;text-align:left;background:var(--card);
    border:1px solid var(--line);border-radius:18px;padding:22px 24px;box-shadow:0 10px 40px #7c5cff14}
  .msg{margin:10px 0;font-size:15px}
  .msg b{color:var(--violet-deep);font-weight:650}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px;padding:56px 0 8px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px}
  .card h3{font-size:17px;margin-bottom:8px}
  .card p{color:var(--muted);font-size:14.5px}
  .card .ico{font-size:22px;margin-bottom:10px;display:block}
  .steps{padding:56px 0}
  .steps h2,.verts h2{text-align:center;font-size:28px;margin-bottom:26px;letter-spacing:-.3px}
  .step{display:flex;gap:16px;align-items:flex-start;max-width:640px;margin:0 auto 18px}
  .n{flex:none;width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;
    color:#fff;font-weight:700;background:linear-gradient(135deg,var(--violet),var(--violet-deep))}
  .verts{padding:8px 0 56px}
  .pills{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
  .pill{background:#fff;border:1px solid var(--line);border-radius:999px;padding:9px 20px;font-size:14.5px;color:var(--ink)}
  footer{border-top:1px solid var(--line);padding:26px 0 34px;text-align:center;color:var(--muted);font-size:13.5px}
  footer a{color:var(--violet-deep);text-decoration:none}
</style>
</head>
<body>
<div class="wash"></div>
<div class="wrap">

<header>
  <div class="logo">Reception<span>AI</span></div>
  <nav>
    <a href="/widget?business_id=bright-smile">Live demo</a>
    <a href="/dashboard">Dashboard</a>
  </nav>
</header>

<section class="hero">
  <span class="eyebrow">For UAE clinics, salons &amp; agencies · English + العربية</span>
  <h1>The AI receptionist that <em>remembers</em> every customer</h1>
  <p class="sub">
    Most booking bots treat your best client like a stranger. Ours greets her by name,
    knows her usual stylist, and books her favourite slot — 24/7, on the first message,
    in English or Arabic.
  </p>
  <div class="cta">
    <a class="btn btn-primary" href="/widget?business_id=bright-smile">Try the live demo</a>
    <a class="btn btn-ghost" href="/widget?business_id=velvet-hair">See the salon version</a>
  </div>
  <p class="demo-note">No signup — you'll be chatting with a real demo clinic in seconds.</p>

  <div class="chatline">
    <p class="msg"><b>Customer:</b> hi, it's Mariam — can I come in on Thursday?</p>
    <p class="msg"><b>ReceptionAI:</b> Mariam! welcome back 🌸 the usual blow-dry with Rana?
      She has 4:30 or 6:00 free on Thursday — your regular 6:00?</p>
    <p class="msg" style="color:var(--muted);font-size:13px">
      ↑ recognized her, remembered her stylist and usual time — booked in one message.</p>
  </div>
</section>

<section class="grid">
  <div class="card"><span class="ico">🧠</span><h3>Remembers every caller</h3>
    <p>Preferences, past visits, usual services — saved automatically and recalled the moment
    a returning customer says their name. Memory is isolated per business, always.</p></div>
  <div class="card"><span class="ico">📅</span><h3>Real bookings, no double-slots</h3>
    <p>Live availability from your own working hours. Booking, rescheduling and cancelling —
    with a database guarantee that one slot is never sold twice.</p></div>
  <div class="card"><span class="ico">🇦🇪</span><h3>Bilingual by nature</h3>
    <p>Answers in the customer's language — English or Arabic — and switches when they switch.
    Built around how UAE customers actually book: mobile number + reason, captured politely.</p></div>
  <div class="card"><span class="ico">✨</span><h3>Sounds like your front desk</h3>
    <p>Each business gets its own persona — name, tone, services, FAQs. Warm and human,
    never scripted. Care first, logistics second.</p></div>
  <div class="card"><span class="ico">📥</span><h3>Never loses a lead</h3>
    <p>Real-estate and service businesses: every enquiry becomes a captured lead with name,
    number and interest — waiting in your dashboard, not lost in a chat log.</p></div>
  <div class="card"><span class="ico">🔒</span><h3>Private by default</h3>
    <p>Every business's data lives behind its own key. Your customers, your bookings,
    your memory — never shared, never mixed.</p></div>
</section>

<section class="steps">
  <h2>Live in an afternoon</h2>
  <div class="step"><div class="n">1</div><p><strong>Tell us about your business</strong> — name,
    hours, services, tone, FAQs. That's the whole onboarding form.</p></div>
  <div class="step"><div class="n">2</div><p><strong>Put the chat on your site or WhatsApp link</strong> —
    one line of embed code, or share the chat link directly.</p></div>
  <div class="step"><div class="n">3</div><p><strong>Watch the dashboard fill up</strong> — bookings and
    leads appear in real time, while the AI handles the conversations.</p></div>
</section>

<section class="verts">
  <h2>Built for</h2>
  <div class="pills">
    <span class="pill">🦷 Clinics</span>
    <span class="pill">💇‍♀️ Salons &amp; spas</span>
    <span class="pill">🏙️ Real estate</span>
    <span class="pill">🔧 Home services</span>
    <span class="pill">🏢 Any small business</span>
  </div>
</section>

<footer>
  ReceptionAI · Made for the UAE 🇦🇪 ·
  <a href="/widget?business_id=bright-smile">demo</a> ·
  <a href="/dashboard">dashboard</a>
</footer>

</div>
</body>
</html>"""
