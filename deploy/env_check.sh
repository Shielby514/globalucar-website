#!/usr/bin/env bash
# ==============================================================================
# OE 库发布服务器 · 环境自检（境内局域网专用版）
#
# 用法:
#   REPO=~/ucars bash deploy/env_check.sh
#   ENRICH_PROXY=http://10.0.0.5:8080 GIT_PROXY=http://10.0.0.5:8080 \
#     REPO=~/ucars bash deploy/env_check.sh
#
# 设计要点：境内公司局域网和境外 VPS 的故障模式完全不同。
# 境内最常见的是「能上网但不出境」「代理只放行 80/443」「域名白名单」，
# 所以这里对每个外站点分别测「直连」和「走代理」，把结论直接给出来。
# ==============================================================================
set -u

REPO="${REPO:-$HOME/ucars}"
PY="${PY:-python3}"
ENRICH_PROXY="${ENRICH_PROXY:-}"
GIT_PROXY="${GIT_PROXY:-}"

echo "===== OE 发布服务器环境自检 $(date '+%F %T %Z') ====="
echo "REPO=$REPO"
echo "PY=$PY"
echo "ENRICH_PROXY=${ENRICH_PROXY:-(未设置)}"
echo "GIT_PROXY=${GIT_PROXY:-(未设置)}"
echo

pass=0; warn=0; fail=0
ok()   { echo "  [OK]   $1"; pass=$((pass+1)); }
bad()  { echo "  [FAIL] $1"; [ -n "${2:-}" ] && echo "         -> $2"; fail=$((fail+1)); }
warn_(){ echo "  [WARN] $1"; [ -n "${2:-}" ] && echo "         -> $2"; warn=$((warn+1)); }
info() { echo "  [INFO] $1"; }

# 数据源有 UA 反爬：短 UA "Mozilla/5.0" 会被判 403，必须用完整浏览器 UA，
# 否则自检会误报"数据源不可达"，让人白折腾代理。
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 测一个 URL，返回 HTTP 码；走不走代理由第二个参数决定
probe() { # probe <url> <proxy|direct>
  local url="$1" mode="${2:-direct}"
  if [ "$mode" = "direct" ]; then
    curl -s -o /dev/null -w "%{http_code}" --max-time 20 -A "$UA" "$url" 2>/dev/null
  else
    curl -s -o /dev/null -w "%{http_code}" --max-time 20 -x "$mode" -A "$UA" "$url" 2>/dev/null
  fi
}

# ============================================================ 1. 基础环境
echo "--- 1. 基础环境 ---"
$PY --version >/dev/null 2>&1 && ok "Python 可用 ($($PY --version 2>&1 | head -1))" \
  || bad "Python 不可用" "apt-get install -y python3"

$PY -c "import requests" >/dev/null 2>&1 && ok "requests 已安装" \
  || bad "requests 缺失" "$PY -m pip install requests"

command -v git >/dev/null 2>&1 && ok "git 已安装 ($(git --version | awk '{print $3}'))" \
  || bad "git 未安装" "apt-get install -y git"

command -v curl >/dev/null 2>&1 && ok "curl 已安装" || bad "curl 未安装" "apt-get install -y curl"

if command -v crontab >/dev/null 2>&1; then
  ok "cron 客户端存在"
elif [ "$(uname -s)" = "Linux" ]; then
  bad "无 crontab" "apt-get install -y cron"
else
  info "当前不是 Linux（$(uname -s)），跳过 cron 检查 —— 本机只做测试，正式运行在 Linux 服务器"
fi

if command -v systemctl >/dev/null 2>&1; then
  if systemctl is-active --quiet cron 2>/dev/null || systemctl is-active --quiet crond 2>/dev/null; then
    ok "cron 服务运行中"
  else
    bad "cron 服务未运行" "systemctl enable --now cron（否则定时任务根本不会触发）"
  fi
fi

[ -d "$REPO/.workbuddy/scripts" ] && ok ".workbuddy/scripts 存在" \
  || bad ".workbuddy/scripts 缺失" "见 README 步骤 3：.workbuddy 不在 git 里，需单独同步"

[ -f "$REPO/.workbuddy/data/oe-master-db.json" ] \
  && ok "母库存在 ($(du -m "$REPO/.workbuddy/data/oe-master-db.json" 2>/dev/null | cut -f1) MB)" \
  || bad "母库缺失" "同上，一次性同步 ~70MB"

