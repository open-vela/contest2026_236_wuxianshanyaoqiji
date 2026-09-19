> 历史记录，不作为当前 Gemini-S1 固件构建入口。当前成果与复现流程见项目 docs/build-pack-guide.md；旧配置及脚本已停用。

# 板端烧入与验证指南

> **目标**：将二次元 Live2D 对话应用部署到润芯微 Gemini-S1（全志 R528）开发板，通过 OpenVela webview 加载，连接 PC 端 Node.js 网关实现豆包语音对话。
>
> 本指南基于润芯微官方飞书文档《开发编译环境准备》《软件烧录指南》整理，并结合大赛参赛仓库 `contest2026_236_wuxianshanyaoqiji` 的 manifest。

## 架构概览

```
┌──────────────────────────────┐         ┌──────────────────────────────┐         ┌─────────────────┐
│  Gemini-S1 开发板             │  Wi-Fi  │  PC / 笔记本                  │  HTTPS  │  豆包云端        │
│  (OpenVela + webview)         │◄───────►│  Node.js 网关 (Express + WS)  │◄───────►│  ASR/LLM/TTS    │
│                                │  WS     │  + 静态文件服务 (dist/)       │         │                 │
│  2.8" SPI 竖屏 320×480        │         │  端口: 3001                   │         │                 │
│  板载麦克风                    │         │  PC IP: 192.168.0.116         │         │                 │
└──────────────────────────────┘         └──────────────────────────────┘         └─────────────────┘
```

---

## 第一阶段：构建 Web 应用（已完成）

### 1.1 构建前端

```bash
pnpm build
```

构建产物在 `dist/` 目录。

### 1.2 启动生产网关

```powershell
# Windows PowerShell
$env:NODE_ENV="production"; $env:HOST="0.0.0.0"; node --import tsx api/server.ts
```

网关监听 `0.0.0.0:3001`，板端访问 `http://192.168.0.116:3001/`。

健康检查：`http://localhost:3001/api/health`
- LLM：configured（豆包 Seed 2.1 Turbo）
- ASR/TTS：mock（待配置真实凭证）

---

## 第二阶段：WSL 环境准备

> ⚠️ OpenVela 编译必须在 Linux 环境下进行。WSL 是 Windows 用户的推荐方案。
> 已验证 Ubuntu 22.04 与 Ubuntu 24.04 均可编译 OpenVela；若机器上已有 24.04 直接用即可。

### 2.1 硬件需求

- 64 位 x86 系统
- 至少 80 GB 剩余硬盘空间（源码+编译产物）
- 至少 16 GB RAM

### 2.2 WSL 中安装 Ubuntu

如果尚未安装 WSL：
```powershell
# Windows PowerShell（管理员）— 推荐 22.04
wsl --install -d Ubuntu-22.04 --no-launch

# 若 22.04 下载受阻而机器上已装 24.04，可直接用：
wsl --install -d Ubuntu --no-launch
```

> `--no-launch` 避免安装后立刻进入交互式首次设置（设置用户名密码）。
> 安装完成后用 `wsl -d Ubuntu-22.04`（或 `wsl -d Ubuntu`）进入，
> 首次启动会要求设置 UNIX 用户名和密码，这一步**只用于普通用户**；
> 后续 OpenVela 编译命令建议直接用 `sudo` 或 `wsl -d <distro> -u root` 执行。

> **重要排查**：若 `wsl --install` 在最后一步报 `Wsl/InstallDistro/Service/RegisterDistro/CreateVm/HCS/E_INVALIDARG`，
> 99% 是 `%USERPROFILE%\.wslconfig` 里残留了 Docker Desktop 写入的错配置，
> 典型症状是把 `kernel=` 指向了 Docker 的 `docker_data.vhdx`（不是 Linux 内核）。
> 修复方法：备份原文件后删除 `kernel=` 和 `swapFile=` 行，让 WSL 使用自带内核。

检查是否安装成功：
```powershell
wsl -l -v
# 应看到 Ubuntu-22.04 或 Ubuntu 状态为 Stopped，VERSION 为 2
```

### 2.3 安装必备软件包

在 WSL 中执行（Ubuntu 22.04 / 24.04 通用）：

