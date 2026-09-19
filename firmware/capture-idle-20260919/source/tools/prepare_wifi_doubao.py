"""Apply Wi-Fi startup and monotonic watchdog fixes after prepare_official_chat.py.

Run on the established clean official tree; official audio patch must already
be applied. No Wi-Fi passwords or API keys are embedded here.
"""
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
project = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, str(project / "tools/prepare_official_chat.py"), str(root)], check=True)
rc = root / "vendor/allwinnertech/boards/r528/r528s3-gemini-s1/src/etc/init.d/rcS.nsh"
text = rc.read_text()
old = "  sh /etc/wifi/start_wifi.sh &"
new = """#ifdef CONFIG_GEMINI_CHAT_MINIMAL
  qiji_config wifi_reconnect &
#else
  sh /etc/wifi/start_wifi.sh &
#endif"""
if "qiji_config wifi_reconnect" not in text:
    if text.count(old) != 1:
        raise RuntimeError("Wi-Fi startup block changed")
    rc.write_text(text.replace(old, new))

agent = root / "packages/ai_agent/src/core/agent_loop.c"
text = agent.read_text()
marker = "/* ── Clock-safe elapsed time calculation"
if "static void qiji_monotonic_timeval" not in text:
    at = text.index(marker)
    helper = """/* TLS/NTP may change CLOCK_REALTIME during the first request. */
static void qiji_monotonic_timeval(struct timeval *value, void *unused)
{
    (void)unused;
    struct timespec now = {0};
    clock_gettime(CLOCK_MONOTONIC, &now);
    value->tv_sec = now.tv_sec;
    value->tv_usec = now.tv_nsec / 1000;
}

"""
    text = text[:at] + helper + text[at:]
    text = text.replace("gettimeofday(", "qiji_monotonic_timeval(")
    agent.write_text(text)
print("Prepared Wi-Fi reconnect and monotonic request timing")
