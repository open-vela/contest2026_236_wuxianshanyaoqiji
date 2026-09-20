# Gemini-S1 2.8 寸 SPI 屏：固定构建与打包流程

## 当前双硬件版（2026-09-20）

当前 Gemini 源码版本为 v0.4.0，包含分层角色、ENTER、阿里语音和局域网联动。当前累计资源准备入口为 `tools/prepare_layered_ui.py`，它串联 sprite、portrait、语音等准备步骤。固定版本官方树首次运行 `prepare_official_chat.py` 与 `packages/ai_agent/fix_gemini_s1.sh` 后，运行 `python3 /path/to/contest/tools/prepare_layered_ui.py "$PWD"`，再按下文执行官方 build/pack；不要把旧的冻结镜像当作当前代码构建结果。

当前应用源码随准备脚本复制，包含 qiji_duet；16 个分层和 8 个特殊动作资源按 manifest 校验。双机编译记录见 `firmware/duet-20260920`，后续 Passport 源码见 `app/passport_companion`。这些目录在 Git 中仅保存构建元数据、配置与哈希，IMG/ELF 和本地调试包不提交，SHA256SUMS 中未入仓的文件属于本地完整归档。历史 source 子目录只属于对应旧版本，不是当前源码。

系统关系、电脑服务与凭据配置见 [架构与运行](contest/架构与运行.md) 和 [Passport 指南](passport-companion.zh_CN.md)。当前设备成功证据与未解决问题见 [验收清单](contest/验收与问题清单.md)。以下保留历史版本构建说明。

## 当前图标与统一间距候选版（v0.3.1）

当前入口是 `tools/prepare_sprite_ui.py`，成果目录为 `firmware/icon-ui-20260920`。它继承竖屏、实体 ENTER、时间/版本及音频修复，包含 8 种图片动作、播放期间文字滚动，右下角采用无文字麦克风/停止图标，卡片与文本框使用统一间距和同心圆角。先准备齐 assets/kotone-v1/bin 下的全部图片，缺图时不能发布。下方“对话包”一节保留的是最初亮屏版本的历史流程，不能替代当前累计准备步骤。

完成下方固定版本源码同步后，在干净官方树根目录依次运行：

```sh
python3 /path/to/contest/tools/prepare_official_chat.py "$PWD"
bash packages/ai_agent/fix_gemini_s1.sh
python3 /path/to/contest/tools/prepare_sprite_ui.py "$PWD"
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/qiji_chat/ -j4
source build/envsetup.sh
cd vendor/allwinnertech/lichee
source envsetup.sh
lunch_nuttx r528s3-gemini-s1
pack
```

官方音频补丁仅在干净树应用一次。准备脚本已串联累计修复，不要再叠加冻结目录内的累计 patch。最终镜像仍须运行下方验证器核验。通用镜像不预置 Wi-Fi 密码或云端 Key；烧录后通过配置工具设置。

当前检查与验收边界见 [图标与间距说明](icon-ui-20260920.md)。最新版板端图像、滚动、ENTER 操作和多轮语音尚待验收。预提交不代表最终参赛放行。

## 最初亮屏版本记录

对应 2026-09-19 `qiji-chat.img`，用户确认亮屏及基本文本对话可用，语音未成功。
成果目录：`firmware/official-clean-20260919`，保存配置、ELF、源码提交号、补丁及日志。

## 源码与环境

官方依据：