```bash
sudo apt update
sudo apt install -y \
  bison flex gettext texinfo libncurses5-dev libncursesw5-dev xxd \
  git gperf automake libtool build-essential genromfs \
  libgmp-dev libmpc-dev libmpfr-dev libisl-dev binutils-dev libelf-dev \
  libexpat1-dev gcc-multilib g++-multilib picocom u-boot-tools util-linux \
  dfu-util libx11-dev libxext-dev net-tools pkg-config unionfs-fuse zlib1g-dev \
  libusb-1.0-0-dev libv4l-dev libuv1-dev nasm yasm libdivsufsort-dev \
  libc++-dev libc++abi-dev libprotobuf-dev protobuf-compiler protobuf-c-compiler mtools
```

> 常见坑：
> - Ubuntu 24.04 自带 `nodejs` 是 18.x，OpenVela 编译用不到，可忽略。
> - 包名是 `pkg-config`（不是 `pkgconf`），上面命令已更正。
> - `gperf` 在第一行已包含，原指南中重复出现是冗余，已删除。
> - 不要重复执行 `apt-get install` 第二遍，会让 apt 浪费时间检查已装包。
> - `libtool` / `texinfo` / `protobuf-c-compiler` 安装后命令名分别是 `libtoolize` / `makeinfo` / `protoc-c`。

### 2.4 安装 Repo 工具

```bash
# Google 官方源（已验证可用）
curl -fsSL https://storage.googleapis.com/git-repo-downloads/repo > /usr/local/bin/repo
chmod +x /usr/local/bin/repo

# 清华镜像（路径已变更，旧 URL 404，新路径请参考 mirrors.tuna.tsinghua.edu.cn 当前说明）
# 如官方源被墙，可改用：curl -fsSL https://gerrit.googlesource.com/git-repo/+/HEAD/repo?format=TEXT | base64 -d > /usr/local/bin/repo
```

### 2.5 安装 Python 依赖（kconfiglib 等）

OpenVela 编译实际使用的是 Python 版 kconfiglib，不需要 apt 版 kconfig-frontends：

```bash
sudo apt install -y python3 python3-pip python-is-python3
# Ubuntu 24.04 需加 --break-system-packages；22.04 不需要但加上也无害
sudo pip3 install --break-system-packages -i https://pypi.tuna.tsinghua.edu.cn/simple kconfiglib pyelftools cxxfilt
```

> `pip3` 直接走 Python 官方源在国内会超时，必须用清华镜像 `-i https://pypi.tuna.tsinghua.edu.cn/simple`。

### 2.6 Ubuntu 24.04 编译 OpenVela 的额外注意

OpenVela 官方 manifest 基于 Ubuntu 22.04（GCC 11）测试，24.04 用的是 GCC 13。可能差异：

1. **更多警告**：GCC 13 默认开 `-Werror=implicit-function-declaration` 等严格检查，
   部分 OpenVela 旧代码会因未声明函数直接报错。
   临时缓解：编译前 `export CFLAGS="-Wno-error=implicit-function-declaration -Wno-error=int-conversion"`，
   或在 build.sh 出错时手动 patch 报错文件加 `#include <header.h>`。
2. **多库路径**：24.04 的 `gcc-multilib` 头文件路径略有调整，通常不影响 NuttX 编译。
3. **glibc 2.39**：某些 host 工具链接时可能找不到 `libcrypt.so`，可 `apt install libcrypt-dev`。
4. **不要降级 GCC**：网上很多教程教把 24.04 的 GCC 降到 11，OpenVela 实际并不需要，
   反而会破坏 24.04 自带包的依赖关系。

> 已验证：截至 2026-07-22，Ubuntu 24.04.1 + GCC 13.3 上可正常编译 `nsh_minidisplay` 配置。
> 编译时若遇到个别文件报错，把错误贴给对话助手排查，不要回退 GCC。

---

## 第三阶段：拉取 OpenVela 源码

> ⚠️ 前置条件：`.wslconfig` 必须配置 `networkingMode=mirrored`（见 2.2 节），
> 否则 WSL NAT 模式下访问 GitHub 会出现 `GnuTLS recv error (-110): The TLS connection was non-properly terminated`。

### 3.1 大赛参赛仓库方式（推荐）

大赛参赛者使用专属仓库的 manifest：

