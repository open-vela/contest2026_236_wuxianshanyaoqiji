# 阿里云 Paraformer 接入准备

状态（2026-09-19）：阿里云后端已实现，ARM 固件编译完成；电脑端通过真实云端调用。新固件尚未烧录，板载麦克风端到端待验收。
目标：语音识别使用 paraformer-realtime-v2，文字对话继续使用豆包拟人模型。

## 用户需要提供

- 阿里云百炼华北2（北京）地域 API Key，并确认账户有 Paraformer 模型调用权限。
- 如果使用控制台推荐的工作空间专属域名，同时提供 Workspace ID 或完整 WebSocket 地址。
- 如果控制台参数与文档不同，可提供去掉密钥后的官方调用示例。

不需要阿里云账户密码，也不需要账户级 AccessKey ID / AccessKey Secret。
密钥应保存到设备 /data，不能进入源码、预览、构建日志或分发固件。

## 官方协议

- [WebSocket API](https://help.aliyun.com/en/model-studio/websocket-for-paraformer-real-time-service)
- [客户端事件](https://help.aliyun.com/zh/model-studio/paraformer-client-events)
- [服务端事件](https://help.aliyun.com/zh/model-studio/paraformer-server-events)

北京旧域名 dashscope.aliyuncs.com 仍可用；新推荐域名为 {WorkspaceId}.cn-beijing.maas.aliyuncs.com。
路径为 /api-ws/v1/inference，使用 wss。握手 Authorization 为 Bearer 加 API Key。

顺序：run-task → 等待 task-started → 发送 PCM 二进制帧并接收 result-generated → finish-task → 等待 task-finished → 关闭。
模型 paraformer-realtime-v2；本项目拟使用 16000 Hz、16 bit、单声道 PCM，与现有 voice_asr 接口一致。
识别结果按 begin_time 区分句子，仅拼接 sentence_end=true 的最终句；相同 begin_time 的重复最终结果覆盖原句，不重复追加中间结果。

## 已实现

- 修复官方 streaming 包装固定调用 volc_asr_stream_* 的问题；会话在创建时绑定后端，后续切换不会改变已打开会话。
- app/gemini_chat_minimal/qiji_aliyun_asr.c 实现阿里握手、任务状态、分片帧、ping/pong、最终句拼接、错误与超时处理，复用板端 16 kHz PCM。
- TLS 强制验证证书和主机名，使用 Ubuntu/Mozilla 信任库中的公开 GlobalSign R3/R46 根证书；Wi-Fi 获取 IP 后启动 NTP。时钟未校准时不放宽校验。
- qiji_config set_aliyun_asr 独立保存 Key 和后端选择，跨重启加载；不修改豆包 LLM Key。配置脚本 tools/configure_aliyun.ps1 使用安全输入。
- socket/TLS 与任务使用单调时钟截止时间；DNS 解析仍受系统 resolver 超时控制。网络会话最长约 90 秒，结束等待 15 秒。
- 修复官方 stop_with_text 流式路径将失败返回为成功的问题。

## 测试证据

1. Windows WebSocket 测试：两秒静音任务收到 task-started / task-finished，鉴权通过。
2. Windows 系统语音生成短中文 PCM，阿里返回“你好，我是启迹。今天天气怎么样？”。原文角色名“绮迹”存在同音字差异，可后续增加热词。
3. tools/asr_host 使用与固件完全相同的 C 后端和官方源码树内 mbedTLS/cJSON，真实证书验证及音频识别通过，结果同上。
4. ARM 官方工具链编译及官方 pack 完成。IMAGEWTY/组件校验结果随发行包保存。

以上均不是板载麦克风验收，TTS 发声也没有因此接通。

## 构建和配置

在已应用官方音频补丁的固定源码树运行：

```sh
python3 tools/prepare_aliyun_asr.py /home/vela/gemini-official-clean-20260919
cd /home/vela/gemini-official-clean-20260919
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/qiji_chat/ -j4
source build/envsetup.sh
cd vendor/allwinnertech/lichee
source envsetup.sh
lunch_nuttx r528s3-gemini-s1
pack
```

新固件启动后运行 `tools/configure_aliyun.ps1`，按提示输入北京地域 Key。当前连接设备的 /data 私有配置已写入 Key，并核对豆包拟人模型设置；正常保留数据升级后应自动选择 aliyun。如果烧录格式化了 /data，需重新配置 Wi-Fi、豆包和阿里。

点录音开始，等进入录音状态后说一句短句，再点停止。先确认识别文字，再确认模型回复。`qiji_config test_asr /data/test.pcm` 可独立测试 16 kHz 单声道 PCM16 文件。

电脑诊断：`tools/test_aliyun_asr.ps1 -PcmFile <文件>`；不传文件则发送两秒静音，只验证服务生命周期。

## 待上板检查

- Wi-Fi 自动重连、NTP 校时及 TLS；麦克风采样内容/音量/录音停止。
- 连续多轮识别、断网恢复与长录音。官方录音管线的中途流式失败会转入有限缓冲批识别，失败前音频可能丢失，不能据此承诺无损恢复。
- 原创 Q 版女角色显示；阿里识别 → 豆包拟人回复。TTS 另行配置、验收。

旧固件不具备 set_aliyun_asr 命令，set_volc_asr / set_volc_key 也不适用于阿里云。
