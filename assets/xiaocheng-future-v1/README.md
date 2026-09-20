[简体中文](README.zh_CN.md)

# Xiaocheng: silver-haired future traveller

Original project character artwork in `character.svg`, authored as editable
vector paths. No external character, image API, or stock art was used.
Direction: silver hair, blue/violet clothing, a cyan headset, expressive eyes,
and an asymmetric hair accessory. This is distinct from Kotone's existing art.

`tools/duet/build_character.py` uses Pillow and resvg-py to rasterize the SVG at
3x resolution and downsample to 240x280. It exports transparent PNG previews and
five RGB565A8 C image descriptors: idle, half blink, blink, small mouth, large mouth.
The refined eyes use rounded lids, clipped irises, layered violet highlights,
and a half-closed transition before and after each blink.
The 1,008,000 bytes of pixel data reside in Flash; the firmware uses native-size
images with no runtime scaling or full-image transformation buffer.

The actual LVGL preview is `docs/assets/duet/xiaocheng-eyes-preview.png` and
`.gif`. Host rendering is not on-device display or memory acceptance.
