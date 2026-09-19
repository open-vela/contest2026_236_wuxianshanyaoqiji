"""Verify a newly packed Allwinner NAND image against its build inputs.

Usage: python3 verify_official_image.py <lichee output image directory> <image.img>
This checks file integrity, not successful boot or physical display behavior.
"""

import hashlib
import json
import pathlib
import re
import struct
import sys


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify_qiji_romfs(packed, board):
    generated = (board / 'etctmp.c').read_text()
    array = generated.split('{', 1)[1].split('}', 1)[0]
    romfs = bytes(int(n, 16) for n in re.findall(r'0x([0-9a-fA-F]{2})', array))
    if not romfs.startswith(b'-rom1fs-') or romfs not in packed:
        raise ValueError('Final RTOS image does not contain the generated ROMFS')
    checked = {}
    for name in ('criteria.txt', 'settings.pfw', 'graph.conf'):
        expected = (board / 'etc/media' / name).read_bytes()
        staged = (board / 'etctmp/etc/media' / name).read_bytes()
        if not expected or expected != staged or expected not in romfs:
            raise ValueError('Stale media ROMFS payload: ' + name)
        checked[name] = sha256(expected)
    startup = (board / 'etctmp/etc/init.d/rcS').read_bytes()
    if startup not in romfs or b'qiji_config wifi_reconnect &' not in startup or b'ntpcstart' in startup:
        raise ValueError('Stale Wi-Fi / NTP startup ROMFS payload')
    checked['rcS'] = sha256(startup)
    return {'sha256': sha256(romfs), 'bytes': len(romfs), 'files': checked}


def main():
    source = pathlib.Path(sys.argv[1])
    image = pathlib.Path(sys.argv[2])
    packed = image.read_bytes()
    if not packed.startswith(b"IMAGEWTY"):
        raise ValueError("Not an Allwinner IMAGEWTY container")
    report = {"image": str(image), "bytes": len(packed),
              "sha256": sha256(packed), "components": {}}
    for name in ("boot0_nand.fex", "fes1.fex", "boot_package.fex",
                 "nsh.fex", "res.fex", "usrdata.fex"):
        data = (source / name).read_bytes()
        if not data or data.startswith(b"version https://git-lfs"):
            raise ValueError(f"Missing binary content: {name}")
        offset = packed.find(data)
        if offset < 0:
            raise ValueError(f"Packed image does not contain exact input: {name}")
        entry = {"bytes": len(data), "sha256": sha256(data), "offset": offset}
        if name in ("boot0_nand.fex", "fes1.fex"):
            if data[4:12] != b"eGON.BT0":
                raise ValueError(f"Bad eGON header: {name}")
            checksum, length = struct.unpack_from("<II", data, 12)
            if length > len(data) or length < 32 or length % 4:
                raise ValueError(f"Invalid eGON length: {name}")
            words = struct.unpack(f"<{length // 4}I", data[:length])
            computed = (sum(words) - checksum + 0x5F0A6C39) & 0xFFFFFFFF
            if checksum != computed:
                raise ValueError(f"Bad eGON checksum: {name}")
            entry["egon_checksum_valid"] = True
        if name == "nsh.fex":
            if data[4:8] != b"rtos" or len(data) > 32768 * 512:
                raise ValueError("Invalid RTOS header or bootloader partition overflow")
        report["components"][name] = entry
    if len(sys.argv) == 4:
        report['qiji_romfs'] = verify_qiji_romfs((source / 'nsh.fex').read_bytes(), pathlib.Path(sys.argv[3]))
    report["hardware_verified"] = False
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
