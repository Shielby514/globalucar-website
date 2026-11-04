# -*- coding: utf-8 -*-
"""
16-release-gate.py —— 出页护栏闸门（收录率回归检测）

为什么需要它（2026-11-04 GSC 实测后的口径澄清）
──────────────────────────────────────────────
1. sitemap API 的 `discovered` 是"Google 已发现"，`indexed` 才是"已收录"；
   新提交的分片 lastDownloaded=null，此时 indexed=0 只代表"Google 还没处理"，
   不能当"没收录"。周报里那个 96.2% 的"发现率"其实是把我们自己提交的
   URL 数回显了一遍，不是真收录率。
2. URL Inspection 抽样如果把"发布当天的新页"算进去，PASS 率必然是 0%——
   2026-11-03 实测 180 条里 116 条 lastCrawl 为空（Google 根本没抓）。
   换来的不是信号，是噪声。
3. 老页（已发布 ≥7 天）的真实稳态 PASS 率约 50~53%。

所以闸门不能写成"低于 50% 就停"，必须是**相对基线的回归检测**：
  · 只抽样"已发布 ≥ min_age_days 天"的页（排除未被抓取的新页）
  · PASS 率 < max(基线 × 0.6, 25%) → HOLD（暂停出页，只做 B 层补强）
  · 指标缺失 / 过期 / 抽样本身失败 → ALLOW（不能因为测不到就把站点锁死）

用法
  python 16-release-gate.py --measure [--sample 20] [--min-age-days 7]   # 抽样测量
  python 16-release-gate.py                                              # 判定
输出
  GATE=ALLOW / GATE=HOLD + 原因；退出码 0=ALLOW，10=HOLD
"""
import argparse
import datetime
import glob
import json
import os
import random
import re
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(BASE, '.workbuddy', 'data')
OE_DIR = os.path.join(BASE, 'oe')
GATE_FILE = os.path.join(DATA, 'index-gate.json')
DECISION_FILE = os.path.join(DATA, 'release-gate-decision.json')

SITE = 'https://www.global-ucars.com'
_AGG = re.compile(r'^(index|engine|cooling|electrical|body|brake|transmission|'
                  r'suspension|steering|ignition|fuel|sensors)')
# 基线回归系数：实测低于基线的 60% 才判定为"收录塌陷"
REGRESSION_FACTOR = 0.6
# 绝对下限：再低也不能只看比例（基线本身很小时）
ABS_FLOOR = 25.0
# 首次测量不可信时使用的保守基线（2026-11-04 实测老页稳态 PASS 率约 53%）
DEFAULT_BASELINE = 50.0
# 指标最长有效期（天）；过期 → 放行，不锁站点
MAX_AGE_DAYS = 8


def _batch_dates():
    """OE → 发布批次日期（来自 allowlist 文件名里的日期）。取最早批次为准。"""
    out = {}
    for p in glob.glob(os.path.join(DATA, 'oe-*-allowlist*.json')):
        name = os.path.basename(p)
        m = re.search(r'(\d{8})', name)
        day = None
        if m:
            try:
                day = datetime.datetime.strptime(m.group(1), '%Y%m%d').date()
            except ValueError:
                day = None
        if day is None:
            day = datetime.date(2020, 1, 1)      # 无日期的批次视为"老批次"
        try:
            keys = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        if not isinstance(keys, list):
            continue
        for k in keys:
            kk = str(k).replace('-', '').upper()
            if kk not in out or day < out[kk]:
                out[kk] = day
    return out


def candidates(min_age_days):
    """已发布 ≥ min_age_days 天的详情页文件名（排除聚合页与新批次）。"""
    cutoff = datetime.date.today() - datetime.timedelta(days=min_age_days)
    batch = _batch_dates()
    out = []
    for f in os.listdir(OE_DIR):
        if not f.endswith('.html') or _AGG.match(f):
            continue
        key = f[:-5].replace('-', '').upper()
        day = batch.get(key)
        if day is not None and day > cutoff:
            continue          # 最近批次：还没被抓取，抽样会得到假阴性
        out.append(f)
    return out


