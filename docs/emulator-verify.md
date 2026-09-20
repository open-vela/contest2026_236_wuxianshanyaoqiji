> 历史记录，不作为当前 Gemini-S1 固件构建入口。当前成果与复现流程见项目 docs/build-pack-guide.md；旧配置及脚本已停用。

# openvela 模拟器验证清单（qemu-armeabi-v7a-ap）

> 目标：验证「先编译、再启动 QEMU 模拟器跑 NSH」，确认环境与固件链路可用。
> 结论依据：本文件所有路径/配置均已在 WSL `~/openvela` 中实测确认。
> 编写时间：2026-09-13

---

## 一、选哪个模拟器目标（关键结论）

`vendor/openvela/boards/vela/configs/` 下有 12 个配置，但**只有一个应该先试**：

| 配置 | board name | 预编译库路径 | 依赖 QuickApp | 能否编译 |
| ---- | ---------- | ------------ | ------------- | -------- |
| `goldfish-armeabi-v7a-ap` | `armv7a` | `libs/armv7a_cmake/` ❌ 不存在 | 有 | ❌ 必然链接失败 |
| `goldfish-armeabi-v7a-ap-citest` | — | — | 无 | 待测 |
| **`qemu-armeabi-v7a-ap`** | **`ap`** | **`libs/ap_cmake/` ✅ 存在** | **无** | **✅ 推荐** |
| `qemu-arm64-v8a-ap` | `ap` | `libs/ap_cmake/` ✅ | 无 | ✅ 可试（ARM64） |
| `goldfish-x86_64-ap` | `vela` | `libs/vela_cmake/` ❌ | 有 | ❌ |
| `qemu-arm64-v8a-server` 等 | — | — | 无 | 非 AP 形态 |

### 为什么是这个（根因）

`vendor/openvela/boards/vela/CMakeLists.txt`：

```cmake
set(PREBUILT_LIB_PATH ".../libs/${CONFIG_ARCH_BOARD_CUSTOM_NAME}_cmake")
file(GLOB EXTRA_LIBS ".../libs/${CONFIG_ARCH_BOARD_CUSTOM_NAME}/*.a")
```

库目录名由 **defconfig 里的 `CONFIG_ARCH_BOARD_CUSTOM_NAME`** 动态拼接：

- `qemu-armeabi-v7a-ap/defconfig` → `CONFIG_ARCH_BOARD_CUSTOM_NAME="ap"` → 找 `libs/ap_cmake/`
- 实测 `libs/` 下存在：`ap_cmake/libapps_vapp.a`（5.8 MB）✅ 命中
- `goldfish-armeabi-v7a-ap/defconfig` → `"armv7a"` → 找 `libs/armv7a_cmake/` → **不存在** ❌

> 这解释了 `docs/development-notes.md` 里记录的「armv7a_cmake 预编译库缺失」问题。
> 该问题**只影响板端与 goldfish 目标**；qemu 系（board name = `ap`）不受影响，无需关闭 MEDIA/QUICKAPP。
> 另外 qemu-* 系列 defconfig 中 **完全没有** VAPP/QUICKAPP 引用（grep 计数 = 0），本就不依赖 QuickApp 运行时。

### 架构匹配性

`qemu-armeabi-v7a-ap` 使用 `CONFIG_ARCH_CHIP_QEMU_CORTEXA7`，与目标硬件 R528S3 的 **Cortex-A7 同核**，架构层面可比性最好。

---

## 二、构建产物与流程（读自 CMakeLists.txt）

```
nuttx（ELF）
  └─ gen_images  → vela_system.bin（genromfs 打包 prebuilts/system）
                 → vela_data.bin（256MB FAT，含 prebuilts/data）
  └─ nuttx_post_build（CONFIG_VELA_AP=y 时）
                 → vela_ap.elf / vela_ap.bin
```

- QEMU 参数（`CONFIG_ARCH_ARMV7A` 分支，已写入 `qemu_args.txt`）：
  `-cpu cortex-a7 -nographic -machine virt,virtualization=off,gic-version=2 ...`
- 生成 `config.ini` / `advancedFeatures.ini` 供模拟器使用。

**依赖工具**：`genromfs`、`mkfs.fat`（dosfstools）、`mcopy`（mtools）—— 缺失会导致 `gen_images` 失败。

---

## 三、执行步骤

在 WSL 中（非当前沙箱，`wsl.exe` 被安全策略拦截）：

```bash
cd ~/openvela
```

### 3.0 前置检查（先跑这个，成本最低）

```bash
which genromfs mkfs.fat mcopy
ls prebuilts/emulator/linux-x86_64/qemu/
```

三个工具 + QEMU 都要有。缺则：

```bash
sudo apt-get install -y genromfs dosfstools mtools
```

### 3.1 编译

```bash
./build.sh vendor/openvela/boards/vela/configs/qemu-armeabi-v7a-ap/ -j8
```

**成功标志**（对照板端经验，注意别被 exit 0 误导）：

```
Generating: nuttx.bin
```

并产出：

