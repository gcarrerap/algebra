// Algebra video player. Draws the video at any time t (seconds) from timeline.json, so the same
// page can play live with its narration or be filmed frame by frame (tools/render_video.py).
//
// Markup in video.html:
//   <section class="scene" data-scene="s01"> … </section>     visible while its scene plays
//   data-at="REF"   element appears at REF;  data-out="REF"  it goes away at REF
//   REF = b03 | b03.end | b03@five | b03@five#2 (2nd "five") | any of these ±seconds (b03.end+0.5)
// Each animated element gets --p (eased 0→1 in, 1→0 out) and --q (linear 0→1 from at to out);
// the CSS classes in player.css (fade, pop, hl, strike, timer…) turn them into motion.
(function () {
  const FADE = 0.45;          // seconds for an element to fade in/out
  const SCENE_FADE = 0.5;     // seconds for a scene crossfade
  const SCENE_LEAD = 0.9;     // a scene starts fading in this long before its first word
  const clamp = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
  const ease = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
  const clean = (w) => w.toLowerCase().replace(/[^a-z0-9'-]/g, "").replace(/^[-']+|[-']+$/g, "");

  let TL, blocks = {}, items = [], scenes = [], caption, progress;
  const errors = [];

  function resolve(ref) {
    const m = ref.trim().match(/^(b\d+)(?:\.(end)|@([a-z0-9'-]+)(?:#(\d+))?)?\s*([+-]\s*[\d.]+)?$/i);
    if (!m) { errors.push(`bad ref "${ref}"`); return 0; }
    const b = blocks[m[1]];
    if (!b) { errors.push(`unknown block in "${ref}"`); return 0; }
    let t = b.t0;
    if (m[2]) t = b.t1;
    else if (m[3]) {
      const n = +(m[4] || 1);
      const hits = b.words.filter((w) => clean(w.w) === m[3].toLowerCase());
      if (hits.length < n) errors.push(`no word "${m[3]}"#${n} in ${m[1]}`);
      else t = hits[n - 1].t0;
    }
    if (m[5]) t += parseFloat(m[5].replace(/\s/g, ""));
    return t;
  }

  function build(timeline) {
    TL = timeline;
    TL.blocks.forEach((b) => (blocks[b.id] = b));
    const byId = Object.fromEntries(TL.scenes.map((s) => [s.id, s]));
    const els = [...document.querySelectorAll(".scene")];
    els.forEach((el, i) => {
      const s = byId[el.dataset.scene];
      if (!s) { errors.push(`scene ${el.dataset.scene} not in timeline`); return; }
      const next = els[i + 1] && byId[els[i + 1].dataset.scene];
      scenes.push({ el, t0: i === 0 ? -1 : s.t0 - SCENE_LEAD, t1: next ? next.t0 - SCENE_LEAD : Infinity });
    });
    document.querySelectorAll("[data-at]").forEach((el) => {
      const sc = scenes.find((s) => s.el.contains(el));
      const at = resolve(el.dataset.at);
      const out = el.dataset.out ? resolve(el.dataset.out) : Infinity;
      items.push({ el, at, out, span: isFinite(out) ? Math.max(out - at, 0.01) : FADE, dur: +(el.dataset.dur || FADE) });
    });
    caption = document.querySelector(".caption");
    progress = document.querySelector(".progress");
  }

  function render(t) {
    for (const s of scenes) {
      const p = ease((t - s.t0) / SCENE_FADE) * (1 - ease((t - s.t1) / SCENE_FADE));
      s.el.style.setProperty("--p", p.toFixed(4));
      s.el.style.visibility = p > 0 ? "visible" : "hidden";
    }
    for (const it of items) {
      const p = ease((t - it.at) / it.dur) * (1 - ease((t - it.out) / FADE));
      it.el.style.setProperty("--p", p.toFixed(4));
      it.el.style.setProperty("--q", clamp((t - it.at) / it.span).toFixed(4));
      it.el.toggleAttribute("data-off", p < 0.002);
    }
    if (progress) progress.style.width = (100 * clamp(t / TL.duration)).toFixed(3) + "%";
    if (caption) {
      const b = TL.blocks.find((x) => t >= x.t0 - 0.15 && t <= x.t1 + 0.5);
      caption.innerHTML = b
        ? b.words.map((w) => `<span class="w${t >= w.t1 ? " said" : t >= w.t0 ? " now" : ""}">${w.w}</span>`).join(" ")
        : "";
    }
  }

  function fit() {
    const stage = document.getElementById("stage");
    const box = stage.parentElement.getBoundingClientRect();
    const k = Math.min(box.width / 1920, box.height / 1080);
    stage.style.transform = `translate(${(box.width - 1920 * k) / 2}px, ${(box.height - 1080 * k) / 2}px) scale(${k})`;
  }

  async function start() {
    const rendering = location.search.includes("render");
    document.body.classList.toggle("render", rendering);
    build(await (await fetch("timeline.json")).json());
    window.videoErrors = errors;
    window.videoDuration = TL.duration;
    window.render = render;
    if (errors.length) console.error("video errors:\n" + errors.join("\n"));
    render(0);
    if (rendering) { window.videoReady = true; return; }
    fit(); addEventListener("resize", fit);
    const audio = new Audio("narration.mp3");
    audio.preload = "auto";
    const play = document.getElementById("play");
    const label = play.querySelector(".play-label") || play;
    const seek = document.getElementById("seek");
    const toggle = () => {
      if (audio.paused) { audio.play(); play.hidden = true; }
      else { audio.pause(); label.textContent = "❚❚ Paused · tap to continue"; play.hidden = false; }
    };
    play.onclick = toggle;
    document.getElementById("stage").addEventListener("click", (e) => {
      if (!e.target.closest("#play, #seek")) toggle();
    });
    if (seek) seek.addEventListener("click", (e) => {
      const r = seek.getBoundingClientRect();
      audio.currentTime = clamp((e.clientX - r.left) / r.width) * TL.duration;
    });
    addEventListener("keydown", (e) => {
      if (e.code === "Space") { e.preventDefault(); toggle(); }
      if (e.code === "ArrowRight") audio.currentTime = Math.min(TL.duration, audio.currentTime + 5);
      if (e.code === "ArrowLeft") audio.currentTime = Math.max(0, audio.currentTime - 5);
    });
    audio.onended = () => { label.textContent = "↻ Watch again"; play.hidden = false; };
    (function loop() { render(audio.currentTime); requestAnimationFrame(loop); })();
  }

  addEventListener("DOMContentLoaded", start);
})();
