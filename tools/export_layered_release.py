"""Verify and freeze the layered firmware without replacing older releases."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

project = Path(__file__).resolve().parents[1]
root = Path(sys.argv[1]).resolve()
kotone = '--kotone' in sys.argv[2:]
release = project / ('firmware/kotone-persona-20260920' if kotone else 'firmware/layered-ui-20260920')
image_name = 'qiji-chat-kotone.img' if kotone else 'qiji-chat-layered.img'
if release.exists():
    raise FileExistsError('Do not overwrite a frozen layered release')
out = root/'vendor/allwinnertech/lichee/out/r528s3/gemini-s1_nand'
image = out/'rtos_nuttx_r528s3-gemini-s1_uart0_128Mnand.img'
board = root/'vendor/allwinnertech/boards/r528/r528s3-gemini-s1/src'
report = json.loads(subprocess.check_output([sys.executable,
    str(project/'tools/verify_official_image.py'), str(out/'image'), str(image), str(board)]))
resource = (out/'image/res.fex').read_bytes()
manifest = json.loads((project/'assets/kotone-layered-v1/manifest.json').read_text())
for entry in manifest['layers']:
    data = (project/'assets/kotone-layered-v1/bin'/(entry['name']+'.bin')).read_bytes()
    if hashlib.sha256(data).hexdigest() != entry['sha256'] or data not in resource:
        raise RuntimeError('Packed layer missing or stale: '+entry['name'])
for name in ('idle','blink','listen','think','speak','happy','comfort','surprise'):
    if (project/'assets/kotone-v1/bin'/(name+'.bin')).read_bytes() not in resource:
        raise RuntimeError('Original sprite missing: '+name)
for directory, component in (('UDISK','usrdata.fex'),('res','res.fex')):
    wifi = (root/'vendor/allwinnertech/lichee/board/common/data'/directory/'etc/wifi/wapi.conf').read_bytes()
    data = json.loads(wifi)['wlan0']
    if data.get('ssid') or data.get('psk') or wifi not in (out/'image'/component).read_bytes():
        raise RuntimeError('Generic Wi-Fi settings not empty or not packed')
elf = root/'nuttx/nuttx'
if kotone:
    subprocess.run([sys.executable,str(project/'tools/build_kotone_persona.py'),'--check'],check=True)
    packed = image.read_bytes()
    for marker in ('藤田琴音'.encode(), b'qiji_kotone_v1', b'0.4.0',
                   (project/'app/gemini_chat_minimal/SOUL.md').read_bytes()):
        if marker not in packed:
            raise RuntimeError('Packed Kotone identity/session/version/persona is missing')
sources = [p for p in (project/'app/gemini_chat_minimal').rglob('*') if p.is_file()
           and (p.suffix in ('.c','.h','.md','.txt','.pfw','.conf','.json') or p.name in ('Makefile','Make.defs','Kconfig'))]
for p in sources:
    if p.suffix in ('.c','.h') and p.stat().st_mtime > elf.stat().st_mtime:
        raise RuntimeError('Source newer than linked firmware: '+str(p))
release.mkdir(parents=True)
(release/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
shutil.copy2(image,release/image_name)
for src,name in [(elf,'chat.elf'),(root/'nuttx/.config','chat.config'),
                 (root/'nuttx/defconfig','qiji-chat.defconfig'),
                 (Path('/home/vela/qiji-kotone-build.log' if kotone else '/home/vela/qiji-layered-firmware-build-final.log'),'build.log'),
                 (Path('/home/vela/qiji-kotone-pack.log' if kotone else '/home/vela/qiji-layered-pack.log'),'pack.log'),
                 (Path('/home/vela/qiji-layered-preview/Testing/Temporary/LastTest.log'),'host-tests.log')]:
    shutil.copy2(src,release/name)
for folder,name in [('packages/ai_agent','agent.patch'),('vendor/allwinnertech','vendor.patch'),
                    ('frameworks/multimedia/media','media.patch'),('external/ffmpeg/ffmpeg','ffmpeg.patch')]:
    (release/name).write_bytes(subprocess.check_output(['git','-C',str(root/folder),'diff','--binary']))
for folder in ('assets/kotone-v1','assets/kotone-layered-v1','assets/material-icons',
               'output/imagegen/kotone-layered-v1','tools/portrait_preview','docs/assets/layered-ui'):
    sources += [p for p in (project/folder).rglob('*') if p.is_file() and p.suffix not in ('.ppm','.pyc')]
sources += list((project/'tools').glob('prepare_*.py'))
sources += [project/'tools/build_kotone_persona.py',project/'tools/deploy_kotone_persona.py',
            project/'tools/board_acceptance.py',project/'tools/eval_kotone_persona.py']
if kotone:
    sources += [project/'docs/kotone-persona-20260920.md',
                project/'artifacts/kotone-persona-20260920/eval-v3.json',
                project/'artifacts/kotone-persona-20260920/review.json']
    sources += list((project/'docs/assets/kotone-persona').glob('*.png'))
sources += [project/p for p in ('tools/split_layered_avatar.py','tools/convert_sprite.py',
    'tools/portrait_touch.h','tools/export_layered_release.py','tools/verify_official_image.py',
    'tools/convert_material_icons.py','docs/layered-ui-20260920.md','docs/build-pack-guide.md',
    'firmware/official-clean-20260919/qiji-chat.defconfig')]
for p in sources:
    dest = release/'source'/p.relative_to(project)
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,dest)
for name in ('source-lock.xml','gemini-official-provenance.json'):
    shutil.copy2(project/'firmware/official-clean-20260919'/name,release/name)
summary = dict(image=image_name,sha256=report['sha256'],bytes=report['bytes'],
    implementation='12 live layers + 4 eye/mouth alternatives + original 8 sprites',
    layer_format=manifest['format'],layer_bytes=manifest['total_bin_bytes'],
    mouth='Real accepted PCM amplitude with estimated playback position; not phoneme alignment',
    build_verified=True,host_tests_passed=6,packed_assets_verified=24,hardware_verified=False,
    credentials_embedded=False,image_api_model='gpt-image-2',image_api_provider='https://sapi.riyuexy.cc/v1')
if kotone:
    summary.update(version='0.4.0',assistant_name='藤田琴音',session='qiji_kotone_v1',
        persona_bytes=len((project/'app/gemini_chat_minimal/SOUL.md').read_bytes()),
        persona_sha256=hashlib.sha256((project/'app/gemini_chat_minimal/SOUL.md').read_bytes()).hexdigest(),
        host_tests_passed=7,persona_host_probes=12,existing_soul_requires_deployment=True)
(release/'release.json').write_text(json.dumps(summary,indent=2)+'\n')
(release/'README.md').write_text('# 分层动画候选固件\n\n'
    'qiji-chat-layered.img：Gemini-S1，240×320。12 个活动部件、4 个眼/嘴差分，保留原 8 张整图。'
    '支持呼吸、摆头、辫子延迟、眨眼和真实 PCM 音量嘴型。\n\n'
    '板端编译、6 项主机测试、实际 LVGL 多帧预览、24 个图片资源及镜像完整性校验已完成。'
    '尚未烧录，帧率、长期稳定性和音画延迟仍待实机验收。通用镜像不含网络密码或云端 Key。\n\n'
    '源码、素材、提示词和复现说明见 source/docs/layered-ui-20260920.md。\n',encoding='utf-8')
if kotone:
    (release/'README.md').write_text('# 藤田琴音 v0.4.0 候选固件\n\n'
        'qiji-chat-kotone.img：新增官方来源性格与人物关系知识卡、独立会话及括号动作过滤。'
        '保留分层动画、ENTER、Material 图标、朗读滚动与阿里语音链路。\n\n'
        '板端编译、7 项主机回归、12 个云端角色探测、24 个图片资源与镜像完整性核验完成。'
        '云端原始回复曾出现括号动作，板端已加过滤；模型仍可能 OOC，不代表全剧情通过。'
        '设备未连接，尚未烧录或实机验收。通用镜像无 Wi-Fi 密码和云端 Key。\n\n'
        '保留数据升级时，请运行 source/tools/deploy_kotone_persona.py 更新已有 SOUL；'
        '工具会备份并读回核对，不清除历史和 Key。详见 source/docs/kotone-persona-20260920.md。\n',encoding='utf-8')
hashes = {str(p.relative_to(release)):hashlib.sha256(p.read_bytes()).hexdigest()
          for p in release.rglob('*') if p.is_file()}
(release/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2)+'\n')
print(json.dumps(summary,indent=2))
