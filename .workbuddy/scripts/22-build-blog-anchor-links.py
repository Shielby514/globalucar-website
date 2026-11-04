#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
22-build-blog-anchor-links.py
=============================
博客文内锚文本打通：把 155 篇博客正文里的零件关键词链接到对应产品页 / 分类页。

做法：
  1) 行内锚：正文首次出现的零件词（oil cooler / brake pad / tie rod ...）→ 包成
     <a href="/parts/<slug>.html">，每篇最多 3 个，避免堆砌。
  2) 文末模块：每篇加一个 "Parts mentioned in this guide" 区块，
     列出 4-6 个最相关产品 + 1 个分类页入口，把博客流量导向产品页。

安全约束：
  · 只在 <article> 正文里改，不动导航/页脚/已有链接
  · 已有 <a>...</a> 区间整体跳过（不会嵌套链接）
  · 注入后打哨兵注释，重复运行不重复注入（幂等）

用法：python 22-build-blog-anchor-links.py [--dry-run] [--limit N]
"""
import argparse
import glob
import html
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')
BLOG_DIR = os.path.join(ROOT, 'blog')
CATALOG = os.path.join(ROOT, '.workbuddy', 'data', 'product-catalog.json')
SITE = 'https://www.global-ucars.com'

SENTINEL = '<!--BLOG-PARTS:INJECTED-->'
MAX_INLINE = 3
MAX_BLOCK = 6

# 允许做行内锚的词（单词需有区分度；多词组合需完整出现）
SINGLE_OK = {'alternator', 'radiator', 'thermostat', 'condenser', 'evaporator',
             'clutch', 'bumper', 'mirror', 'wiper', 'flywheel'}
MULTI_ALIASES = [
    'oil cooler', 'brake pad', 'brake disc', 'brake kit', 'tie rod', 'tie rod end',
    'control arm', 'ball joint', 'shock absorber', 'strut mount', 'wheel hub bearing',
    'wheel bearing', 'starter motor', 'oxygen sensor', 'water pump', 'fuel injector',
    'spark plug', 'ignition coil', 'throttle body', 'stabilizer link', 'steering knuckle',
    'drive shaft', 'cv joint', 'door lock', 'expansion tank', 'heater core', 'wiper blade',
    'headlight', 'tail light', 'fog light', 'cabin air filter', 'oil filter', 'air filter',
    'fuel filter', 'fuel pump', 'engine mount', 'cylinder head gasket', 'piston ring',
    'timing belt', 'timing chain', 'crank shaft', 'crankshaft', 'alternator and starter',
    'windshield wiper', 'rear shock absorber', 'front shock absorber',
]

STOP_PREFIX = ('front ', 'rear ', 'left ', 'right ', 'upper ', 'lower ', 'complete ', 'assembled ')


def esc(s):
    return html.escape(str(s if s is not None else ''), quote=True)


def load_catalog():
    cat = json.load(open(CATALOG, encoding='utf-8'))
    if isinstance(cat, dict):
        return cat['products'], cat.get('type_pages', [])
    return cat, []


def build_keyword_map(products, type_pages):
    """关键词 → (slug, 显示名, 权重)；只用有区分度的完整词组，避免把 "Lower Control" 这种截断词做锚"""
    kw = {}

    def offer(term, slug, disp, weight):
        term = term.strip().lower()
        if len(term) < 5 or len(term.split()) > 3:
            return
        if ' ' not in term and term not in SINGLE_OK:
            return
        if term not in kw or weight > kw[term][2]:
            kw[term] = (slug, disp, weight)

    # 1) 产品的 sub_category（完整词组）
    for p in products:
        sub = (p.get('sub_category') or '').strip()
        if not sub:
            continue
        offer(sub, p['slug'], sub, 10 + len(sub) + (3 if p.get('source') == 'existing' else 0))
    # 2) 精选别名 → 最匹配的产品
    for alias in MULTI_ALIASES:
        best = None
        for p in products:
            sub = (p.get('sub_category') or '').lower()
            if alias in sub or sub in alias:
                cand = (10 + len(alias) + (3 if p.get('source') == 'existing' else 0), p)
                if best is None or cand[0] > best[0]:
                    best = cand
        if best:
            offer(alias, best[1]['slug'], alias, best[0])
    # 3) 分类 hub 页（泛类型）作为兜底锚点
    for tp in type_pages:
        sub = (tp.get('sub_category') or '').strip()
        if sub:
            offer(sub, tp['slug'], sub, 8)
    return kw


def split_links(body):
    """把正文按 <a>...</a> 切成 [普通段, 链接段, 普通段, ...]"""
    parts = []
    last = 0
    for m in re.finditer(r'<a\b[^>]*>.*?</a>', body, re.S | re.I):
        if m.start() > last:
            parts.append((False, body[last:m.start()]))
        parts.append((True, m.group(0)))
        last = m.end()
    if last < len(body):
        parts.append((False, body[last:]))
    return parts


def inject_inline(body, kw, used_slugs):
    """在正文首次出现的零件词上加链接；返回 (新正文, 命中数)"""
    hits = 0
    used_terms = set()
    new_parts = []
    for seg_is_link, seg in split_links(body):
        if seg_is_link or hits >= MAX_INLINE:
            new_parts.append(seg)
            continue
        out = seg
        for term, (slug, disp, _w) in sorted(kw.items(), key=lambda x: -len(x[0])):
            if hits >= MAX_INLINE:
                break
            if term in used_terms or slug in used_slugs:
                continue
            pat = re.compile(r'(?<![\w-])(' + re.escape(term) + r')(?![\w-])', re.I)
            m = pat.search(out)
            if not m:
                continue
            txt = m.group(1)
            if len(txt) < 5 or len(txt) > 50:
                continue
            out = out[:m.start()] + '<a href="/parts/%s.html">%s</a>' % (slug, txt) + out[m.end():]
            used_terms.add(term)
            used_slugs.add(slug)
            hits += 1
        new_parts.append(out)
    return ''.join(new_parts), hits


def pick_related(body_lower, kw, products_by_slug):
    """按正文命中的关键词挑选相关产品"""
    score = defaultdict(float)
    for term, (slug, disp, w) in kw.items():
        if len(term) < 5:
            continue
        if re.search(r'(?<![\w-])' + re.escape(term) + r'(?![\w-])', body_lower):
            score[slug] += w
    ranked = sorted(score.items(), key=lambda x: -x[1])
    out = []
    for slug, sc in ranked:
        p = products_by_slug.get(slug)
        if not p:
            continue
        out.append(p)
        if len(out) >= MAX_BLOCK:
            break
    return out


def build_block(related):
    if not related:
        return ''
    items = ''.join(
        '<li><a href="/parts/%s.html">%s</a></li>' % (esc(p['slug']), esc(p.get('name', '')[:90]))
        for p in related)
    return ("""
    <section class="bp-parts-block" style="margin:28px 0 8px;padding:18px 20px;border:1px solid #e2e8f0;border-radius:12px;background:#f8fafc;">
      <h2 style="font-size:1.15rem;margin:0 0 10px;color:#0d1f3c;">Parts mentioned in this guide</h2>
      <ul style="margin:0 0 10px 18px;font-size:.95rem;line-height:1.7;">
        %s
      </ul>
      <p style="margin:0;font-size:.88rem;color:#64748b;">Every SKU above is quoted FOB Guangzhou with MOQ 10 pieces and a 12-month warranty.
        Full catalogue: <a href="/parts/index.html" style="color:#c8102e;font-weight:600;">all parts</a>.</p>
    </section>""" % items)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    products, type_pages = load_catalog()
    kw = build_keyword_map(products, type_pages)
    products_by_slug = {p['slug']: p for p in products}
    for tp in type_pages:
        products_by_slug.setdefault(tp['slug'], tp)
    print('关键词表：%d 个（可做行内锚）' % len(kw))

    files = sorted(glob.glob(os.path.join(BLOG_DIR, '*.html')))
    if args.limit:
        files = files[:args.limit]
    n_inj = n_skip = n_inline = n_block = 0
    for f in files:
        s = open(f, encoding='utf-8', errors='ignore').read()
        if SENTINEL in s:
            n_skip += 1
            continue
        m = re.search(r'(<article[^>]*>)(.*?)(</article>)', s, re.S)
        if not m:
            n_skip += 1
            continue
        body = m.group(2)
        low = body.lower()
        related = pick_related(low, kw, products_by_slug)
        used = set()
        new_body, hits = inject_inline(body, kw, used)
        block = build_block(related)
        if block:
            # 插到 </article> 前
            new_body = new_body + block
        if new_body == body:
            n_skip += 1
            continue
        s = s[:m.start()] + m.group(1) + new_body + m.group(3) + s[m.end():]
        s = s.replace('<article>', '<article>\n' + SENTINEL, 1)
        if not args.dry_run:
            open(f, 'w', encoding='utf-8').write(s)
        n_inj += 1
        n_inline += hits
        n_block += 1 if block else 0
    print('处理：注入 %d 篇 / 跳过 %d 篇；行内锚 %d 个；文末模块 %d 个'
          % (n_inj, n_skip, n_inline, n_block))
    if args.dry_run:
        print('[dry-run] 未写盘')


if __name__ == '__main__':
    main()
