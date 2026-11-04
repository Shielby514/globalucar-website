#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_product_pages.py
=========================
产品页静态化出页（catalog 驱动）。

输入： .workbuddy/data/product-catalog.json
输出：
  parts/<slug>.html            产品页（品牌 / OE 交叉号 / 适配车型 / 规格 / MOQ / 库存 /
                                图片 alt / FAQ 3+ / Product+Offer+FAQPage+Breadcrumb JSON-LD）
  parts/index.html              产品库总索引（600 条，可爬 HTML 链接）
  parts/<type-page slug>.html   泛类型分类 hub 页（沿用既有 URL，不删页）
  sitemap.xml                   追加 /parts/ URL（幂等）
  product-detail.html           旧址 ?id=N 真跳转（location.replace + canonical + noscript）
  products-inline.js            追加新产品的精简记录（列表页筛选用）
  全站 product-detail.html?id=N → /parts/<slug>.html 内链改写

用法：
  python generate_product_pages.py --dry-run
  python generate_product_pages.py
"""
import argparse
import html
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

SITE = 'https://www.global-ucars.com'
PARTS_DIR = os.path.join(ROOT, 'parts')
CATALOG = os.path.join(ROOT, '.workbuddy', 'data', 'product-catalog.json')
SITEMAP = os.path.join(ROOT, 'sitemap.xml')
PRODUCT_DETAIL = os.path.join(ROOT, 'product-detail.html')
PRODUCTS_JS = os.path.join(ROOT, 'products-inline.js')

SYSTEM_PAGE = {
    'engine': ('parts-engine.html', 'Engine & Fuel System'),
    'cooling': ('parts-cooling.html', 'Cooling & Climate'),
    'suspension': ('parts-suspension.html', 'Suspension & Steering'),
    'electrical': ('parts-electrical.html', 'Electrical & Sensors'),
}
SYSTEM_ORDER = ['suspension', 'engine', 'cooling', 'electrical']

CSS = """*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0a0e17;--card:#1a2234;--bd:#2a3550;--tx:#f1f5f9;--tx2:#94a3b8;--ac:#c8102e;--gold:#f59e0b;--r:12px}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg);color:var(--tx);line-height:1.65}
.navbar{position:sticky;top:0;z-index:99;background:rgba(10,14,23,.96);border-bottom:1px solid var(--bd)}
.nav-inner{max-width:1200px;margin:0 auto;display:flex;align-items:center;gap:18px;padding:12px 20px}
.nav-brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--tx);font-weight:700}
.nav-logo{height:36px;border-radius:6px}
.nav-tagline{font-size:12px;color:var(--tx2)}
.nav-menu{display:flex;gap:4px;list-style:none;margin-left:auto;flex-wrap:wrap}
.nav-menu a{color:var(--tx2);text-decoration:none;font-size:13.5px;padding:8px 11px;border-radius:8px}
.nav-menu a:hover{color:var(--tx);background:var(--card)}
.wrap{max-width:1040px;margin:0 auto;padding:26px 20px 60px}
.crumb{font-size:13px;color:var(--tx2);margin-bottom:14px}
.crumb a{color:var(--tx2);text-decoration:none}.crumb a:hover{color:var(--gold)}
h1{font-size:clamp(21px,3.1vw,31px);line-height:1.28;margin-bottom:12px}
.lead{color:var(--tx2);font-size:16px;max-width:860px}
.ans-blk{background:var(--card);border:1px solid var(--bd);border-left:4px solid var(--gold);border-radius:var(--r);padding:16px 18px;margin:18px 0}
.ans-blk p{color:var(--tx2);font-size:15px}
.hero{display:grid;grid-template-columns:minmax(240px,380px) 1fr;gap:26px;margin-top:22px;align-items:start}
@media(max-width:760px){.hero{grid-template-columns:1fr}}
.gallery img{width:100%;border-radius:var(--r);border:1px solid var(--bd);background:var(--card)}
.qcard{background:var(--card);border:1px solid var(--bd);border-radius:var(--r);padding:18px;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}
.qkv{display:flex;flex-direction:column;gap:2px}
.qkv b{font-size:11.5px;color:var(--tx2);text-transform:uppercase;letter-spacing:.06em}
.qkv span{font-size:15px}
.qkv .hl{color:var(--gold);font-weight:600}
.cta{margin-top:16px;display:flex;gap:10px;flex-wrap:wrap}
.cta a{text-decoration:none;padding:12px 22px;border-radius:10px;font-weight:600;font-size:14.5px}
.cta .p{background:var(--ac);color:#fff}.cta .p:hover{filter:brightness(1.1)}
.cta .s{border:1px solid var(--bd);color:var(--tx)}.cta .s:hover{border-color:var(--gold);color:var(--gold)}
.sec{margin-top:32px}
.sec h2{font-size:20px;margin-bottom:12px;border-left:4px solid var(--ac);padding-left:10px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--bd);border-radius:var(--r);overflow:hidden}
th,td{padding:10px 14px;text-align:left;border-bottom:1px solid var(--bd);font-size:14.5px}
th{background:#131a2b;color:var(--tx2);font-size:12.5px;text-transform:uppercase;letter-spacing:.05em}
tr:last-child td{border-bottom:none}
.oe-nums{display:flex;flex-wrap:wrap;gap:8px}
.oe-nums span{background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:6px 12px;font-family:monospace;font-size:14px;color:var(--gold)}
ul.feat{list-style:none;display:grid;gap:8px}
ul.feat li{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 14px;font-size:14.5px;color:var(--tx)}
.rich{color:var(--tx2);font-size:15.5px;max-width:900px}
.rich h2{color:var(--tx);font-size:19px;margin:22px 0 8px;border-left:4px solid var(--ac);padding-left:10px}
.rich h3{color:var(--tx);font-size:16px;margin:16px 0 6px}
.rich p{margin-bottom:10px}
.rich ul,.rich ol{margin:0 0 10px 20px}
.rich li{margin-bottom:4px}
.rel-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px}
.rel-card{background:var(--card);border:1px solid var(--bd);border-radius:var(--r);overflow:hidden;text-decoration:none;color:var(--tx);display:block}
.rel-card:hover{border-color:var(--gold)}
.rel-card img{width:100%;height:130px;object-fit:cover}
.rel-card .rc-b{padding:12px}
.rel-card .rc-t{font-size:14px;font-weight:600;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.rel-card .rc-p{font-size:12.5px;color:var(--gold);margin-top:6px}
.faq dt{font-weight:600;margin:16px 0 6px;font-size:15px}
.faq dd{color:var(--tx2);font-size:14.5px;margin:0 0 8px}
.index-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
.index-grid a{display:block;background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:12px 14px;text-decoration:none;color:var(--tx);font-size:14px}
.index-grid a:hover{border-color:var(--gold)}
.index-grid .ie{font-family:monospace;font-size:12.5px;color:var(--gold)}
footer{border-top:1px solid var(--bd);background:#0d1320;margin-top:56px}
.f-in{max-width:1040px;margin:0 auto;padding:32px 20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:22px;font-size:13.5px;color:var(--tx2)}
.f-in h4{color:var(--tx);font-size:13px;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px}
.f-in a{color:var(--tx2);text-decoration:none;display:block;padding:2px 0}
.f-in a:hover{color:var(--gold)}
.f-bot{text-align:center;padding:14px;border-top:1px solid var(--bd);color:var(--tx2);font-size:12.5px}"""

NAV = """<nav class="navbar"><div class="nav-inner">
  <a href="/index.html" class="nav-brand"><img src="/assets/VEHICLE-logo-nav.jpg" alt="Globalucar" class="nav-logo" onerror="this.style.display='none'"><span class="nav-tagline">Car & Auto Parts One-Stop Solution</span></a>
  <ul class="nav-menu">
    <li><a href="/index.html">Home</a></li><li><a href="/products.html">Products</a></li>
    <li><a href="/parts-finder.html">Parts Finder</a></li><li><a href="/kingmay.html">Kingmay Parts</a></li>
    <li><a href="/services.html">Services</a></li><li><a href="/blog.html">Blog</a></li>
    <li><a href="/contact.html">Contact</a></li>
  </ul>
</div></nav>"""

FOOT = """<footer><div class="f-in">
  <div><h4>KingMay Auto Parts</h4>Guangzhou Globalucar Vehicle Trading Co., Ltd.<br>OEM-grade parts export since 2013.<br>30,000+ SKUs &middot; 50+ brands.</div>
  <div><h4>Quick Links</h4><a href="/products.html">All Products</a><a href="/parts/index.html">Parts Catalogue</a><a href="/parts-finder.html">Parts Finder</a><a href="/kingmay.html">Kingmay Parts</a><a href="/blog.html">Blog</a></div>
  <div><h4>OE Reference</h4><a href="/oe/index.html">OE Number Hub</a><a href="/oe/engine.html">Engine & Fuel</a><a href="/oe/suspension-steering.html">Suspension & Steering</a><a href="/oe/electrical.html">Electrical & Sensors</a></div>
  <div><h4>Contact</h4>Miss UU (Auto Parts)<br><a href="mailto:ku@kingmay-autoparts.com">ku@kingmay-autoparts.com</a><br>+86 133 0240 8528</div>
</div><div class="f-bot">&copy; 2013-2026 Guangzhou Globalucar Vehicle Trading Co., Ltd. All rights reserved.</div></footer>"""


def esc(s):
    return html.escape(str(s if s is not None else ''), quote=True)


def as_list(v):
    if isinstance(v, list):
        return [x for x in v if x]
    if isinstance(v, str):
        try:
            r = json.loads(v)
            return r if isinstance(r, list) else [v]
        except Exception:
            return [x.strip() for x in v.split(',') if x.strip()]
    return []


def as_dict(v):
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            r = json.loads(v)
            return r if isinstance(r, dict) else {}
        except Exception:
            return {}
    return {}


def money(price):
    """从 '$28.00 - $60.00' 之类解析 Offer price；解析不出就返回 None"""
    m = re.search(r'\$\s*([0-9]+(?:\.[0-9]+)?)', str(price or ''))
    if not m:
        return None
    return m.group(1)


def jsonld(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1).replace('</', '<\\/')


def build_related(products, rec, limit=8):
    same_type = [p for p in products if p is not rec and p.get('sub_category') == rec.get('sub_category')]
    same_sys = [p for p in products if p is not rec and p not in same_type
                 and p.get('part_system') == rec.get('part_system')]
    out, seen = [], set()
    for p in same_type + same_sys:
        if p['slug'] in seen:
            continue
        seen.add(p['slug'])
        out.append(p)
        if len(out) >= limit:
            break
    return out


def render_product(rec, products, url_map):
    name = rec.get('name') or 'Auto Part'
    sys_key = rec.get('part_system') or 'engine'
    sys_page, sys_label = SYSTEM_PAGE.get(sys_key, ('products.html', 'Auto Parts'))
    psys = sys_key
    brand = rec.get('brand') or (rec.get('compatible_makes') or ['KingMay'])[0]
    makes = rec.get('compatible_makes') or []
    fitment = rec.get('fitment') or makes
    oes = as_list(rec.get('oem_refs'))
    specs = as_dict(rec.get('specs'))
    feats = as_list(rec.get('features'))
    faqs = rec.get('faq') or []
    if len(faqs) < 3:
        faqs = faqs + [('What is your lead time?', 'Stock references leave Guangzhou within 7 working days; production runs take 25-35 days depending on quantity.'),
                       ('Can you quote FOB or CIF?', 'Yes. We quote FOB Guangzhou and CIF to your destination port once the SKU list is confirmed.'),
                       ('Do you accept sample orders?', 'Yes. Sample and mixed-SKU trial orders are welcome before volume contracts.')]
    imgs = [i for i in as_list(rec.get('images')) if not str(i).startswith('http')]
    if not imgs and rec.get('local_image'):
        imgs = [rec['local_image']]
    main_img = imgs[0] if imgs else 'assets/parts/gen/gen-abs-wheel-speed-sensor.png'
    ogimg = '%s/%s' % (SITE, main_img.lstrip('/'))
    canonical = '%s/parts/%s.html' % (SITE, rec['slug'])
    title = (rec.get('meta_title') or name)[:160]
    desc = (rec.get('meta_description') or '')[:300]
    kw = (rec.get('meta_keywords') or '')[:300]
    alt = rec.get('alt_text') or name
    price = rec.get('price') or 'Contact for Quote'
    moq = rec.get('moq') or '10 Pieces'
    in_stock = bool(rec.get('in_stock'))
    stock_txt = 'In Stock' if in_stock else 'Made to Order'

    # ---- hero ----
    thumbs = ''
    if len(imgs) > 1:
        t = ''.join('<img src="/%s" alt="%s thumbnail" loading="lazy">'
                    % (esc(i.lstrip('/')), esc(alt[:70])) for i in imgs[1:5])
        thumbs = '<div class="thumbs" style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">%s</div>' % t

    fit_short = ' / '.join(fitment[:3]) if fitment else '—'
    qcard = """<div class="qcard">
        <div class="qkv"><b>Part Type</b><span>%s</span></div>
        <div class="qkv"><b>Brand</b><span>%s</span></div>
        <div class="qkv"><b>System</b><span>%s</span></div>
        <div class="qkv"><b>Vehicle</b><span>%s</span></div>
        <div class="qkv"><b>Price</b><span class="hl">%s</span></div>
        <div class="qkv"><b>MOQ</b><span>%s</span></div>
        <div class="qkv"><b>Stock</b><span>%s</span></div>
      </div>""" % (esc(rec.get('sub_category') or 'Auto Part'), esc(brand), esc(sys_label),
                   esc(fit_short[:60]), esc(price), esc(moq), esc(stock_txt))

    # ---- OEM 交叉号 ----
    oem_sec = ''
    if oes:
        chips = ''.join('<span>%s</span>' % esc(o) for o in oes[:14])
        oem_sec = ('<section class="sec"><h2>OEM Reference Numbers</h2>'
                   '<div class="oe-nums">%s</div>'
                   '<p style="margin-top:10px;font-size:13.5px;color:var(--tx2)">'
                   'Send the OE number printed on your original part and we will confirm the exact match before you order.</p>'
                   '</section>' % chips)

    # ---- 适配车型 ----
    fit_sec = ''
    if fitment:
        rows = ''.join('<tr><td>%s</td><td>%s</td></tr>' % (esc(brand), esc(v)) for v in fitment[:12])
        fit_sec = ('<section class="sec"><h2>Vehicle Application</h2>'
                   '<table><thead><tr><th>Make / Brand</th><th>Model / Platform</th></tr></thead>'
                   '<tbody>%s</tbody></table>'
                   '<p style="margin-top:10px;font-size:13.5px;color:var(--tx2)">'
                   'Fitment is confirmed against VIN and build date. We re-check every row in writing before a PI is issued.</p>'
                   '</section>' % rows)

    # ---- 规格 ----
    spec_sec = ''
    if specs:
        rows = ''.join('<tr><th>%s</th><td>%s</td></tr>' % (esc(k), esc(str(v)))
                        for k, v in specs.items())
        spec_sec = '<section class="sec"><h2>Specifications</h2><table><tbody>%s</tbody></table></section>' % rows

    feat_sec = ''
    if feats:
        lis = ''.join('<li>%s</li>' % esc(str(f)[:180]) for f in feats[:8])
        feat_sec = '<section class="sec"><h2>Key Features</h2><ul class="feat">%s</ul></section>' % lis

    desc_html = rec.get('description') or ''
    desc_sec = ('<section class="sec"><h2>Product Details</h2><div class="rich">%s</div></section>' % desc_html
                if desc_html else '')

    logistics = """<section class="sec"><h2>Logistics & Packaging</h2>
      <table><tbody>
        <tr><th>MOQ</th><td>%s</td></tr>
        <tr><th>Price</th><td>%s</td></tr>
        <tr><th>Supply</th><td>RFQ &mdash; quote issued within one business day</td></tr>
        <tr><th>Lead time</th><td>7-15 days for stock references; 25-35 days for production runs</td></tr>
        <tr><th>Packing</th><td>Neutral or Kingmay branded box; anti-rust protection; export pallets</td></tr>
        <tr><th>Shipping</th><td>FOB Guangzhou / Shenzhen, or CIF to your port. Air and sea freight both available.</td></tr>
        <tr><th>Warranty</th><td>12 months against manufacturing defects</td></tr>
      </tbody></table></section>""" % (esc(moq), esc(price))

    faq_html = ''.join('<dt>%s</dt><dd>%s</dd>' % (esc(q), esc(a)) for q, a in faqs[:5])
    faq_sec = ('<section class="sec"><h2>Frequently Asked Questions</h2><dl class="faq">%s</dl></section>' % faq_html)

    rel = build_related(products, rec)
    rel_html = ''
    for r in rel:
        ri = as_list(r.get('images')) or ([r['local_image']] if r.get('local_image') else [])
        ri = [i for i in ri if not str(i).startswith('http')]
        rimg = ri[0] if ri else 'assets/parts/gen/gen-abs-wheel-speed-sensor.png'
        rel_html += ('<a class="rel-card" href="/parts/%s.html"><img src="/%s" alt="%s" loading="lazy">'
                     '<div class="rc-b"><div class="rc-t">%s</div><div class="rc-p">%s</div></div></a>') % (
            esc(r['slug']), esc(rimg.lstrip('/')), esc((r.get('alt_text') or r.get('name', ''))[:70]),
            esc(r.get('name', '')[:70]), esc(r.get('price') or 'RFQ')[:40])
    rel_sec = ('<section class="sec"><h2>Related %s Parts</h2><div class="rel-grid">%s</div></section>'
               % (esc(rec.get('sub_category') or 'Auto'), rel_html)) if rel_html else ''

    # ---- JSON-LD ----
    price_val = money(price)
    offer = {
        '@type': 'Offer',
        'url': canonical,
        'priceCurrency': 'USD',
        'availability': 'https://schema.org/InStock' if in_stock else 'https://schema.org/PreOrder',
        'seller': {'@type': 'Organization', 'name': 'KingMay Auto Parts (Guangzhou Globalucar)'},
    }
    if price_val:
        offer['price'] = price_val
    schema_product = {
        '@context': 'https://schema.org', '@type': 'Product',
        'name': name,
        'sku': 'KM-%s' % rec['id'],
        'mpn': oes[0] if oes else 'KM-%s' % rec['id'],
        'image': ['%s/%s' % (SITE, i.lstrip('/')) for i in imgs[:3]] or [ogimg],
        'description': desc,
        'brand': {'@type': 'Brand', 'name': brand},
        'category': rec.get('sub_category') or 'Auto Part',
        'offers': offer,
    }
    schema_faq = {
        '@context': 'https://schema.org', '@type': 'FAQPage',
        'mainEntity': [{'@type': 'Question', 'name': q,
                        'acceptedAnswer': {'@type': 'Answer', 'text': a}}
                       for q, a in faqs[:5]],
    }
    schema_crumb = {
        '@context': 'https://schema.org', '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Products', 'item': SITE + '/products.html'},
            {'@type': 'ListItem', 'position': 3, 'name': sys_label, 'item': '%s/%s' % (SITE, sys_page)},
            {'@type': 'ListItem', 'position': 4, 'name': name[:90]},
        ],
    }
    schema_page = {
        '@context': 'https://schema.org', '@type': 'WebPage',
        'name': title, 'url': canonical, 'keywords': kw,
        'about': [{'@type': 'Brand', 'name': brand},
                  {'@type': 'DefinedTerm', 'name': rec.get('sub_category') or 'Auto Part'}],
        'speakable': {'@type': 'SpeakableSpecification', 'cssSelector': ['.lead']},
    }
    schema_list = None
    if rel:
        schema_list = {
            '@context': 'https://schema.org', '@type': 'ItemList',
            '@id': canonical + '#related',
            'name': 'Related %s products' % (rec.get('sub_category') or 'auto'),
            'itemListElement': [{'@type': 'ListItem', 'position': i + 1,
                                 'url': '%s/parts/%s.html' % (SITE, r['slug']),
                                 'name': r.get('name', '')[:90]} for i, r in enumerate(rel)],
        }

    rfq = html.escape('%s (SKU KM-%s)' % (name, rec['id']), quote=True)
    html_doc = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%s</title>
<meta name="description" content="%s">
<meta name="keywords" content="%s">
<link rel="canonical" href="%s">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:type" content="product">
<meta property="og:url" content="%s">
<meta property="og:site_name" content="KingMay Auto Parts">
<meta property="og:image" content="%s">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="%s">
<meta name="twitter:description" content="%s">
<meta name="twitter:image" content="%s">
<style>%s</style>
</head>
<body>
%s
<div class="wrap">
  <div class="crumb"><a href="/index.html">Home</a> &rsaquo; <a href="/products.html">Products</a> &rsaquo; <a href="/%s">%s</a> &rsaquo; <span>%s</span></div>
  <h1>%s</h1>
  <p class="lead">%s</p>

  <div class="ans-blk"><p>%s</p></div>

  <div class="hero">
    <div class="gallery">
      <img src="/%s" alt="%s" loading="eager" width="600" height="600">
      %s
    </div>
    <div>
      %s
      <div class="cta">
        <a class="p" href="/contact.html?product=%s" rel="nofollow">Request a Quote (RFQ)</a>
        <a class="s" href="/oem-parts-lookup.html">Search by OE Number</a>
      </div>
    </div>
  </div>

  %s
  %s
  %s
  %s
  %s
  %s
  %s
</div>
%s
%s
<script type="application/ld+json">
%s
</script>
<script type="application/ld+json">
%s
</script>
<script type="application/ld+json">
%s
</script>
<script type="application/ld+json">
%s
</script>
%s
</body>
</html>""" % (
        esc(title), esc(desc), esc(kw), esc(canonical),
        esc(title), esc(desc), esc(canonical), esc(ogimg),
        esc(title), esc(desc), esc(ogimg), CSS,
        NAV,
        esc(sys_page), esc(sys_label), esc(name[:48]),
        esc(name), esc(desc),
        esc('%s. OE reference %s. MOQ %s, FOB/CIF quoted on request, supplied by KingMay Guangzhou.'
            % (name, ' / '.join(oes[:2]) or 'on request', moq)),
        esc(main_img.lstrip('/')), esc(alt),
        thumbs, qcard, rfq,
        oem_sec, fit_sec, spec_sec, feat_sec, desc_sec, logistics, faq_sec,
        rel_sec, FOOT,
        jsonld(schema_product), jsonld(schema_faq), jsonld(schema_crumb), jsonld(schema_page),
        ('<script type="application/ld+json">\n%s\n</script>' % jsonld(schema_list)) if schema_list else '',
    )
    return html_doc


def render_type_page(rec, products, url_map):
    """泛类型页 → 分类 hub（保留原 URL，列出同类型产品）"""
    name = rec.get('name') or rec.get('sub_category') or 'Auto Part'
    slug = rec.get('slug')
    sys_key = rec.get('part_system') or 'engine'
    sys_page, sys_label = SYSTEM_PAGE.get(sys_key, ('products.html', 'Auto Parts'))
    sub = rec.get('sub_category') or name
    sub_l = sub.lower()
    # 子串匹配：'Oil Cooler' 命中 'Engine Oil Cooler' / 'Transmission Oil Cooler'
    kids = [p for p in products if p.get('slug') != slug
            and (p.get('sub_category', '').lower().find(sub_l) >= 0
                 or sub_l in p.get('name', '').lower())]
    total_matched = len(kids)
    same_sys = [p for p in products if p.get('part_system') == sys_key and p not in kids][:60]
    listed = (kids + same_sys)[:120]
    canonical = '%s/parts/%s.html' % (SITE, slug)
    title = '%s Wholesale for %s | KingMay Auto Parts' % (sub, ' / '.join((rec.get('compatible_makes') or ['Hyundai / Kia'])[:2]))
    desc = ('%s catalogue for %s: %d listed SKUs with OE reference numbers, vehicle application, '
            'MOQ and FOB terms from KingMay Guangzhou. Request a quote within one business day.'
            % (sub, ' / '.join((rec.get('compatible_makes') or ['Hyundai / Kia'])[:2]), len(listed)))
    grid = ''.join('<a href="/parts/%s.html"><span class="ie">%s</span><br>%s</a>'
                   % (esc(p['slug']), esc((p.get('oem_refs') or [''])[0]), esc(p.get('name', '')[:80]))
                   for p in listed)
    faqs = [
        ('What is the MOQ for %s?' % sub, 'MOQ is 10 pieces per SKU. Mixed SKUs within the %s family can be consolidated into one export order.' % sub),
        ('How do I confirm the right %s for my vehicle?' % sub.lower(), 'Send the OE number or the VIN. We confirm fitment in writing before issuing the proforma invoice.'),
        ('Can you supply genuine OEM parts as well?', 'Yes. OEM-grade aftermarket is our standard line, and genuine OEM units can be sourced on request.'),
    ]
    schema_item = {
        '@context': 'https://schema.org', '@type': 'ItemList',
        'name': '%s products' % sub,
        'numberOfItems': len(listed),
        'itemListElement': [{'@type': 'ListItem', 'position': i + 1,
                             'url': '%s/parts/%s.html' % (SITE, p['slug']),
                             'name': p.get('name', '')[:90]} for i, p in enumerate(listed)],
    }
    schema_faq = {
        '@context': 'https://schema.org', '@type': 'FAQPage',
        'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}}
                       for q, a in faqs],
    }
    schema_crumb = {
        '@context': 'https://schema.org', '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Parts Catalogue', 'item': SITE + '/parts/index.html'},
            {'@type': 'ListItem', 'position': 3, 'name': sys_label, 'item': '%s/%s' % (SITE, sys_page)},
            {'@type': 'ListItem', 'position': 4, 'name': sub},
        ],
    }
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%s</title>
<meta name="description" content="%s">
<link rel="canonical" href="%s">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:type" content="website">
<meta property="og:url" content="%s">
<meta property="og:site_name" content="KingMay Auto Parts">
<style>%s</style>
</head>
<body>
%s
<div class="wrap">
  <div class="crumb"><a href="/index.html">Home</a> &rsaquo; <a href="/parts/index.html">Parts Catalogue</a> &rsaquo; <a href="/%s">%s</a> &rsaquo; <span>%s</span></div>
  <h1>%s Catalogue</h1>
  <p class="lead">%s</p>
  <div class="ans-blk"><p>KingMay lists %d %s SKUs for %s with OE reference numbers, confirmed vehicle application, MOQ 10 pieces and FOB/CIF terms on request. Mixed-SKU consolidation is available on the same order.</p></div>
  <section class="sec"><h2>Listed SKUs</h2><div class="index-grid">%s</div>
    <p style="margin-top:12px;font-size:13.5px;color:var(--tx2)">Showing %d of %d matching SKUs &mdash; the full catalogue is at <a href="/parts/index.html" style="color:var(--gold)">/parts/index.html</a>.</p>
  </section>
  <section class="sec"><h2>Frequently Asked Questions</h2><dl class="faq">%s</dl></section>
  <section class="sec"><h2>Related Parts</h2><div class="index-grid">
    <a href="/parts/index.html"><span class="ie">Catalogue</span><br>All parts listings</a>
    <a href="/%s"><span class="ie">System</span><br>%s</a>
    <a href="/oem-parts-lookup.html"><span class="ie">OE Lookup</span><br>Search by OE number</a>
  </div></section>
