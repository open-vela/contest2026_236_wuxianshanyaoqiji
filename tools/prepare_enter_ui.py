"""Portrait v0.2.0: onboard ENTER, clock/version and Qiji-chan persona."""
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
project = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, str(project/'tools/prepare_portrait.py'), str(root)], check=True)
p = root/'vendor/allwinnertech/chips/r528/drv/lradc/drv_lradc.c'
s = p.read_text()
old = 'syslog(LOG_INFO,"r528_bl_buttons:retval:%lu\\n",retval);'
new = 'iinfo("r528_bl_buttons:retval:%lu\\n",retval);'
if old in s:
    s = s.replace(old, new)
    p.write_text(s)
elif new not in s:
    raise RuntimeError('Official button driver changed; inspect its sample logging')
print('Prepared ENTER input; per-sample LRADC logs use debug level')
