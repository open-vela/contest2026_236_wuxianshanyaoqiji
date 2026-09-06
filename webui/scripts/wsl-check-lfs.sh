#!/bin/bash
# 检查 armv7a_cmake 下所有 .a 文件是否真实下载（>1KB）还是 LFS 指针（<1KB）
DIR="$HOME/openvela/vendor/openvela/boards/vela/libs/armv7a_cmake"
echo "=== armv7a_cmake 下所有 .a 文件 ==="
if [ ! -d "$DIR" ]; then
  echo "目录不存在: $DIR"
  exit 1
fi

missing=0
pointer=0
ok=0
for f in libquickapp.a libquickappfeatures.a libquickapp_inspector.a libgui_wrapper.a liblibfeature.a liblibmedia.a liblibpfw.a libapps_vapp.a libapps_mediad.a libapps_mediatool.a; do
  p="$DIR/$f"
  if [ ! -f "$p" ]; then
    printf "%-30s MISSING\n" "$f"
    missing=$((missing+1))
  else
    sz=$(stat -c %s "$p")
    if [ "$sz" -lt 1000 ]; then
      printf "%-30s %8d bytes  <-- LFS 指针未下载\n" "$f" "$sz"
      pointer=$((pointer+1))
    else
      printf "%-30s %8d bytes  OK\n" "$f" "$sz"
      ok=$((ok+1))
    fi
  fi
done

echo
echo "总结: OK=$ok  LFS指针未下载=$pointer  MISSING=$missing"

# 对 LFS 指针文件单独 pull
if [ "$pointer" -gt 0 ] || [ "$missing" -gt 0 ]; then
  echo
  echo "=== 单独执行 git lfs pull ==="
  cd "$DIR/.." || exit 1
  git lfs pull 2>&1 | tail -20
  echo
  echo "=== 再次检查 ==="
  for f in libquickapp.a libquickappfeatures.a libquickapp_inspector.a libgui_wrapper.a; do
    p="$DIR/$f"
    if [ -f "$p" ]; then
      sz=$(stat -c %s "$p")
      printf "%-30s %8d bytes\n" "$f" "$sz"
    else
      printf "%-30s MISSING\n" "$f"
    fi
  done
fi
