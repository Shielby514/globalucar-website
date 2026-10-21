# -*- coding: utf-8 -*-
"""wholesale 站内接线 + 主站反链注入。

1) 重建 wholesale sitemap（首页 + 全部聚合页）
2) wholesale 首页 #parts 区加聚合页导航
3) 主站 3 个入口页（index / parts-finder / oem-parts-lookup）注入 wholesale 聚合页区块
   —— 解决「主站 0 内链 -> wholesale」的孤儿问题

用法: python wire_wholesale_links.py
"""
import os, re, sys, json, time, html

WS = r'C:\Users\123\WorkBuddy\wholesale-portal'
MAIN = r'C:\Users\123\WorkBuddy\20260324111450'
SITE = 'https://wholesale.global-ucars.com'
MAINURL = 'https://www.global-ucars.com'

BRAND_PAGES = [
    ('wholesale-hyundai-parts', 'Hyundai'),
    ('wholesale-kia-parts', 'Kia'),
    ('wholesale-toyota-parts', 'Toyota'),
    ('wholesale-nissan-parts', 'Nissan'),
    ('wholesale-mercedes-parts', 'Mercedes-Benz'),
    ('wholesale-bmw-parts', 'BMW'),
    ('wholesale-audi-parts', 'Audi'),
    ('wholesale-volkswagen-parts', 'Volkswagen'),
]
CAT_PAGES = [
    ('wholesale-brake-parts', 'Brake parts'),
    ('wholesale-suspension-parts', 'Suspension parts'),
    ('wholesale-engine-parts', 'Engine parts'),
    ('wholesale-cooling-parts', 'Cooling system'),
    ('wholesale-electrical-parts', 'Electrical'),
    ('wholesale-filters-parts', 'Filters'),
    ('wholesale-transmission-parts', 'Transmission & clutch'),
    ('wholesale-steering-parts', 'Steering'),
    ('wholesale-body-parts', 'Body parts'),
    ('wholesale-fuel-parts', 'Fuel system'),
]


def esc(s):
    return html.escape(s, quote=True)


# ---------------- 1. sitemap ----------------
def build_sitemap(pages):
    today = time.strftime('%Y-%m-%d')
    urls = [f'{SITE}/']
    for slug in pages:
        urls.append(f'{SITE}/{slug}/')
    body = ''.join(
        f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{today}</lastmod>\n"
        f"    <changefreq>weekly</changefreq>\n    <priority>{'1.0' if u == SITE + '/' else '0.8'}</priority>\n  </url>\n"
        for u in urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f'{body}</urlset>\n')
    open(os.path.join(WS, 'sitemap.xml'), 'w', encoding='utf-8', newline='').write(xml)
    return len(urls)


# ---------------- 2. wholesale 首页导航 ----------------
def wire_home(pages):
    f = os.path.join(WS, 'index.html')
    h = open(f, encoding='utf-8').read()
    # 移除旧的注入块（幂等）
    h = re.sub(r'\n<!-- WS-HUBS -->[\s\S]*?<!-- /WS-HUBS -->\n', '\n', h)
    bchips = ''.join(f'<a class="chip" href="{SITE}/{s}/">{esc(n)}</a>'
                     for s, n in BRAND_PAGES)
    cchips = ''.join(f'<a class="chip" href="{SITE}/{s}/">{esc(n)}</a>'
                     for s, n in CAT_PAGES)
    block = (f'\n<!-- WS-HUBS -->\n'
             f'<section>\n  <div class="wrap">\n'
             f'    <h2>Wholesale parts by vehicle brand</h2>\n'
             f'    <p class="sub">Each page lists the OE numbers we can quote for that brand.</p>\n'
             f'    <div class="chips">{bchips}</div>\n'
             f'    <h2 style="margin-top:34px">Wholesale parts by system</h2>\n'
             f'    <div class="chips">{cchips}</div>\n'
             f'  </div>\n</section>\n<!-- /WS-HUBS -->\n')
    # 插到 #parts 区之后（在 <section class="why"> 之前）
    anchor = '<section class="why">'
    if anchor in h:
        h = h.replace(anchor, block + '\n' + anchor, 1)
    else:
        h = h.replace('</body>', block + '</body>', 1)
    # 补 CSS（chips）
    if '.chips{' not in h:
        h = h.replace('</style>',
                      '.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:16px}\n'
                      '.chip{display:inline-block;padding:7px 14px;border:1px solid #d1d5db;border-radius:20px;'
                      'font-size:13.5px;color:#0c2d50;text-decoration:none;background:#fff}\n'
                      '.chip:hover{border-color:#0c2d50;background:#f8fafc}\n</style>', 1)
    open(f, 'w', encoding='utf-8', newline='').write(h)
    return True


