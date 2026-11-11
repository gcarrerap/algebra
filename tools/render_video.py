#!/usr/bin/env python3
"""Film a video page (videos/<video>/video.html) into an MP4 with its narration.

    python3 tools/render_video.py videos/<video> --stills 12.5 33 80   # JPEG stills to check a few moments
    python3 tools/render_video.py videos/<video>                       # full render -> videos/<video>/video.mp4

The page draws any instant t through window.render(t) (videos/_engine/player.js), so every frame
is exact and nothing depends on real time. The video is cut into chunks at scene changes, each
chunk is filmed by its own browser and encoded to its own MP4 (same size, rate and encoder),
then the chunks are joined with -c copy and the narration is added.
"""
import argparse
import functools
import http.server
import math
import multiprocessing as mp
import os
import pathlib
import socketserver
import subprocess
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
W, H, FPS = 1920, 1080, 30
X264 = ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p"]


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(ROOT / "videos"))
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def open_page(pw, port, video):
    browser = pw.chromium.launch(args=["--disable-gpu", "--font-render-hinting=none"])
    page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    page.goto(f"http://127.0.0.1:{port}/{video}/video.html?render=1")
    page.wait_for_function("window.videoReady === true", timeout=30000)
    page.evaluate("document.fonts.ready")
    errs = page.evaluate("window.videoErrors")
    if errs:
        sys.exit("video.html errors:\n  " + "\n  ".join(errs))
    return browser, page


def shot(page, t):
    page.evaluate(f"window.render({t:.4f})")
    return page.screenshot(type="jpeg", quality=92)


def chunk(args):
    port, video, f0, f1, out = args
    from playwright.sync_api import sync_playwright
    tmp = out.with_name(out.stem + ".part.mp4")
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS),
                            "-c:v", "mjpeg", "-i", "-", *X264, "-r", str(FPS), str(tmp)], stdin=subprocess.PIPE)
    with sync_playwright() as pw:
        browser, page = open_page(pw, port, video)
        for f in range(f0, f1):
            enc.stdin.write(shot(page, f / FPS))
        browser.close()
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {out.name}")
    tmp.replace(out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video_dir", type=pathlib.Path)
    ap.add_argument("--stills", type=float, nargs="+", metavar="T", help="only save JPEG stills at these times")
    ap.add_argument("--out", type=pathlib.Path, help="where stills go (default: the video folder)")
    ap.add_argument("--jobs", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 1)))
    a = ap.parse_args()
    vdir = a.video_dir.resolve()
    video = vdir.name
    import json
    tl = json.loads((vdir / "timeline.json").read_text())
    srv, port = serve()
    from playwright.sync_api import sync_playwright

    if a.stills:
        out = (a.out or vdir).resolve()
        out.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser, page = open_page(pw, port, video)
            for t in a.stills:
                p = out / f"still-{t:07.2f}.jpg"
                p.write_bytes(shot(page, t))
                print(p)
            browser.close()
        return

    total = math.ceil(tl["duration"] * FPS)
    # chunk boundaries: just before each scene's crossfade, then split long chunks so all workers stay busy
    cuts = sorted({0, total} | {max(0, round((s["t0"] - 1.0) * FPS)) for s in tl["scenes"][1:]})
    target = math.ceil(total / a.jobs)
    spans = []
    for f0, f1 in zip(cuts, cuts[1:]):
        n = max(1, round((f1 - f0) / target))
        edges = [f0 + (f1 - f0) * k // n for k in range(n + 1)]
        spans += list(zip(edges, edges[1:]))
    work = vdir / ".render"
    work.mkdir(exist_ok=True)
    jobs = [(port, video, f0, f1, work / f"chunk-{i:03d}.mp4") for i, (f0, f1) in enumerate(spans)]
    print(f"{total} frames in {len(jobs)} chunks, {a.jobs} at a time")
    with mp.get_context("spawn").Pool(a.jobs) as pool:
        for done in pool.imap_unordered(chunk, jobs):
            print("done", done.name, flush=True)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{j[4].name}'\n" for j in jobs))
    silent = work / "silent.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(silent)], check=True)
    tmp = vdir / "video.tmp.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(silent), "-i", str(vdir / "narration.mp3"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(vdir / "video.mp4")
    for f in work.iterdir():
        f.unlink()
    work.rmdir()
    print(vdir / "video.mp4")


if __name__ == "__main__":
    main()
