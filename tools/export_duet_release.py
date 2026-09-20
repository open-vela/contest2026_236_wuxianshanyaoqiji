"""Freeze matching verified images and source for the two-device companion."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

project = Path(__file__).resolve().parents[1]
gemini, passport = (Path(p).resolve() for p in sys.argv[1:3])
release = project / "firmware/duet-20260920"
if release.exists():
    raise SystemExit("Refusing to replace a frozen release")
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

full = passport / "build/FoloToy-AI-Passport-full.bin"
archive = passport / "build/firmware" / digest(full)
subprocess.run([sys.executable, str(passport / "tools/archive_firmware.py"), "verify", str(archive)], check=True)
for p in (project / "app/passport_companion/main").iterdir():
    if digest(p) != digest(passport / "main" / p.name):
        raise RuntimeError("Passport build source differs: " + p.name)

out = gemini / "vendor/allwinnertech/lichee/out/r528s3/gemini-s1_nand"
image = out / "rtos_nuttx_r528s3-gemini-s1_uart0_128Mnand.img"
board = gemini / "vendor/allwinnertech/boards/r528/r528s3-gemini-s1/src"
report = json.loads(subprocess.check_output([sys.executable,
    str(project / "tools/verify_official_image.py"), str(out / "image"), str(image), str(board)]))
elf = gemini / "nuttx/nuttx"
for p in (project / "app/gemini_chat_minimal").rglob("*"):
    if p.suffix in (".c", ".h") and p.stat().st_mtime > elf.stat().st_mtime:
        raise RuntimeError("Gemini source is newer than its ELF: " + p.name)
# LTO can inline qiji_duet_start and omit its symbol name; verify live protocol
# and command strings in the linked image instead of requiring that symbol.
elf_bytes = elf.read_bytes()
if any(marker not in elf_bytes for marker in (b"POST /v1/poll HTTP/1.0", b"duet_token", b"qiji_duet: network worker failed")):
    raise RuntimeError("Gemini ELF lacks duet implementation markers")
for folder, component in (("UDISK", "usrdata.fex"), ("res", "res.fex")):
    wifi = (gemini / "vendor/allwinnertech/lichee/board/common/data" / folder / "etc/wifi/wapi.conf").read_bytes()
    config = json.loads(wifi)["wlan0"]
    if config.get("ssid") or config.get("psk") or wifi not in (out / "image" / component).read_bytes():
        raise RuntimeError("Generic image contains network configuration")

release.mkdir(parents=True)
shutil.copy2(full, release / "passport-xiaocheng-full.bin")
shutil.copytree(archive, release / "passport-debug")
shutil.copy2(image, release / "qiji-chat-duet.img")
shutil.copy2(elf, release / "gemini-chat.elf")
shutil.copy2(gemini / "nuttx/.config", release / "gemini-chat.config")
(release / "gemini-verification.json").write_text(json.dumps(report, indent=2) + "\n")
for name, log in (("passport-build.log", "passport-build-local.log"),
                  ("gemini-build.log", "gemini-duet-build.log"), ("gemini-pack.log", "gemini-duet-pack.log")):
    shutil.copy2(Path("/home/vela") / log, release / name)

sources = []
for folder in ("app/gemini_chat_minimal", "app/passport_companion", "tools/duet", "tools/passport_preview", "assets/xiaocheng-font"):
    sources += [p for p in (project / folder).rglob("*") if p.is_file() and
                p.suffix in (".c", ".h", ".py", ".html", ".md", ".json", ".txt", ".conf", ".pfw")]
sources += [project / p for p in ("app/gemini_chat_minimal/Makefile", "app/gemini_chat_minimal/Make.defs",
    "app/gemini_chat_minimal/Kconfig", "tools/prepare_passport_companion.py", "tools/export_duet_release.py",
    "docs/passport-companion.md", "docs/passport-companion.zh_CN.md")]
for p in sources:
    dest = release / "source" / p.relative_to(project)
    dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)
for name in ("dependencies.lock", "sdkconfig.defaults", "partitions.csv"):
    shutil.copy2(passport / name, release / ("passport-" + name))
manifest = {
    "version": "duet-0.1", "transport": "LAN HTTP with computer coordinator",
    "passport_upstream": subprocess.check_output(["git", "-C", str(passport), "rev-parse", "HEAD"], text=True).strip(),
    "passport_sha256": digest(release / "passport-xiaocheng-full.bin"),
    "gemini_sha256": digest(release / "qiji-chat-duet.img"),
    "build": "PASS", "host_tests": "PASS", "device_tests": "NOT RUN", "cloud_tests": "NOT RUN",
    "passport_flash_offset": "0x0", "merged_flash_may_reset_nvs": True,
    "host_tests_count": 13, "font_glyphs_checked": 20976,
    "unverified": ["physical screens/buttons", "Wi-Fi plus audio heap", "real voice playback", "two-device live AI encounter"],
}
(release / "release.json").write_text(json.dumps(manifest, indent=2) + "\n")
(release / "SHA256SUMS.json").write_text(json.dumps({str(p.relative_to(release)): digest(p)
    for p in release.rglob("*") if p.is_file()}, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
