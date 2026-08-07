"""The reliability pipeline page — a self-contained, interactive node-graph of one
conversation turn: where the model can claim an action without performing it (the
say-do gap) and where the deterministic net guarantees the lead lands anyway.

Served at /pipeline, same pattern as /demo and /watch: HTML-in-module, no build
step, no external assets, no API calls — it plays instantly even on a cold Render."""

PIPELINE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ReceptionAI — Agent Pipeline</title>
<style>
  :root{
    --canvas:#0B0F14; --panel:#0d1219; --grid:#1B2430;
    --text:#E6EDF3; --muted:#7D8590; --val:#9DA7B3;
    --violet:#8B5CF6; --violet2:#C084FC;
    --emerald:#34D399; --amber:#FBBF24; --red:#F87171;
    --cyan:#22D3EE; --cyan-deep:#0E7490;
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --mono:ui-monospace,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--canvas);color:var(--text);font-family:var(--sans);
    line-height:1.55;-webkit-font-smoothing:antialiased;
    background-image:radial-gradient(60% 45% at 84% -8%,#8b5cf61c,transparent 60%),
                     radial-gradient(45% 40% at 4% 6%,#22d3ee12,transparent 60%)}
  .wrap{max-width:960px;margin:0 auto;padding:40px 18px 64px}

  header{margin-bottom:16px}
  .eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.2em;text-transform:uppercase;
    color:var(--violet2);font-weight:600}
  h1{font-size:clamp(21px,4vw,28px);letter-spacing:-.02em;margin:9px 0 7px;font-weight:750}
  header p{color:var(--muted);font-size:14.5px;margin:0;max-width:60ch}
  .mstats{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:14px;font-family:var(--mono);
    font-size:12px;color:var(--muted)}
  .mstats b{font-size:15px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
  .mstats .am{color:var(--amber)} .mstats .cy{color:var(--cyan)}
  .chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}
  .chips span{font-family:var(--mono);font-size:9px;color:#cbbdf7;background:#8b5cf618;
    border:1px solid #8b5cf63a;border-radius:5px;padding:1px 6px}

  .bar{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:16px 0 12px}
  .switch{display:inline-flex;align-items:center;gap:10px;background:#0f151d;border:1px solid #222c3a;
    border-radius:999px;padding:7px 8px 7px 15px;cursor:pointer;-webkit-user-select:none;user-select:none;
    font-size:13.5px;color:var(--muted)}
  .switch .track{width:44px;height:24px;border-radius:999px;background:#22d3ee2b;border:1px solid #22d3ee66;
    position:relative;transition:.25s}
  .switch .knob{position:absolute;top:2px;left:22px;width:18px;height:18px;border-radius:50%;
    background:var(--cyan);box-shadow:0 0 10px #22d3ee88;transition:.25s}
  .switch .state{font-family:var(--mono);font-weight:700;color:var(--cyan);letter-spacing:.04em}
  .net-off .switch .track{background:#f871711f;border-color:#f8717155}
  .net-off .switch .knob{left:2px;background:var(--red);box-shadow:0 0 10px #f8717188}
  .net-off .switch .state{color:var(--red)}
  .hint{font-family:var(--mono);font-size:11.5px;color:var(--muted)}

  .stage{position:relative;border:1px solid #1e2734;border-radius:18px;overflow:hidden;
    background:var(--canvas);box-shadow:0 40px 90px -55px #000, inset 0 1px 0 #ffffff08}
  .scroll{overflow-x:auto}
  .canvas{position:relative;width:900px;height:480px;margin:0 auto;
    background-image:radial-gradient(#243040 1px, transparent 1px);background-size:24px 24px;
    background-position:12px 12px}
  .grain{position:absolute;inset:0;pointer-events:none;opacity:.05;mix-blend-mode:soft-light;z-index:5}

  svg.wires{position:absolute;inset:0;width:900px;height:480px;z-index:1;pointer-events:none}
  .edge{fill:none;stroke-width:1.6;stroke-linecap:round}
  .edge.thick{stroke-width:2.6}
  .lbl{position:absolute;z-index:3;font-family:var(--mono);font-size:10.5px;letter-spacing:.02em;
    color:var(--muted);background:#0b0f14cc;padding:2px 7px;border-radius:6px;border:1px solid #1c2531;white-space:nowrap}
  .lbl.em{color:#7fe6c2;border-color:#1d4a38}
  .lbl.am{color:#f4cf8a;border-color:#4a3b1a}
  .lbl.cy{color:#8be6f2;border-color:#144a55}

  /* particles */
  .p{position:absolute;left:0;top:0;width:9px;height:9px;border-radius:50%;z-index:4;
    offset-rotate:0deg;animation:travel 2.4s linear infinite}
  @keyframes travel{from{offset-distance:0%}to{offset-distance:100%}}
  .p.happy{offset-path:path("M566,214 C632,200 660,208 724,208");background:var(--emerald);box-shadow:0 0 12px #34d399cc}
  .p.claim{offset-path:path("M566,258 C582,300 560,322 560,344");background:var(--amber);box-shadow:0 0 12px #fbbf24cc}
  .p.guar{offset-path:path("M640,392 C704,392 706,300 724,262");background:var(--cyan);box-shadow:0 0 12px #22d3eecc;animation-delay:-1.2s}
  .p.lost{offset-path:path("M640,392 C726,420 812,442 900,452");background:var(--red);box-shadow:0 0 12px #f87171cc;animation-delay:-1.2s;opacity:0}

  /* nodes */
  .node{position:absolute;z-index:2;border-radius:14px;padding:12px 14px}
  .node .hd{display:flex;align-items:center;gap:7px;font-family:var(--mono);font-size:9.5px;
    letter-spacing:.13em;text-transform:uppercase}
  .node .hd .d{width:7px;height:7px;border-radius:50%}
  .node .ttl{font-size:14px;font-weight:650;letter-spacing:-.01em;margin-top:5px}
  .node .sub{font-size:11px;color:var(--val);margin-top:3px;font-family:var(--mono);line-height:1.4}

  /* probabilistic = glass, violet, soft */
  .glass{background:rgba(139,92,246,.06);-webkit-backdrop-filter:blur(13px) saturate(140%);
    backdrop-filter:blur(13px) saturate(140%);
    border:1px solid rgba(196,132,252,.30);box-shadow:0 16px 40px -20px #8b5cf655, inset 0 1px 0 #ffffff12}
  .glass .hd{color:var(--violet2)} .glass .hd .d{background:var(--violet2);box-shadow:0 0 8px #c084fc}
  .glass .ttl{color:#f0ecff}

  /* deterministic = hard, cyan, circuit, grounded */
  .circuit{background:linear-gradient(180deg,#0c161b,#0a1216);border:1px solid #1c4e59;border-radius:5px;
    box-shadow:0 0 0 1px #22d3ee14, 0 10px 24px -16px #000;position:absolute;overflow:hidden}
  .circuit::before{content:"";position:absolute;inset:0;background-image:
    linear-gradient(#22d3ee0e 1px,transparent 1px),linear-gradient(90deg,#22d3ee0e 1px,transparent 1px);
    background-size:12px 12px;opacity:.5}
  .circuit .hd{color:var(--cyan)} .circuit .hd .d{background:var(--cyan);box-shadow:0 0 8px #22d3ee}
  .circuit .ttl{color:#d6f6fb}
  .circuit.lit{border-color:#22d3ee;box-shadow:0 0 0 1px #22d3ee33, 0 0 34px -8px #22d3ee66}

  .node.io{background:#0f151d;border:1px solid #222c3a}
  .node.io .hd{color:var(--muted)} .node.io .hd .d{background:var(--muted)}

  /* counters in DB */
  .count{display:flex;gap:16px;margin-top:8px}
  .count .c{font-family:var(--mono);font-size:11px;color:var(--muted)}
  .count .c b{display:block;font-size:19px;letter-spacing:-.02em;font-variant-numeric:tabular-nums;margin-top:1px}
  .count .saved b{color:var(--cyan)} .count .lost b{color:var(--red)}

  /* state-driven visibility */
  .net-off .circuit.net{opacity:.28;filter:grayscale(.4)}
  .net-off .edge.guar{opacity:.12}
  .net-off .p.guar{opacity:0}
  .net-off .p.lost{opacity:1}
  .net-off .lbl.guar{opacity:.2} .net-off .lbl.lost{opacity:1}
  .lbl.lost{opacity:0;transition:opacity .3s}

  @media (prefers-reduced-motion: reduce){ .p{animation:none;offset-distance:60%} }
  @media(max-width:600px){ .canvas{transform-origin:left top} }

  footer{color:var(--muted);font-family:var(--mono);font-size:11px;margin-top:16px;text-align:center}
</style>
</head>
<body>

<div class="wrap" id="root">

  <header>
    <div class="eyebrow">ReceptionAI · agent pipeline</div>
    <h1>One turn — where the model can slip, and where code guarantees it can't</h1>
    <p>Soft violet nodes are the probabilistic model. Sharp cyan nodes are deterministic code. Watch a single turn flow through — then flip the safety net off.</p>
    <div class="mstats">
      <span>measured on 15 real conversations:</span>
      <span><b class="am">~60%</b> the model skipped the tool</span>
      <span><b class="cy">100%</b> caught by the net</span>
      <span><b class="cy">0</b> leads lost</span>
    </div>
  </header>

  <div class="bar">
    <div class="switch" id="toggle" role="switch" aria-checked="true" tabindex="0">
      <span>Safety net</span>
      <span class="track"><span class="knob"></span></span>
      <span class="state">ON</span>
    </div>
    <span class="hint" id="hint">&#9656; every lead lands — the net catches what the model skips</span>
  </div>

  <div class="stage">
    <div class="scroll">
      <div class="canvas" id="canvas">

        <svg class="wires" viewBox="0 0 900 480" aria-hidden="true">
          <!-- flow edges -->
          <path class="edge" d="M156,238 C176,238 182,238 196,238" stroke="#8b5cf6" stroke-opacity=".45"/>
          <path class="edge" d="M372,238 C396,238 400,238 420,238" stroke="#8b5cf6" stroke-opacity=".45"/>
          <path class="edge" d="M566,214 C632,200 660,208 724,208" stroke="#34d399" stroke-opacity=".55"/>
          <path class="edge" d="M566,258 C582,300 560,322 560,344" stroke="#fbbf24" stroke-opacity=".55" stroke-dasharray="5 6"/>
          <path class="edge guar thick" d="M640,392 C704,392 706,300 724,262" stroke="#22d3ee" stroke-opacity=".7"/>
          <path class="edge" d="M640,392 C726,420 812,442 900,452" stroke="#f87171" stroke-opacity=".35" stroke-dasharray="4 7"/>
        </svg>

        <!-- particles -->
        <div class="p happy"></div>
        <div class="p claim"></div>
        <div class="p guar"></div>
        <div class="p lost"></div>

        <!-- edge labels -->
        <div class="lbl em"  style="left:598px;top:184px">tool fired &#8594; saved</div>
        <div class="lbl am"  style="left:452px;top:292px">claims &#8220;saved!&#8221; &middot; no tool</div>
        <div class="lbl cy guar" style="left:648px;top:322px">net re-fires &#8594; verified</div>
        <div class="lbl lost" style="left:724px;top:436px;color:#f4a3a3;border-color:#4a1f1f">lead lost</div>

        <!-- nodes -->
        <div class="node io" style="left:24px;top:208px;width:132px">
          <div class="hd"><span class="d"></span> Input</div>
          <div class="ttl">Message in</div>
        </div>

        <div class="node glass" style="left:196px;top:196px;width:176px">
          <div class="hd"><span class="d"></span> LLM &middot; probabilistic</div>
          <div class="ttl">Gemini picks a tool</div>
          <div class="sub">tools on &middot; may skip the call</div>
          <div class="chips"><span>capture_lead</span><span>book_appointment</span><span>qualify</span></div>
        </div>

        <div class="node glass" style="left:420px;top:202px;width:146px">
          <div class="hd"><span class="d"></span> Router</div>
          <div class="ttl">Called the tool?</div>
        </div>

        <div class="circuit net" style="left:430px;top:344px;width:210px;padding:12px 14px">
          <div class="hd" style="position:relative"><span class="d"></span> Guarantee &middot; deterministic</div>
          <div class="ttl" style="position:relative">SAFETY_NET</div>
          <div class="sub" style="position:relative;color:#8fd6df">phone but no lead? save it &middot; skips duplicates</div>
        </div>

        <div class="circuit lit" id="dbnode" style="left:726px;top:172px;width:150px;padding:12px 14px">
          <div class="hd" style="position:relative"><span class="d"></span> Store</div>
          <div class="ttl" style="position:relative">leads</div>
          <div class="count" style="position:relative">
            <div class="c saved">saved<b id="saved">128</b></div>
            <div class="c lost">lost<b id="lost">0</b></div>
          </div>
        </div>

      </div>
    </div>
    <svg width="0" height="0"><filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" stitchTiles="stitch"/></filter></svg>
    <div class="grain" style="filter:url(#grain)"></div>
  </div>

  <footer>probabilistic = glass/violet &middot; deterministic = circuit/cyan &middot; amber = the say-do gap &middot; flip the net to feel the difference</footer>

</div>

<script>
(function(){
  var root=document.getElementById('root');
  var toggle=document.getElementById('toggle');
  var hint=document.getElementById('hint');
  var savedEl=document.getElementById('saved');
  var lostEl=document.getElementById('lost');
  var db=document.getElementById('dbnode');
  var saved=128, lost=0, off=false;
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  function paint(){ savedEl.textContent=saved.toLocaleString(); lostEl.textContent=lost; }

  function setOff(v){
    off=v;
    root.classList.toggle('net-off', off);
    toggle.setAttribute('aria-checked', String(!off));
    toggle.querySelector('.state').textContent = off ? 'OFF' : 'ON';
    db.classList.toggle('lit', !off);
    hint.innerHTML = off
      ? '&#9656; net off — the leads the model skips now vanish (watch &#8220;lost&#8221; climb)'
      : '&#9656; every lead lands — the net catches what the model skips';
  }
  toggle.addEventListener('click', function(){ setOff(!off); });
  toggle.addEventListener('keydown', function(e){ if(e.key===' '||e.key==='Enter'){ e.preventDefault(); setOff(!off); }});

  if(!reduce){
    setInterval(function(){
      saved += 1;
      if(off) lost += 1;
      paint();
    }, 2400);
  } else {
    saved=128; lost=0; paint();
  }
  paint();
})();
</script>

</body>
</html>
"""
