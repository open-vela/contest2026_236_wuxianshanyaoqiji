"""Normalize an existing RGBA sprite and write LVGL 9 RGB565A8 .bin (no image generation)."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from PIL import Image

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('input',type=Path)
parser.add_argument('output',type=Path,help='output stem, without suffix')
args=parser.parse_args()
src=Image.open(args.input).convert('RGBA')
# Provider alpha may contain near-invisible specks far from the character.
# Ignore those only when measuring bounds; preserve the original edge alpha.
bounds=src.getchannel('A').point(lambda a: 255 if a >= 32 else 0).getbbox()
if not bounds:raise ValueError('Empty alpha')
src=src.crop(bounds)
src.thumbnail((160,256),Image.Resampling.LANCZOS)
canvas=Image.new('RGBA',(176,272),(0,0,0,0))
canvas.alpha_composite(src,((176-src.width)//2,264-src.height))
args.output.parent.mkdir(parents=True,exist_ok=True)
png=args.output.with_suffix('.png')
binary=args.output.with_suffix('.bin')
canvas.save(png)
colors=bytearray();alpha=bytearray()
for r,g,b,a in canvas.getdata():
    value=((r>>3)<<11)|((g>>2)<<5)|(b>>3)
    colors.extend(struct.pack('<H',value));alpha.append(a)
# Actual LVGL 9 lv_image_header_t: magic, cf, flags, width, height, stride, reserved.
header=struct.pack('<BBHHHHH',0x19,0x14,0,176,272,352,0)
binary.write_bytes(header+colors+alpha)
assert binary.stat().st_size==12+176*272*3
print(json.dumps({'file':str(binary),'bytes':binary.stat().st_size,
    'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'generation':False}))
