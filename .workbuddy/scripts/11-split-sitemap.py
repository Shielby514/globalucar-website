# -*- coding: utf-8 -*-
"""
11-split-sitemap.py
==================
把单文件 sitemap.xml（当前 15,746 条，OE 页占 97.9%）拆成
sitemap-index.xml + 若干子 sitemap，让 Google 的抓取预算能按优先级分配。

设计要点（为什么不改 sitemap.xml）：
  generate_oe_pages.py / generate_blog_static_pages.py / generate_product_pages.py /
  build_oe_hubs.py 在出页时都会「读现有 sitemap.xml 再追加/改写」。
  如果把 sitemap.xml 本身改成 index 格式，这些脚本会写坏它。
  → 所以 sitemap.xml 保持原样（单文件），另建 sitemap-index.xml 作为分片入口，
    并在 robots.txt 里登记它。两个入口同时存在不会让 Google 重复抓取。

分片规则：
  sitemap-core.xml     核心页 + 分类页（首页/about/contact/kingmay/parts-*/oem-* 等）
  sitemap-blog.xml     /blog/<slug>.html
  sitemap-product.xml  /parts/<slug>.html（产品静态页）+ product-detail.html?id=
  sitemap-oe-N.xml     /oe/<oe>.html 详情页，按顺序切片，每片不超过 4000 条

用法:
  python 11-split-sitemap.py            # 生成/覆盖分片文件
  python 11-split-sitemap.py --dry-run  # 只统计不写文件
"""
import os
import re
import sys
import json
import argparse
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITEMAP = os.path.join(ROOT, 'sitemap.xml')
INDEX = os.path.join(ROOT, 'sitemap-index.xml')
ROBOTS = os.path.join(ROOT, 'robots.txt')
SITE = 'https://www.global-ucars.com'
OE_CHUNK = 4000

URL_RE = re.compile(r'<url>(.*?)</url>', re.S)
LOC_RE = re.compile(r'<loc>\s*([^<]+?)\s*</loc>')
LASTMOD_RE = re.compile(r'<lastmod>\s*([^<]+?)\s*</lastmod>')


def parse_sitemap(path):
    """-> [(loc, lastmod or '')]，保持文档顺序"""
    if not os.path.exists(path):
        print(f'!! 找不到 {path}')
        return []
    s = open(path, encoding='utf-8').read()
    out = []
    for m in URL_RE.finditer(s):
        blk = m.group(1)
        lm = LOC_RE.search(blk)
        if not lm:
            continue
        dt = LASTMOD_RE.search(blk)
        out.append((lm.group(1), dt.group(1) if dt else ''))
    return out


def classify(loc):
    p = loc.replace(SITE, '').split('#')[0]
    if p.startswith('/oe/'):
        return 'oe'
    if p.startswith('/blog/'):
        return 'blog'
    if p.startswith('/parts/') or p.startswith('/product'):
        return 'product'
    return 'core'


def write_urlset(path, entries):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in entries:
        lines.append('  <url>')
        lines.append(f'    <loc>{loc}</loc>')
        if lastmod:
            lines.append(f'    <lastmod>{lastmod}</lastmod>')
        lines.append('  </url>')
    lines.append('</urlset>')
    open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')


def write_index(path, children):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in children:
        lines.append('  <sitemap>')
        lines.append(f'    <loc>{loc}</loc>')
        if lastmod:
            lines.append(f'    <lastmod>{lastmod}</lastmod>')
        lines.append('  </sitemap>')
    lines.append('</sitemapindex>')
    open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    entries = parse_sitemap(SITEMAP)
    print(f'sitemap.xml 共 {len(entries)} 条 URL')

    buckets = {'core': [], 'blog': [], 'product': [], 'oe': []}
    for loc, lastmod in entries:
        buckets[classify(loc)].append((loc, lastmod))
    for k in ('core', 'blog', 'product', 'oe'):
        print(f'  {k:<8} {len(buckets[k])}')

    # OE 按顺序切片
    oe_files = []
    oe = buckets['oe']
    for i in range(0, len(oe), OE_CHUNK):
        oe_files.append((f'sitemap-oe-{i//OE_CHUNK + 1}.xml', oe[i:i + OE_CHUNK]))
    print(f'  OE 分片 {len(oe_files)} 个，每片 ≤{OE_CHUNK}')

    children = []
    plan = [('sitemap-core.xml', buckets['core']),
            ('sitemap-blog.xml', buckets['blog']),
            ('sitemap-product.xml', buckets['product'])]
    for name, data in plan:
        children.append((f'{SITE}/{name}', ''))
    for name, data in oe_files:
        children.append((f'{SITE}/{name}', ''))

    if args.dry_run:
        print('\nDRY-RUN，不写文件。计划生成：')
        for name, data in plan + oe_files:
            print(f'  {name}  {len(data)} 条')
        print(f'  sitemap-index.xml  {len(children)} 个子表')
        for c in children:
            print(f'    - {c[0]}')
        return

    for name, data in plan + oe_files:
        write_urlset(os.path.join(ROOT, name), data)
        print(f'  wrote {name}  {len(data)} 条')
    write_index(INDEX, children)
    print(f'  wrote sitemap-index.xml  {len(children)} 个子表')

    # robots.txt 登记 index（保留原有 sitemap.xml 行，两条都提交不会重复抓取）
    if os.path.exists(ROBOTS):
        r = open(ROBOTS, encoding='utf-8').read()
        line = f'Sitemap: {SITE}/sitemap-index.xml'
        if line not in r:
            r = r.rstrip('\n') + f'\n{line}\n'
            open(ROBOTS, 'w', encoding='utf-8', newline='\n').write(r)
            print('  robots.txt 已登记 sitemap-index.xml')
        else:
            print('  robots.txt 已含 sitemap-index.xml')

    # 汇总输出给调用方
    summary = {
        'total': len(entries),
        'core': len(buckets['core']),
        'blog': len(buckets['blog']),
        'product': len(buckets['product']),
        'oe': len(buckets['oe']),
        'oe_chunks': len(oe_files),
        'children': [c[0] for c in children],
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    logp = os.path.join(ROOT, '.workbuddy', 'data', 'sitemap_split.json')
    try:
        json.dump(summary, open(logp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f'  summary -> {logp}')
    except Exception as e:
        print(f'  summary 写入失败: {e}')
    print('SPLIT DONE')


if __name__ == '__main__':
    main()
