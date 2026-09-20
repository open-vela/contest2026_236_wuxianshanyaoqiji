"""Archive the verified Passport overlay UI without replacing the duet release."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

project = Path(__file__).resolve().parents[1]
checkout = Path(sys.argv[1]).resolve()
release = project / "firmware/passport-overlay-20260920"
if release.exists():
    raise SystemExit("Refusing to overwrite a frozen release")
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
image = checkout / "build/FoloToy-AI-Passport-full.bin"
archive = checkout / "build/firmware" / sha(image)
subprocess.run([sys.executable, str(checkout / "tools/archive_firmware.py"),
                "verify", str(archive)], check=True)
for source in (project / "app/passport_companion/main").iterdir():
    if sha(source) != sha(checkout / "main" / source.name):
        raise RuntimeError("Build source differs: " + source.name)
    if source.stat().st_mtime > image.stat().st_mtime:
        raise RuntimeError("Source newer than firmware: " + source.name)
data = image.read_bytes()
if "小澄 / %s".encode() not in data or "上下翻页 确认开始/停止".encode() in data:
    raise RuntimeError("Expected new header and removed footer in firmware")

release.mkdir(parents=True)
shutil.copy2(image, release / "passport-xiaocheng-overlay-full.bin")
shutil.copytree(archive, release / "debug")
shutil.copytree(project / "app/passport_companion/main", release / "source/main")
for name in ("sdkconfig.defaults", "dependencies.lock", "partitions.csv"):
    shutil.copy2(checkout / name, release / name)
for name in ("passport-overlay-build.log", "xiaocheng-overlay-preview.log"):
    shutil.copy2(Path("/home/vela") / name, release / name)
for name in ("xiaocheng-overlay-preview.png", "xiaocheng-overlay-preview.gif"):
    shutil.copy2(project / "docs/assets/duet" / name, release / name)
for name in ("OFL.txt", "coverage.json", "status-characters.txt"):
    shutil.copy2(project / "assets/xiaocheng-font" / name, release / name)
manifest = json.loads((archive / "manifest.json").read_text())
result = {
    "version": "xiaocheng-0.1-overlay", "image": "passport-xiaocheng-overlay-full.bin",
    "sha256": sha(image), "bytes": image.stat().st_size,
    "app_elf_sha256": manifest["app_elf_sha256"],
    "passport_upstream": subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip(),
    "layout": "1.875x character, one 12px header row, translucent dialogue above character, no footer hint",
    "Build": "PASS", "Host tests": "PASS (upstream gate and actual LVGL rendering)",
    "Device tests": "NOT RUN", "Unverified": ["physical display", "on-device heap and animation", "button scrolling"],
    "flash_offset": "0x0", "merged_flash_may_reset_nvs": True,
    "matching_debug_manifest": "debug/manifest.json",
}
(release / "release.json").write_text(json.dumps(result, indent=2) + "\n")
(release / "SHA256SUMS.json").write_text(json.dumps({str(p.relative_to(release)): sha(p)
    for p in release.rglob("*") if p.is_file()}, indent=2) + "\n")
print(json.dumps(result, indent=2))
