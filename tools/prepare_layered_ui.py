"""Cumulative layered-avatar install. Keep all eight original special sprites."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
project = Path(__file__).resolve().parents[1]
source = project / 'assets/kotone-layered-v1'
manifest = json.loads((source / 'manifest.json').read_text())
if len(manifest['layers']) != 16:
    raise RuntimeError('Expected all 16 layer assets')
for entry in manifest['layers']:
    data = (source / 'bin' / (entry['name'] + '.bin')).read_bytes()
    if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise RuntimeError('Layer integrity failed: ' + entry['name'])
subprocess.run([sys.executable, str(project/'tools/prepare_sprite_ui.py'), str(root)], check=True)
dest = root / 'vendor/allwinnertech/lichee/board/common/data/res/qiji/kotone/layers'
dest.mkdir(parents=True, exist_ok=True)
for entry in manifest['layers']:
    name = entry['name'] + '.bin'
    shutil.copy2(source / 'bin' / name, dest / name)
print('Installed 16 verified layer assets, preserved all 8 special sprites')
