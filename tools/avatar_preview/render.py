"""Render PNG and animated PNG from the firmware's native LVGL preview.

Usage: python3 render.py /path/to/avatar_preview /path/to/output-directory
"""
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zlib


def chunk(name, data):
    return (struct.pack(">I", len(data)) + name + data +
            struct.pack(">I", zlib.crc32(name + data) & 0xffffffff))


target = Path(sys.argv[2])
target.mkdir(parents=True, exist_ok=True)
frames = []
with tempfile.TemporaryDirectory() as work:
    ppm = Path(work) / "frame.ppm"
    for tick in range(0, 5000, 100):
        subprocess.run([sys.argv[1], str(ppm), str(tick)], check=True)
        magic, dimensions, maximum, pixels = ppm.read_bytes().split(b"\n", 3)
        width, height = map(int, dimensions.split())
        assert magic == b"P6" and maximum == b"255"
        assert len(pixels) == width * height * 3
        raw = b"".join(b"\0" + pixels[y*width*3:(y+1)*width*3] for y in range(height))
        frames.append(zlib.compress(raw))
assert frames[0] != frames[46], "Blink/breathing must visibly change the rendered frame"
header = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
(target / "qiji-avatar-preview.png").write_bytes(header + chunk(b"IDAT", frames[12]) + chunk(b"IEND", b""))
animated = header + chunk(b"acTL", struct.pack(">II", len(frames), 0))
seq = 0
for i, frame in enumerate(frames):
    animated += chunk(b"fcTL", struct.pack(">IIIIIHHBB", seq, width, height, 0, 0, 1, 10, 0, 0))
    seq += 1
    if i == 0:
        animated += chunk(b"IDAT", frame)
    else:
        animated += chunk(b"fdAT", struct.pack(">I", seq) + frame)
        seq += 1
animated += chunk(b"IEND", b"")
(target / "qiji-avatar-animated.png").write_bytes(animated)
print("50 frames rendered; blink/breathing frame-change check passed")