</div>
%s
<script type="application/ld+json">
%s
</script>
<script type="application/ld+json">
%s
</script>
<script type="application/ld+json">
%s
</script>
</body>
</html>""" % (
        esc(title), esc(desc), esc(canonical), esc(title), esc(desc), esc(canonical), CSS, NAV,
        esc(sys_page), esc(sys_label), esc(sub),
        esc(sub), esc(desc), len(listed), esc(sub.lower()),
        ' / '.join((rec.get('compatible_makes') or ['Hyundai / Kia'])[:2]),
        grid,
        len(listed), total_matched,
        ''.join('<dt>%s</dt><dd>%s</dd>' % (esc(q), esc(a)) for q, a in faqs),
        esc(sys_page), esc(sys_label),
        FOOT, jsonld(schema_item), jsonld(schema_faq), jsonld(schema_crumb))


def render_index(products):
    groups = defaultdict(list)
    for p in products:
        groups[p.get('part_system') or 'engine'].append(p)
    out = []
    for sk in SYSTEM_ORDER + [k for k in groups if k not in SYSTEM_ORDER]:
        items = groups.get(sk) or []
        if not items:
            continue
        sys_page, sys_label = SYSTEM_PAGE.get(sk, ('products.html', 'Auto Parts'))
        by_type = defaultdict(list)
        for p in items:
            by_type[p.get('sub_category') or 'Auto Part'].append(p)
        secs = []
        for t, ps in sorted(by_type.items(), key=lambda x: -len(x[1])):
            links = ''.join('<a href="/parts/%s.html"><span class="ie">%s</span><br>%s</a>'
                            % (esc(p['slug']), esc((p.get('oem_refs') or [''])[0]), esc(p.get('name', '')[:80]))
                            for p in ps)
            secs.append('<section class="sec"><h2>%s (%d)</h2><div class="index-grid">%s</div></section>'
                        % (esc(t), len(ps), links))
        out.append('<section class="sec"><h2>%s &mdash; %d SKUs</h2>%s</section>'
                   % (esc(sys_label), len(items), ''.join(secs)))
    total = len(products)
    title = 'Auto Parts Catalogue — %d SKUs | KingMay Wholesale | Globalucar' % total
    desc = ('Wholesale auto parts catalogue: %d engine, cooling, suspension and electrical SKUs '
            'with OE reference numbers, vehicle application, MOQ and FOB terms from KingMay Guangzhou.'
            % total)
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%s</title>
<meta name="description" content="%s">
<link rel="canonical" href="%s/parts/index.html">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:type" content="website">
<meta property="og:url" content="%s/parts/index.html">
<meta property="og:site_name" content="KingMay Auto Parts">
<style>%s</style>
</head>
<body>
%s
<div class="wrap">
  <div class="crumb"><a href="/index.html">Home</a> &rsaquo; <a href="/products.html">Products</a> &rsaquo; <span>Parts Catalogue</span></div>
  <h1>Auto Parts Catalogue</h1>
  <p class="lead">%s</p>
  <div class="ans-blk"><p>KingMay publishes %d wholesale auto part SKUs, each with OE reference numbers, confirmed vehicle application, specifications, MOQ and FOB/CIF terms. Every listing links to its own detail page with fitment tables and a request-for-quote route.</p></div>
  %s
</div>
%s
</body>
</html>""" % (
        esc(title), esc(desc), SITE, esc(title), esc(desc), SITE, CSS, NAV, esc(desc), total,
        ''.join(out), FOOT)