if [ -f "$REPO/.workbuddy/data/oe-enriched.jsonl" ]; then
  info "补强已有 $(wc -l < "$REPO/.workbuddy/data/oe-enriched.jsonl") 条"
fi

# 时间同步：证书校验与 cron 都依赖准确时间，境内内网机器常长期漂移
chrony_sync=0
command -v timedatectl >/dev/null 2>&1 && timedatectl status 2>/dev/null | grep -qi "synchronized: yes" && chrony_sync=1
[ "$chrony_sync" -eq 1 ] && ok "系统时间已同步 NTP" \
  || warn_ "系统时间可能未同步" "时间漂移会让 HTTPS 证书校验失败；timedatectl set-ntp true"
echo

# ============================================================ 2. 出口连通性
echo "--- 2. 出口连通性（境内关键项）---"
echo "    先测直连，再测代理。判定标准：数据源要 200，GitHub 要 401/200 都算通。"

DATASRC="https://www.hyundaipartsdeal.com/genuine/hyundai-cover-rr-seat-mtg~89137-2e001-z9.html"

d_direct=$(probe "$DATASRC" direct)
if [ "$d_direct" = "200" ]; then
  ok "数据源 直连可达 (200)"
  D_SRC_OK=direct
else
  warn_ "数据源 直连不通 (HTTP ${d_direct:-000})" "境内部网常态，继续看代理是否可用"
  D_SRC_OK=none
fi

if [ -n "$ENRICH_PROXY" ]; then
  d_proxy=$(probe "$DATASRC" "$ENRICH_PROXY")
  if [ "$d_proxy" = "200" ]; then
    ok "数据源 经代理可达 (200)"
    D_SRC_OK=proxy
  else
    bad "数据源 经代理仍不通 (HTTP ${d_proxy:-000})" \
        "代理地址/认证是否正确？公司是否把该域名列入白名单？curl -x $ENRICH_PROXY -v -I $DATASRC"
  fi
fi

if [ "$D_SRC_OK" = "none" ]; then
  bad "数据源 完全不可达 —— 补强无法在服务器进行" \
      "三种出路：①配公司代理 ②局域网内找一台可出网的机器做 squid/privoxy 正向代理 ③改为本机抓取后 rsync 数据到服务器（见 README 方案 C）"
fi

gh_direct=$(probe "https://api.github.com" direct)
if [ "$gh_direct" != "000" ]; then
  ok "GitHub 直连可达 (HTTP $gh_direct)"
  GH_OK=direct
else
  warn_ "GitHub 直连不通" "境内常态，继续看代理"
  GH_OK=none
fi

if [ -n "$GIT_PROXY" ]; then
  gh_proxy=$(probe "https://api.github.com" "$GIT_PROXY")
  if [ "$gh_proxy" != "000" ]; then
    ok "GitHub 经代理可达 (HTTP $gh_proxy)"
    GH_OK=proxy
  else
    bad "GitHub 经代理仍不通" "推送会失败。curl -x $GIT_PROXY -v https://api.github.com"
  fi
fi

[ "$GH_OK" = "none" ] && bad "GitHub 完全不可达 —— 服务器无法推送" \
  "退路：服务器只做出页并 git commit 到本地，由本机定时 pull 后推送（README 方案 C）"

in_direct=$(probe "https://api.indexnow.org/" direct)
in_proxy="000"; [ -n "$ENRICH_PROXY" ] && in_proxy=$(probe "https://api.indexnow.org/" "$ENRICH_PROXY")
if [ "$in_direct" != "000" ] || [ "$in_proxy" != "000" ]; then
  ok "IndexNow 可达 (直连 $in_direct / 代理 $in_proxy)"
else
  warn_ "IndexNow 不可达" "不影响页面发布，仅新页收录慢一些"
fi

gsc_direct=$(probe 'https://searchconsole.googleapis.com/$discovery/rest' direct)
if [ "$gsc_direct" = "200" ]; then
  info "GSC API 直连可达 —— 服务器可兼任周测（但仍建议留本机，凭据在这边）"
else
  info "GSC API 不可达 (HTTP ${gsc_direct:-000}) —— 符合预期，GSC 任务留在本机"
fi
echo