```bash
# 在 WSL 中创建工作目录
mkdir -p ~/openvela && cd ~/openvela

# 配置 git 身份（repo 必需）
git config --global user.name "your_name"
git config --global user.email "your_email@example.com"

# 用大赛仓库的 manifest 初始化
# 注意：--repo-url 必须指向 git 仓库地址，不能是文件下载链接
# ✅ https://mirrors.ustc.edu.cn/aosp/git-repo       （已验证可用，推荐）
# ✅ https://gerrit.googlesource.com/git-repo         （官方，需翻墙）
# ❌ https://storage.googleapis.com/git-repo-downloads/  （这是 launcher 下载链接，不是仓库）
# ❌ https://mirrors.tuna.tsinghua.edu.cn/git/git-repo/  （路径已变更，404）
repo init -u https://github.com/open-vela/contest2026_236_wuxianshanyaoqiji \
  -b dev-ai-contest-2026 -m contest2026_236_wuxianshanyaoqiji.xml \
  --repo-url=https://mirrors.ustc.edu.cn/aosp/git-repo \
  --no-clone-bundle

# 同步源码（首次 30+ 分钟，约 30GB）
repo sync -c -j8 --no-clone-bundle
```

> `--no-clone-bundle` 跳过 Google CDN bundle 加速（国内访问 googleapis 会失败）。
> 如果网络中断，可重复执行 `repo sync -c -j8 --no-clone-bundle` 增量同步。
>
> **已知问题**：sync 末尾可能报 4 个非全志平台的 LFS 仓库 checkout 失败：
> ```
> Cannot checkout prebuilts_gcc_linux_tricore
> Cannot checkout libs_sifli_sf32lb52
> Cannot checkout libs_openvela_vela
> Cannot checkout vendor_infineon_chips_aurix_illd_tc4x_Libraries
> ```
> 这些是 TriCore/Infineon/Sifli/Vela 通用库，**不影响 r528s3-gemini-s1 编译**，可忽略。

### 3.2 官方通用方式（备选）

如果大赛仓库方式有问题，可使用官方通用 manifest：

```bash
mkdir -p ~/openvela && cd ~/openvela

# GitHub HTTPS
repo init -u https://github.com/open-vela/manifests.git -b trunk -m tags/trunk-5.4.xml \
  --repo-url=https://mirrors.ustc.edu.cn/aosp/git-repo --git-lfs --no-clone-bundle

# 或 Gitee HTTPS（国内推荐）
repo init -u https://gitee.com/open-vela/manifests.git -b trunk -m tags/trunk-5.4.xml \
  --repo-url=https://mirrors.ustc.edu.cn/aosp/git-repo --git-lfs --no-clone-bundle

repo sync -c -j8 --no-clone-bundle
```

### 3.3 SDK 目录结构

同步完成后，Gemini SDK 位于 `vendor/allwinnertech/` 目录：

```
vendor/allwinnertech/
├── apps/                 # 核心应用与 Demo
├── boards/               # 板级支持包
│   └── r528/
│       └── r528s3-gemini-s1/  # 本开发板核心目录
├── chips/                # 芯片级驱动
├── lichee/               # 固件打包与产线工具
├── Make.defs             # 全局构建规则
└── Kconfig               # 全局配置入口
```

---

## 第四阶段：编译固件（2.8寸 SPI 屏）

### 4.1 编译 nsh_minidisplay 配置

`nsh_minidisplay` 是 2.8 寸 SPI 屏的配置：

```bash
cd ~/openvela

# Ubuntu 24.04 + GCC 13 兼容：放宽部分严格警告（22.04 无需）
export CFLAGS="-Wno-error=implicit-function-declaration -Wno-error=int-conversion -Wno-error=incompatible-pointer-types"
export CXXFLAGS="$CFLAGS"

# 清理（首次编译必须）
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh_minidisplay/ distclean -j8

# 编译
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh_minidisplay/ -j8
```

> 编译约 5-10 分钟，产物：
> - `nuttx/vela.bin` 7.3MB（精简运行固件）
> - `nuttx/nuttx.elf` 155MB（带调试符号）
> - `vendor/allwinnertech/lichee/board/r528s3/gemini-s1_nand/configs/nsh.fex`（rtos 固件，已自动拷贝）

> **LFS 仓库必须先装 git-lfs**：若编译时链接报 `cannot find .../armv7a_cmake/libquickapp.a` 等错误，
> 是因为 sync 时未装 git-lfs 导致 LFS 文件未下载。修复：
> ```bash
> sudo apt install -y git-lfs
> cd ~/openvela && repo forall -c "git lfs install"
> repo sync -c -j4 --no-clone-bundle vendor/openvela/boards/vela/libs
> cd vendor/openvela/boards/vela/libs && git lfs pull
> ```

### 4.2 启用 webview 组件（如需要）

