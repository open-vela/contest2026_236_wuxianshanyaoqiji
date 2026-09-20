# Google Material Icons Round

Official source: https://github.com/google/material-design-icons

Vendored mic, stop and more_horiz icons (24px, rounded). Exact upstream commit, source URLs and SHA-256 are recorded in source.json. License: Apache-2.0; full text is in LICENSE.

Modification: rasterized to 24px alpha masks and colored white; packed as embedded LVGL RGB565A8 arrays in app/gemini_chat_minimal/qiji_material_icons.h. No icon font is required at runtime.

Regenerate with `python tools/convert_material_icons.py` (host dependencies: pillow, resvg-py).
