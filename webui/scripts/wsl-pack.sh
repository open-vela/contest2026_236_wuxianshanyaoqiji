#!/bin/bash
# 编译 brandy pack 工具并打包完整 PhoenixSuit 镜像
# GCC 13 兼容：加 -fcommon 允许全局变量重复定义（旧 SDK 代码风格）
set -e
export CFLAGS="-fcommon -Wno-error"
export CXXFLAGS="-fcommon -Wno-error"

LICHEE=/root/openvela/vendor/allwinnertech/lichee
cd "$LICHEE/brandy-2.0/tools/pack_tools" || exit 1

echo "=== 编译 dragonsecboot ==="
cd toc_tools && make clean 2>/dev/null; make -j8 CFLAGS="$CFLAGS" 2>&1 | tail -8
cd ..

echo "=== 编译 update_boot0 ==="
cd update_boot0 && make clean 2>/dev/null; make -j8 CFLAGS="$CFLAGS" 2>&1 | tail -5
cd ..

echo "=== 编译 update_uboot ==="
cd update_uboot && make clean 2>/dev/null; make -j8 CFLAGS="$CFLAGS" 2>&1 | tail -5
cd ..

echo "=== 编译 update_uboot_v2 ==="
cd update_uboot_v2 && make clean 2>/dev/null; make -j8 CFLAGS="$CFLAGS" 2>&1 | tail -5
cd ..

echo
echo "=== 工具就位检查 ==="
find "$LICHEE/brandy-2.0/tools/pack_tools" -maxdepth 3 -type f -executable \( -name "dragonsecboot" -o -name "update_boot0" -o -name "update_uboot" \) 2>/dev/null

echo
echo "=== 创建 pctools 目录结构（pack_img.sh 期望的路径）==="
mkdir -p "$LICHEE/tools/pack/pctools/linux/mod_update"
mkdir -p "$LICHEE/tools/pack/pctools/linux/mod_update_boot0"
mkdir -p "$LICHEE/tools/pack/pctools/linux/mod_pubkey"
mkdir -p "$LICHEE/tools/pack/pctools/linux/dragonsecboot"
cp -v toc_tools/dragonsecboot "$LICHEE/tools/pack/pctools/linux/dragonsecboot/" 2>/dev/null || echo "dragonsecboot 拷贝跳过"
cp -v update_boot0/update_boot0 "$LICHEE/tools/pack/pctools/linux/mod_update_boot0/" 2>/dev/null || echo "update_boot0 拷贝跳过"
cp -v update_uboot/update_uboot "$LICHEE/tools/pack/pctools/linux/mod_update/" 2>/dev/null || echo "update_uboot 拷贝跳过"

echo
echo "=== 打包 gemini-s1_nand 镜像 ==="
cd "$LICHEE"
export PATH="$LICHEE/tools/pack/pctools/linux/mod_update:$LICHEE/tools/pack/pctools/linux/mod_update_boot0:$LICHEE/tools/pack/pctools/linux/dragonsecboot:$PATH"
RTOS_TOP="$LICHEE"
bash tools/scripts/pack_img.sh -c sun8iw20p1 -p rtos -b r528s3-gemini-s1 -o nuttx -d uart0 -s none -m normal -w none -v none -i none -t "$RTOS_TOP" -f r528s3/gemini-s1_nand -g r528s3/gemini-s1_nand 2>&1 | tail -30

echo
echo "=== 打包产物 ==="
find "$LICHEE/out/r528s3/gemini-s1_nand/" -name "*.img" -o -name "sunxi*.fex" -o -name "nsh*.fex" 2>/dev/null | xargs ls -la 2>/dev/null | head -20
