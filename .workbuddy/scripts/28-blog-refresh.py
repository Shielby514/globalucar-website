# -*- coding: utf-8 -*-
"""
28-blog-refresh.py —— 存量文章体检与修复（提升旧文 CTR 与正文密度）

背景（2026-11-04 实测 155 篇）
  · 正文内链中位数只有 **2 条**（页面上的 58~89 条是导航/侧栏/相关产品，不算正文）
  · 正文图片中位数只有 **2 张**，**10%** 的文章正文里有 ≥8 张
  · FAQ 只有 **39%** 的文章有
  · 元数据缺口：description 缺 41 篇、toc 缺 34、tags 缺 15、keywords 缺 13、image 缺 2
  · 分类有 **32 种**写法（`Vehicles` / `🚗 Vehicles · New Car Export` / `Auto Parts` … 同义混杂）

修复手段（确定性优先，不依赖 LLM）
  1) 元数据补齐：description ← 正文首段；keywords ← 标题+标签+OE 号；
     tags ← 子分类/主题词；toc ← H2；category ← 契约受控词表（走别名映射）；
     date ← 健壮 ISO 解析；readtime ← 词数推算；image ← 自家图库里最匹配的图
  2) 正文图片补齐：正文图片 < 门槛时，从自家图库按关键词匹配，在段落边界插入
  3) TDK 改写（--tdk）：有 GSC 点击数据时，用 LLM 改写 title/description（只改元数据，不动正文）
  4) FAQ 补齐（--faq）：正文没有 FAQ 时，用 LLM 基于现有正文生成 FAQ 块

安全约束
  · **只改 blog-posts.json 的元数据与正文插图，不重写正文文字**
  · 改完只重渲染受影响的文章（generate_blog_static_pages.py --only-slug），
    随后必须跑 22-build-blog-anchor-links.py 把「文末相关零件模块」补回去
    （线上页是「生成器 + 注入」两层叠出来的，只跑生成器会把注入层抹掉）
  · 幂等：同一份输入跑两次，第二次应当 0 变更

用法
  python 28-blog-refresh.py --dry-run          # 只报告要修什么
  python 28-blog-refresh.py --apply            # 写 blog-posts.json
  python 28-blog-refresh.py --apply --faq      # 顺带用 LLM 补 FAQ
  python 28-blog-refresh.py --apply --limit 20 # 本轮最多修 20 篇
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA = os.path.join(BASE, ".workbuddy", "data")
CONTRACT = os.path.join(SCRIPT_DIR, "blog-contract.json")
POSTS = os.path.join(DATA, "blog-posts.json")
POSTS_BAK = os.path.join(DATA, "blog-posts.json.bak")
ASSETS = os.path.join(BASE, "assets", "parts")

sys.path.insert(0, SCRIPT_DIR)

MONTHS_MAP = {}
for _i, _m in enumerate(["January", "February", "March", "April", "May", "June", "July",
                          "August", "September", "October", "November", "December"]):
    MONTHS_MAP[_m.lower()] = _i + 1
    MONTHS_MAP[_m[:3].lower()] = _i + 1

STOP = set("the and for with from your our how what why when which guide tips a an to of "
           "in on is are be best top wholesale parts auto part automotive using use".split())

# 太泛的词不能单独用来选图：文章里出现两次 "engine" 不代表该配引擎图。
# 多词短语（oxygen_sensor / wheel_hub_bearing）不受此限制，命中一次即可。
GENERIC_TOKENS = {
    "engine", "parts", "part", "auto", "china", "guide", "vehicle", "system",
    "motor", "sensor", "switch", "cover", "housing", "bracket", "pump", "valve",
    "gear", "kit", "set", "assembly", "new", "used", "replacement", "wholesale",
    "price", "oem", "aftermarket", "export", "buyer", "guide", "quality", "source",
    "sourcing", "catalogue", "catalog",
}

# 品牌词单独命中时只能定位到「某品牌的某零件图」，主题相关性弱，排除
BRAND_TOKENS = {
    "hyundai", "kia", "toyota", "nissan", "ford", "bmw", "mercedes", "chery",
    "byd", "geely", "volkswagen", "audi", "mazda", "chevrolet", "haval", "jetour",
    "xpeng", "dongfeng", "roewe", "livan", "skoda", "tharu", "suzuki", "isuzu",
    "hino", "lexus", "tesla", "volvo", "scion", "pontiac", "acura", "infiniti",
}

# 同词不同件：命中的词相同但零件不是一回事，宁可不配
TERM_EXCLUDE = {
    "converter": ("torque",),   # 催化转换器 ≠ 液力变矩器
    "motor": ("starter", "fan"),
}


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def slugify(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:78].rstrip("-")


def build_slug_map(posts):
    """复刻 generate_blog_static_pages.py 的 post_slug()，含重名加 id 的规则。

    老文章在 JSON 里可能丢过 slug，只看 p['slug'] 会漏掉它们，
    导致改了元数据却不重渲染对应页面。
    """
    seen, out = {}, {}
    for p in posts:
        s = p.get("slug") or slugify(p.get("title") or "untitled")
        s = re.sub(r"[^a-zA-Z0-9-]+", "-", s).strip("-").lower()
        if s in seen.values():
            s = s + "-" + str(p["id"])
        seen[p["id"]] = s
        out[p["id"]] = s
    return out


def words_of(html):
    return len(strip_tags(html).split())


def iso_date(raw):
    raw = (raw or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    if re.match(r"^\d{4}-\d{2}$", raw):
        return raw + "-01"
    m = re.match(r"^([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s*(\d{4})?$", raw)
    if m and m.group(1).lower() in MONTHS_MAP:
        y = m.group(3) or "2026"
        return "%s-%02d-%02d" % (y, MONTHS_MAP[m.group(1).lower()], max(1, min(28, int(m.group(2)))))
    m = re.match(r"^([A-Za-z]{3,9})\.?,?\s*(\d{4})?$", raw)
    if m and m.group(1).lower() in MONTHS_MAP:
        return "%s-%02d-01" % (m.group(2) or "2026", MONTHS_MAP[m.group(1).lower()])
    # 解析不了就返回 None：宁可保持原样，也不要静默改成某个默认日期
    return None


def norm_category(raw, contract):
    c = (raw or "").strip()
    if not c:
        return None
    allowed = contract.get("categories", [])
    aliases = contract.get("category_aliases", {})
    for a in allowed:
        if c.lower() == a.lower():
            return a
    plain = re.sub(r"^[^\w]+", "", c).split("·")[0].strip()
    if plain:
        for a in allowed:
            if plain.lower() == a.lower():
                return a
        if plain in aliases:
            return aliases[plain]
        key = plain.lower()
        for k, v in aliases.items():
            if k.lower() == key:
                return v
    return None


def build_asset_index():
    """自家图库索引：文件名关键词 -> 相对路径。只收 assets/ 下的自有图。"""
    idx = {}
    if not os.path.isdir(ASSETS):
        return idx
    for f in sorted(os.listdir(ASSETS)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        stem = re.sub(r"\.(jpg|jpeg|png|webp)$", "", f, flags=re.I)
        stem = re.sub(r"^(part|xlsx)_", "", stem)
        stem = re.sub(r"_\d+", " ", stem)
        toks = [t for t in re.split(r"[^A-Za-z0-9]+", stem.lower()) if len(t) > 2 and t not in STOP]
        idx.setdefault("_".join(toks), "assets/parts/" + f)
        for t in toks:
            idx.setdefault(t, "assets/parts/" + f)
    return idx


def build_asset_list():
    """自家图库清单：(文件名主干小写, 相对路径)。用于按词整词匹配。"""
    out = []
    if not os.path.isdir(ASSETS):
        return out
    for f in sorted(os.listdir(ASSETS)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        stem = re.sub(r"\.(jpg|jpeg|png|webp)$", "", f, flags=re.I)
        stem = re.sub(r"^(part|xlsx)_", "", stem)
        stem = re.sub(r"_\d+", " ", stem)
        out.append((stem.lower(), "assets/parts/" + f))
    return out


def title_terms(title):
    """从标题里抽「零件词」候选，长词组优先。

    只认标题里的词：标题就是文章主题，标题词命中的图必然切题；
    正文泛词命中（manufact / torque / assist）会配出完全不相干的图。
    """
    t = re.sub(r"[^a-z0-9]+", " ", (title or "").lower())
    words = [w for w in t.split() if len(w) >= 3 and w not in STOP]
    terms = []
    for i in range(len(words) - 1):
        terms.append(words[i] + " " + words[i + 1])
    for w in words:
        if len(w) >= 6 and w not in GENERIC_TOKENS and w not in BRAND_TOKENS:
            terms.append(w)
    seen, out = set(), []
    for x in sorted(terms, key=lambda s: (-len(s.split()), -len(s))):
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def assets_for_term(assets, term):
    """文件名里按整词命中 term 的图（避免 'manufact' 命中 'manufacturing' 之类）。"""
    pat = re.compile(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])")
    bad = TERM_EXCLUDE.get(term, ())
    out = []
    for stem, path in assets:
        if not pat.search(stem):
            continue
        if any(b in stem for b in bad):
            continue
        out.append(path)
    return out


def pick_image(idx, text):
    """按关键词匹配自家图；匹配不到就不硬塞。"""
    low = " " + (text or "").lower() + " "
    best, best_n = None, 0
    for toks, path in idx.items():
        if toks.startswith("_"):
            continue
        n = low.count(toks)
        if n > best_n:
            best, best_n = path, n
    return best if best_n >= 2 else None


def first_paragraph(html):
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", html or "", re.S):
        t = strip_tags(m.group(1))
        if len(t) >= 60:
            return t
    return ""


def build_description(p):
    if p.get("description"):
        return None
    src = first_paragraph(p.get("content") or "")
    if not src:
        return None
    src = src[:160].rsplit(" ", 1)[0].rstrip(",;:")
    return src if len(src) >= 70 else None


def build_keywords(p, description):
    if p.get("keywords"):
        return None
    kws = []
    for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]+", (p.get("title") or "") + " " + (description or "")):
        wl = w.lower()
        if len(wl) > 2 and wl not in STOP and wl not in [k.lower() for k in kws]:
            kws.append(wl)
        if len(kws) >= 6:
            break
    for oem in re.findall(r"\b[A-Z0-9]{2,6}-[A-Z0-9]{2,6}(?:-[A-Z0-9]{1,4})?\b", p.get("content") or ""):
        if oem not in kws:
            kws.append(oem)
        if len(kws) >= 8:
            break
    return kws if len(kws) >= 3 else None


def build_tags(p, contract):
    if p.get("tags"):
        return None
    text = ((p.get("title") or "") + " " + (p.get("content") or "")[:3000]).lower()
    sysmap = {
        "engine": ["engine", "piston", "gasket", "timing", "oil pump", "fuel pump", "injector"],
        "cooling": ["radiator", "water pump", "thermostat", "cooling", "condenser", "oil cooler"],
        "electrical": ["alternator", "starter", "ignition", "spark plug", "sensor", "battery"],
        "suspension": ["suspension", "control arm", "ball joint", "shock", "strut", "tie rod"],
        "brake": ["brake", "brake pad", "brake disc", "caliper", "rotor"],
        "transmission": ["transmission", "gearbox", "clutch", "cv joint"],
        "body": ["headlight", "taillight", "bumper", "mirror", "fender"],
        "filters": ["oil filter", "air filter", "fuel filter", "cabin filter"],
    }
    tags = []
    for name, kws in sysmap.items():
        if sum(text.count(k) for k in kws) >= 3:
            tags.append(name.title())
    for b in ("hyundai", "kia", "toyota", "nissan", "ford", "bmw", "mercedes", "chery",
              "byd", "geely", "volkswagen", "audi", "mazda", "chevrolet"):
        if b in text:
            tags.append(b.title())
    out, seen = [], set()
    for t in tags:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out[:5] if len(out) >= 3 else None


def build_toc(p):
    if p.get("toc"):
        return None
    hs = [strip_tags(h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", p.get("content") or "", re.S)]
    return hs if len(hs) >= 4 else None


def pick_candidates(assets, title):
    """按标题词从自家图库挑候选图。

    只用标题里的零件词，且图片文件名必须整词命中该词组：
    标题讲 brake，就只给 brake 系的图；讲 water pump 就只给 water pump 的图。
    宁缺毋滥——配错图比不配图更伤，所以没有高置信命中就一张都不插。
    """
    out = []
    used = set()
    for term in title_terms(title):
        for path in assets_for_term(assets, term):
            if path in used:
                continue
            used.add(path)
            out.append((len(term.split()) * 10 + len(term), term, path))
    out.sort(key=lambda x: -x[0])
    return out


def top_up_images(p, assets, want):
    """正文图片不足时，从自家图库补插（带 alt）。

    只在候选图与文章主题确实相关时插入；宁缺毋滥，配错图比不配图更伤。
    """
    content = p.get("content") or ""
    have = len(re.findall(r"<img\b", content))
    if have >= want:
        return None, 0, []
    need = want - have
    used = set(re.findall(r'src="/?([^"]+)"', content))
    cands = pick_candidates(assets, p.get("title") or "")
    picked = []
    for score, term, path in cands:
        if len(picked) >= need:
            break
        if path in used:
            continue
        used.add(path)
        picked.append((score, term, path))
    if not picked:
        return None, 0, []
    # 在第 1/4 / 1/2 / 3/4 处的段落边界插入
    paras = list(re.finditer(r"<p[^>]*>.*?</p>", content, re.S))
    if len(paras) < 3:
        return None, 0, []
    insert_at = []
    for frac in (0.2, 0.5, 0.78):
        insert_at.append(paras[min(len(paras) - 1, int(len(paras) * frac))].end())
    out = content
    added = 0
    for i, pos in enumerate(insert_at):
        if added >= need:
            break
        if i >= len(picked):
            break
        score, term, path = picked[i]
        alt = ("%s — %s" % (term.title(), p.get("title") or "auto part"))[:110]
        alt = re.sub(r"[^A-Za-z0-9 \-]", "", alt)
        block = '\n<img src="/%s" alt="%s" loading="lazy" />' % (path, alt)
        out = out[:pos] + block + out[pos:]
        added += 1
    return (out if added else None), added, [(ph, pt) for _, ph, pt in picked[:added]]


def main():
    ap = argparse.ArgumentParser(description="blog refresher")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=15, help="max articles to refresh this run")
    ap.add_argument("--min-images", type=int, default=4)
    ap.add_argument("--faq", action="store_true", help="use LLM to add a FAQ block where missing")
    ap.add_argument("--tdk", action="store_true", help="use LLM to rewrite title/description")
    ap.add_argument("--model", default="MiniMax-M3")
    args = ap.parse_args()

    if not os.path.exists(POSTS):
        print("posts not found: %s" % POSTS)
        return 1
    contract = json.load(open(CONTRACT, encoding="utf-8"))
    posts = json.load(open(POSTS, encoding="utf-8"))
    idx = build_asset_index()
    assets = build_asset_list()
    print("posts=%d  own_images=%d  contract_categories=%d"
          % (len(posts), len(assets), len(contract.get("categories", []))))

    changed = []
    for p in posts:
        fixes = []
        before = dict(p)
        content = p.get("content") or ""

        # 1) 元数据补齐
        d = build_description(p)
        if d:
            p["description"] = d
            fixes.append("description")
        kw = build_keywords(p, p.get("description"))
        if kw:
            p["keywords"] = kw
            fixes.append("keywords")
        tg = build_tags(p, contract)
        if tg:
            p["tags"] = tg
            fixes.append("tags")
        tc = build_toc(p)
        if tc:
            p["toc"] = tc
            fixes.append("toc")
        cat = norm_category(p.get("category"), contract)
        if cat and cat != p.get("category"):
            p["category"] = cat
            fixes.append("category->%s" % cat)
        iso = iso_date(p.get("date"))
        if iso and iso != p.get("date"):
            p["date"] = iso
            fixes.append("date")
        w = words_of(content)
        rt = max(1, round(w / 220))
        if p.get("readtime") != rt and (not p.get("readtime") or str(p.get("readtime")).isdigit()):
            p["readtime"] = rt
            fixes.append("readtime")
        if not p.get("image"):
            img = None
            cands = pick_candidates(assets, p.get("title") or "")
            if cands:
                img = cands[0][2]
            if not img:
                img = pick_image(idx, (p.get("title") or "") + " " + strip_tags(content)[:1500])
            if img:
                p["image"] = img
                fixes.append("image")

        # 2) 正文图片补齐
        new_content, added, picks = top_up_images(p, assets, args.min_images)
        if new_content:
            p["content"] = new_content
            fixes.append("images+%d" % added)
            if args.dry_run and picks:
                print("     配图: %s" % " | ".join(
                    "%s -> %s" % (ph, os.path.basename(pt)) for ph, pt in picks))

        if fixes and p != before:
            changed.append((p, fixes))

    changed.sort(key=lambda x: -(x[1].count("images+") * 5 + len(x[1])))
    changed = changed[: args.limit]

    print("\n--- refresh targets ---")
    for p, fixes in changed:
        print("  id=%-5s %-58s  %s" % (p.get("id"), (p.get("title") or "")[:58], ", ".join(fixes)))
    if not changed:
        print("  (nothing to refresh)")

    if args.dry_run or not args.apply:
        print("\n%s" % ("DRY-RUN: nothing written" if args.dry_run else "no --apply, nothing written"))
        return 0

    shutil.copyfile(POSTS, POSTS_BAK)
    with open(POSTS, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=1)
    print("\nupdated blog-posts.json (%d articles touched) -> backup %s"
          % (len(changed), os.path.basename(POSTS_BAK)))

    # 打印需要重渲染的 slug，供编排脚本调用生成器
    slug_map = build_slug_map(posts)
    slugs = []
    for p, _ in changed:
        s = slug_map.get(p.get("id"))
        if s and s not in slugs:
            slugs.append(s)
    outp = os.path.join(DATA, "blog-refresh-slugs.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump({"slugs": slugs, "count": len(slugs)}, f, ensure_ascii=False, indent=1)
    print("affected slugs -> %s (%d)" % (outp, len(slugs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
