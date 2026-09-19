# 重复录音卡顿与绮迹人设

## 卡顿的现场证据

设备运行 dialogue-reply 固件（19:50:54）。用户反馈点击说话卡顿，ADB 读取到 `busy=0 recording=1`，不是仍在等待模型。20:13:04 开启录音，到 20:13:39 才出现第一批 PCM；媒体混音输入首次记录 `first size: 10268160`，随后出现 capture overflow 和流式识别发送失败。用户确认界面是卡顿，尚能操作。

官方 `asrc_adevsrc.c` 的设备可读事件会强制设置 `frame_wanted_out`，但 `adevsrc_activate()` 原本不检查下游已经结束的状态。录音 sink 断开后，结束状态沿 volume 回传；采集设备却仍可响应事件并往已结束的链路写入，空闲期间不断积压。当前补丁在激活时先检查链路状态，关闭采集设备和解码器；下次录音由官方格式协商清除状态，再重新打开设备。

## 验证范围

`tools/asr_host/test_capture_idle.py` 提取并编译官方实际采集激活函数。原始官方代码可复现空闲状态仍采集的问题；修改后通过三次录音/结束/重开，以及三万次空闲设备事件的回归，空闲期间不再读取或排入新音频。覆盖设备 EAGAIN、EOF。测试底层设备为桩，不能替代板上连续录音与触摸响应验收。

新增 `capture first PCM` 日志测量每轮首批音频延迟。新增 `qiji_config record` / `qiji_config stop` 诊断命令，使用与屏幕按钮相同的状态转换和工作线程，便于烧录后自动检查多轮录音。没有新增触屏文本框。

## 原创人设

用户指定参考《学园偶像大师》藤田ことね的氛围。核对[官方角色页](https://gakuen.idolmaster-official.jp/idol/kotone/)后，使用“喜欢被夸、精打细算、对可爱有自信”等一般性格方向，另行创作绮迹自己的伙伴身份、中文语气和对话示例。

完整设定在 `app/gemini_chat_minimal/SOUL.md`：活泼机灵、俏皮、有点小得意，会短暂泄气但愿意努力。日常一到三句，适合小屏和朗读；不再以工程设备助手的功能清单自我介绍。沿用原创浅紫短发 Q 版形象和已有阿里音色，未复刻作品台词、剧情、角色美术或声优声音。

`prepare_qiji_persona.py` 把设定作为官方 `memory_store_init()` 的默认 SOUL 内容，限定当前应用配置；保留已有 SOUL 文件。已有设备可直接推送到 `/data/ai_agent/config/SOUL.md`，下一次模型调用读取新设定，不需要为人设单独重启。已有会话和缓存可能仍含旧回答，测试使用新问题。

## 构建与交付

最终准备入口：`python3 tools/prepare_qiji_persona.py OFFICIAL_ROOT`，串联本次空闲采集修复和之前的正式回复、播放 EOF、录音停止、阿里语音、Wi-Fi 与官方屏幕适配。

构建仍使用官方 qiji_chat 配置和 `build.sh`、`pack`。成果位于 `firmware/capture-idle-20260919`，导出参数 `--capture-idle`；2F 本地调试包 `qiji-chat-capture-idle-2f-debug.img`，统一交付入口 `qiji-latest.img`。新包板端多轮录音和人设回复效果仍待验收。
