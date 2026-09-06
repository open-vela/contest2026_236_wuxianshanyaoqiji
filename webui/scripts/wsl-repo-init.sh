#!/bin/bash
# 检查可用的 git-repo 镜像
set -e

URLS=(
  "https://mirrors.tuna.tsinghua.edu.cn/git/git-repo.git"
  "https://mirrors.ustc.edu.cn/aosp/git-repo"
  "https://mirrors.huaweicloud.com/git-repo"
  "https://gerrit.googlesource.com/git-repo"
)

echo "=== 测试 git-repo 镜像连通性 ==="
WORKING=""
for u in "${URLS[@]}"; do
  echo "--- $u ---"
  if git ls-remote "$u" HEAD >/dev/null 2>&1; then
    echo "OK"
    WORKING="$u"
    break
  else
    echo "FAIL: $(git ls-remote "$u" HEAD 2>&1 | head -1)"
  fi
done

if [ -z "$WORKING" ]; then
  echo "!!! 所有镜像都不通"
  exit 1
fi

echo
echo "=== 使用 $WORKING 作为 repo-url ==="
cd ~/openvela || { echo "openvela 目录不存在"; exit 1; }
rm -rf .repo

# 配置 git 走 https 不走代理
git config --global --unset http.proxy 2>/dev/null || true
git config --global --unset https.proxy 2>/dev/null || true
git config --global user.name "rivotek" 2>/dev/null || true
git config --global user.email "rivotek@local" 2>/dev/null || true

# 初始化大赛仓库的 manifest
repo init \
  -u https://github.com/open-vela/contest2026_236_wuxianshanyaoqiji \
  -b dev-ai-contest-2026 \
  -m contest2026_236_wuxianshanyaoqiji.xml \
  --repo-url="$WORKING" \
  --no-clone-bundle

echo
echo "=== repo init 完成，开始 sync ==="
repo sync -c -j8 --no-clone-bundle