- [BSP 构建说明](https://github.com/open-vela/vendor_allwinnertech/blob/1676386193f0e710121e710935f1757c0f34b662/README)
- [AI Agent 说明](https://github.com/open-vela/packages_ai_agent/blob/e65550f18759f086d7f544edcf17d1e31223244f/defconfigs/gemini-s1/README.md)
- [Ubuntu 环境说明](https://github.com/open-vela/docs/blob/cb0389919ea4fc86774702fb36c08ee9b1366e6c/zh-cn/quickstart/openvela_ubuntu_quick_start.md)

官方要求 Ubuntu 22.04、至少 16 GB 内存和 40 GB 可用空间，不支持 WSL/Docker。本次实际构建环境为 WSL2 / Ubuntu 24.04、ARM GCC 13.4.0；未在 Ubuntu 22.04 重建。

使用独立官方树，不能复用旧的修改过的 `~/openvela`。归档锁文件只包含本次实际检出的仓库，版本同时保存于 `gemini-official-provenance.json`：

```sh
mkdir openvela-release
cd openvela-release
repo init -u https://github.com/open-vela/manifests -b dev-ai-contest-2026 --git-lfs
cp /path/to/contest/firmware/official-clean-20260919/source-lock.xml .repo/manifests/qiji-release.xml
repo init -m qiji-release.xml
repo sync -c -j4
git -C vendor/openvela/boards/vela/libs lfs pull --include='armv7a_cmake/*'
```

不要把 LFS 指针当作库。本次 `libquickapp.a` SHA-256 为 `34d2aad207edeccfc795b1fb7e08f329ab84c4f59eabdbd10677f0333d804768`。

## 对话包

在干净源码树根目录运行，替换项目路径：

```sh
python3 /path/to/contest/tools/prepare_official_chat.py "$PWD"
bash packages/ai_agent/fix_gemini_s1.sh
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/qiji_chat/ -j4
source build/envsetup.sh
cd vendor/allwinnertech/lichee
source envsetup.sh
lunch_nuttx r528s3-gemini-s1
pack
```

音频补丁仅在干净树应用一次，核对三个补丁成功。准备脚本安装应用、自启及 Agent 就绪通知；官方音频脚本安装音频修复及资源。归档补丁供审计，不能在上述步骤后重复叠加。

`chat.config` 是实际构建配置，`qiji-chat.defconfig` 是生成配置。保持 `LCD`、`LCD_DEV`，不启用 `LCD_FRAMEBUFFER` / `LCD_EXTERNINIT`。启用媒体服务、`MBEDTLS_NET_C`、`PIPES`、`SYSTEM_POPEN`。关闭 QuickApp 是为使用已打补丁的媒体源码，避免 BSP 强制链接预编译媒体实现；不能关闭媒体功能代替修复。

## 官方桌面基线

另用一份干净树，不能复用已打对话补丁的树并称为原样基线：

```sh
./build.sh vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh_minidisplay/ -j4
source build/envsetup.sh
cd vendor/allwinnertech/lichee
source envsetup.sh
lunch_nuttx r528s3-gemini-s1
pack
```

## 打包核验

输出为 `lichee/out/r528s3/gemini-s1_nand/rtos_nuttx_r528s3-gemini-s1_uart0_128Mnand.img`。
从输出目录找到同时含 `boot0_nand.fex`、`fes1.fex`、`nsh.fex`、`res.fex` 等的组件目录：

```sh
python3 /path/to/contest/tools/verify_official_image.py /path/to/components /path/to/image.img > verification.json
sha256sum /path/to/image.img
```

核验工具检查六个组件匹配、NAND/FES 启动块校验和内核分区上限，不替代真机验收。本次 pack 在 Dragon 成功后因末尾可选 hook 检查返回 1；不可忽略其他非零退出，需检查完整日志和新镜像。详见审计记录。

用 PhoenixSuit 烧录完整 `.img`，完成后关闭 PhoenixSuit。裸 `vela.bin` 不是完整镜像。不从旧镜像抽取启动组件，不修改 DDR 或扩大 sst 分区。

重建可能含时间戳差异，不承诺哈希逐字节复现；既有成果以归档镜像和 SHA-256 为准。设备配置见 `app/gemini_chat_minimal/README.md`。保留本次可用包后再继续排查语音。

准备脚本已固化为安装本次成功构建经 savedefconfig 规范化的 qiji-chat.defconfig，并校验 BSP / AI Agent 提交号；不再随分支更新重新生成配置。
