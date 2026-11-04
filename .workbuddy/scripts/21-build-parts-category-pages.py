#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
21-build-parts-category-pages.py
================================
parts 分类页提排名：把「JS 渲染的产品网格」改成服务端静态网格。

为什么：分类页原本 pc-grid 是空的，靠 products-inline.js 运行时填充，
静态 HTML 里一条产品链接都没有 → 爬虫抓不到详情页，排名卡在 pos 22。
改造后：静态 HTML 直接输出 <a href="/parts/<slug>.html">，JS 只负责更新计数。

同时：
  · 更新 H2 计数为真实 SKU 数
  · 补 ItemList JSON-LD
  · 顶部加 /parts/index.html 总目录入口
  · 保留原 JS（仅在无静态网格时渲染），不影响交互

用法：python 21-build-parts-category-pages.py [--dry-run]
"""
import argparse
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')
SITE = 'https://www.global-ucars.com'
CATALOG = os.path.join(ROOT, '.workbuddy', 'data', 'product-catalog.json')

PAGES = {
    'parts-engine.html': ('engine', 'Engine & Fuel System'),
    'parts-cooling.html': ('cooling', 'Cooling & Climate'),
    'parts-suspension.html': ('suspension', 'Suspension & Steering'),
    'parts-electrical.html': ('electrical', 'Electrical & Sensors'),
}
MAX_CARDS = 90


def esc(s):
    return html.escape(str(s if s is not None else ''), quote=True)


def load_catalog():
    cat = json.load(open(CATALOG, encoding='utf-8'))
    if isinstance(cat, dict):
        return cat['products'], cat.get('type_pages', [])
    return cat, []


def type_links(products, type_pages, sys_key):
    """该系统下的分类 hub 页（泛类型页）→ 按类型浏览链接"""
    out = []
    for tp in type_pages:
        if (tp.get('system') or tp.get('part_system')) != sys_key:
            continue
        n = sum(1 for p in products
                if tp.get('sub_category', '').lower() in p.get('sub_category', '').lower())
        out.append((tp.get('sub_category') or tp.get('name'), tp.get('slug'), n))
    out.sort(key=lambda x: -x[2])
    return out


def card(p):
    img = p.get('local_image') or (p.get('images') or [''])[0] or 'assets/parts/gen/gen-abs-wheel-speed-sensor.png'
    img = img.lstrip('/')
    oe = (p.get('oem_refs') or [''])[0]
    makes = ' / '.join((p.get('compatible_makes') or [])[:3])
    fit = ' / '.join((p.get('fitment') or [])[:3])
    return ("""<a class="pc-card" href="/parts/%s.html" style="text-decoration:none;display:block;">
          <img class="pc-img" src="/%s" alt="%s" loading="lazy" width="400" height="400" />
          <div class="pc-body">
            <div class="pc-name">%s</div>
            <div class="pc-compat">Fits: %s</div>
            <div class="pc-oem">OEM Ref: %s &middot; MOQ %s</div>
            <div class="pc-actions">
              <span class="pc-btn-detail">View Details</span>
              <a href="/contact.html?product=%s" class="pc-btn-quote">Get Quote</a>
            </div>
          </div>
        </a>""" % (esc(p['slug']), esc(img), esc((p.get('alt_text') or p.get('name', ''))[:80]),
                   esc(p.get('name', '')[:90]), esc(fit or makes), esc(oe),
                   esc(p.get('moq') or '10 Pieces'),
                   html.escape('%s (SKU KM-%s)' % (p.get('name', ''), p['id']), quote=True)))


def build():
    products, type_pages = load_catalog()
    out = {}
    for fname, (sys_key, sys_label) in PAGES.items():
        path = os.path.join(ROOT, fname)
        if not os.path.exists(path):
            print('!! 缺少 %s' % fname)
            continue
        s = open(path, encoding='utf-8', errors='ignore').read()
        items = [p for p in products if (p.get('system') or p.get('part_system')) == sys_key]
        # 车型/品牌维度也放进列表，分类页不只服务单一品牌
        items.sort(key=lambda p: (p.get('source', ''), p.get('name', '')))
        shown = items[:MAX_CARDS]
        grid = '\n'.join(card(p) for p in shown)
        more = ''
        if len(items) > len(shown):
            more = ('<p style="margin-top:14px;font-size:.9rem;color:#718096;">Showing %d of %d SKUs in this '
                    'category &mdash; <a href="/parts/index.html" style="color:#c8102e;font-weight:600;">see the '
                    'full parts catalogue</a>.</p>' % (len(shown), len(items)))
        # 按类型浏览（分类 hub 页）——补足细分入口，同时把 29 个 hub 页纳入内链
        tl = type_links(products, type_pages, sys_key)
        type_sec = ''
        if tl:
            links = ''.join('<a class="sort-btn" style="text-decoration:none;" href="/parts/%s.html">%s (%d)</a>'
                            % (esc(slug), esc(name), n) for name, slug, n in tl)
            type_sec = ('<div style="display:flex;flex-wrap:wrap;gap:8px;margin:0 0 18px;">%s</div>' % links)
        # 1) 静态网格注入（整体替换 → 幂等；兼容早期无哨兵版本）
        new_grid = ('<!--PRODUCT-GRID:START-->\n%s<div class="pc-grid" id="pcGrid" data-static="1">\n%s\n</div>\n%s\n<!--PRODUCT-GRID:END-->'
                    % (type_sec, grid, more))
        m = re.search(r'<div class="pc-grid" id="pcGrid"(?:\s+data-static="1")?>', s)
        if not m:
            print('!! %s 未找到 pcGrid 容器，跳过' % fname)
            continue
        end = s.find('</section>', m.end())
        if end == -1:
            print('!! %s pcGrid 后未找到 section 收尾，跳过' % fname)
            continue
        s = s[:m.start()] + new_grid + '\n  ' + s[end:]
        # 2) 计数更新（静态写死，JS 也会再更新一次）
        s = re.sub(r'(<h2>[^<]*?)(\d+)( Products)</h2>', r'\g<1>%d\g<3></h2>' % len(items), s, count=1)
        # 3) JS 渲染保护：静态网格存在时不覆盖
        s = s.replace("var grid = document.getElementById('pcGrid');\n    if (!grid) return;",
                      "var grid = document.getElementById('pcGrid');\n    if (!grid) return;\n"
                      "    if (grid.getAttribute('data-static') === '1') { return; }")
        # 4) ItemList JSON-LD
        item_list = {
            '@context': 'https://schema.org', '@type': 'ItemList',
            'name': '%s products' % sys_label,
            'numberOfItems': len(shown),
            'itemListElement': [{'@type': 'ListItem', 'position': i + 1,
                                 'url': '%s/parts/%s.html' % (SITE, p['slug']),
                                 'name': p.get('name', '')[:90]} for i, p in enumerate(shown)],
        }
        ld = ('<!--CATEGORY-ITEMLIST:START-->\n<script type="application/ld+json">\n%s\n</script>\n'
              '<!--CATEGORY-ITEMLIST:END-->' % json.dumps(item_list, ensure_ascii=False, indent=1))
        # 先清掉历史注入的 ItemList（含无哨兵版本），再写新的
        s = re.sub(r'<!--CATEGORY-ITEMLIST:START-->.*?<!--CATEGORY-ITEMLIST:END-->', '', s, flags=re.S)
        s = re.sub(r'<script type="application/ld\+json">\s*\{[^<]*?"@type":\s*"ItemList".*?</script>',
                   '', s, flags=re.S)
        s = s.replace('</head>', ld + '\n</head>', 1)
        # 5) 顶部品类说明里补总目录入口
        s = s.replace('<p>All products ship FOB Nansha Port, Guangzhou &middot; OEM cross-reference available</p>',
                      '<p>All products ship FOB Nansha Port, Guangzhou &middot; OEM cross-reference available '
                      '&middot; <a href="/parts/index.html" style="color:#c8102e;font-weight:600;">Full catalogue &rarr;</a></p>')
        out[fname] = (s, len(items), len(shown))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    res = build()
    for fname, (s, total, shown) in res.items():
        print('%-26s SKUs=%-4d 静态卡片=%-4d 体积=%d bytes' % (fname, total, shown, len(s)))
        if not args.dry_run:
            open(os.path.join(ROOT, fname), 'w', encoding='utf-8').write(s)
    if not args.dry_run:
        print('已写入 %d 个分类页' % len(res))
    else:
        print('[dry-run] 未写盘')


if __name__ == '__main__':
    main()
