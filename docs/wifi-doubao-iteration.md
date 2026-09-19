# Wi-Fi 与豆包模型迭代

设备：Gemini-S1 + 2.8 寸 SPI 屏。调试 SSID：`2F`。
密码和 Ark API Key 只保存到设备 /data，没有编入固件或写入源码。

## 实机记录（2026-09-19）

- 连接 2F 的 2.4 GHz 接入点，DHCP 地址为 192.168.5.158。
- 开发板解析并 ping 通 ark.cn-beijing.volces.com。
- 两个模型均通过官方 Chat Completions 接口测试。
- 板端 Turbo 短句测试：3012 ms，成功。
- 板端 Character 短句测试：894 ms，成功；当前选用拟人模型。
- 以上各一次不同短句请求，不是统计性能基准，也不能保证拟人模型始终更快。

接口：https://ark.cn-beijing.volces.com/api/v3/chat/completions

| 选择 | 模型 ID |
| --- | --- |
| 默认拟人 | doubao-seed-character-260628 |
| Turbo | doubao-seed-2-1-turbo-260628 |

## 配置设备

Windows PowerShell 运行 `tools/configure_gemini.ps1`，交互输入 Wi-Fi 密码和 Ark Key。
默认 SSID 为 2F、模型为 character；指定 `-Model turbo` 可切换。
脚本不在本机写入凭据文件；配置后须验证屏幕上的真实模型回复。

新版本提供 NSH 命令：

```text
qiji_config wifi <SSID> <password>
qiji_config wifi_reconnect
qiji_config model character
qiji_config model turbo
qiji_config result
```

模型切换沿用已经保存的 Key，请在当前回复结束后切换。不要启动第二个 ai_agent。

## 修正依据

1. 官方 WAPI 枚举：CCMP=3，WPA2=2；原 start_wifi.sh 使用的 `psk ... 1 3` 不对应 WPA2/CCMP。
2. wapi_save_config 命令要求接口 RUNNING；未连接时不能靠它覆盖旧网络。
3. wapi_load_config 要求 bssid 字符串，即使按 SSID 连接也必须提供空字符串。
4. 板上保留出厂 10.0.0.2 会导致此次 DHCP 失败；清为 0.0.0.0 后成功。
5. 首次 TLS 握手会把过旧系统时间调整到 2026 年，Agent 用 gettimeofday 测耗时会把正常回复误判为数十亿毫秒超时。改为 CLOCK_MONOTONIC 计时，保留超时阈值。

新固件启动使用 qiji_config wifi_reconnect，直接读取设备的 WAPI 配置，不再经过旧脚本的参数解析。
界面增加 Wi-Fi 地址；qiji_config result 可读取当前状态及回复。语音尚未验收成功。

## 构建

先按原构建指南准备干净官方树和官方音频补丁，然后运行：

```sh
python3 /path/to/project/tools/prepare_wifi_doubao.py /path/to/openvela
cd /path/to/openvela
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/qiji_chat/ -j4
source build/envsetup.sh
cd vendor/allwinnertech/lichee
source envsetup.sh
lunch_nuttx r528s3-gemini-s1
pack
```

旧成果 ZIP 保留原始版本；新镜像须单独验收重启联网，不能把旧包上的现场配置测试等同于新固件已上板。
