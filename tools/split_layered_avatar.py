"""Reproducible separation of the generated neutral kotone-layered-v1 base.

Requires Pillow, numpy, opencv-python and scipy. Small overlap repairs only:
Masks are authored for this specific neutral illustration, not arbitrary art.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, binary_dilation

ROOT = Path(__file__).resolve().parents[1]
SIZE = (176, 272)
OFFSET = (0, 0)


def polygon(points):
    im = Image.new('L', SIZE)
    ImageDraw.Draw(im).polygon(points, fill=255)
    return np.asarray(im) > 0


def separate(source, destination):
    source_bytes = source.read_bytes()
    original = Image.open(source).convert('RGBA')
    bounds = original.getchannel('A').point(lambda a: 255 if a >= 32 else 0).getbbox()
    if not bounds:
        raise ValueError('Empty source')
    original = original.crop(bounds)
    original.thumbnail((160,256),Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA',SIZE)
    canvas.alpha_composite(original,((176-original.width)//2,264-original.height))
    original = canvas
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'source.png').write_bytes(source_bytes)
    rgba = np.array(original)
    visible = rgba[:, :, 3] > 0
    # The cut lines follow clothing/skin/hair boundaries, not rectangular tiles.
    masks = {
        'legs': polygon([(0,181),(176,181),(176,272),(0,272)]),
        'body': polygon([(51,97),(121,97),(145,180),(122,184),(51,184),(30,180)]),
        'braid_l': polygon([(32,82),(55,82),(62,102),(46,124),(44,146),(12,146),(12,110)]),
        'braid_r': polygon([(118,82),(145,82),(166,111),(166,146),(130,146),(129,123),(112,102)]),
        'head': polygon([(20,0),(155,0),(153,83),(119,87),(111,94),
                           (95,98),(78,98),(61,94),(55,87),(20,84)]),
        'bangs': polygon([(42,59),(54,37),(70,23),(96,19),(116,31),(122,55),(122,68),
                            (115,67),(107,63),(94,63),(83,61),(77,61),(72,62),(61,62),(56,69),(49,70)]),
        'arms': polygon([(53,111),(62,130),(57,152),(55,170),(56,175),(51,190),(32,190),(32,147)]) |
                polygon([(121,111),(113,131),(117,152),(119,170),(119,175),(124,190),(143,190),(145,147)]),
    }
    # Resolve ownership back to front. Remaining pixels belong to the torso.
    owner = np.full(visible.shape, 'body', dtype='<U16')
    for name, mask in masks.items():
        owner[mask] = name
    eye_l = polygon([(59,66),(63,63),(76,63),(80,67),(81,77),(76,83),(61,82),(56,76)])
    eye_r = polygon([(97,66),(101,63),(114,63),(119,67),(119,76),(114,83),(99,83),(95,77)])
    brows = polygon([(64,50),(68,48),(77,48),(79,51),(74,51),(68,51),(64,53)]) | polygon(
        [(101,48),(110,48),(115,51),(116,54),(110,52),(104,51),(101,51)])
    mouth = polygon([(80,83),(95,83),(96,89),(80,89)])
    features = {'eye_l': eye_l, 'eye_r': eye_r, 'brows': brows, 'mouth_closed': mouth}
    layers = {}
    for name in masks:
        part = rgba.copy()
        part[:, :, 3] = np.where((owner == name) & visible, rgba[:, :, 3], 0)
        layers[name] = part

    # Reconstruct exposed skin under eyes, brows and mouth using surrounding
    # pixels. The mask includes the complete dark outline, so no ghost eyes.
    head = layers['head']
    face_mask = eye_l | eye_r | brows | mouth
    repaired = cv2.inpaint(rgba[:, :, :3], face_mask.astype('uint8') * 255, 5, cv2.INPAINT_NS)
    # Eye borders touch dark lashes/hair. Do not let those colors diffuse into
    # closed lids: rebuild skin from the unoccluded center of the same face.
    for y in range(63,84):
        skin = rgba[y,84:92,:3].mean(axis=0).astype('uint8')
        repaired[y, (eye_l | eye_r)[y], :] = skin
    head[face_mask, :3] = repaired[face_mask]
    for name, mask in features.items():
        part = rgba.copy()
        part[:, :, 3] = np.where(mask & visible, rgba[:, :, 3], 0)
        layers[name] = part

    # Paint a continuous forehead behind the movable fringe, contained within
    # the original silhouette. Retain crown/side hair and the source outline.
    under_fringe = (owner == 'bangs') & visible
    head[under_fringe] = rgba[under_fringe]
    yy, xx = np.indices(visible.shape)
    forehead = under_fringe & (yy > 51)
    head[forehead] = (255, 247, 232, 255)
    # Eyebrows cross the fringe. Repaint their old location on the hair and
    # render the separate eyebrows over it, allowing a subtle expression shift.
    layers['bangs'][brows,:3] = repaired[brows]
    # Extend torso/legs/head along internal cut lines by 3px using nearest
    # source pixels. Never dilate the outer silhouette into the background.
    repairs = {}
    for name in ('legs', 'body', 'head', 'braid_l', 'braid_r'):
        part = layers[name]
        occupied = part[:, :, 3] > 0
        _, indices = distance_transform_edt(~occupied, return_indices=True)
        extra = binary_dilation(occupied, iterations=3) & ~occupied & visible
        part[extra] = part[indices[0][extra], indices[1][extra]]
        repairs[name] = int(extra.sum())
    # Neck is a complete hidden bridge up into the jaw, with a warm edge.
    neck = Image.new('RGBA', SIZE)
    nd = ImageDraw.Draw(neck)
    nd.polygon([(80,90),(94,90),(94,100),(100,102),(93,106),(81,106),(76,102),(80,100)], fill='#ffe5d1')
    nd.line([(78,103),(86,105),(94,104),(98,102)], fill='#d79b76', width=1)
    layers['neck'] = np.array(neck)

    # Eyelids and open mouths reuse repaired skin patches, so blink/speech
    # never stack on top of the original eyes or lips.
    for side, mask, points in [('l',eye_l,[(60,74),(65,77),(71,78),(77,75)]),
                               ('r',eye_r,[(97,75),(103,78),(110,77),(115,74)])]:
        closed = np.zeros_like(rgba)
        closed[:, :, :3] = repaired
        closed[:, :, 3] = np.where(mask, rgba[:, :, 3], 0)
        im = Image.fromarray(closed)
        ImageDraw.Draw(im).line(points, fill='#85522e', width=1)
        layers['eye_closed_' + side] = np.array(im)
    for name, box in [('mouth_small',(84,84,91,88)), ('mouth_large',(83,83,92,89))]:
        part = np.zeros_like(rgba)
        part[:, :, :3] = repaired
        part[:, :, 3] = np.where(mouth, rgba[:, :, 3], 0)
        im = Image.fromarray(part)
        draw = ImageDraw.Draw(im)
        draw.ellipse(box, fill='#9d4f43', outline='#ca805b')
        draw.arc(box, 10, 160, fill='#f5afa0', width=1)
        layers[name] = np.array(im)

    order = ['legs','braid_l','braid_r','body','neck','head','eye_l','eye_r',
             'brows','mouth_closed','bangs','arms','eye_closed_l','eye_closed_r',
             'mouth_small','mouth_large']
    pivots = {'legs':(87,183), 'body':(87,181), 'neck':(87,100),
              'braid_l':(50,89), 'braid_r':(126,89), 'arms':(87,110)}
    manifest = {'version':1,'canvas':[176,272], 'source_sha256':hashlib.sha256(source_bytes).hexdigest(),
                'method':'deterministic polygon separation, local skin inpainting, 3px seam overlap',
                'limitations':'Small rotations with seam overlaps and local skin repairs; no Cubism mesh or full head turns.',
                'repair_pixels':repairs, 'layers':[]}
    composite = Image.new('RGBA', (176,272))
    for name in ['legs','braid_l','braid_r','neck','body','head','eye_l','eye_r',
                 'mouth_closed','bangs','brows','arms']:
        composite.alpha_composite(Image.fromarray(layers[name]))
    sheet = Image.new('RGB', (176*4, 302*4), '#302c46')
    declarations = []
    binary_dir = destination / 'bin'
    binary_dir.mkdir(exist_ok=True)
    for i, name in enumerate(order):
        full = Image.new('RGBA',(176,272))
        full.alpha_composite(Image.fromarray(layers[name]), OFFSET)
        bounds = full.getbbox()
        cropped = full.crop(bounds)
        cropped.save(destination / (name + '.png'))
        a = np.array(cropped)
        w,h = cropped.size
        # ARGB8888 is BGRA on this little-endian target. Runtime loads whole
        # buffers for rotation; scanline-only file decoding cannot rotate.
        data = struct.pack('<BBHHHHH',0x19,0x10,0,w,h,w*4,0) + a[:,:,[2,1,0,3]].tobytes()
        (binary_dir / (name + '.bin')).write_bytes(data)
        px,py = pivots.get(name,(87,97))
        record = dict(name=name,rect=[*bounds[:2],w,h],pivot=[px,py],
                      bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        manifest['layers'].append(record)
        declarations.append('    {"%s", %d, %d, %d, %d, %d, %d},' %
                            (name,*record['rect'],*record['pivot']))
        sheet.paste(full, ((i%4)*176,(i//4)*302), full)
        ImageDraw.Draw(sheet).text(((i%4)*176+5,(i//4)*302+276),name,fill='white')
    composite.save(destination / 'composite.png')
    sheet.save(destination / 'layer-sheet.png')
    manifest['total_bin_bytes'] = sum(x['bytes'] for x in manifest['layers'])
    manifest['format'] = 'LVGL 9 ARGB8888 (BGRA bytes), cropped per layer'
    (destination / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (ROOT/'app/gemini_chat_minimal/qiji_layer_assets.h').write_text(
        '/* Generated by tools/split_layered_avatar.py. Coordinates are canvas-local. */\n'
        '#ifndef QIJI_LAYER_ASSETS_H\n#define QIJI_LAYER_ASSETS_H\n'
        'static const struct { const char *name; int x, y, w, h, px, py; } qiji_layer_assets[] = {\n'+
        '\n'.join(declarations)+'\n};\n#endif\n',encoding='utf-8')
    print(json.dumps({'layers':len(order),'bin_bytes':manifest['total_bin_bytes']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'assets/kotone-layered-v1')
    args = parser.parse_args()
    separate(args.source,args.output)
