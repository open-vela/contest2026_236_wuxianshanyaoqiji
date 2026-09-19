"""Archive the Aliyun build from the fixed official tree; no credentials included."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

project = Path(__file__).resolve().parent.parent
root = Path(sys.argv[1]).resolve()
delivery = Path(sys.argv[2]).resolve()
tts = '--tts' in sys.argv[3:]
voice_fix = '--capture-idle' in sys.argv[3:]
if not voice_fix:
    raise RuntimeError('Prior releases are frozen. Current sources include the media policy fix; use --capture-idle.')
release_name = 'capture-idle-20260919'
image_name = 'qiji-chat-capture-idle.img'
release = project / 'firmware' / release_name
if (release/image_name).exists():
    raise FileExistsError('Frozen release already exists: '+str(release))
release.mkdir(parents=True, exist_ok=True)
out = root / 'vendor/allwinnertech/lichee/out/r528s3/gemini-s1_nand'
image = out / 'rtos_nuttx_r528s3-gemini-s1_uart0_128Mnand.img'
report = subprocess.check_output([sys.executable, str(project/'tools/verify_official_image.py'), str(out/'image'), str(image),
    str(root/'vendor/allwinnertech/boards/r528/r528s3-gemini-s1/src')])
(release/'verification.json').write_bytes(report)
shutil.copy2(image, release/image_name)
for source, name in [(root/'nuttx/nuttx','chat.elf'), (root/'nuttx/.config','chat.config'),
                     (root/'nuttx/defconfig','qiji-chat.defconfig'),
                     (Path('/home/vela/gemini-capture-idle-build.log'),'build.log'),
                     (Path('/home/vela/gemini-capture-idle-pack.log'),'pack.log')]:
    shutil.copy2(source, release/name)
for folder, name in [('packages/ai_agent','agent.patch'), ('vendor/allwinnertech','vendor.patch'),
                     ('frameworks/multimedia/media','media.patch'), ('external/ffmpeg/ffmpeg','ffmpeg.patch')]:
    patch = subprocess.check_output(['git','-C',str(root/folder),'diff','--binary'])
    if not patch: raise RuntimeError(f'Expected changes missing: {folder}')
    (release/name).write_bytes(patch)
baseline=project/'firmware/official-clean-20260919'
for name in ['source-lock.xml','gemini-official-provenance.json']:
    shutil.copy2(baseline/name,release/name)
files=list((project/'app/gemini_chat_minimal').glob('*.c'))+list((project/'app/gemini_chat_minimal').glob('*.h'))
files += [p for p in (project/'app/gemini_chat_minimal/media').glob('*') if p.is_file()]
files += [project/'app/gemini_chat_minimal'/n for n in ['Makefile','Make.defs','Kconfig','README.md','ARTWORK.md','SOUL.md']]
files += [project/n for n in ['README.md','docs/aliyun-asr-integration.md','docs/qwen-tts-integration.md','docs/avatar-iteration.md',
    'docs/voice-fix-20260919.md','docs/voice-ui-20260919.md','docs/audio-unblock-20260919.md','docs/capture-stop-20260919.md','docs/dialogue-reply-20260919.md','docs/capture-idle-20260919.md','tools/prepare_qiji_persona.py','tools/prepare_capture_idle.py','tools/prepare_dialogue_reply.py','tools/prepare_audio_unblock.py','tools/restore_board_config.ps1','tools/pack_debug_wifi.py',
    'tools/prepare_official_chat.py','tools/prepare_wifi_doubao.py','tools/prepare_aliyun_asr.py',
    'tools/verify_official_image.py','tools/export_aliyun_release.py','tools/configure_aliyun.ps1',
    'tools/configure_gemini.ps1','tools/test_aliyun_asr.ps1','tools/prepare_aliyun_tts.py','firmware/official-clean-20260919/qiji-chat.defconfig']]
files += [p for p in (project/'tools/asr_host').rglob('*') if p.is_file()]
files += [p for p in (project/'docs/assets/qwen-tts').glob('*') if p.suffix in ['.wav','.json']]
for p in files:
    dest=release/'source'/p.relative_to(project)
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'image':image_name,'sha256':sha(image),'bytes':image.stat().st_size,
    'asr':'paraformer-realtime-v2','llm':'doubao-seed-character-260628',
    'host_cloud_lifecycle_verified':True,'host_firmware_c_backend_cloud_verified':True,
    'tts':'qwen-audio-3.1-tts-flash','voice':'longanlingxi_v3.1',
    'host_tts_verified':True,'host_playback_contract_verified':True,
    'host_media_policy_verified':True,'final_romfs_payload_verified':True,
    'ui':'Voice only; single status row; 58px record button',
    'r2_device_media_daemon_verified':True,
    'host_nonblocking_capture_stop_verified':True,
    'host_pcm_conversion_timeout_cancel_verified':True,'host_speech_lock_deadline_verified':True,
    'audio_fix':'48kHz stereo playback, bounded PCM/control I/O and speech lock',
    'policy_fix':'Matched criteria/settings to official minimal graph; fixed incremental ROMFS dependencies',
    'old_firmware_device_wifi_restored':True,'old_firmware_media_failure_confirmed':True,
    'persona':'Original Qiji virtual idol; SOUL.md bootstrap',
    'host_capture_idle_regression_verified':True,
    'dialogue_reply_device_two_text_rounds_verified':True,
    'host_final_reply_callback_verified':True,'host_audio_sink_eof_verified':True,
    'capture_stop_device_asr_verified':True,'capture_stop_device_llm_reply_ms':2033,
    'hardware_verified':False,'microphone_verified':False,'speaker_verified':False,
    'credentials_embedded':False,'build_environment':'WSL2 Ubuntu 24.04; outside official supported environment'}
(release/'release.json').write_text(json.dumps(manifest,indent=2)+'\n')
(release/'README.md').write_text('# 录音空闲积压修复固件\n\n使用 qiji-chat-capture-idle.img，适配 Gemini-S1 + 2.8 寸 SPI 屏。\n\n移除输入框、发送按钮、屏幕键盘；头部合并一行，录音按钮加高为 58px。保留 R2 媒体与 ROMFS 构建修复。新增 48kHz 双声道播放转换、写入超时和语音锁限时等待。修复录音阻塞读取及跨线程关闭导致无法结束录音的问题，增加停止和 ASR 分段耗时日志。保留正式回复和播放 EOF 修复。本次新增：采集源收到下游 EOF 时关闭设备，防止空闲时积压旧音频；增加首批 PCM 计时与 ADB record/stop 诊断入口，加入绮迹原创偶像少女人设。格式化烧录仍需重新配置网络与 Key。\n\n阿里 ASR + 豆包拟人 LLM + Qwen Audio 3.1 TTS（龙安灵希）。\n\n前版已通过两轮板端文本回复和播放软件链路；本次主机回归复现旧采集缺陷并验证修复，新包仍待板端连续录音验收。\n\n详见 source/docs/capture-idle-20260919.md；tools/restore_board_config.ps1 可恢复配置。镜像不含密钥。\n')
checks={p.relative_to(release).as_posix():sha(p) for p in release.rglob('*') if p.is_file() and p.name!='SHA256SUMS.json'}
(release/'SHA256SUMS.json').write_text(json.dumps(checks,indent=2)+'\n')
delivery.mkdir(parents=True,exist_ok=True)
zip_path=delivery/'gemini-capture-idle-20260919.zip'
with zipfile.ZipFile(zip_path,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(release.rglob('*')):
        if p.is_file():z.write(p,release_name+'/'+p.relative_to(release).as_posix())
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    for name,digest in checks.items():assert hashlib.sha256(z.read(release_name+'/'+name)).hexdigest()==digest
shutil.copy2(release/image_name,delivery/image_name)
(delivery/(zip_path.name+'.sha256')).write_text(sha(zip_path)+'  '+zip_path.name+'\n')
print(json.dumps({'archive':str(zip_path),'sha256':sha(zip_path),'files':len(checks),'release':manifest},indent=2))