# ============================================================ 3. 代理一致性
echo "--- 3. 代理一致性 ---"
if [ -n "$ENRICH_PROXY" ] && [ "$ENRICH_PROXY" != "none" ]; then
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -x "$ENRICH_PROXY" https://api.github.com 2>/dev/null)
  [ "$code" != "000" ] && ok "ENRICH_PROXY 本身可用 (HTTP $code)" \
    || bad "ENRICH_PROXY 不可用" "地址/端口/账号密码？需要认证的写 http://user:pass@host:port"
fi

gitcfg=$(git -C "$REPO" config --get http.proxy 2>/dev/null || true)
if [ -n "$gitcfg" ]; then
  info "仓库已配置 http.proxy=$gitcfg（流水线还会用 GIT_PROXY 显式覆盖）"
else
  info "仓库未配置 http.proxy —— 靠 crontab 里的 GIT_PROXY 传入即可"
fi

envproxy=$(env | grep -iE '^(https?_proxy)=' | head -2 | tr '\n' ' ')
[ -n "$envproxy" ] && info "当前 shell 有全局代理变量：$envproxy" \
  || info "当前 shell 无全局代理变量（cron 环境更干净，必须显式传 GIT_PROXY/ENRICH_PROXY）"
echo

# ============================================================ 4. git 推送
echo "--- 4. git 推送能力 ---"
if [ -d "$REPO/.git" ]; then
  # 用 cd 而不是 git -C：Windows 版 git 不认 /c/... 形式的 -C 路径
  ( cd "$REPO" || exit 1
    PUSH_ARGS=(-c credential.helper=)
    if [ -n "$GIT_PROXY" ]; then
      PUSH_ARGS+=(-c "http.proxy=$GIT_PROXY" -c "https.proxy=$GIT_PROXY")
    fi
    timeout 60 git "${PUSH_ARGS[@]}" ls-remote origin >/dev/null 2>&1 || exit 2
  )
  case $? in
    0) ok "git ls-remote 通过" ;;
    2) bad "git ls-remote 失败" "①remote URL 内嵌 PAT 是否有效 ②GIT_PROXY 是否可达 ③PAT 是否过期" ;;
    *) warn_ "git ls-remote 超时/失败" "网络抖动，重跑一次；持续失败按上一行排查" ;;
  esac
  remote=$(cd "$REPO" && git remote get-url origin 2>/dev/null | sed -E 's#//[^@]*@#//***@#')
  info "remote = ${remote:-（读取不到，检查 .git/config）}"
  info "推送务必用: git -c credential.helper= push origin main（不加会永久挂起）"
else
  warn_ "$REPO 不是 git 仓库" "先 git clone"
fi
echo

# ============================================================ 5. 磁盘与权限
echo "--- 5. 磁盘与权限 ---"
avail=$(df -Pm "$REPO" 2>/dev/null | awk 'NR==2{print $4}')
if [ -n "$avail" ]; then
  if [ "$avail" -gt 3000 ]; then ok "可用空间 ${avail} MB"
  else warn_ "可用空间仅 ${avail} MB" "OE 页每千页约 100-200MB，建议留 3GB 以上"; fi
fi
[ -w "$REPO/.workbuddy" ] && ok ".workbuddy 可写" || bad ".workbuddy 不可写" "chown -R 当前用户 $REPO"
mkdir -p "$REPO/.workbuddy/logs" 2>/dev/null && ok ".workbuddy/logs 可创建" || bad "日志目录不可创建"
echo

# ============================================================ 6. 断电自启
echo "--- 6. 断电/重启后能否自愈 ---"
if command -v systemctl >/dev/null 2>&1; then
  systemctl is-enabled --quiet cron 2>/dev/null && ok "cron 已设为开机启动" \
    || warn_ "cron 未开机启动" "systemctl enable cron —— 否则断电恢复后定时任务不再运行"
fi
ls "$REPO/.workbuddy/logs/pipeline.lock" >/dev/null 2>&1 && \
  warn_ "存在残留 pipeline.lock" "断电导致上轮没清理。脚本会检测 pid 自动放行；若 pid 被复用可手删"
echo

echo "===== 汇总: $pass 通过 / $warn 警告 / $fail 待处理 ====="
if [ "$fail" -gt 0 ]; then
  echo "有 FAIL 项，先按提示逐条解决，再装 crontab。"
  exit 1
fi
echo "无阻塞项。按 README 步骤 6 先 DRY 空跑，再小批量真跑，最后装 crontab。"
