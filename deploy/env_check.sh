#!/usr/bin/env bash
# ==============================================================================
# OE 库服务器环境自检 —— 部署前先跑这个，按输出逐项补齐
# 用法: bash deploy/env_check.sh
# ==============================================================================
set -u

REPO="${REPO:-$HOME/ucars}"
# Python 解释器：改成服务器上实际路径
PY="${PY:-python3}"
# 境外服务器留空（直连）；境内服务器填 http://host:port
PROXY="${ENRICH_PROXY:-}"

echo "===== OE 库发布服务器环境自检 $(date '+%F %T') ====="
echo "REPO=$REPO  PY=$PY  PROXY=${PROXY:-(直连)}"
echo

pass=0; fail=0
chk() { # chk <描述> <结果: 0/1> [提示]
  if [ "$2" -eq 0 ]; then echo "  [OK]   $1"; pass=$((pass+1));
  else echo "  [FAIL] $1"; [ -n "${3:-}" ] && echo "         -> $3"; fail=$((fail+1)); fi
}

# ---------- 1. 基础环境 ----------
echo "--- 1. 基础环境 ---"
$PY --version >/dev/null 2>&1
chk "Python 可用 ($($PY --version 2>&1 | head -1))" $? "先装 Python 3.9+"

$PY -c "import requests" >/dev/null 2>&1
chk "requests 已安装" $? "$PY -m pip install requests"

command -v git >/dev/null 2>&1
chk "git 已安装" $? "apt-get install -y git"

[ -d "$REPO/.workbuddy/scripts" ]
chk ".workbuddy/scripts 存在" $? "见 README：需从工作站同步 .workbuddy 目录（它不在 git 里）"

[ -f "$REPO/.workbuddy/data/oe-master-db.json" ]
chk "母库 oe-master-db.json 存在（约 70MB）" $? "同上，一次性同步"

echo

# ---------- 2. 网络连通性 ----------
echo "--- 2. 网络连通性（决定是否要配代理）---"
curlit() { # url
  if [ -n "$PROXY" ]; then curl -s -o /dev/null -w "%{http_code}" --max-time 20 -x "$PROXY" -A "Mozilla/5.0" "$1";
  else curl -s -o /dev/null -w "%{http_code}" --max-time 20 -A "Mozilla/5.0" "$1"; fi
}

code=$(curlit "https://www.hyundaipartsdeal.com/genuine/hyundai-cover-rr-seat-mtg~89137-2e001-z9.html")
[ "$code" = "200" ]
chk "数据源 hyundaipartsdeal 可达 (HTTP $code)" $? "境内服务器需配代理，export ENRICH_PROXY=http://host:port"

code=$(curlit "https://api.indexnow.org/")
[ "$code" != "000" ]
chk "IndexNow 端点可达 (HTTP $code)" $? "不推 IndexNow 也能跑，仅收录加速变慢"

code=$(curlit "https://api.github.com")
[ "$code" != "000" ]
chk "GitHub API 可达 (HTTP $code)" $? "推送会失败；境内服务器需配 git http.proxy"

code=$(curlit "https://searchconsole.googleapis.com/\$discovery/rest")
if [ "$code" = "200" ]; then
  echo "  [INFO] GSC API 可达 —— 本服务器可兼任周测/周报"
else
  echo "  [INFO] GSC API 不可达 (HTTP $code) —— GSC 相关任务留在本机跑，服务器只做补强+发布"
fi
echo

# ---------- 3. 推送能力实测 ----------
echo "--- 3. git 推送能力 ---"
if [ -d "$REPO/.git" ]; then
  timeout 40 git -C "$REPO" ls-remote origin >/dev/null 2>&1
  chk "git ls-remote origin 通" $? "remote URL 内嵌 PAT 是否有效？git 代理是否配置？"
  # 关键：credential helper 会让 push 挂起，必须绕过
  echo "  [INFO] 推送务必用: git -c credential.helper= push origin main"
else
  echo "  [SKIP] $REPO 不是 git 仓库"
fi
echo

# ---------- 4. 磁盘 ----------
echo "--- 4. 磁盘 ---"
avail=$(df -Pm "$REPO" 2>/dev/null | awk 'NR==2{print $4}')
if [ -n "$avail" ]; then
  if [ "$avail" -gt 3000 ]; then echo "  [OK]   可用空间 ${avail} MB"; pass=$((pass+1));
  else echo "  [WARN] 可用空间仅 ${avail} MB，OE 页每千页约 100-200MB"; fail=$((fail+1)); fi
fi
echo

echo "===== 汇总: $pass 通过 / $fail 待处理 ====="
echo "全部通过后，再按 README 配置 crontab。"
