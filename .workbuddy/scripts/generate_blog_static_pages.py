#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
博客静态化出页（P0 改版核心）
- 数据源：.workbuddy/data/blog-posts.json（125 篇，已从 blog-post.html 反抽持久化）
- 每篇 → blog/{slug}.html 真静态页（完整 meta / OG / Twitter / Article+Breadcrumb JSON-LD /
  TOC / Quick Answer / OE 库导流块 / 相关产品 / 相关文章 / 侧栏）
- 旧 blog-post.html 替换为 2KB 跳转 stub（id→slug 映射 + location.replace + noscript 兜底）
- blog.html / index.html 旧链接 blog-post.html?id=N → /blog/{slug}.html
- sitemap.xml：移除 blog-post.html?id=N，登记 /blog/{slug}.html
- 幂等，可重复运行
用法: python generate_blog_static_pages.py [--only-pages]
"""
import json, os, re, sys, html as htmlmod
from datetime import datetime
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE = "https://www.global-ucars.com"
DATA = os.path.join(ROOT, ".workbuddy", "data")
BLOG_DIR = os.path.join(ROOT, "blog")
BAK = os.path.join(DATA, "blog-post.html.bak")   # 原始 2.78MB 页（模板骨架来源）
SITEMAP = os.path.join(ROOT, "sitemap.xml")
TODAY = datetime.now().strftime("%Y-%m-%d")

# ── 数据 ─────────────────────────────────────────────
POSTS = json.load(open(os.path.join(DATA, "blog-posts.json"), encoding="utf-8"))
POST_IMAGES = json.load(open(os.path.join(DATA, "blog-post-images.json"), encoding="utf-8"))
_prods = json.load(open(os.path.join(ROOT, "products-data.json"), encoding="utf-8"))
PRODUCTS = _prods if isinstance(_prods, list) else _prods.get("products", _prods)
PART_URL = {str(p["id"]): p.get("slug") for p in PRODUCTS if p.get("category") == "parts" and p.get("slug")}

# 断链图片修复映射（原 JS 版同样断链，被 onerror 隐藏；静态化后统一指到真实存在的文件）
IMG_FIX = {
    "assets/parts/part_066_control_arm.jpg": "assets/parts/part_061_control_arm.jpg",
    "assets/images/factory-container-loading-02.jpg": "assets/gallery/factory-cage-transport-01.jpg",
    "assets/blog/hyundai-kia-ac-compressor-condenser-wholesale.jpg": "assets/parts/part_053_ac_compressor.jpg",
    "assets/blog/brake-system-components-diagram.jpg": "assets/blog/brake-pads-comparison.jpg",
    "assets/blog/hyundai-kia-timing-chain-kit-tensioner.jpg": "assets/blog/hyundai-kia-timing-chain-kit-tensioner-wholesale.jpg",
    "assets/blog/hyundai-kia-fuel-injector-rail-pump.jpg": "assets/blog/kia-fuel-pump-assembly-module-wholesale.jpg",
    "assets/blog/tie-rod-end-hyundai-kia.jpg": "assets/blog/inner-tie-rod-rack-end-steering-linkage-bulk.jpg",
    "assets/products/product_221.jpg": "assets/parts/part_044_engine_piston.jpg",
    "assets/blog/steering-suspension-power-steering-pump.jpg": "assets/blog/kingmay-power-steering-rack-hyundai-wholesale.jpg",
    "assets/blog/power-steering-pump-hyundai-kia.jpg": "assets/blog/kingmay-power-steering-rack-hyundai-wholesale.jpg",
    "assets/blog/control-arm-lower-front-hyundai.jpg": "assets/parts/part_165_control_arm_tucson.jpg",
    "assets/blog/hyundai-kia-turbocharger-assembly-actuator-wholesale.jpg": "assets/parts/part_044_engine_piston.jpg",
    "assets/products/product_163.jpg": "assets/products/product_162.jpg",
}

def fix_img(path):
    return IMG_FIX.get(path, path)

# ── slug 处理 ────────────────────────────────────────
def slugify(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:78].rstrip("-")

SLUGS = {}
def post_slug(p):
    s = p.get("slug") or slugify(p.get("title") or "untitled")
    # 原始 slug 可能带空格/大写等非法 URL 字符（如 'x peng-g6-...'），统一清洗
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", s).strip("-").lower()
    if s in SLUGS.values():
        s = s + "-" + str(p["id"])
    SLUGS[p["id"]] = s
    return s

ID2SLUG = {p["id"]: post_slug(p) for p in POSTS}
BY_ID = {p["id"]: p for p in POSTS}

def post_url(p):
    return SITE + "/blog/" + ID2SLUG[p["id"]] + ".html"

# ── 工具 ─────────────────────────────────────────────
def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()

def esc(s):
    # 属性一律双引号包裹，只需转义 & < >（单引号转成 &#x27; 会污染可见文本）
    return htmlmod.escape(str(s or ""), quote=False)

def meta_desc(p):
    d = p.get("description") or p.get("excerpt") or strip_tags(p.get("content") or "")[:280]
    return d[:300].rstrip()

MONTHS_MAP = {m.lower(): i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}
for _m, _i in list(MONTHS_MAP.items()):
    MONTHS_MAP[_m[:3]] = _i


def iso_date(p):
    """把历史上混杂的日期写法统一成 YYYY-MM-DD。

    线上实测存在 4 种写法，旧的实现只认 3 种格式，其余全部 fallback 到同一个
    固定日期 —— 导致几十篇文章的 datePublished 是错的：
      "2026-06" / "2026-06-15" / "April 1" / "July 20," / "October" / "Novembe..."
    """
    raw = (p.get("date") or "").strip()
    if not raw:
        return "2026-03-24"
    # 1) 完整 ISO
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", raw)
    if m:
        return raw
    # 2) 年月
    m = re.match(r"^(\d{4})-(\d{2})$", raw)
    if m:
        return "%s-%s-01" % (m.group(1), m.group(2))
    # 3) "Month D, YYYY" / "Month D YYYY" / "Month D" / "Month"
    m = re.match(r"^([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s*(\d{4})?$", raw)
    if m:
        mon = MONTHS_MAP.get(m.group(1).lower())
        if mon:
            day = max(1, min(28, int(m.group(2))))
            year = m.group(3) or "2026"
            return "%s-%02d-%02d" % (year, mon, day)
    m = re.match(r"^([A-Za-z]{3,9})\.?,?\s*(\d{4})?$", raw)
    if m:
        mon = MONTHS_MAP.get(m.group(1).lower())
        if mon:
            year = m.group(2) or "2026"
            return "%s-%02d-01" % (year, mon)
    # 4) 兜底：找任意 "Month" + 4 位年份
    m = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s*(\d{4})", raw)
    if m:
        mon = MONTHS_MAP.get(m.group(1).lower())
        if mon:
            return "%s-%02d-%02d" % (m.group(3), mon, max(1, min(28, int(m.group(2)))))
    return "2026-03-24"

def feat_image(p):
    img = p.get("image") or POST_IMAGES.get(str(p["id"])) or POST_IMAGES.get(p["id"]) or "assets/parts/part_044_engine_piston.jpg"
    return fix_img(img)

# 正文链接改写：旧博客互链 → 新静态 URL；产品详情 → parts 静态页
def rewrite_content_links(c):
    def blog_sub(m):
        pid = m.group(1)
        if pid.isdigit() and int(pid) in ID2SLUG:
            return "/blog/" + ID2SLUG[int(pid)] + ".html"
        return "/blog.html"
    c = re.sub(r"blog-post\.html\?id=(\d+)", blog_sub, c)
    def prod_sub(m):
        pid = m.group(1)
        if pid in PART_URL:
            return "/parts/" + PART_URL[pid] + ".html"
        return "/product-detail.html?id=" + pid
    c = re.sub(r"product-detail\.html\?id=(\d+)", prod_sub, c)
    # 断链图片修复（src 与 href 都覆盖）
    for bad, good in IMG_FIX.items():
        c = c.replace('src="%s"' % bad, 'src="%s"' % good)
        c = c.replace('href="%s"' % bad, 'href="%s"' % good)
    return c

# 相对 URL → 根相对（页面在 /blog/ 子目录）
def rootrel(html_str):
    def fix(m):
        attr, url = m.group(1), m.group(2)
        if url.startswith(("http", "//", "#", "mailto:", "tel:", "data:", "javascript:", "/")):
            return m.group(0)
        return '%s="/%s"' % (attr, url.lstrip("./"))
    return re.sub(r'(src|href)="([^"]*)"', fix, html_str)

# ── 模板骨架 ─────────────────────────────────────────
def build_skeleton():
    c = open(BAK, encoding="utf-8").read()
    bp = c.find("const BLOG_POSTS")
    sm = c.rfind("<script", 0, bp)
    skel = c[:sm]

    # 1. 去掉 head 里动态 canonical 的 IIFE（静态页不需要）
    skel = re.sub(
        r"<script>\s*\(function\(\)\{[^<]*?post-canonical[^<]*?\}\)\(\);\s*</script>",
        "", skel, count=1)

    # 2. navbar 加 OE 库入口（全站权重导流）
    nav_old = '<li role="none"><a href="kingmay.html"      role="menuitem" class="nav-link">Kingmay Parts</a></li>'
    nav_new = nav_old + '\n        <li role="none"><a href="/oe/"               role="menuitem" class="nav-link">OE Parts</a></li>'
    skel = skel.replace(nav_old, nav_new, 1)

    # 3. 追加 Quick Answer / OE 导流块样式（插在内联 style 块尾部）
    extra_css = """
    /* ── Quick Answer (AEO) ──────────────────── */
    .qa-box {
      background: #eef6ff; border-left: 4px solid #2980b9;
      padding: 14px 20px; border-radius: 0 8px 8px 0; margin: 0 0 26px;
      font-size: 0.95rem; color: #334;
    }
    .qa-box strong { color: #1a6090; }
    /* ── OE Library CTA ──────────────────────── */
    .oe-cta {
      margin: 40px 0 8px; padding: 26px 28px;
      background: linear-gradient(135deg, #0d1f3c 0%, #1a3a6e 100%);
      border-radius: 12px; color: #e7edf7;
    }
    .oe-cta h2 { color: #fff; font-size: 1.2rem; font-weight: 800; margin-bottom: 8px; border-bottom: none; }
    .oe-cta p { font-size: 0.9rem; color: #b8c6dd; margin-bottom: 14px; }
    .oe-cta-links { display: flex; flex-wrap: wrap; gap: 10px; }
    .oe-cta-links a {
      font-size: 0.82rem; font-weight: 700; text-decoration: none;
      color: #fff; background: rgba(255,255,255,0.12);
      border: 1px solid rgba(255,255,255,0.25);
      padding: 8px 14px; border-radius: 8px; transition: background 0.2s;
    }
    .oe-cta-links a:hover { background: #c8102e; border-color: #c8102e; }
    .oe-cta-links a.oe-all { background: #c8102e; border-color: #c8102e; }
    .oe-cta-links a.oe-all:hover { background: #e63950; }
"""
    skel = skel.replace("</style>", extra_css + "  </style>", 1)

    # 4. sidebar CTA 加一行 OE 库入口
    cta_old = '<a href="products.html">Browse Products →</a>'
    cta_new = cta_old + '\n        <a href="/oe/" style="display:block;margin-top:8px;">Search 236,000+ OE Numbers →</a>'
    skel = skel.replace(cta_old, cta_new, 1)
    return skel

SKELETON = build_skeleton()

def set_attr_by_id(html_str, id_, attr, value):
    """替换 <tag id="..." ... attr="..."> 的属性值"""
    pat = re.compile(r'(<[^>]*\bid="%s"[^>]*\b%s=")[^"]*(")' % (re.escape(id_), attr))
    return pat.sub(lambda m: m.group(1) + value + m.group(2), html_str, count=1)

def set_tag_text(html_str, id_, text):
    pat = re.compile(r'(<[^>]*\bid="%s"[^>]*>)[^<]*(</[^>]+>)' % re.escape(id_))
    return pat.sub(lambda m: m.group(1) + text + m.group(2), html_str, count=1)

# ── OE 导流块 ────────────────────────────────────────
OE_HUBS = [
    ("engine",        "/oe/engine.html",             "Engine & Fuel System"),
    ("cooling",       "/oe/cooling.html",            "Cooling & Climate"),
    ("electrical",    "/oe/electrical.html",         "Electrical & Sensors"),
    ("brake",         "/oe/brake.html",             "Brake System"),
    ("transmission",  "/oe/transmission.html",       "Transmission & Drivetrain"),
    ("suspension",    "/oe/suspension-steering.html","Suspension & Steering"),
    ("body",          "/oe/body.html",               "Body & Exterior"),
]
OE_KW = {
    "engine": ["engine", "cylinder", "piston", "gasket", "timing belt", "timing chain", "valve", "oil pump", "fuel pump", "injector", "turbo", "catalytic", "exhaust", "intake"],
    "cooling": ["radiator", "water pump", "thermostat", "cooling", "coolant", "condenser", "compressor", "a/c", "air conditioning", "blower"],
    "electrical": ["alternator", "starter", "ignition", "spark plug", "ignition coil", "sensor", "battery", "wiring", "ecu", "oxygen sensor", "abs sensor", "switch"],
    "brake": ["brake", "brake pad", "brake disc", "rotor", "caliper", "brake hose", "master cylinder"],
    "transmission": ["transmission", "gearbox", "clutch", "cv joint", "drive shaft", "differential", "axle"],
    "suspension": ["suspension", "control arm", "ball joint", "shock", "strut", "sway bar", "tie rod", "wheel bearing", "spring", "steering"],
    "body": ["headlight", "taillight", "bumper", "mirror", "fender", "grille", "door", "hood", "windshield", "glass", "panel"],
}

def kw_string(p):
    """keywords 字段历史上是逗号分隔字符串，新草稿是数组 —— 两种都要能吃。"""
    k = p.get("keywords")
    if isinstance(k, (list, tuple)):
        return ", ".join(str(x).strip() for x in k if str(x).strip())
    return str(k or "")


def oe_links_html(p):
    text = ((p.get("title") or "") + " " + " ".join(p.get("tags") or []) + " " +
            kw_string(p) + " " + strip_tags((p.get("content") or "")[:6000])).lower()
    matched = [(k, u, lbl) for k, u, lbl in OE_HUBS if any(w in text for w in OE_KW[k])]
    matched = matched[:3]
    links = ['<a href="%s">%s OE Numbers</a>' % (u, lbl) for k, u, lbl in matched]
    links.append('<a class="oe-all" href="/oe/">Browse All 236,000+ OE Numbers →</a>')
    if matched:
        blurb = ("Every part covered in this guide has a matching OE number in our reference library — "
                 "grouped by system with cross-references, so you can source the exact fit for Hyundai, Kia, GM Korea and more.")
    else:
        blurb = ("Cross-check any part number against our verified OE reference library — "
                 "236,000+ OE numbers grouped by system with cross-reference and fitment data.")
    return """
      <section class="oe-cta" aria-label="OE number library">
        <h2>Verify Part Numbers in Our OE Library</h2>
        <p>%s</p>
        <div class="oe-cta-links">%s</div>
      </section>""" % (blurb, "\n          ".join(links))

# ── 相关产品（复刻原 JS 的 KEYWORD_MAP 逻辑，静态化）──
SYS_KW = {
    "engine": ["engine", "cylinder", "piston", "gasket", "valve", "sensor", "oil pump", "fuel pump", "intake", "exhaust", "turbo", "catalytic", "oxygen sensor", "oxygen"],
    "cooling": ["cooling", "radiator", "water pump", "thermostat", "fan", "coolant", "heater"],
    "suspension": ["suspension", "control arm", "ball joint", "sway bar", "stabilizer", "strut", "shock", "coil spring", "leaf spring"],
    "electrical": ["electrical", "alternator", "starter", "wiring", "battery", "ignition", "spark", "ecu", "sensor", "switch", "lock cylinder"],
}
SYS_LABEL = {"engine": "Engine System", "cooling": "Cooling System", "suspension": "Suspension System", "electrical": "Electrical System"}

def sys_of_product(p):
    s = p.get("slug") or ""
    for k in ("suspension", "electrical", "engine", "cooling"):
        if s.startswith("parts-" + k):
            return k
    return None

def related_products(p):
    cat = p.get("category") or ""
    tags = list(p.get("tags") or []) + [k.strip() for k in kw_string(p).split(",") if k.strip()]
    parts_all = [x for x in PRODUCTS if x.get("category") == "parts" and x.get("slug")]
    label = ""
    sel = []
    if "Parts" in cat:
        detected = None
        for kw in tags:
            l = kw.lower()
            for sysname, words in SYS_KW.items():
                if any(w in l for w in words):
                    detected = sysname
                    break
            if detected:
                break
        if detected:
            sel = [x for x in parts_all if sys_of_product(x) == detected][:4]
            label = "From our %s catalog — %d products ready for export" % (SYS_LABEL[detected], len(sel))
        if not sel:
            sel = parts_all[:4]
            label = "From our Auto Parts catalog — %d export-ready products" % len(sel)
    elif "Vehicles" in cat or "Vehicle" in cat:
        new = [x for x in PRODUCTS if x.get("category") == "new_car"][:2]
        used = [x for x in PRODUCTS if x.get("category") == "used_car"][:2]
        sel = new + used
        label = "From our Vehicle Export catalog — new &amp; used cars ready for international delivery"
    else:
        sel = parts_all[:4]
        label = "Popular auto parts from our export catalog"
    cards = []
    for x in sel:
        img = x.get("local_image") or ""
        if not isinstance(img, str) or not img.startswith("assets"):
            img = ""
        cat_label = x.get("sub_category") or ("New Car" if x.get("category") == "new_car" else "Used Car" if x.get("category") == "used_car" else "Auto Part")
        name = x.get("name") or ""
        name_short = name[:52] + "…" if len(name) > 55 else name
        price = (x.get("price") or "FOB Price on Request").replace("US $", "US$")
        if x.get("category") == "parts" and x.get("slug"):
            detail = "/parts/" + x["slug"] + ".html"
        else:
            detail = "/product-detail.html?id=" + str(x["id"])
        cards.append('<div class="product-mini-card">'
                     '<img class="p-img" src="%s" alt="%s" loading="lazy" onerror="this.style.display=\'none\'" />'
                     '<div class="p-body"><p class="p-cat">%s</p><p class="p-name">%s</p>'
                     '<p class="p-price">%s</p><a href="%s" class="p-btn">View Details</a></div></div>'
                     % (esc(img), esc(name), esc(cat_label), esc(name_short), esc(price), detail))
    return label, "\n          ".join(cards)

# ── 单页渲染 ─────────────────────────────────────────
def ensure_toc(p):
    """返回 (toc_list, content)：无 toc 字段的文章从 h2 自建（并给 h2 注入 id）"""
    content = p.get("content") or ""
    toc = p.get("toc")
    if toc:
        return toc, content
    hs = list(re.finditer(r"<h2([^>]*)>(.*?)</h2>", content, re.S))
    if not hs:
        return [], content
    out, last = [], 0
    for i, m in enumerate(hs, 1):
        attrs, inner = m.group(1), m.group(2)
        sid = "s%d" % i
        idm = re.search(r'id="([^"]+)"', attrs)
        if idm:
            sid = idm.group(1)
        else:
            attrs = attrs + ' id="%s"' % sid
        new_tag = "<h2%s>%s</h2>" % (attrs, inner)
        content = content[:m.start()] + new_tag + content[m.end():]
        out.append(strip_tags(inner)[:90])
        # 重扫（位置已变）
        hs = list(re.finditer(r"<h2([^>]*)>(.*?)</h2>", content, re.S))
    return out, content

def extract_faq(content):
    """从正文抽 FAQ 问答对。

    优先找 class="faq" 的 section；否则找标题含 FAQ 的 h2 之后的片段。
    形如 <h3>问题</h3><p>答案</p>（允许中间夹别的标签）。
    """
    if not content:
        return []
    # 新版文章每条问答一个 <section class="faq">；旧版是单个 section 内多个 h3。
    # 两种都要收全，否则 FAQPage JSON-LD 只会有 1 条。
    segs = []
    for mm in re.finditer(r'<section[^>]*class="[^"]*\bfaq\b[^"]*"[^>]*>(.*?)</section>',
                          content, re.S | re.I):
        segs.append(mm.group(1))
    if not segs:
        m = re.search(r"<h2[^>]*>[^<]*FAQ[^<]*</h2>(.*)$", content, re.S | re.I)
        if m:
            segs.append(m.group(1))
    pairs = []
    seen = set()
    for seg in segs:
        for mm in re.finditer(r"<h3[^>]*>(.*?)</h3>(.*?)(?=<h3[^>]*>|$)", seg, re.S | re.I):
            q = strip_tags(mm.group(1)).strip()
            a = strip_tags(mm.group(2)).strip()
            if not q or not a or len(q) > 200 or len(a) > 900:
                continue
            key = q.lower()
            if key in seen:
                continue
            seen.add(key)
            pairs.append((q, a))
    return pairs


def render_post(p):
    slug = ID2SLUG[p["id"]]
    url = SITE + "/blog/" + slug + ".html"
    title = p.get("title") or "Untitled"
    desc = meta_desc(p)
    kws = kw_string(p) or ", ".join(p.get("tags") or []) or "auto parts, car export, China"
    date_iso = iso_date(p)
    img = feat_image(p)
    readtime = p.get("readtime") or p.get("readTime") or "6 min read"
    author = p.get("author") or "Globalucar Editorial"

    h = SKELETON

    # head meta
    h = set_tag_text(h, "post-page-title", esc(title) + " | Globalucar Blog")
    h = set_attr_by_id(h, "post-meta-desc", "content", esc(desc))
    h = set_attr_by_id(h, "post-meta-keys", "content", esc(kws))
    h = set_attr_by_id(h, "post-canonical", "href", url)
    h = set_attr_by_id(h, "post-og-title", "content", esc(title))
    h = set_attr_by_id(h, "post-og-desc", "content", esc(desc))
    h = set_attr_by_id(h, "post-og-img", "content", SITE + "/" + img)
    h = set_attr_by_id(h, "post-og-url", "content", url)
    h = set_attr_by_id(h, "post-og-pubtime", "content", date_iso)
    h = set_attr_by_id(h, "tw-title", "content", esc(title))
    h = set_attr_by_id(h, "tw-desc", "content", esc(desc))
    h = set_attr_by_id(h, "tw-img", "content", SITE + "/" + img)

    # JSON-LD Article（静态替换空壳）
    article_ld = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": title[:110], "description": desc,
        "image": SITE + "/" + img, "datePublished": date_iso, "dateModified": date_iso,
        "author": {"@type": "Organization", "name": "Globalucar"},
        "publisher": {"@type": "Organization", "name": "Guangzhou Vehicle External Trade Co., Ltd.",
                      "logo": {"@type": "ImageObject", "url": SITE + "/assets/VEHICLE-logo.jpg"}},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
    }
    h = h.replace('<script type="application/ld+json" id="schema-article">{}</script>',
                  '<script type="application/ld+json" id="schema-article">%s</script>' % json.dumps(article_ld, ensure_ascii=False), 1)

    # Breadcrumb JSON-LD（head 内静态追加）
    bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Blog", "item": SITE + "/blog.html"},
        {"@type": "ListItem", "position": 3, "name": title[:95], "item": url},
    ]}
    h = h.replace("</head>",
                  '<script type="application/ld+json">%s</script>\n</head>' % json.dumps(bc, ensure_ascii=False), 1)

    # FAQPage JSON-LD（正文里有问答对才发）
    faq = extract_faq(p.get("content") or "")
    if faq:
        faq_ld = {
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in faq[:10]
            ],
        }
        h = h.replace("</head>",
                      '<script type="application/ld+json">%s</script>\n</head>'
                      % json.dumps(faq_ld, ensure_ascii=False), 1)

    # body 骨架占位
    h = set_tag_text(h, "bp-breadcrumb-title", esc(title[:40] + "…"))
    h = set_tag_text(h, "bp-cat-label", esc(p.get("category") or "Industry Insights"))
    h = set_tag_text(h, "bp-main-title", esc(title))
    h = set_tag_text(h, "bp-date", esc(p.get("date") or ""))
    h = set_tag_text(h, "bp-readtime", esc(readtime))

    # featured image
    h = re.sub(r'(<img[^>]*id="bp-featured-img"[^>]*src=")[^"]*(")',
               lambda m: m.group(1) + "/" + img + m.group(2), h, count=1)
    h = re.sub(r'(<img[^>]*id="bp-featured-img"[^>]*alt=")[^"]*(")',
               lambda m: m.group(1) + esc(title) + m.group(2), h, count=1)

    # 正文：Quick Answer + content + OE 导流块
    toc, content = ensure_toc(p)
    content = rewrite_content_links(content)
    body_html = ('<div class="qa-box"><strong>Quick Answer:</strong> %s</div>\n        %s\n        %s'
                 % (esc(desc), content, oe_links_html(p)))
    h = h.replace('<p style="color:#aaa;text-align:center;padding:60px 0">Loading article...</p>', body_html, 1)

    # TOC（无 toc 则隐藏侧栏 widget）
    if toc:
        toc_lis = "\n          ".join(
            '<li><a href="#s%d"><span class="toc-num">%02d</span> %s</a></li>' % (i + 1, i + 1, esc(t))
            for i, t in enumerate(toc[:10]))
        h = h.replace('<li><a href="#"><span class="toc-num">01</span> Loading...</a></li>', toc_lis, 1)
    else:
        h = re.sub(r'<div class="sidebar-widget">\s*<h3>In This Article</h3>.*?</div>\s*(?=<div class="sidebar-cta")',
                   "", h, count=1, flags=re.S)

    # tags
    tags = p.get("tags") or []
    if tags:
        pills = "\n          ".join('<a href="/blog.html" class="bp-tag-pill">%s</a>' % esc(t) for t in tags[:6])
        h = h.replace('<div class="bp-tags" id="bp-tags"></div>',
                      '<div class="bp-tags" id="bp-tags"><span>Tags:</span> %s</div>' % pills, 1)

    # 相关文章（同类别优先，链接指向新静态 URL）
    others = [x for x in POSTS if x["id"] != p["id"] and x.get("category") == p.get("category")][:3]
    if len(others) < 3:
        more = [x for x in POSTS if x["id"] != p["id"] and x not in others][:3 - len(others)]
        others += more
    rel_cards = []
    for x in others:
        thumb = feat_image(x)
        rel_cards.append('<div class="related-card">'
                         '<img src="/%s" alt="%s" loading="lazy" onerror="this.style.display=\'none\'" />'
                         '<div class="related-card-body"><p class="related-cat">%s</p>'
                         '<h3 class="related-title"><a href="/blog/%s.html">%s</a></h3></div></div>'
                         % (esc(thumb), esc(x.get("title") or ""), esc(x.get("category") or ""), ID2SLUG[x["id"]], esc(x.get("title") or "")))
    h = h.replace('<div class="related-grid" id="related-grid"></div>',
                  '<div class="related-grid" id="related-grid">%s</div>' % "\n          ".join(rel_cards), 1)

    # 侧栏最近文章（按 id 取最新 4 篇）
    recent = sorted([x for x in POSTS if x["id"] != p["id"]], key=lambda x: -x["id"])[:4]
    rec_html = []
    for x in recent:
        rec_html.append('<div class="recent-post-item">'
                        '<img class="recent-thumb" src="/%s" alt="%s" loading="lazy" onerror="this.style.background=\'#eee\'" />'
                        '<div><a href="/blog/%s.html" class="recent-post-title">%s</a>'
                        '<p class="recent-post-date">%s</p></div></div>'
                        % (esc(feat_image(x)), esc(x.get("title") or ""), ID2SLUG[x["id"]],
                           esc((x.get("title") or "")[:55] + "…"), esc(x.get("date") or "")))
    h = h.replace('<div id="sidebar-recent"></div>',
                  '<div id="sidebar-recent">%s</div>' % "\n          ".join(rec_html), 1)

    # 相关产品
    label, cards = related_products(p)
    h = h.replace('<p class="section-sub" id="bp-products-sub"></p>',
                  '<p class="section-sub" id="bp-products-sub">%s</p>' % label, 1)
    h = h.replace('<div class="products-mini-grid" id="products-mini-grid"></div>',
                  '<div class="products-mini-grid" id="products-mini-grid">%s</div>' % cards, 1)

    # 相对 URL → 根相对
    h = rootrel(h)
    return h

# ── 旧 URL stub ──────────────────────────────────────
def build_stub():
    m = {str(k): v for k, v in ID2SLUG.items()}
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blog | Globalucar</title>
<meta name="description" content="Auto parts sourcing and vehicle export guides from Globalucar.">
<link rel="canonical" href="https://www.global-ucars.com/blog.html" />
<script>
  (function(){
    var MAP = %s;
    var id = new URLSearchParams(window.location.search).get('id');
    var slug = id && MAP[id];
    var target = slug ? ('/blog/' + slug + '.html') : '/blog.html';
    if (slug) {
      var c = document.querySelector('link[rel=canonical]');
      if (c) c.href = 'https://www.global-ucars.com' + target;
    }
    window.location.replace(target);
  })();
</script>
<noscript><meta http-equiv="refresh" content="0;url=/blog.html"></noscript>
</head>
<body style="font-family:Arial,sans-serif;text-align:center;padding:80px 20px;background:#0a0e17;color:#f1f5f9;">
  <h1 style="font-size:1.4rem;">This article has moved</h1>
  <p style="color:#94a3b8;">We have upgraded our blog to faster static pages.</p>
  <p><a href="/blog.html" style="color:#c8102e;font-weight:700;">Go to the Globalucar Blog →</a></p>
</body>
</html>
""" % json.dumps(m)

# ── 站内旧链接改写 ────────────────────────────────────
def rewrite_site_links():
    total = 0
    for fname in ["blog.html", "index.html", "gx-content-studio.html"]:
        p = os.path.join(ROOT, fname)
        if not os.path.exists(p):
            continue
        c = open(p, encoding="utf-8").read()
        orig = c
        def sub(m):
            pid = m.group(1)
            if pid.isdigit() and int(pid) in ID2SLUG:
                return "/blog/" + ID2SLUG[int(pid)] + ".html"
            return "/blog.html"
        c, n = re.subn(r"blog-post\.html\?id=(\d+)", sub, c)
        # blog.html 内可能还有不带引号上下文的写法，统一处理 blog-post.html 纯引用
        c = c.replace('href="blog-post.html"', 'href="/blog.html"')
        if c != orig:
            open(p, "w", encoding="utf-8").write(c)
            total += n
            print("  rewrote %s: %d links" % (fname, n))
    return total

# ── sitemap ──────────────────────────────────────────
def update_sitemap():
    c = open(SITEMAP, encoding="utf-8").read()
    # 移除旧 blog-post.html?id=N 的 <url> 块
    c, removed = re.subn(r"<url>\s*<loc>[^<]*blog-post\.html\?id=\d+[^<]*</loc>.*?</url>\s*", "", c, flags=re.S)
    # 幂等：先移除可能已存在的 /blog/ 条目再统一追加
    c = re.sub(r"<url>\s*<loc>[^<]*/blog/[^<]*</loc>.*?</url>\s*", "", c, flags=re.S)
    entries = []
    for p in POSTS:
        lm = iso_date(p)
        if lm > TODAY:
            lm = TODAY
        entries.append("<url><loc>%s/blog/%s.html</loc><lastmod>%s</lastmod></url>"
                       % (SITE, ID2SLUG[p["id"]], lm))
    c = c.replace("</urlset>", "\n".join(entries) + "\n</urlset>")
    open(SITEMAP, "w", encoding="utf-8").write(c)
    print("  sitemap: removed %d old blog urls, added %d new" % (removed, len(POSTS)))

# ── main ─────────────────────────────────────────────
def main():
    only_pages = "--only-pages" in sys.argv
    only_new = "--only-new" in sys.argv
    only_slug = None
    for i, a in enumerate(sys.argv):
        if a == "--only-slug" and i + 1 < len(sys.argv):
            only_slug = set(x.strip() for x in sys.argv[i + 1].split(",") if x.strip())
    os.makedirs(BLOG_DIR, exist_ok=True)
    n = skipped = 0
    for p in POSTS:
        slug = ID2SLUG[p["id"]]
        out = os.path.join(BLOG_DIR, slug + ".html")
        if only_slug is not None:
            if slug not in only_slug:
                continue
        elif only_new and os.path.exists(out):
            skipped += 1
            continue
        html_out = render_post(p)
        open(out, "w", encoding="utf-8").write(html_out)
        n += 1
    print("generated static blog pages: %d (skipped existing: %d)" % (n, skipped))
    if only_pages or only_slug is not None:
        return
    # 覆盖 blog-post.html 为跳转 stub
    open(os.path.join(ROOT, "blog-post.html"), "w", encoding="utf-8").write(build_stub())
    print("blog-post.html -> redirect stub (%d bytes)" % os.path.getsize(os.path.join(ROOT, "blog-post.html")))
    print("rewriting internal links...")
    rewrite_site_links()
    update_sitemap()
    # 写 id→slug 映射供后续工具使用
    json.dump({"id2slug": {str(k): v for k, v in ID2SLUG.items()}},
              open(os.path.join(DATA, "blog-id2slug.json"), "w", encoding="utf-8"), indent=1)
    print("saved blog-id2slug.json")

if __name__ == "__main__":
    main()
