"""Freeze the portrait build, matching sources and official image verification."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

project = Path(__file__).resolve().parent.parent
root, delivery = (Path(p).resolve() for p in sys.argv[1:3])
icon_ui = '--icon-ui' in sys.argv[3:]
sprite_ui = icon_ui or '--sprite-ui' in sys.argv[3:]
enter_ui = sprite_ui or '--enter-ui' in sys.argv[3:]
release_name = 'icon-ui-20260920' if icon_ui else 'sprite-ui-20260920' if sprite_ui else 'enter-ui-20260920' if enter_ui else 'portrait-20260919'
image_name = 'qiji-chat-icon.img' if icon_ui else 'qiji-chat-sprite.img' if sprite_ui else 'qiji-chat-enter.img' if enter_ui else 'qiji-chat-portrait.img'
log_prefix = 'icon' if icon_ui else 'sprite' if sprite_ui else 'enter' if enter_ui else 'portrait'
release = project/'firmware'/release_name
if release.exists():
    raise FileExistsError('Do not overwrite a frozen portrait release')
config = (root/'nuttx/.config').read_text()
for required in ('CONFIG_LCD_PORTRAIT=y', 'CONFIG_LCD_ILI9341_IFACE0_PORTRAIT=y',
                 'CONFIG_GEMINI_CHAT_MINIMAL=y', 'CONFIG_DRIVERS_TPADC=y'):
    if required not in config.splitlines():
        raise RuntimeError('Missing final build option: ' + required)
out = root/'vendor/allwinnertech/lichee/out/r528s3/gemini-s1_nand'
image = out/'rtos_nuttx_r528s3-gemini-s1_uart0_128Mnand.img'
report = subprocess.check_output([sys.executable, str(project/'tools/verify_official_image.py'),
    str(out/'image'), str(image), str(root/'vendor/allwinnertech/boards/r528/r528s3-gemini-s1/src')])
if enter_ui:
    packed = image.read_bytes()
    for marker in (b'qiji_chat: ENTER=0x08 on /dev/input/event1', b'0.3.1' if icon_ui else b'0.3.0' if sprite_ui else b'0.2.0', '绮迹酱'.encode()):
        if marker not in packed:
            raise RuntimeError('ENTER/name/version payload missing from packed image')
if sprite_ui:
    resource = (out/'image/res.fex').read_bytes()
    for state in ('idle','blink','listen','think','speak','happy','comfort','surprise'):
        asset = project/'assets/kotone-v1/bin'/(state+'.bin')
        if asset.read_bytes() not in resource:
            raise RuntimeError('Sprite resource not packed: '+state)
for directory, component in (('UDISK', 'usrdata.fex'), ('res', 'res.fex')):
    wifi = (root/'vendor/allwinnertech/lichee/board/common/data'/directory/'etc/wifi/wapi.conf').read_bytes()
    data = json.loads(wifi)['wlan0']
    if data.get('ssid') or data.get('psk') or wifi not in (out/'image'/component).read_bytes():
        raise RuntimeError('Generic Wi-Fi resource is not empty or not packed: ' + component)
release.mkdir(parents=True)
(release/'verification.json').write_bytes(report)
shutil.copy2(image, release/image_name)
for source, name in ((root/'nuttx/nuttx', 'chat.elf'), (root/'nuttx/.config', 'chat.config'),
                     (root/'nuttx/defconfig', 'qiji-chat.defconfig'),
                     (Path('/home/vela/gemini-'+log_prefix+'-build.log'), 'build.log'),
                     (Path('/home/vela/gemini-'+log_prefix+'-pack.log'), 'pack.log'),
                     (Path('/home/vela/qiji-portrait-preview/Testing/Temporary/LastTest.log'), 'host-tests.log')):
    shutil.copy2(source, release/name)
for folder, name in (('packages/ai_agent', 'agent.patch'),
                     ('vendor/allwinnertech', 'vendor.patch'),
                     ('frameworks/multimedia/media', 'media.patch'),
                     ('external/ffmpeg/ffmpeg', 'ffmpeg.patch')):
    (release/name).write_bytes(subprocess.check_output(['git', '-C', str(root/folder), 'diff', '--binary']))
for name in ('source-lock.xml', 'gemini-official-provenance.json'):
    shutil.copy2(project/'firmware/official-clean-20260919'/name, release/name)
files = [p for p in (project/'app/gemini_chat_minimal').rglob('*')
         if p.is_file() and (p.suffix in ('.c', '.h', '.md', '.conf', '.json', '.xml', '.txt', '.pfw')
         or p.name in ('Makefile', 'Make.defs', 'Kconfig'))]
files += list((project/'tools').glob('prepare_*.py'))
files += [project/p for p in ('tools/portrait_touch.h', 'tools/export_portrait_release.py',
    'tools/verify_official_image.py', 'tools/pack_debug_wifi.py', 'tools/restore_board_config.ps1',
    'docs/portrait-20260919.md', 'docs/build-pack-guide.md', 'README.md',
    'firmware/official-clean-20260919/qiji-chat.defconfig')]
files += [p for p in (project/'tools/portrait_preview').iterdir() if p.is_file()]
files += list((project/'docs/assets/portrait').glob('*.png'))
if enter_ui:
    files += [project/'docs/enter-ui-20260920.md']
    files += list((project/'docs/assets/enter-ui').glob('*.png'))
if sprite_ui:
    files += [project/'docs/sprite-ui-20260920.md', project/'tools/convert_sprite.py']
    files += [p for p in (project/'assets/kotone-v1').rglob('*') if p.is_file()]
    files += [p for p in (project/'output/imagegen/kotone-v1').rglob('*')
              if p.is_file() and p.suffix in ('.png','.txt','.json','.md')]
    files += [p for p in (project/'docs/assets/sprite-ui').iterdir() if p.suffix in ('.png','.gif')]
if icon_ui:
    files += [project/'docs/icon-ui-20260920.md']
    files += list((project/'docs/assets/icon-ui').glob('*.png'))
files += [p for p in (project/'assets/material-icons').rglob('*') if p.is_file()]
files += [project/'tools/convert_material_icons.py', project/'docs/material-ui-20260920.md']
files += list((project/'docs/assets/material-ui').glob('*.png'))
for p in files:
    dest = release/'source'/p.relative_to(project)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
manifest = dict(image=image_name, sha256=sha(image), bytes=image.stat().st_size,
    resolution=[240, 320], orientation='ILI9341 hardware portrait', status_height=20,
    status_font_px=12, dialogue_font_px=14, voice_button_height=46,
    ui='Original chibi girl, translucent dialogue overlay, automatic reply pagination',
    touch='Clamped portrait TPADC coordinates; host corner and full-range tests passed',
    preview='Actual app view + official LVGL/FreeType + bundled MiSans',
    asr='paraformer-realtime-v2', llm='doubao-seed-character-260628',
    tts='qwen-audio-3.1-tts-flash', voice='longanlingxi_v3.1',
    inherited_fixes='capture-idle and original Qiji persona',
    credentials_embedded=False, hardware_verified=False,
    physical_touch_verified=False, microphone_verified=False, speaker_verified=False,
    build_environment='WSL2 Ubuntu 24.04; outside official supported environment')
if enter_ui:
    manifest.update(version='0.2.0', assistant_name='绮迹酱',
        buttons='Onboard ENTER 0x08 on /dev/input/event1, 40ms debounce, one action per press',
        header='Beijing HH:MM and v0.2.0; --:-- until time is synchronized',
        host_button_behavior_verified=True, physical_button_verified=False)
if sprite_ui:
    manifest.update(version='0.3.0', voice_button_height=44,
        ui='8 reference-derived bitmap poses, translucent dialogue, playback-relative scrolling',
        header='Beijing HH:MM and v0.3.0; --:-- until time is synchronized',
        sprite_format='LVGL RGB565A8, 176x272, 143628 bytes each',
        artwork='User-provided Fujita Kotone reference; generated edits; not original project character art',
        image_api_model='gpt-image-2', image_api_provider='https://sapi.riyuexy.cc/v1',
        scrolling='Approximate PCM duration/elapsed-time aid, not word-level alignment',
        host_scroll_behavior_verified=True, hardware_playback_scroll_verified=False)
if icon_ui:
    manifest.update(version='0.3.1', header='Beijing HH:MM and v0.3.1',
        record_control='Vector microphone, stop square while recording, three dots while busy; no text',
        card_bounds=[8,28,224,284], dialogue_bounds=[16,200,208,104],
        record_bounds=[172,252,44,44], outer_gap_px=8, inner_gap_px=8,
        card_radius_px=16, dialogue_radius_px=8,
        corner_alignment='Concentric nested lower corners; outer radius minus inset equals inner radius')
(release/'release.json').write_text(json.dumps(manifest, indent=2)+'\n')
(release/'README.md').write_text('# 绮迹竖屏候选固件\n\n240×320，Gemini-S1 + 2.8 寸 SPI 屏。\n\n'
    '20px 状态轮播、放大原创角色、前景半透明对话层、长回复自动翻页、底部 46px 语音按钮。'
    '使用官方 ILI9341 竖屏配置并同步修正 TPADC 映射。\n\n'
    '编译、主机渲染、触摸坐标测试及完整镜像校验已完成；实物方向、触摸和多轮语音待验收。'
    '通用镜像不含 Wi-Fi 密码或云端 Key。详见 source/docs/portrait-20260919.md。\n')
if enter_ui:
    (release/'README.md').write_text('# 绮迹酱 v0.2.0 · 实体 ENTER 交互\n\n'
        '按开发板 ENTER 开始/结束录音，保留触屏按钮。顶部右侧为北京时间和版本号。'
        '助手名字及默认人设统一为绮迹酱。\n\n'
        '编译、按键消抖回归、触摸坐标测试、主机预览和完整镜像校验通过。'
        '实体按键控制语音、显示时间和多轮语音仍待新固件烧录验收。'
        '通用镜像无网络密码及云端 Key。详见 source/docs/enter-ui-20260920.md。\n')
if sprite_ui:
    (release/'README.md').write_text('# 绮迹酱 v0.3.0 · 图片动作与朗读滚动\n\n'
        '藤田琴音参考图生成 8 种动作，176×272 透明图片；右下角 44px 录音按钮叠于对话层，保留实体 ENTER。'
        '长文本按照 PCM 时长及接收进度近似滚动，不是逐字时间戳同步。\n\n'
        '编译、主机界面预览、按键/坐标/滚动测试和完整镜像校验通过；本版尚待烧录及实物音画验收。'
        '通用镜像无网络密码及云端 Key。图片属于指定现有角色的衍生素材，未作为原创比赛素材发布。'
        '详见 source/docs/sprite-ui-20260920.md 和 source/app/gemini_chat_minimal/ARTWORK.md。\n')
if icon_ui:
    (release/'README.md').write_text('# 绮迹酱 v0.3.1 · 图标与统一间距\n\n'
        '右下角按钮改为麦克风图标，录音时为停止方块，等待时为三个圆点，无按钮文字。'
        '外卡片到屏幕左右/底部/状态栏为 8px；文本框到卡片左右/底部为 8px。'
        '外圆角 16px、内圆角 8px，使嵌套下方圆角同心。\n\n'
        '保留 8 种动作、文本滚动、实体 ENTER 和时间显示。'
        '主机实际渲染、现有回归、编译和镜像核验通过；本版尚未烧录。'
        '通用镜像不含 Wi-Fi 密码和云端 Key。详见 source/docs/icon-ui-20260920.md。\n')
checks = {p.relative_to(release).as_posix(): sha(p) for p in release.rglob('*') if p.is_file()}
(release/'SHA256SUMS.json').write_text(json.dumps(checks, indent=2)+'\n')
delivery.mkdir(parents=True, exist_ok=True)
archive_path = delivery/('gemini-'+release_name+'.zip')
with zipfile.ZipFile(archive_path, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for p in sorted(release.rglob('*')):
        if p.is_file(): archive.write(p, release_name+'/'+p.relative_to(release).as_posix())
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    for name, digest in checks.items():
        assert hashlib.sha256(archive.read(release_name+'/'+name)).hexdigest() == digest
shutil.copy2(release/image_name, delivery/image_name)
(delivery/(archive_path.name+'.sha256')).write_text(sha(archive_path)+'  '+archive_path.name+'\n')
print(json.dumps(dict(release=manifest, archive=str(archive_path), files=len(checks)), indent=2))
