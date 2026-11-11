#!/usr/bin/env python3
"""Build the web version of a video: the live HTML/CSS animation with its narration, no MP4.

    python3 tools/build_web.py videos/<video>      # -> dist/<video>/ (index.html + 4 files)

dist/<video>/ is a self-contained folder: index.html, player.css, player.js, timeline.json and
narration.mp3. It plays in any browser (served over http) and is what gets published as an artifact.
index.html is written without <html>/<head>/<body>, because the artifact host adds them.
"""
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=Inter:wght@400;500;600;700&family=Poppins:wght@500;600;700&display=swap">')


def build(vdir):
    src = (vdir / "video.html").read_text(encoding="utf-8")
    head = re.search(r"<head>(.*?)</head>", src, re.S).group(1)
    body = re.search(r"<body>(.*?)</body>", src, re.S).group(1)
    title = re.search(r"<title>.*?</title>", head, re.S).group(0)
    styles = "\n".join(re.findall(r"<style>.*?</style>", head, re.S))
    body = body.replace("../_engine/", "")
    page = f"{title}\n{FONTS}\n<link rel=\"stylesheet\" href=\"player.css\">\n{styles}\n{body.strip()}\n"
    out = ROOT / "dist" / vdir.name
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    for f in [ROOT / "videos/_engine/player.css", ROOT / "videos/_engine/player.js",
              vdir / "timeline.json", vdir / "narration.mp3"]:
        shutil.copy2(f, out / f.name)
    print(out)


if __name__ == "__main__":
    build(pathlib.Path(sys.argv[1]).resolve())