# ---------------- 3. 主站入口页注入 ----------------
MAIN_BLOCK_CSS = """
.wsgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin:18px 0}
.wsgrid a{display:block;padding:14px 16px;border:1px solid #e5e7eb;border-radius:10px;text-decoration:none;
  background:#fff;font-size:14px;font-weight:600;color:#0c2d50;transition:.15s}
.wsgrid a:hover{border-color:#0c2d50;background:#f8fafc;transform:translateY(-1px)}
.wsgrid a span{display:block;font-size:12px;font-weight:400;color:#6b7280;margin-top:3px}
"""
MAIN_BLOCK = """
<!-- WS-LINK -->
<section class="ws-block" style="padding:44px 0;background:#f8fafc">
  <div class="wrap">
    <h2 style="font-size:24px;margin-bottom:6px">Buying in bulk? Wholesale pages with consolidated quotes</h2>
    <p style="color:#6b7280;margin-bottom:4px">
      Every page lists the OE numbers we hold for that brand or system, with MOQ-free mixed container loading.
    </p>
    <div class="wsgrid">
      __LINKS__
    </div>
    <p style="margin-top:16px"><a href="https://wholesale.global-ucars.com/" rel="noopener">
      <b>Open the wholesale portal &rarr;</b></a> One RFQ, one consolidated quote within 24 hours.</p>
  </div>
</section>
<!-- /WS-LINK -->
"""


def wire_main(pages):
    targets = [os.path.join(MAIN, 'index.html'),
               os.path.join(MAIN, 'parts-finder.html'),
               os.path.join(MAIN, 'oem-parts-lookup.html')]
    links = ''.join(
        f'      <a href="{SITE}/{s}/" rel="noopener">{esc(n)} wholesale'
        f'<span>OE list + container loading</span></a>\n'
        for s, n in (BRAND_PAGES[:4] + CAT_PAGES[:4]))
    done = []
    for f in targets:
        if not os.path.exists(f):
            print(f'  缺 {os.path.basename(f)}')
            continue
        h = open(f, encoding='utf-8', errors='ignore').read()
        h = re.sub(r'\n?<!-- WS-LINK -->[\s\S]*?<!-- /WS-LINK -->\n?', '\n', h)
        blk = MAIN_BLOCK.replace('__LINKS__', links.rstrip('\n'))
        if '.wsgrid{' not in h:
            h = re.sub(r'</style>', MAIN_BLOCK_CSS + '</style>', h, count=1)
        # 插到 footer 前
        if '<footer' in h:
            i = h.rfind('<footer')
            h = h[:i] + blk + '\n' + h[i:]
        else:
            h = h.replace('</body>', blk + '</body>', 1)
        open(f, 'w', encoding='utf-8', newline='').write(h)
        done.append(os.path.basename(f))
    return done


def main():
    pages = [s for s, _ in BRAND_PAGES + CAT_PAGES]
    exist = [p for p in pages if os.path.exists(os.path.join(WS, p, 'index.html'))]
    print(f'聚合页 {len(exist)}/{len(pages)}')

    n = build_sitemap(exist)
    print(f'sitemap: {n} URL -> {WS}\\sitemap.xml')

    wire_home(exist)
    print('wholesale 首页: 已注入聚合页导航')

    for f in wire_main(exist):
        print(f'主站 {f}: 已注入 wholesale 区块')

    # 校验
    sm = open(os.path.join(WS, 'sitemap.xml'), encoding='utf-8').read()
    print(f'\n校验: sitemap <loc> {sm.count("<loc>")}')
    for f in ['index.html', 'parts-finder.html', 'oem-parts-lookup.html']:
        p = os.path.join(MAIN, f)
        if os.path.exists(p):
            h = open(p, encoding='utf-8', errors='ignore').read()
            print(f'  主站 {f:24s} wholesale 链接 {h.count(chr(34)+SITE)} 个')
    hi = open(os.path.join(WS, 'index.html'), encoding='utf-8').read()
    print(f'  wholesale 首页 指向聚合页链接 {len(set(re.findall(chr(34)+SITE+"/(wholesale-[a-z]+)/"+chr(34), hi)))} 个')
    return 0


if __name__ == '__main__':
    sys.exit(main())
