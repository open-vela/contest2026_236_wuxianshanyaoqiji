"""Configure an already flashed Xiaocheng via USB; secrets are read interactively."""
import argparse
import getpass
import json
import time
import urllib.parse


def main():
    import serial
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--host", required=True, help="http://LAN_IP:8765 (the computer's address)")
    a = p.parse_args()
    url = urllib.parse.urlsplit(a.host)
    if url.scheme != "http" or not url.hostname or url.path not in ("", "/"):
        p.error("Use a LAN HTTP origin, for example http://192.168.1.20:8765")
    data = {"ssid": input("Wi-Fi SSID: "), "password": getpass.getpass("Wi-Fi password: "),
            "host": a.host.rstrip("/"), "token": getpass.getpass("Duet pairing token: ")}
    port = serial.Serial(port=None, baudrate=115200, timeout=.5)
    port.dtr = False; port.rts = False; port.port = a.port
    with port:
        port.write((json.dumps(data, ensure_ascii=False) + "\n").encode())
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            line = port.readline()
            if b"DUET_CONFIG_OK" in line:
                print("Configuration saved; device is restarting."); return
            if b"DUET_CONFIG_INVALID" in line:
                raise SystemExit("Device rejected configuration")
    raise SystemExit("No acknowledgement. Verify Xiaocheng firmware is installed.")


if __name__ == "__main__": main()