def measure(sample, min_age_days, seed=None):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gsc_api_client as api
    from googleapiclient.errors import HttpError

    site = api.get_site_url().rstrip('/') + '/'
    pool = candidates(min_age_days)
    if not pool:
        print('没有符合条件的候选页（全部都是新批次？）')
        return None
    seed = seed if seed is not None else int(datetime.date.today().strftime('%Y%m%d'))
    rnd = random.Random(seed)
    picked = rnd.sample(pool, min(sample, len(pool)))
    print('候选 %d 页（已发布 ≥%d 天）→ 抽样 %d 条' % (len(pool), min_age_days, len(picked)), flush=True)

    creds = api.load_credentials()
    sc = api.build_service(creds)

    passed = 0
    http_err = 0
    never_crawled = 0
    details = []
    t0 = time.time()
    for i, f in enumerate(picked, 1):
        # ⚠️ site 已带尾斜杠，这里绝不能再加 '/' —— 否则拼出 "https://…com//oe/x.html"，
        #    双斜杠在 URL Inspection 里是另一个 URL，会 100% 返回 "URL is unknown to Google"，
        #    看起来像"收录塌陷"，实际是自己拼错了（2026-11-04 实测踩过）。
        url = '%soe/%s' % (site, f)
        try:
            r = sc.urlInspection().index().inspect(
                body={'inspectionUrl': url, 'siteUrl': site}).execute()
            idx = r.get('inspectionResult', {}).get('indexStatusResult', {})
            v = idx.get('verdict', 'UNKNOWN')
            last = idx.get('lastCrawlTime', '')
            if v == 'PASS':
                passed += 1
            if not last:
                never_crawled += 1
            details.append({'file': f, 'verdict': v,
                            'coverage': idx.get('coverageState', ''),
                            'lastCrawl': last})
        except HttpError as e:
            http_err += 1
            details.append({'file': f, 'verdict': 'HTTPERR', 'error': str(e)[:120]})
        except Exception as e:
            http_err += 1
            details.append({'file': f, 'verdict': 'ERROR', 'error': str(e)[:120]})
        if i % 5 == 0:
            print('  进度 %d/%d  PASS=%d  用时 %.0fs' % (i, len(picked), passed, time.time() - t0), flush=True)

    n = len(picked)
    valid = n - http_err
    rate = (passed / valid * 100) if valid > 0 else 0.0

    prev = {}
    if os.path.exists(GATE_FILE):
        try:
            prev = json.load(open(GATE_FILE, encoding='utf-8'))
        except Exception:
            prev = {}
    baseline = prev.get('baseline')
    if baseline is None:
        # 首次测量：只有当结果站得住脚时才拿来做基线；
        # 样本太小或结果低于绝对下限时，说明测量本身不可信，先用保守基线并标记待人工确认。
        if rate >= ABS_FLOOR and valid >= max(10, int(n * 0.5)):
            baseline = rate
        else:
            baseline = DEFAULT_BASELINE
            print('  [warn] 首测结果 %.1f%%（样本 %d）不足以作为基线，先用默认基线 %.1f%%'
                  % (rate, n, DEFAULT_BASELINE))
    threshold = max(baseline * REGRESSION_FACTOR, ABS_FLOOR)

    out = {
        'sampled_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'sample_size': n,
        'valid': valid,
        'http_err': http_err,
        'passed': passed,
        'never_crawled': never_crawled,
        'pass_rate': round(rate, 2),
        'baseline': round(baseline, 2),
        'threshold': round(threshold, 2),
        'min_age_days': min_age_days,
        'source': 'gsc-url-inspection',
        'valid_measurement': bool(valid >= max(5, int(n * 0.5))),
        'details': details,
    }
    json.dump(out, open(GATE_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('抽样完成: PASS %d/%d = %.1f%%  （基线 %.1f%%，触发线 %.1f%%，HTTPERR %d，从未抓取 %d）'
          % (passed, valid, rate, baseline, threshold, http_err, never_crawled))
    print('已写 %s' % GATE_FILE)
    return out


def decide():
    if not os.path.exists(GATE_FILE):
        return 'ALLOW', '无索引指标（首次运行或测量失败）—— 不因测不到而锁死站点'
    try:
        g = json.load(open(GATE_FILE, encoding='utf-8'))
    except Exception as e:
        return 'ALLOW', '索引指标文件损坏（%s）' % e
    try:
        t = datetime.datetime.fromisoformat(g.get('sampled_at', ''))
        age_days = (datetime.datetime.now() - t).total_seconds() / 86400.0
    except Exception:
        age_days = 999
    if age_days > MAX_AGE_DAYS:
        return 'ALLOW', '索引指标已过期 %.1f 天（> %d）—— 放行并建议重测' % (age_days, MAX_AGE_DAYS)
    if not g.get('valid_measurement'):
        return 'ALLOW', '上次抽样无效（有效样本 %s/%s）—— 不据此停发' % (g.get('valid'), g.get('sample_size'))
    rate = float(g.get('pass_rate', 0))
    thr = float(g.get('threshold', ABS_FLOOR))
    if rate < thr:
        return 'HOLD', ('收录率塌陷：实测 %.1f%% < 触发线 %.1f%%（基线 %.1f%%，样本 %s，测量于 %s）'
                        % (rate, thr, g.get('baseline', 0), g.get('sample_size'), g.get('sampled_at')))
    return 'ALLOW', ('收录率正常：实测 %.1f%% ≥ 触发线 %.1f%%（基线 %.1f%%）'
                     % (rate, thr, g.get('baseline', 0)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--measure', action='store_true', help='抽样测量并写 index-gate.json')
    ap.add_argument('--sample', type=int, default=20, help='抽样条数（每条约 6.7s，20 条约 2.5 分钟）')
    ap.add_argument('--min-age-days', type=int, default=7, help='只抽已发布满 N 天的页（避开未被抓取的新页）')
    ap.add_argument('--set-baseline', type=float, default=None,
                    help='人工指定基线 PASS 率（%%），覆盖文件里的基线；用于首测不可信时人工锚定')
    a = ap.parse_args()

    if a.set_baseline is not None:
        g = {}
        if os.path.exists(GATE_FILE):
            try:
                g = json.load(open(GATE_FILE, encoding='utf-8'))
            except Exception:
                g = {}
        g['baseline'] = round(a.set_baseline, 2)
        g['threshold'] = round(max(a.set_baseline * REGRESSION_FACTOR, ABS_FLOOR), 2)
        g['baseline_set_by'] = 'manual'
        g['baseline_set_at'] = datetime.datetime.now().isoformat(timespec='seconds')
        json.dump(g, open(GATE_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('基线已设为 %.1f%%（触发线 %.1f%%）' % (g['baseline'], g['threshold']))

    if a.measure:
        measure(a.sample, a.min_age_days)

    verdict, reason = decide()
    print('GATE=%s' % verdict)
    print('  %s' % reason)
    try:
        json.dump({'at': datetime.datetime.now().isoformat(timespec='seconds'),
                   'verdict': verdict, 'reason': reason},
                  open(DECISION_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    except Exception:
        pass
    return 10 if verdict == 'HOLD' else 0


if __name__ == '__main__':
    sys.exit(main())
