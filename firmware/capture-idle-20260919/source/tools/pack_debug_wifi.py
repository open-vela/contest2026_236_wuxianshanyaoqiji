"""Pack a local debug image with the requested Wi-Fi; restore sources afterward.

Usage (WSL): python3 pack_debug_wifi.py OFFICIAL_ROOT DELIVERY --ssid 2F
Password is prompted, or read from stdin with --password-stdin. No cloud keys.
Run after exporting the generic release. Uses the official pack command.
"""
import argparse
import getpass
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('root', type=Path)
parser.add_argument('delivery', type=Path)
parser.add_argument('--ssid', default='2F')
parser.add_argument('--password-stdin', action='store_true')
args = parser.parse_args()
password = sys.stdin.readline().rstrip('\r\n') if args.password_stdin else getpass.getpass('Wi-Fi password: ')
if not 1 <= len(args.ssid.encode()) <= 32 or not 8 <= len(password) <= 63:
    raise ValueError('Invalid SSID or WPA2 password length')
root = args.root.resolve()
delivery = args.delivery.resolve()
delivery.mkdir(parents=True, exist_ok=True)
dest = delivery / 'qiji-chat-capture-idle-2f-debug.img'
if dest.exists():
    raise FileExistsError('Debug release already exists')
lichee = root / 'vendor/allwinnertech/lichee'
paths = [lichee / 'board/common/data' / name / 'etc/wifi/wapi.conf' for name in ('UDISK', 'res')]
original = {p: p.read_bytes() for p in paths}
config = json.dumps({'wlan0': {'mode': 2, 'auth': 4, 'cmode': 8, 'alg': 3,
    'ssid': args.ssid, 'bssid': '', 'psk': password}}, indent=2).encode() + b'\n'
log = delivery / 'qiji-chat-capture-idle-2f-debug.pack.log'
try:
    for p in paths:
        p.write_bytes(config)
    with log.open('wb') as out:
        result = subprocess.run(['bash', '-lc', 'source build/envsetup.sh && cd vendor/allwinnertech/lichee && source envsetup.sh && lunch_nuttx r528s3-gemini-s1 && pack'], cwd=root, stdout=out, stderr=subprocess.STDOUT)
    output = log.read_text(errors='replace')
    if 'Dragon execute image.cfg SUCCESS' not in output or 'pack finish' not in output:
        raise RuntimeError('Official pack failed; inspect log')
    outdir = lichee / 'out/r528s3/gemini-s1_nand'
    image = outdir / 'rtos_nuttx_r528s3-gemini-s1_uart0_128Mnand.img'
    check = subprocess.check_output([sys.executable, str(Path(__file__).with_name('verify_official_image.py')),
        str(outdir / 'image'), str(image), str(root / 'vendor/allwinnertech/boards/r528/r528s3-gemini-s1/src')])
    for name in ('usrdata.fex', 'res.fex'):
        if config not in (outdir / 'image' / name).read_bytes():
            raise RuntimeError('Debug Wi-Fi missing from ' + name)
    shutil.copy2(image, dest)
    manifest = json.loads(check)
    manifest.update(image=dest.name, wifi_ssid=args.ssid, wifi_password_embedded=True,
        cloud_keys_embedded=False, local_debug_only=True)
    dest.with_suffix('.json').write_text(json.dumps(manifest, indent=2) + '\n')
    dest.with_suffix('.img.sha256').write_text(hashlib.sha256(dest.read_bytes()).hexdigest() + '  ' + dest.name + '\n')
    print('PASS: local debug image created; default Wi-Fi verified in both data partitions')
finally:
    for p, data in original.items():
        p.write_bytes(data)
