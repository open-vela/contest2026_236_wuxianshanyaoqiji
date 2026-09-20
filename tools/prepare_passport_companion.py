"""Install the companion application into a dedicated FoloToy baseline checkout."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

BASELINE = "855d2106547988e33128e27aadff4fe98351fe14"
ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("checkout", type=Path)
    args = p.parse_args()
    target = args.checkout.resolve()
    rev = subprocess.check_output(["git", "-C", str(target), "rev-parse", "HEAD"], text=True).strip()
    if rev != BASELINE:
        raise SystemExit("Use the pinned FoloToy baseline " + BASELINE)
    source = ROOT / "app/passport_companion/main"
    if not (source / "companion_font.c").exists():
        raise SystemExit("Run tools/duet/build_font.py first")
    marker = target / ".qiji-companion-installed"
    dirty = subprocess.check_output(["git", "-C", str(target), "status", "--porcelain"], text=True)
    if dirty.strip() and not marker.exists():
        raise SystemExit("Use a clean, dedicated checkout; existing changes are preserved")
    for path in source.iterdir():
        shutil.copy2(path, target / "main" / path.name)
    # Keep baseline files for its existing static tests, but do not compile its test UI.
    defaults = (target / "sdkconfig.defaults").read_text(encoding="utf-8")
    for line in defaults.splitlines():
        if line.startswith("CONFIG_BT_"):
            defaults = defaults.replace(line + "\n", "")
    defaults = defaults.replace("CONFIG_LV_MEM_SIZE_KILOBYTES=24", "CONFIG_LV_MEM_SIZE_KILOBYTES=40")
    if "# Qiji companion" not in defaults:
        defaults += "\n# Qiji companion\nCONFIG_BT_ENABLED=n\nCONFIG_LV_USE_FONT_PLACEHOLDER=y\n"
    if "CONFIG_LV_FONT_FMT_TXT_LARGE=y" not in defaults:
        defaults += "CONFIG_LV_FONT_FMT_TXT_LARGE=y\n"
    (target / "sdkconfig.defaults").write_text(defaults, encoding="utf-8")
    marker.write_text(json.dumps({"baseline": BASELINE, "application": "xiaocheng-0.1"}), encoding="utf-8")
    print("Installed Xiaocheng application; BSP/pins/partitions unchanged")


if __name__ == "__main__": main()
