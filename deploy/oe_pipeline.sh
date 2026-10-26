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
# released = 只补已发布页（先见效）；new = 只补未发布页（备数据）；all = 全部
ENRICH_MODE="${ENRICH_MODE:-released}"
DRY="${DRY:-0}"
LOG="${LOG:-$REPO/.workbuddy/logs/pipeline-$(date +%F).log}"

cd "$REPO" || { echo "REPO 不存在: $REPO"; exit 1; }
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1

echo "=============================================================="
echo "== OE 流水线启动 $(date '+%F %T') | mode=$ENRICH_MODE limit=$ENRICH_LIMIT"

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
case "$ENRICH_MODE" in
  released) FLAG="--only-released" ;;
  new)      FLAG="--skip-released" ;;
  *)        FLAG="" ;;
esac
run "$PY .workbuddy/scripts/enrich_oe_from_hpd.py --limit $ENRICH_LIMIT \
     --delay $ENRICH_DELAY --workers $ENRICH_WORKERS $FLAG"

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
    # 关键：必须用 -c credential.helper=，否则凭证 helper 会让 push 永久挂起
    timeout 600 git -c credential.helper= push origin main
    push_rc=$?
    [ $push_rc -eq 0 ] || echo "!! push 失败 rc=$push_rc（多为超时，下轮会重试）"
  else
    echo "   无变更，跳过提交"
  fi
  # 推送新页给 IndexNow（无需 Google API，境内服务器也能跑）
  [ "$SKIP_RELEASE" = "0" ] && \
    timeout 900 $PY .workbuddy/scripts/indexnow_push.py --recent 600
fi

echo "== 流水线结束 $(date '+%F %T')"
