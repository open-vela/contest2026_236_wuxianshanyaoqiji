"""Prepare the cumulative 240x320 ILI9341 portrait build and matching TPADC."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
project = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, str(project/'tools/prepare_qiji_persona.py'), str(root)], check=True)
config = root/'vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/qiji_chat/defconfig'
s = config.read_text()
for stem in ('LCD', 'LCD_ILI9341_IFACE0'):
    for orientation in ('LANDSCAPE', 'RLANDSCAPE', 'PORTRAIT', 'RPORTRAIT'):
        key = 'CONFIG_' + stem + '_' + orientation
        s = re.sub(r'^(?:' + key + r'=.*|# ' + key + r' is not set)\n', '', s, flags=re.M)
    s += 'CONFIG_' + stem + '_PORTRAIT=y\n'
config.write_text(s)

driver_dir = root/'vendor/allwinnertech/chips/r528/drv/tpadc'
p = driver_dir/'drv_tpadc.c'
s = p.read_text()
if '/* Qiji portrait TPADC mapping */' not in s:
    original = '''    screen_x = (y - driver->x_min) * driver->screen_width / (driver->x_max - driver->x_min);
    screen_y = (x - driver->y_min) * driver->screen_height / (driver->y_max - driver->y_min);
    screen_y = driver->screen_height - screen_y;'''
    dimensions = '''    tpadc_driver->screen_width = 320;
    tpadc_driver->screen_height = 240;'''
    if s.count(original) != 1 or s.count(dimensions) != 1:
        raise RuntimeError('Official TPADC driver changed: review before patching')
    s = s.replace('#include <nuttx/config.h>',
        '#include <nuttx/config.h>\n#include "qiji_portrait_touch.h"')
    s = s.replace(original, '''    /* Qiji portrait TPADC mapping */
#if defined(CONFIG_LCD_ILI9341_IFACE0_PORTRAIT)
    qiji_touch_portrait(x, y, driver->x_min, driver->x_max,
                       driver->y_min, driver->y_max, &screen_x, &screen_y);
#else
''' + original + '\n#endif')
    s = s.replace(dimensions, '''#if defined(CONFIG_LCD_ILI9341_IFACE0_PORTRAIT)
    tpadc_driver->screen_width = 240;
    tpadc_driver->screen_height = 320;
#else
''' + dimensions + '\n#endif')
    p.write_text(s)
shutil.copy2(project/'tools/portrait_touch.h', driver_dir/'qiji_portrait_touch.h')
# The generic image has no network credentials, including upstream examples.
# pack_debug_wifi.py inserts the local network only during its private pack.
data_root = root/'vendor/allwinnertech/lichee/board/common/data'
for directory in ('UDISK', 'res'):
    path = data_root/directory/'etc/wifi/wapi.conf'
    data = json.loads(path.read_text())
    for key in ('ssid', 'psk', 'bssid'):
        data['wlan0'][key] = ''
    path.write_text(json.dumps(data, indent=2) + '\n')
print('Prepared 240x320 hardware portrait with clamped TPADC mapping')
