#!/usr/bin/env python3
"""Cricvana: BCCI match highlights -> best moments -> 9:16 branded reels.
usage: make_reels.py <query> <max_videos> <reels_per_video>   e.g. 'tags=men,season:2011' 1 2"""
import json, re, subprocess, sys, random, requests
from pathlib import Path
ROOT = Path(__file__).parent; OUT = ROOT / "out"; SRC = ROOT / "src"; OUT.mkdir(exist_ok=True); SRC.mkdir(exist_ok=True)
STATE = ROOT / "state.json"
API = "https://www.bcci.tv/api/bff/cms/videos"
UA = {"User-Agent": "Mozilla/5.0"}
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BG, ACC, SUB = "0x0b1d3a", "0xff7a00", "0xffb066"
LEN = 25
SKIP = ["women", "u19", "under-19", "u-19", "india a", "rising stars", "domestic", "ranji", "vijay hazare", "syed mushtaq", "duleep", "irani"]
CAPS = ["Ye moment baar baar dekhoge 🔁", "Stadium hil gaya tha 🔊", "Pure Team India vibes 🇮🇳", "Isse kehte hain class 🔥",
        "Goosebumps guaranteed 🥶", "Bleed Blue 💙", "Ek dum mast moment 🏏", "Repeat pe chalao 🔁"]

def st(): return json.loads(STATE.read_text()) if STATE.exists() else {"done": [], "reels": []}
def save(s): STATE.write_text(json.dumps(s, indent=1, ensure_ascii=False))
def run(c, t=1800):
    r = subprocess.run(c, capture_output=True, text=True, timeout=t)
    if r.returncode: raise RuntimeError(r.stderr[-800:])
    return r

def listing(query, page=1):
    d = requests.get(f"{API}?category=highlights&{query}&page={page}", headers=UA, timeout=30).json()["data"]
    return d["videos"], d["videosMeta"]["totalPages"]

def titles(t):
    t = t.replace("’", "'")
    parts = [p.strip() for p in t.split("|")]
    if len(parts) >= 3:   # "India vs X | ICC Men's ... 2011 | Final | Match Highlights"
        ev = re.sub(r"ICC Men'?s ", "", parts[1]); stage = parts[2] if "highlight" not in parts[2].lower() else ""
        return (f"{ev} {stage}".strip(), parts[0])
    m = re.match(r"(.+?),\s*(.+?):", t)   # "IND vs WI 2026, 5th T20I: Match Highlights"
    return (m.group(2), m.group(1)) if m else (t[:40], "MATCH HIGHLIGHTS")

def peaks(path, n):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vn", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True, timeout=1500)
    pts = [(float(a), float(b)) for a, b in re.findall(r"t:\s*([\d.]+).*?S:\s*(-?[\d.]+)", r.stderr)]
    total = pts[-1][0] if pts else 0
    pts = [p for p in pts if 60 < p[0] < total - 10]
    pts.sort(key=lambda p: -p[1]); chosen = []
    for t, s in pts:
        if all(abs(t - c) > 45 for c in chosen): chosen.append(t)
        if len(chosen) >= n: break
    return sorted(chosen), total

def esc(t): return t.replace("\\", "\\\\").replace("'", "\u2019").replace(":", "\\:").replace("%", "\\%").replace(",", "\\,")
def lines(t, w, k):
    out, cur = [], ""
    for word in t.split():
        if len(cur) + len(word) + 1 > w and cur: out.append(cur); cur = word
        else: cur = (cur + " " + word).strip()
    out.append(cur); return out[:k]
def block(t, w, k, size, y, color="white", up=False):
    t = re.sub(r"[^\u0000-\u24ff]", "", t).strip()
    ls = lines(t, w, k); f = []
    for i, l in enumerate(ls):
        yy = (y - (len(ls) - i) * (size + 14)) if up else (y + i * (size + 14))
        f.append(f"drawtext=fontfile={FONT}:text='{esc(l)}':fontcolor={color}:fontsize={size}:x=(w-tw)/2:y={yy}:shadowcolor=black@0.6:shadowx=2:shadowy=2")
    return ",".join(f)

def render(src, out, start, top, sub, cap):
    W, H, vw = 1080, 1920, 972
    vf = (f"color=c={BG}:s={W}x{H}:d={LEN}[bg];[0:v]scale={vw}:-2,setsar=1,fade=t=in:d=0.4,fade=t=out:st={LEN-0.6}:d=0.6[v];"
          f"[bg][v]overlay=(W-w)/2:(H-h)/2[b];[b]drawbox=x=0:y=560:w={W}:h=6:color={ACC}:t=fill,drawbox=x=0:y=1354:w={W}:h=6:color={ACC}:t=fill,"
          + block(top.upper(), 20, 2, 66, 470, up=True) + "," + block(sub.upper(), 34, 1, 38, 492, SUB) + ","
          + block(cap, 30, 2, 48, 1430) + f",drawtext=fontfile={FONT}:text='@cricvana':fontcolor={ACC}:fontsize=36:x=(w-tw)/2:y=1800[o]")
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-t", str(LEN), "-i", src, "-filter_complex", vf + ";[0:a]volume=1.0,afade=t=out:st=" + str(LEN-0.6) + ":d=0.6[a]",
         "-map", "[o]", "-map", "[a]", "-t", str(LEN), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out])

def main(query, maxv, per):
    s = st(); made = 0; page = 1
    while made < maxv:
        vids, pages = listing(query, page)
        for v in vids:
            if made >= maxv: break
            if v["slug"] in s["done"] or any(k in v["title"].lower() for k in SKIP) or not v.get("playbackUrl"): continue
            src = str(SRC / f"{v['slug'][:50]}.mp4")
            run(["ffmpeg", "-y", "-v", "error", "-i", v["playbackUrl"], "-c", "copy", src])
            top, sub = titles(v["title"]); old = int(re.search(r"20\d\d", v["title"]).group(0)) < 2025 if re.search(r"20\d\d", v["title"]) else False
            ps, total = peaks(src, per)
            for i, p in enumerate(ps):
                start = max(0, min(p - 17, total - LEN)); cap = ("Throwback 🏆 " if old else "") + random.choice(CAPS)
                out = str(OUT / f"{v['slug'][:40]}_{i+1}.mp4"); render(src, out, start, top, sub, cap)
                meta = {"file": Path(out).name, "title": v["title"], "top": top, "sub": sub, "cap": cap, "start": round(start, 1)}; s["reels"].append(meta)
                with open(OUT / "manifest.jsonl", "a") as mf: mf.write(json.dumps(meta, ensure_ascii=False) + "\n")
                print("REEL", out, top, "|", sub, "|", cap, start)
            s["done"].append(v["slug"]); save(s); Path(src).unlink(missing_ok=True); made += 1
        page += 1
        if page > pages: break

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
