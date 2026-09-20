"""Generate the 16 px / 2 bpp CJK font; no runtime font heap or PSRAM needed."""
import hashlib
import json
import re
import sys
from pathlib import Path
import shutil
import subprocess
import urllib.request
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "app/passport_companion/main"
ASSETS = ROOT / "assets/xiaocheng-font"
ASSETS.mkdir(parents=True, exist_ok=True)
font = ASSETS / "NotoSansSC.ttf"
base = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/"
for path, source in ((font, "NotoSansSC%5Bwght%5D.ttf"), (ASSETS / "OFL.txt", "OFL.txt")):
    if not path.exists():
        urllib.request.urlretrieve(base + source, path)
if hashlib.sha256(font.read_bytes()).hexdigest() != "a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da":
    raise SystemExit("Upstream source font changed; review coverage and license before regenerating")
npx = shutil.which("npx.cmd") or shutil.which("npx")
if not npx:
    raise SystemExit("Node/npm is required for lv_font_conv")
medium = ASSETS / "NotoSansSC-Medium.ttf"
if not medium.exists():
    instantiateVariableFont(TTFont(font), {"wght": 500}, inplace=True).save(medium)
if "--status-only" not in sys.argv:
    subprocess.run([npx, "--yes", "lv_font_conv@1.5.3", "--font", str(medium),
    "--size", "16", "--bpp", "2", "--format", "lvgl", "--lv-include", "lvgl.h", "--no-compress", "--no-kerning",
    "--range", "0x20-0x7e,0x2014,0x2018-0x2019,0x201c-0x201d,0x2026,0x2605,0x3000-0x303f,0x4e00-0x9fff,0xff00-0xffef",
        "--output", str(DEST / "companion_font.c")], check=True)
# Small headers use a fixed subset; dialogue retains the full 16 px CJK font.
header_sources = [DEST / "main.c", DEST / "companion_ui.c",
                  ROOT / "app/gemini_chat_minimal/qiji_version.h"]
header_chars = "".join(sorted(set("".join(re.findall(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]",
    "".join(p.read_text(encoding="utf-8") for p in header_sources))))))
subprocess.run([npx, "--yes", "lv_font_conv@1.5.3", "--font", str(medium),
    "--size", "12", "--bpp", "2", "--format", "lvgl", "--lv-include", "lvgl.h",
    "--no-compress", "--no-kerning", "--range", "0x20-0x7e", "--symbols", header_chars,
    "--output", str(DEST / "companion_status_font.c")], check=True)
(ASSETS / "status-characters.txt").write_text(header_chars + "\n", encoding="utf-8")
selected = set(range(0x20, 0x7f)) | set(range(0x3000, 0x3040)) | set(range(0x4e00, 0xa000)) | set(range(0xff00, 0xfff0)) | {0x2014, 0x2018, 0x2019, 0x201c, 0x201d, 0x2026, 0x2605}
points = sorted(selected & TTFont(font).getBestCmap().keys())
ranges = []
for code in points:
    if ranges and code == ranges[-1][1] + 1:
        ranges[-1][1] = code
    else:
        ranges.append([code, code])
(ASSETS / "coverage.json").write_text(json.dumps({"ranges": ranges, "glyph_count": len(points),
    "font_sha256": hashlib.sha256(font.read_bytes()).hexdigest()}, indent=2) + "\n", encoding="utf-8")
print("Source font SHA256:", hashlib.sha256(font.read_bytes()).hexdigest())
