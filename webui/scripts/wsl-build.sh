#!/bin/bash
# 编译 nsh_minidisplay 固件（2.8寸 SPI 屏）
set -e

cd ~/openvela || { echo "openvela 目录不存在"; exit 1; }

# Ubuntu 24.04 + GCC 13 兼容性：放宽部分严格警告
export CFLAGS="-Wno-error=implicit-function-declaration -Wno-error=int-conversion -Wno-error=incompatible-pointer-types"
export CXXFLAGS="$CFLAGS"

CONFIG=vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh_minidisplay

echo "=== 阶段1: distclean ==="
./build.sh "$CONFIG" distclean -j8 2>&1 | tail -30

echo
echo "=== 阶段2: build ==="
./build.sh "$CONFIG" -j8 2>&1 | tail -80

echo
echo "=== 编译产物 ==="
find vendor/allwinnertech/boards/r528/r528s3-gemini-s1/ -name "*.bin" -o -name "*.elf" 2>/dev/null | head -20
ls -la vendor/allwinnertech/boards/r528/r528s3-gemini-s1/configs/nsh_minidisplay/out/ 2>/dev/null || echo "(out 目录未生成)"

echo
echo "=== 编译完成 ==="