如果 nsh_minidisplay 默认不包含 webview：

```bash
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh_minidisplay/ menuconfig
```

在菜单中确认：
```
Device Drivers  --->
    [*] Graphics Support
        [*] LCD support
        [*] NX Graphics Server

Application Configuration  --->
    [*] Web Browser / WebView
        [*] WebView support
```

### 4.3 打包完整 PhoenixSuit 镜像

`pack.sh` 仅内置 `r528s3-evb4` 和 `r528s3-x4b`，不支持 `gemini-s1`。
直接调用 `pack_img.sh`，并先编译 dragonsecboot 工具：

```bash
# 1. 安装依赖
sudo apt install -y busybox

# 2. 编译 dragonsecboot（GCC 13 需加 -fcommon）
cd ~/openvela/vendor/allwinnertech/lichee/brandy-2.0/tools/pack_tools/toc_tools
make clean && make -j8 CFLAGS="-fcommon -Wno-error"

# 3. 创建 pack_img.sh 期望的工具目录结构
LICHEE=~/openvela/vendor/allwinnertech/lichee
mkdir -p "$LICHEE/tools/pack/pctools/linux/dragonsecboot"
mkdir -p "$LICHEE/tools/pack/pctools/linux/mod_update"
mkdir -p "$LICHEE/tools/pack/pctools/linux/mod_update_boot0"
cp toc_tools/dragonsecboot "$LICHEE/tools/pack/pctools/linux/dragonsecboot/"

# 4. 打包
cd "$LICHEE"
export PATH="$LICHEE/tools/pack/pctools/linux/mod_update:$LICHEE/tools/pack/pctools/linux/mod_update_boot0:$LICHEE/tools/pack/pctools/linux/dragonsecboot:$PATH"
bash tools/scripts/pack_img.sh -c sun8iw20p1 -p rtos -b r528s3-gemini-s1 \
  -o nuttx -d uart0 -s none -m normal -w none -v none -i none \
  -t "$LICHEE" -f r528s3/gemini-s1_nand -g r528s3/gemini-s1_nand
```

打包完成后，PhoenixSuit 烧入镜像位于：
```
vendor/allwinnertech/lichee/out/r528s3/gemini-s1_nand/rtos_nuttx_r528s3-gemini-s1_uart0_128Mnand.img
```

> **注**：`update_boot0` / `update_uboot` 在 GCC 13 下编译失败（`-fcommon` 也无法解决全部问题），
> 但 pack_img.sh 用预编译的 dragonsecboot 即可完成打包，这两个工具不影响 NAND 镜像生成。
> 若需 NOR/spinor 镜像，可能需要单独修复这两个工具。

---

## 第五阶段：烧入固件（三确认流程）

> ⚠️ **烧入是不可逆操作，必须严格执行三确认流程！**

### 确认一：MD5 校验确认

```bash
# WSL 中计算固件 MD5
md5sum vendor/allwinnertech/lichee/out/r528s3/gemini-s1_nand/rtos_nuttx_r528s3-gemini-s1_uart0_128Mnand.img
```

确认项：
- [ ] MD5 值与编译输出日志一致
- [ ] 固件文件大小合理（约 29MB）
- [ ] 固件文件未损坏

### 确认二：FEL 模式确认

1. **断开板子电源**
2. **按住 FEL 按钮**（或设置跳线到 FEL/USB Boot 位置）
3. **连接 USB 线**到板子 USB OTG 接口
4. **接通电源**，保持 FEL 按下 2 秒后松开
5. **确认 PC 识别到 USB 设备**（设备管理器中可见）

确认项：
- [ ] FEL 按钮操作正确
- [ ] PC 设备管理器识别到 USB 设备
- [ ] 板子电源指示灯亮起

### 确认三：工具版本确认

使用全志官方工具 **PhoenixSuit**（Windows）：

1. **下载 PhoenixSuit**：
   - 渠道一：润芯微飞书知识库
   - 渠道二：https://www.aw-ol.com/downloads?cat=5 （全志开发者社区，需注册）
2. **安装 USB 驱动**：解压"全志USB烧录驱动"并安装
3. **安装 PhoenixSuit**：解压并运行
4. **选择固件**：在 PhoenixSuit 中选择 `.img` 固件文件

确认项：
- [ ] USB 驱动已安装且设备已识别
- [ ] PhoenixSuit 已安装
- [ ] 固件在工具中加载无报错

### 执行烧录

