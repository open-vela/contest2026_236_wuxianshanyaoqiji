#!/bin/bash
# WSL 编译依赖完整性检查
echo "=== 关键工具检查 ==="
for t in gcc g++ make bison flex gperf makeinfo xxd git automake libtoolize genromfs picocom dfu-util pkg-config nasm yasm protoc protoc-c mtools python3 pip3 repo curl wget; do
  printf '%-15s -> ' "$t"
  command -v "$t" || echo MISSING
done

echo
echo "=== GCC/g++ 版本 ==="
gcc --version | head -1
g++ --version | head -1

echo
echo "=== Python 包 ==="
python3 -c "import kconfiglib, elftools, cxxfilt; print('kconfiglib/elftools/cxxfilt OK')"

echo
echo "=== 多库/multilib ==="
dpkg -l | grep -E 'gcc-multilib|g\+\+-multilib|libncursesw5-dev' | awk '{print $2, $3}'

echo
echo "=== 系统 ==="
cat /etc/os-release | grep PRETTY_NAME
uname -a