def update_sitemap(slugs):
    if not os.path.exists(SITEMAP):
        return 0, 0
    s = open(SITEMAP, encoding='utf-8').read()
    have = set(re.findall(r'<loc>%s/parts/([^<]+)\.html</loc>' % re.escape(SITE), s))
    add = ''
    for sl in slugs:
        if sl not in have:
            add += ('<url><loc>%s/parts/%s.html</loc>'
                    '<changefreq>monthly</changefreq><priority>0.8</priority></url>') % (SITE, sl)
    if add:
        s = s.replace('</urlset>', add + '</urlset>')
        open(SITEMAP, 'w', encoding='utf-8').write(s)
    return len(have), len(slugs) - len([x for x in slugs if x in have])


def patch_product_detail(url_map):
    """旧址 ?id=N → 真跳转（location.replace）+ canonical + noscript 兜底"""
    s = open(PRODUCT_DETAIL, encoding='utf-8').read()
    inject_map = '<script>window.__PARTS_STATIC__=%s;</script>' % json.dumps(url_map, ensure_ascii=False)
    if '__PARTS_STATIC__' in s:
        s = re.sub(r'<script>window\.__PARTS_STATIC__=.*?</script>',
                   lambda m: inject_map, s, count=1, flags=re.S)
    else:
        s = s.replace('</head>', inject_map + '</head>', 1)
    redirect = """<script>
(function(){var m=location.search.match(/[?&]id=(\\d+)/);if(!m)return;var s=(window.__PARTS_STATIC__||{})[m[1]];if(s){location.replace('/parts/'+s+'.html');}})();
</script>"""
    if '__PARTS_REDIRECT__' not in s:
        s = s.replace('</head>', '<script>window.__PARTS_REDIRECT__=1;</script>' + redirect + '</head>', 1)
    else:
        s = re.sub(r'<script>\n\(function\(\)\{var m=location\.search.*?</script>',
                   lambda m: redirect, s, count=1, flags=re.S)
    noscript = ('<noscript><div style="padding:14px 20px;color:#94a3b8">'
                'This page has moved to a static product page. Enable JavaScript to be redirected, '
                'or open the <a href="/parts/index.html">parts catalogue</a>.</div></noscript>')
    if '__PARTS_STATIC__' in s and '<noscript><div style="padding:14px 20px' not in s:
        s = s.replace('</body>', noscript + '</body>', 1)
    open(PRODUCT_DETAIL, 'w', encoding='utf-8').write(s)
    return len(url_map)