1. 在 PhoenixSuit 中确认固件路径
2. **设备下电，再上电**（触发烧录弹框）
3. 点击弹框确认进入烧录流程
4. 等待烧录完成（通常 30~90 秒）
5. **烧录成功后，关闭 PhoenixSuit 程序**
6. 板子会自动重启

> ⚠️ 烧录失败排查：
> - USB 线必须是数据线（不是充电线）
> - 尝试直连主板 USB 接口
> - 重新进入 FEL 模式重试

---

## 第六阶段：板端配置与部署

### 6.1 配置 Wi-Fi

板子启动后，通过串口终端（NSH）配置：

```bash
# 连接串口（115200）
# Windows: PuTTY/MobaXterm 连接 COM 端口
# Linux: minicom -D /dev/ttyUSB0 -b 115200

# NSH 终端中
nsh> ifconfig
nsh> wifi connect "你的WiFi名称" "你的WiFi密码"
```

### 6.2 确认 PC 网关运行

PC 上启动生产网关（已在第一阶段启动）：
- PC IP: `192.168.0.116`
- 端口: `3001`

板端测试连通性：
```bash
nsh> ping 192.168.0.116
```

### 6.3 启动 webview

```bash
nsh> webview http://192.168.0.116:3001/
# 或根据 OpenVela 版本
nsh> help    # 查看可用命令
```

### 6.4 自动启动（可选）

```bash
nsh> echo "webview http://192.168.0.116:3001/" > /data/init.d/rc.webview
nsh> chmod +x /data/init.d/rc.webview
```

---

## 第七阶段：端到端验证

### 基础连通性

| 检查项 | 方法 | 预期结果 |
|--------|------|----------|
| 板端 Wi-Fi | `nsh> ifconfig` | 有 IP 地址 |
| PC 网关 | PC 浏览器 `http://localhost:3001/api/health` | `{"success":true}` |
| 板到 PC | `nsh> ping 192.168.0.116` | 有响应 |
| webview 加载 | 屏幕显示 | 深紫蓝背景 + Live2D |
| WebSocket | 顶部状态栏 | 显示"已连接" |

### 对话功能

1. 触摸屏幕 → Live2D 眼睛跟随
2. 点击录音按钮 → 粉色脉冲 + "聆听中"
3. 停止录音 → "识别中" → "思考中" → 流式文字
4. 语音播放 → "说话中" + Live2D 嘴型同步
5. 播放结束 → 回到"待机"

### 性能指标

| 指标 | 目标 |
|------|------|
| Live2D 帧率 | ≥ 25 fps |
| 模型加载 | < 10 秒 |
| LLM 首字延迟 | < 1.5 秒 |

---

## 故障排查

### webview 白屏
1. 检查 Wi-Fi：`nsh> ifconfig`
2. 检查 PC 网关：PC 浏览器访问 `http://localhost:3001/`
3. 检查网络：`nsh> ping 192.168.0.116`
4. 检查防火墙：确保 3001 端口未被阻止
5. 检查 WebGL：Live2D 需要 WebGL 支持

### Live2D 不显示
1. 板端需访问 `cubism.live2d.com` 和 `cdn.jsdelivr.net`
2. 如板端无法访问外网 CDN，将脚本和模型下载到本地通过 PC 网关托管

### 麦克风无声音
1. 确认板载麦克风在固件中启用
2. 检查 `navigator.mediaDevices.getUserMedia` 是否可用

### WebSocket 连接失败
1. 确认 PC 网关监听 `0.0.0.0`（非仅 localhost）
2. 确认防火墙未阻止 3001 端口
3. 检查 webview WS URL 指向 PC IP

---

## 快速命令速查

```bash
# === WSL 中编译 ===
cd ~/openvela
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh_minidisplay/ distclean -j8
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh_minidisplay/ -j8

# 打包
cd vendor/allwinnertech/lichee/
source envsetup.sh
lunch_nuttx    # 选择 2
pack

# === Windows 中烧录 ===
# 1. 打开 PhoenixSuit
# 2. 选择固件 .img
# 3. 设备下电→上电→弹框确认→烧录

# === PC 网关 ===
# PowerShell
$env:NODE_ENV="production"; $env:HOST="0.0.0.0"; node --import tsx api/server.ts

# === 板端 NSH ===
nsh> ifconfig
nsh> wifi connect "SSID" "PASSWORD"
nsh> ping 192.168.0.116
nsh> webview http://192.168.0.116:3001/
```
