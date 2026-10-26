#!/usr/bin/env bash
# ==============================================================================
# OE 库服务器每日流水线：补强 → 发布 → 推送
#
# 用法:
#   bash deploy/oe_pipeline.sh                  # 默认：补强已发布页 + 按护栏发布
#   ENRICH_MODE=new bash deploy/oe_pipeline.sh  # 补强未发布页（为后续发布备数据）
#   ENRICH_LIMIT=6000 bash deploy/oe_pipeline.sh
#   DRY=1 bash deploy/oe_pipeline.sh            # 只打印不执行
#
# crontab 见 deploy/crontab.example
# ==============================================================================
set -uo pipefail

REPO="${REPO:-$HOME/ucars}"
PY="${PY:-python3}"
ENRICH_LIMIT="${ENRICH_LIMIT:-3000}"
ENRICH_DELAY="${ENRICH_DELAY:-1.0}"
ENRICH_WORKERS="${ENRICH_WORKERS:-4}"
# 境内局域网必填：公司出口代理，如 http://10.0.0.5:8080 或 http://user:pass@10.0.0.5:8080
# 境外直连写 none
ENRICH_PROXY="${ENRICH_PROXY:-}"
export ENRICH_PROXY
# git 推送代理。境内局域网可与 ENRICH_PROXY 相同（公司统一出口），也可不同
GIT_PROXY="${GIT_PROXY:-}"
# 开关（境内部网"全网不能出境"的情形 C 用）：
#   ENRICH_LIMIT=0  跳过补强（数据由本机抓好后 rsync 过来）
#   GIT_PUSH=0      跳过推送（服务器只 commit，由本机 pull 后推）
GIT_PUSH="${GIT_PUSH:-1}"
# released = 只补已发布页（先见效）；new = 只补未发布页（备数据）；all = 全部
ENRICH_MODE="${ENRICH_MODE:-released}"
DRY="${DRY:-0}"
LOG="${LOG:-$REPO/.workbuddy/logs/pipeline-$(date +%F).log}"

cd "$REPO" || { echo "REPO 不存在: $REPO"; exit 1; }
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1

echo "=============================================================="
echo "== OE 流水线启动 $(date '+%F %T') | mode=$ENRICH_MODE limit=$ENRICH_LIMIT"
echo "== 代理=${ENRICH_PROXY:-(脚本默认/直连)}  workers=$ENRICH_WORKERS delay=$ENRICH_DELAY"

# 防重入：上次没跑完就不启动下一轮
LOCK="$REPO/.workbuddy/logs/pipeline.lock"
if [ -e "$LOCK" ]; then
  if kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
    echo "== 上一轮仍在运行( pid $(cat "$LOCK") )，本次退出"; exit 0
  fi
fi
echo $$ >"$LOCK"
trap 'rm -f "$LOCK"' EXIT

run() { echo "-- \$ $*"; [ "$DRY" = "1" ] || eval "$@"; }

# ---------------------------------------------------------------- 1. 数据补强
echo "-- [1/5] B 层数据补强（enrich）"
if [ "$ENRICH_LIMIT" = "0" ]; then
  echo "   ENRICH_LIMIT=0 → 跳过补强（情形 C：数据由本机 rsync 过来）"
  ENRICH_MODE="skip"
fi
case "$ENRICH_MODE" in
  skip)     FLAG="__SKIP__" ;;
  released) FLAG="--only-released" ;;
  new)      FLAG="--skip-released" ;;
  *)        FLAG="" ;;
esac
if [ "$FLAG" = "__SKIP__" ]; then
  :  # 已在上面提示跳过
elif [ "$DRY" = "1" ]; then
  echo "-- \$ $PY .workbuddy/scripts/enrich_oe_from_hpd.py --limit $ENRICH_LIMIT --delay $ENRICH_DELAY --workers $ENRICH_WORKERS $FLAG"
else
  # 脚本自带预检：代理不通会立刻 exit 1，不会白跑几十分钟
  if ! $PY .workbuddy/scripts/enrich_oe_from_hpd.py --limit "$ENRICH_LIMIT" \
        --delay "$ENRICH_DELAY" --workers "$ENRICH_WORKERS" $FLAG; then
    echo "!! 补强阶段失败（多为代理不通，见上面的预检提示）"
    echo "!! 本轮中止：网络已坏的情况下继续发布只会推空提交或超时"
    echo "   境内排查：ENRICH_PROXY 是否正确？curl -x \$ENRICH_PROXY -I https://api.github.com"
    exit 1
  fi
