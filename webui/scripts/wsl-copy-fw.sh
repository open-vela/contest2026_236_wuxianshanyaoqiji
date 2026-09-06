#!/bin/bash
# 拷贝固件产物到 Windows 可访问目录
set -e
SRC=~/openvela
DST=/mnt/e/Project/website/rivotek/firmware
mkdir -p "$DST"

echo "=== 拷贝固件到 $DST ==="
cp -v "$SRC/nuttx/vela.bin" "$DST/vela.bin"
cp -v "$SRC/nuttx/nuttx.elf" "$DST/nuttx.elf"
cp -v "$SRC/nuttx/nuttx.bin" "$DST/nuttx.bin"
cp -v "$SRC/vendor/allwinnertech/lichee/board/r528s3/gemini-s1_nand/configs/nsh.fex" "$DST/nsh.fex"
cp -v "$SRC/vendor/allwinnertech/lichee/board/r528s3/gemini-s1_nand/configs/toc1.fex" "$DST/toc1.fex"
cp -v "$SRC/vendor/allwinnertech/lichee/board/r528s3/gemini-s1_nand/configs/toc0.fex" "$DST/toc0.fex"
cp -v "$SRC/vendor/allwinnertech/lichee/board/r528s3/gemini-s1_nand/configs/sys_config.fex" "$DST/sys_config.fex"

echo
echo "=== 最终产物 ==="
ls -la "$DST"
echo
echo "=== MD5 校验（烧入三确认之 MD5 校验）==="
cd "$DST" && md5sum vela.bin nsh.fex toc1.fex toc0.fex
