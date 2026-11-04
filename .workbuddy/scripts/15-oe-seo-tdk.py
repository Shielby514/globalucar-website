# -*- coding: utf-8 -*-
"""
15-oe-seo-tdk.py —— 批量把已发布 OE 详情页改成"买家形态"的 TDK / H1 / 正文零件名

用法:
  python .workbuddy/scripts/15-oe-seo-tdk.py --dry-run          # 只统计 + 打样例
  python .workbuddy/scripts/15-oe-seo-tdk.py --apply              # 写盘
  python .workbuddy/scripts/15-oe-seo-tdk.py --apply --limit 100  # 小批量试跑

幂等：重复执行不会产生二次改动（第二次 diff 为空）。
只改 head 区（title/description/keywords/og/twitter）与 H1、以及正文里重复出现的脏零件名；
页面主体结构、链接、图片、JSON-LD 一律不动。
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oe_seo_tdk as T

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OE_DIR = os.path.join(BASE, 'oe')
DB_P = os.path.join(BASE, '.workbuddy', 'data', 'oe-master-db.json')

OE_RE = re.compile(r'<span class="oe-n">([^<]+)</span>')
TITLE_RE = re.compile(r'<title>(.*?)</title>', re.S)


def norm(s):
    return re.sub(r'[^A-Z0-9]', '', (s or '').upper())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='写盘（默认只统计）')
    ap.add_argument('--limit', type=int, default=0, help='只处理前 N 页（0=全部）')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    if not os.path.exists(DB_P):
        print('[x] 找不到母库: %s' % DB_P)
        return 1
    db = json.load(open(DB_P, encoding='utf-8'))
    index = {}
    for k, e in db.items():
        oe = e.get('oe') or k
        index[norm(oe)] = e
    print('母库 %d 条，索引 %d 条' % (len(db), len(index)))

    files = sorted(f for f in os.listdir(OE_DIR) if f.endswith('.html'))
    n_total = n_detail = n_changed = n_nodb = n_nowrite = 0
    lens = []
    samples = []
    fixed_parts = 0

    for fn in files:
        n_total += 1
        p = os.path.join(OE_DIR, fn)
        with open(p, 'r', encoding='utf-8', errors='ignore', newline='') as f:
            html = f.read()
        m = OE_RE.search(html)
        if not m:
            continue          # hub / L2 系统页，不是详情页
        n_detail += 1
        oe = m.group(1).strip()
        e = index.get(norm(oe))
        if not e:
            n_nodb += 1
            continue
        new, changed, info = T.apply_to_page(html, oe, e)
        lens.append(len(info['title']))
        if info['raw'] != info['part']:
            fixed_parts += 1
        if not changed:
            n_nowrite += 1
            continue
        n_changed += 1
        if len(samples) < 6:
            old_t = TITLE_RE.search(html)
            samples.append((oe, old_t.group(1) if old_t else '', info['title'],
                            info['desc'], info['part'], info['raw']))
        if args.apply:
            with open(p, 'w', encoding='utf-8', newline='') as f:
                f.write(new)

    print('OE 目录文件 %d，其中详情页 %d' % (n_total, n_detail))
    print('  母库无对应记录（跳过） %d' % n_nodb)
    print('  零件名被清洗的页       %d (%.1f%%)' % (fixed_parts, fixed_parts / max(1, n_detail) * 100))
    print('  有改动的页             %d' % n_changed)
    print('  无改动（幂等/已合规）   %d' % n_nowrite)
    if lens:
        lens.sort()
        print('  新 title 长度 中位 %d，最大 %d，超 70 的 %d' %
              (lens[len(lens) // 2], lens[-1], sum(1 for x in lens if x > 70)))
    print('模式: %s' % ('APPLY 已写盘' if args.apply else 'DRY-RUN（加 --apply 才写盘）'))

    if not args.quiet:
        print()
        for oe, ot, nt, nd, np_, orr in samples:
            print('─' * 78)
            print('OE %s' % oe)
            print('  旧 title : %s' % ot)
            print('  新 title : %s' % nt)
            print('  新 desc  : %s' % nd)
            print('  旧零件名 : %s' % orr)
            print('  新零件名 : %s' % np_)
    return 0


if __name__ == '__main__':
    sys.exit(main())