fi

# ---------------------------------------------------------------- 2. 发布护栏
echo "-- [2/5] 每 2 天 600 页护栏"
if find .workbuddy/data -name 'oe-release-*-allowlist.json' -mtime -2 2>/dev/null | grep -q .; then
  echo "   2 天内已有发布记录，本轮跳过发布（护栏生效）"
  SKIP_RELEASE=1
else
  SKIP_RELEASE=0
fi

# ---------------------------------------------------------------- 3. 出页发布
if [ "$SKIP_RELEASE" = "0" ]; then
  echo "-- [3/5] 释放下一批 + 出页"
  # ⚠️ release_next_oe.py 没有 argparse，加 --help 会被当成正常参数直接触发 release
  run "$PY .workbuddy/scripts/release_next_oe.py --size 600"
  run "$PY .workbuddy/scripts/generate_oe_pages.py --strict-allowlist"
  run "$PY .workbuddy/scripts/build_oe_hubs.py"
  echo "-- [4/5] 健康检查"
  if [ "$DRY" = "1" ]; then
    echo "   (dry) seo_health_monitor.py"
  else
    if ! $PY .workbuddy/scripts/seo_health_monitor.py; then
      echo "!! 健康检查未通过，中止推送，等待人工处理"
      exit 1
    fi
  fi
else
  echo "-- [3/5] 跳过（护栏）"
  echo "-- [4/5] 跳过（护栏）"
fi

# ---------------------------------------------------------------- 5. 提交推送
echo "-- [5/5] git 提交 + 推送 + IndexNow"
if [ "$DRY" = "1" ]; then
  echo "   (dry) git add/push/indexnow"
else
  # 只对页面与 sitemap 入库，.workbuddy 在 .gitignore 内
  git add oe sitemap.xml llms.txt 2>/dev/null
  if ! git diff --cached --quiet; then
    git commit -q -m "chore(oe): pipeline $(date +%F)"
    if [ "$GIT_PUSH" = "0" ]; then
      echo "   GIT_PUSH=0 → 已提交到本地，跳过推送（情形 C：由本机 pull 后推）"
      echo "== 流水线结束 $(date '+%F %T')"
      exit 0
    fi
    # 关键1：必须用 -c credential.helper=，否则凭证 helper 会让 push 永久挂起
    # 关键2：境内服务器走 GIT_PROXY（git 不认 HTTPS_PROXY 的某些形态，显式传最稳）
    PUSH_ARGS=(-c credential.helper=)
    if [ -n "${GIT_PROXY:-}" ]; then
      PUSH_ARGS+=(-c "http.proxy=$GIT_PROXY" -c "https.proxy=$GIT_PROXY")
    fi
    timeout 600 git "${PUSH_ARGS[@]}" push origin main
    push_rc=$?
    if [ $push_rc -ne 0 ]; then
      echo "!! push 失败 rc=$push_rc（本地已提交，下轮会重试）"
      [ -z "${GIT_PROXY:-}" ] && echo "   境内服务器若超时：确认 GIT_PROXY 已设置（crontab 里配）"
    fi
  else
    echo "   无变更，跳过提交"
  fi
  # 推送新页给 IndexNow（无需 Google API，境内服务器配了代理就能跑）
  if [ "$SKIP_RELEASE" = "0" ] && [ "$GIT_PUSH" != "0" ]; then
    if [ -n "${GIT_PROXY:-}" ]; then
      HTTPS_PROXY="$GIT_PROXY" HTTP_PROXY="$GIT_PROXY" \
        timeout 900 $PY .workbuddy/scripts/indexnow_push.py --recent 600 \
        || echo "!! IndexNow 推送失败（不影响页面已上线，仅收录加速变慢）"
    else
      timeout 900 $PY .workbuddy/scripts/indexnow_push.py --recent 600 \
        || echo "!! IndexNow 推送失败（不影响页面已上线，仅收录加速变慢）"
    fi
  fi
fi

echo "== 流水线结束 $(date '+%F %T')"