```
build/.../vela_ap.elf
build/.../vela_ap.bin
build/.../vela_system.bin
build/.../vela_data.bin
```

> ⚠️ **重要**：后台任务通知的 `exit 0` 曾多次误报（见 development-notes 8.2 节）。
> 必须实际核验上述文件是否生成，以及日志尾部有无 `ld: cannot find`。

### 3.2 启动模拟器

```bash
# 先看用法（emulator.sh 在 Windows UNC 下元数据不可读，需在 WSL 内确认）
./emulator.sh -h
# 或直接查看脚本头部
head -60 emulator.sh
```

按官方 `build_qemu.config` 的命名，目标名应为 `qemu-armeabi-v7a-ap`，推测用法形如：

```bash
./emulator.sh qemu-armeabi-v7a-ap
```

> ⚠️ 参数确切形式未验证（`emulator.sh` 在 UNC 路径下 `cat`/`grep` 均报
> `Input/output error`，元数据也显示为 `-?????????`）。请以 `-h` 输出为准。

### 3.3 判定「可用」的标准

1. QEMU 进程正常启动，无 `qemu: could not load kernel` 之类错误
2. 串口（`-nographic`，即当前终端）出现 **NSH 提示符** `nsh>`
3. 能执行基本命令：`help`、`ls /`、`ps`、`free`
4. 无 kernel panic / hard fault / stack dump
5. 若启用了 LVGL（`CONFIG_GRAPHICS_LVGL=y`）：确认图形初始化无报错

---

## 四、可能的坑（已知）

| 现象 | 原因 | 对策 |
| ---- | ---- | ---- |
| `ld: cannot find .../libs/armv7a_cmake/*.a` | 选错目标（用了 goldfish-armeabi-v7a-ap） | 改用 `qemu-armeabi-v7a-ap` |
| `genromfs: command not found` | 缺 romfs 工具 | `apt install genromfs` |
| `mkfs.fat`/`mcopy` 缺失 | 缺 dosfstools/mtools | `apt install dosfstools mtools` |
| 编译「成功」但无产物 | 后台 exit 0 误报 | 直接核验 `vela_ap.elf` 等文件 |
| QEMU 启动失败 | 参数/内核路径不对 | 检查 `qemu_args.txt` 与 `emulator.sh` 传参 |

---

## 四·补、2026-09-14 实测结果（已跑通）

| 项目 | 结论 |
| ---- | ---- |
| 编译 | ✅ `./build.sh vendor/openvela/boards/vela/configs/qemu-armeabi-v7a-ap/ -j8` 成功，产物在 `nuttx/`（vela_ap.elf/bin、vela_system.bin、vela_data.bin、nuttx.bin） |
| 宿主依赖 | 需补装（以 root 进 WSL 免密安装）：`libc++abi-dev`（hidl-gen/aidl 需要，官方文档已要求但本机缺失）、`libasound2t64 libpulse0`（qemu-system-arm 运行需要） |
| 启动 | `emulator.sh` 不可直接使用：① `.config` 里是 `CONFIG_ARCH_CHIP_QEMU_ARM=y`，而脚本精确匹配 `CONFIG_ARCH_CHIP_QEMU=y` 落空；② `qemu_args.txt` 因 `vendor/openvela/boards/vela/CMakeLists.txt:108` 把 `qemu_args` 误写成 `qemu_args_str` 从不生成。**改用直连**：`qemu-system-arm -L prebuilts/qemu/linux-x86_64/share/qemu -kernel nuttx/nuttx $(cat nuttx/qemu_args.txt)`（qemu_args.txt 已按 CMakeLists ARMv7A 分支手动补写） |
| 验证 | ✅ 启动到 `ap>` 提示符（非 `nsh>`）；`ls /`、`ps`（servicemanager 运行中）、`free` 均正常；无 panic/Hard Fault |
| 已知差异 | `/data` 挂载失败回退 tmpfs（qemu 参数未带 `-drive` 挂 vela_data.bin，属预期）；`kvdbd: command not found`（init 脚本引用了未编译组件）；LVGL 图形无报错 |
| 团队 app | `hello_app` 仍为模板（`CONFIG_LVX_USE_DEMO_CONTEST2026_000_HELLO_APP` 默认 n 未启用），未编入镜像 |

> 一键复跑脚本：`webui/scripts/qemu_run.sh`（直连 qemu-system-arm，延时注入 help/ls/ps/free 并输出检查点）。

## 五、与板端的关系

| | 板端（真机） | 模拟器 |
| --- | --- | --- |
| 目标 | `r528s3-gemini-s1/configs/nsh_minidisplay` | `vendor/openvela/boards/vela/configs/qemu-armeabi-v7a-ap` |
| 屏幕 | ILI9341 SPI 2.8" 320×480 | 虚拟 LCD（config.ini 1280×720） |
| QuickApp | 已关闭（库缺失） | 本就不依赖 |
| 用途 | 最终交付 | **逻辑/应用层快速验证** |

模拟器验证通过 ≠ 真机可用（外设、屏幕、NFC 均无法覆盖），但可先排掉应用层与启动链路的低级问题。
