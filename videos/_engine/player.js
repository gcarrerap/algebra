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

  // ---------- live playback: control bar, seeking rules, "watched" ----------
  // Solution videos (videos/<set>-exNN/) are told apart by their id: timeline.json's "video"
  // ending in -exNN. They are always seekable and never record "watched". Lesson videos can't be
  // sought until they have played to the end once; that is remembered in localStorage under
  // WATCHED_KEY as { "<video id>": { "watched": "<ISO date>" } }.
  const WATCHED_KEY = "algebra.videos.v1";
  const isSolution = (id) => /-ex\d+$/.test(id);
  const readWatched = () => { try { return JSON.parse(localStorage.getItem(WATCHED_KEY)) || {}; } catch (e) { return {}; } };
  const markWatched = (id) => {
    try { const w = readWatched(); w[id] = { watched: new Date().toISOString() }; localStorage.setItem(WATCHED_KEY, JSON.stringify(w)); } catch (e) {}
  };
  const fmt = (s) => { s = Math.max(0, Math.floor(s)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };

  let bar;
  function fit() {
    const stage = document.getElementById("stage");
    const box = stage.parentElement.getBoundingClientRect();
    const h = box.height - (bar ? bar.offsetHeight : 0);   // the control bar sits below the stage, never over it
    const k = Math.min(box.width / 1920, h / 1080);
    stage.style.transform = `translate(${(box.width - 1920 * k) / 2}px, ${(h - 1080 * k) / 2}px) scale(${k})`;
  }

  function controls(audio, id, toggle) {
    const solution = isSolution(id);
    let seekable = solution || !!readWatched()[id];
    bar = document.createElement("div");
    bar.className = "controls";
    bar.innerHTML =
      '<button type="button" class="ctl-play" aria-label="Play">▶</button>' +
      '<span class="ctl-time"><span class="ctl-now">0:00</span> / <span class="ctl-dur"></span></span>' +
      '<div class="ctl-track" role="slider" aria-label="Video position" aria-valuemin="0">' +
      '<div class="ctl-fill"></div><div class="ctl-thumb"></div></div>' +
      '<span class="ctl-lock" title="Watch to the end once to skip around">🔒</span>' +
      '<button type="button" class="ctl-fs" aria-label="Full screen" title="Full screen">⛶</button>';
    document.body.appendChild(bar);
    const $ = (c) => bar.querySelector(c);
    const track = $(".ctl-track"), fill = $(".ctl-fill"), thumb = $(".ctl-thumb"), now = $(".ctl-now"), pb = $(".ctl-play");
    $(".ctl-dur").textContent = fmt(TL.duration);
    track.setAttribute("aria-valuemax", Math.round(TL.duration));

    const setSeekable = (v) => {
      seekable = v;
      bar.classList.toggle("locked", !v);
      track.title = v ? "Jump to a moment" : "Watch to the end once to skip around";
      if (v) track.tabIndex = 0; else { track.removeAttribute("tabindex"); track.blur(); }
      track.setAttribute("aria-disabled", String(!v));
    };
    setSeekable(seekable);
    window.videoPlayer = { id, solution, get seekable() { return seekable; } };   // for tests

    const jump = (t) => { if (seekable) audio.currentTime = Math.min(Math.max(t, 0), TL.duration); };
    const at = (e) => { const r = track.getBoundingClientRect(); return clamp((e.clientX - r.left) / r.width) * TL.duration; };
    track.addEventListener("pointerdown", (e) => {
      if (!seekable) return;
      e.preventDefault();
      track.setPointerCapture(e.pointerId);
      bar.classList.add("dragging");
      jump(at(e));
    });
    track.addEventListener("pointermove", (e) => { if (bar.classList.contains("dragging")) jump(at(e)); });
    const drop = () => bar.classList.remove("dragging");
    track.addEventListener("pointerup", drop);
    track.addEventListener("pointercancel", drop);

    pb.onclick = toggle;
    const fsEl = document.documentElement;
    const canFs = document.fullscreenEnabled || document.webkitFullscreenEnabled;
    const fsOn = () => document.fullscreenElement || document.webkitFullscreenElement;
    const fs = () => {
      if (fsOn()) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      else (fsEl.requestFullscreen || fsEl.webkitRequestFullscreen).call(fsEl);
    };
    if (canFs) $(".ctl-fs").onclick = fs; else $(".ctl-fs").hidden = true;   // e.g. iPhone Safari has no page full screen
    const onFs = () => { bar.classList.toggle("fs", !!fsOn()); fit(); };
    document.addEventListener("fullscreenchange", onFs);
    document.addEventListener("webkitfullscreenchange", onFs);

    addEventListener("keydown", (e) => {
      if (e.code === "Space") { e.preventDefault(); toggle(); }
      else if (e.code === "KeyF" && canFs) fs();
      else if (e.code === "ArrowRight" || e.code === "ArrowLeft") {
        e.preventDefault();
        jump(audio.currentTime + (e.code === "ArrowRight" ? 5 : -5));
      }
    });
    audio.addEventListener("ended", () => {
      if (solution) return;
      markWatched(id);
      setSeekable(true);
    });
    return (t) => {
      const f = (100 * clamp(t / TL.duration)).toFixed(3) + "%";
      fill.style.width = f;
      thumb.style.left = f;
      now.textContent = fmt(Math.min(t, TL.duration));
      track.setAttribute("aria-valuenow", Math.round(t));
      const playing = !audio.paused;
      pb.textContent = playing ? "❚❚" : "▶";
      pb.setAttribute("aria-label", playing ? "Pause" : "Play");
    };
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
    // the video's id: timeline.json's "video", else its folder name
    const id = TL.video || location.pathname.split("/").filter(Boolean).slice(-2, -1)[0] || "video";
    const audio = new Audio("narration.mp3");
    audio.preload = "auto";
    window.videoAudio = audio;   // for tests
    const play = document.getElementById("play");
    const label = play.querySelector(".play-label") || play;
    const toggle = () => {
      if (audio.paused) { audio.play(); play.hidden = true; }
      else { audio.pause(); label.textContent = "❚❚ Paused · tap to continue"; play.hidden = false; }
    };
    play.onclick = toggle;
    document.getElementById("stage").addEventListener("click", (e) => {
      if (!e.target.closest("#play")) toggle();
    });
    const draw = controls(audio, id, toggle);
    fit(); addEventListener("resize", fit);
    audio.addEventListener("ended", () => { label.textContent = "↻ Watch again"; play.hidden = false; });
    // ?autoplay=1 (used when a page embeds the video): start right away; if the browser refuses
    // sound without a tap, the big play button stays.
    if (location.search.includes("autoplay")) audio.play().then(() => { play.hidden = true; }).catch(() => {});
    window.videoReady = true;
    (function loop() { render(audio.currentTime); draw(audio.currentTime); requestAnimationFrame(loop); })();
  }

  addEventListener("DOMContentLoaded", start);
})();
