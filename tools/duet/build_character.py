"""Rasterize the original editable SVG to flash-resident LVGL RGB565A8 frames.

Requires Pillow and resvg-py. No image API, external artwork or credentials.
"""
from pathlib import Path
from io import BytesIO
import struct
import xml.etree.ElementTree as ET
import resvg_py
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'assets/xiaocheng-future-v1'
SOURCE = ROOT / 'app/passport_companion/main/companion_character.c'
W, H = 240, 280
FRAMES = [('idle', 'open', 'idle'), ('half_blink', 'half', 'idle'),
          ('blink', 'closed', 'idle'), ('speak_small', 'open', 'small'),
          ('speak_large', 'open', 'large')]


def main():
    declarations = ['/* Original editable artwork: assets/xiaocheng-future-v1/character.svg */',
                    '#include "lvgl.h"']
    for name, eyes, mouth in FRAMES:
        tree = ET.parse(ASSETS / 'character.svg')
        for node in tree.iter():
            ident = node.get('id', '')
            if ident in ('eyes-open', 'eyes-half', 'eyes-closed'):
                visible = ident == 'eyes-' + eyes
                node.set('style', '' if visible else 'display:none')
            elif ident.startswith('mouth-'):
                node.set('style', '' if ident == 'mouth-' + mouth else 'display:none')
        raw = resvg_py.svg_to_bytes(svg_string=ET.tostring(tree.getroot(), encoding='unicode'),
                                   width=W * 3, height=H * 3)
        im = Image.open(BytesIO(raw)).convert('RGBA').resize((W, H), Image.Resampling.LANCZOS)
        im.save(ASSETS / (name + '.png'))
        rgb, alpha = bytearray(), bytearray()
        for r, g, b, a in im.getdata():
            rgb.extend(struct.pack('<H', ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)))
            alpha.append(a)
        data = rgb + alpha
        assert len(data) == W * H * 3
        symbol = 'companion_character_' + name
        declarations.append(f'static const uint8_t {symbol}_data[] = {{')
        declarations.extend('    ' + ','.join(f'0x{v:02x}' for v in data[i:i+24]) + ','
                            for i in range(0, len(data), 24))
        declarations.append('};')
        declarations.append(f'const lv_image_dsc_t {symbol} = {{\n'
            f'    .header = {{.magic = LV_IMAGE_HEADER_MAGIC, .cf = LV_COLOR_FORMAT_RGB565A8, '
            f'.w = {W}, .h = {H}, .stride = {W * 2}}},\n'
            f'    .data_size = sizeof({symbol}_data), .data = {symbol}_data,\n}};')
    SOURCE.write_text('\n'.join(declarations) + '\n', encoding='utf-8')
    print(f'{len(FRAMES)} RGB565A8 frames: {W * H * 3 * len(FRAMES)} flash bytes, {W}x{H}; PNG previews saved')


if __name__ == '__main__':
    main()
