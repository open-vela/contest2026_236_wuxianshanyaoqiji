[English](README.md)

# 小澄：银发未来风旅人

`character.svg` 是以可编辑矢量路径绘制的项目原创角色，没有使用外部角色、
图片 API 或素材图库。设计方向为银发、蓝紫服装、青色耳机、富有表情的眼睛和
不对称发饰，与琴音的现有形象区分。

`tools/duet/build_character.py` 使用 Pillow 和 resvg-py，以三倍分辨率渲染 SVG
后缩小为 240x280，导出透明 PNG 预览及五个 RGB565A8 C 图像描述符：待机、
半闭眼、眨眼、小口型、大口型。优化后的眼睛采用圆润眼型、裁剪虹膜、分层紫色
高光，并在闭眼前后增加过渡。1,008,000 字节的像素数据存放在 Flash 中；固件按原尺寸
显示，不使用运行时缩放或整图变换缓冲区。

真实 LVGL 界面预览位于 `docs/assets/duet/xiaocheng-eyes-preview.png` 和 `.gif`。
主机渲染不代表屏幕实测或设备内存验收。