def rewrite_links(url_map):
    """全站 product-detail.html?id=N → /parts/<slug>.html（按完整 id 匹配，避免 2021 误替换 202）"""
    changed = 0
    links = 0
    pat = re.compile(r'(?<![\w/])/?product-detail\.html\?id=(\d+)')
    for dp, dn, fn in os.walk(ROOT):
        if '.git' in dp or 'assets' in dp or dp.endswith(os.path.join('.workbuddy', 'logs')):
            continue
        for f in fn:
            if not f.endswith('.html'):
                continue
            p = os.path.join(dp, f)
            if os.path.abspath(p) == os.path.abspath(PRODUCT_DETAIL):
                continue
            s = open(p, encoding='utf-8', errors='ignore').read()
            orig = s
            cnt = [0]

            def _sub(m):
                slug = url_map.get(m.group(1))
                if not slug:
                    return m.group(0)
                cnt[0] += 1
                return '/parts/%s.html' % slug

            s = pat.sub(_sub, s)
            if s != orig:
                open(p, 'w', encoding='utf-8').write(s)
                changed += 1
                links += cnt[0]
    return changed, links


def append_inline_js(products):
    """把新产品追加进 products-inline.js（精简字段，避免无限膨胀）"""
    if not os.path.exists(PRODUCTS_JS):
        return 0
    s = open(PRODUCTS_JS, encoding='utf-8').read()
    m = re.search(r'window\.PRODUCTS_INLINE_DATA\s*=\s*\{', s)
    if not m:
        return 0
    try:
        data = json.loads(s[m.end() - 1:].rstrip().rstrip(';'))
    except Exception:
        # 退而求其次：抓最后一个 '}' 之前的 JSON
        j = s.rfind('}')
        try:
            data = json.loads(s[m.end() - 1:j + 1])
        except Exception:
            return 0
    arr = data.get('products') or []
    by_id = {p.get('id'): p for p in arr}
    added = 0
    updated = 0
    for p in products:
        slim = {
            'id': p['id'], 'name': p.get('name', '')[:120], 'category': 'parts',
            'brand': p.get('brand') or 'KingMay',
            'sub_category': p.get('sub_category') or 'Auto Part',
            'part_system': p.get('part_system'), 'part_system_label': p.get('part_system_label'),
            'system': p.get('system') or p.get('part_system'),
            'slug': p.get('slug'), 'price': p.get('price'), 'moq': p.get('moq'),
            'in_stock': p.get('in_stock'), 'featured': False,
            'local_image': p.get('local_image'), 'images': (p.get('images') or [])[:3],
            'oem_refs': (p.get('oem_refs') or [])[:6],
            'compatible_makes': (p.get('compatible_makes') or [])[:4],
            'features': (p.get('features') or [])[:3],
            'meta_title': (p.get('meta_title') or '')[:160],
            'meta_description': (p.get('meta_description') or '')[:300],
            'alt_text': (p.get('alt_text') or '')[:180],
        }
        old = by_id.get(p['id'])
        if old is None:
            arr.append(slim)
            added += 1
        else:
            # 补齐/刷新我们管理的字段（不删除既有额外字段）
            for k, v in slim.items():
                if k in ('id', 'category'):
                    continue
                if old.get(k) in (None, '', [], {}) or k in ('system', 'features', 'slug',
                                                           'local_image', 'compatible_makes',
                                                           'meta_title', 'meta_description'):
                    if old.get(k) != v:
                        old[k] = v
                        updated += 1
    data['products'] = arr
    new_js = s[:m.start()] + 'window.PRODUCTS_INLINE_DATA = ' + json.dumps(data, ensure_ascii=False, indent=1) + ';\n'
    open(PRODUCTS_JS, 'w', encoding='utf-8').write(new_js)
    return added, updated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-links', action='store_true')
    args = ap.parse_args()

    cat = json.load(open(CATALOG, encoding='utf-8'))
    products = cat['products'] if isinstance(cat, dict) else cat
    type_pages = cat.get('type_pages', []) if isinstance(cat, dict) else []
    print('目录：产品 %d / 分类 hub %d' % (len(products), len(type_pages)))

    os.makedirs(PARTS_DIR, exist_ok=True)
    url_map = {str(p['id']): p['slug'] for p in products}

    n = 0
    for p in products:
        doc = render_product(p, products, url_map)
        out = os.path.join(PARTS_DIR, p['slug'] + '.html')
        if not args.dry_run:
            open(out, 'w', encoding='utf-8').write(doc)
        n += 1
    print('产品页出页：%d' % n)

    t = 0
    for tp in type_pages:
        doc = render_type_page(tp, products, url_map)
        out = os.path.join(PARTS_DIR, tp['slug'] + '.html')
        if not args.dry_run:
            open(out, 'w', encoding='utf-8').write(doc)
        t += 1
    print('分类 hub 页：%d' % t)

    if not args.dry_run:
        open(os.path.join(PARTS_DIR, 'index.html'), 'w', encoding='utf-8').write(render_index(products))
        print('目录索引页：parts/index.html')

        have, added = update_sitemap([p['slug'] for p in products] + [t['slug'] for t in type_pages])
        print('sitemap：已有 /parts/ %d 条，新增 %d 条' % (have, added))

        added_js, upd_js = append_inline_js(products)
        print('products-inline.js：追加 %d 条 / 补齐更新 %d 字段' % (added_js, upd_js))

        cnt = patch_product_detail(url_map)
        print('product-detail.html：跳转映射 %d 条' % cnt)

        if not args.no_links:
            ch, lk = rewrite_links(url_map)
            print('内链改写：%d 个文件，静态链接约 %d 条' % (ch, lk))


if __name__ == '__main__':
    main()
