# -*- coding: utf-8 -*-
"""
24-blog-topic-planner.py —— 博客选题规划 + 事实包装配

输入
  .workbuddy/data/product-catalog.json   600 个已过质量门槛的产品（品牌/系统/图片/适配/OEM 交叉号）
  .workbuddy/data/oe-master-db.json      236,445 条 OE 母库（取有 system/fitment 的富化子集）
  .workbuddy/data/blog-posts.json        存量文章（覆盖矩阵 + 去重）
  oe/ 目录                                已发布的 15,415 个 OE 页（判断可链接性）

输出
  .workbuddy/data/blog-topics.json  { generated_at, contract_version, topics[] }

选题逻辑
  1. 最小竞争单元 = 「品牌族 × 系统 × 子分类」
     —— 母库写 "HYUNDAI,KIA"、产品目录写 "Hyundai"/"Kia"，不归一就是孤岛，所以统一映射到 brand family；
     —— 子分类粒度比 "品牌×系统" 细，长尾更准，也天然避开存量 155 篇的泛主题。
  2. OE 事实两个来源：母库富化记录 + 产品自身的 oem_refs（后者正是买家要的交叉号）
  3. 两类文章（决定链接门槛）：
       oem_cross_reference —— 簇内有已发布 OE 页可链   （/oe/ 链接 ≥2）
       product_guide       —— 簇内只有产品页可链，但有真实交叉号进表格（/parts/ 链接 ≥4）
  4. 打分 = 供给量 + 可链接产品页 + 可链接 OE 页 − 覆盖惩罚 + GSC 需求加成
  5. 硬门槛：产品页 ≥2 且 OE 事实 ≥2，否则不成选题

只读输入，只写 blog-topics.json。幂等：同样输入 → 同样输出（排序稳定）。

用法
  python 24-blog-topic-planner.py                 # 生成
  python 24-blog-topic-planner.py --count 3       # 本轮出 3 个选题
  python 24-blog-topic-planner.py --dry-run       # 只报告不写盘
  python 24-blog-topic-planner.py --print-topics  # 只列候选簇排名
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(BASE, ".workbuddy", "data")
SCRIPTS = os.path.join(BASE, ".workbuddy", "scripts")
CONTRACT = os.path.join(SCRIPTS, "blog-contract.json")
CATALOG = os.path.join(DATA, "product-catalog.json")
MASTER = os.path.join(DATA, "oe-master-db.json")
POSTS = os.path.join(DATA, "blog-posts.json")
OE_DIR = os.path.join(BASE, "oe")
GSC_LEDGER = os.path.join(DATA, "gsc-ledger.json")
OUT = os.path.join(DATA, "blog-topics.json")

from datetime import datetime, timezone, timedelta
TODAY = datetime.now(timezone(timedelta(hours=8))).date().isoformat()

# ── 品牌族 ──────────────────────────────────────────────
BRAND_FAMILY = {
    "hyundai": "hyundai_kia", "kia": "hyundai_kia",
    "toyota": "toyota", "lexus": "toyota", "daihatsu": "toyota",
    "nissan": "nissan", "infiniti": "nissan",
    "honda": "honda", "acura": "honda",
    "ford": "ford", "lincoln": "ford",
    "bmw": "bmw", "mini": "bmw",
    "volkswagen": "vw", "vw": "vw", "skoda": "vw", "seat": "vw",
    "mercedes-benz": "mercedes", "mercedes benz": "mercedes",
    "chevrolet": "gm", "chevy": "gm", "gmc": "gm", "gm": "gm",
    "buick": "gm", "cadillac": "gm", "pontiac": "gm",
    "chery": "chery", "geely": "geely", "byd": "byd", "mazda": "mazda",
    "renault": "renault", "peugeot": "peugeot", "citroen": "peugeot",
    "land rover": "landrover", "volvo": "volvo", "fiat": "fiat",
    "audi": "audi", "opel": "opel", "porsche": "porsche", "faw": "faw",
    "wuling": "wuling", "mg": "mg", "haval": "haval",
    "great wall motors": "gwm", "gwm": "gwm", "deutz": "deutz",
    "dodge": "dodge", "chrysler": "dodge", "jeep": "dodge",
    "subaru": "subaru", "suzuki": "suzuki", "baic": "baic", "jac": "jac",
    "perodua": "perodua", "other": "other",
}
FAMILY_LABEL = {
    "hyundai_kia": "Hyundai and Kia", "toyota": "Toyota", "nissan": "Nissan",
    "honda": "Honda", "ford": "Ford", "bmw": "BMW", "vw": "Volkswagen",
    "mercedes": "Mercedes-Benz", "gm": "GM and Chevrolet", "chery": "Chery",
    "geely": "Geely", "byd": "BYD", "mazda": "Mazda", "renault": "Renault",
    "peugeot": "Peugeot", "landrover": "Land Rover", "volvo": "Volvo",
    "fiat": "Fiat", "audi": "Audi", "opel": "Opel", "porsche": "Porsche",
    "faw": "FAW", "wuling": "Wuling", "mg": "MG", "haval": "Haval",
    "gwm": "Great Wall Motors", "deutz": "Deutz", "dodge": "Dodge and Jeep",
    "subaru": "Subaru", "suzuki": "Suzuki", "baic": "BAIC", "jac": "JAC",
    "perodua": "Perodua", "other": "Multi-brand",
}
FAMILY_SLUG = {
    "hyundai_kia": "hyundai-kia", "toyota": "toyota", "nissan": "nissan",
    "honda": "honda", "ford": "ford", "bmw": "bmw", "vw": "volkswagen",
    "mercedes": "mercedes-benz", "gm": "gm-chevrolet", "chery": "chery",
    "geely": "geely", "byd": "byd", "mazda": "mazda", "renault": "renault",
    "peugeot": "peugeot", "landrover": "land-rover", "volvo": "volvo",
    "fiat": "fiat", "audi": "audi", "opel": "opel", "porsche": "porsche",
    "faw": "faw", "wuling": "wuling", "mg": "mg", "haval": "haval",
    "gwm": "great-wall-motors", "deutz": "deutz", "dodge": "dodge-jeep",
    "subaru": "subaru", "suzuki": "suzuki", "baic": "baic", "jac": "jac",
    "perodua": "perodua", "other": "multi-brand",
}
FAMILY_KEYWORDS = {
    "hyundai_kia": ["hyundai", "kia"], "toyota": ["toyota", "lexus"],
    "nissan": ["nissan", "infiniti"], "honda": ["honda", "acura"],
    "ford": ["ford"], "bmw": ["bmw"], "vw": ["volkswagen", " vw "],
    "mercedes": ["mercedes", "benz"], "gm": ["chevrolet", "chevy", "gmc", "general motors"],
    "chery": ["chery"], "geely": ["geely"], "byd": ["byd"], "mazda": ["mazda"],
    "renault": ["renault"], "peugeot": ["peugeot"], "landrover": ["land rover"],
    "volvo": ["volvo"], "fiat": ["fiat"], "audi": ["audi"], "opel": ["opel"],
    "porsche": ["porsche"], "faw": ["faw"], "wuling": ["wuling"], "mg": ["mg"],
    "haval": ["haval"], "gwm": ["great wall"], "deutz": ["deutz"],
    "dodge": ["dodge", "jeep", "chrysler"], "subaru": ["subaru"],
    "suzuki": ["suzuki"], "baic": ["baic"], "jac": ["jac"], "other": [],
}

SYSTEM_ALIASES = {
    "engine": "engine", "engine parts": "engine", "fuel": "engine",
    "cooling": "cooling", "air conditioning": "cooling", "hvac": "cooling",
    "electrical": "electrical", "electrical/ignition": "electrical",
    "ignition": "electrical", "body/electrical": "electrical",
    "suspension": "suspension", "suspension & steering": "suspension",
    "suspension/steering/brake": "suspension", "steering": "suspension",
    "brake": "brake", "brakes": "brake",
    "transmission": "transmission", "drivetrain": "transmission",
    "body": "body", "body/interior": "body", "exterior": "body",
    "filters": "filters", "filter": "filters",
}
SYSTEM_LABEL = {
    "engine": "Engine Parts", "cooling": "Cooling Parts",
    "electrical": "Electrical and Ignition Parts",
    "suspension": "Suspension and Steering Parts",
    "brake": "Brake System Parts", "transmission": "Transmission Parts",
    "body": "Body and Exterior Parts", "filters": "Filter Parts",
}
SYSTEM_KEYWORDS = {
    "engine": ["engine", "piston", "gasket", "cylinder", "oil pump", "fuel pump",
               "injector", "timing", "turbo", "valve", "crankshaft",
               "engine oil cooler", "oil cooler", "exhaust", "manifold",
               "catalytic", "egr", "throttle"],
    "cooling": ["radiator", "water pump", "thermostat", "cooling", "coolant",
                "condenser", "compressor", "a/c", "air conditioning", "blower",
                "oil cooler", "intercooler", "expansion tank", "heater core"],
    "electrical": ["alternator", "starter", "ignition", "spark plug",
                   "ignition coil", "sensor", "battery", "wiring", "ecu",
                   "oxygen sensor", "abs sensor", "switch", "regulator", "relay"],
    "suspension": ["suspension", "control arm", "ball joint", "shock", "strut",
                   "sway bar", "stabilizer", "tie rod", "wheel bearing",
                   "spring", "steering", "lower arm", "bush", "knuckle",
                   "rack and pinion"],
    "brake": ["brake", "brake pad", "brake disc", "rotor", "caliper",
              "brake hose", "master cylinder", "brake drum", "brake cylinder"],
    "transmission": ["transmission", "gearbox", "clutch", "cv joint",
                     "drive shaft", "differential", "axle", "transaxle"],
    "body": ["headlight", "taillight", "bumper", "mirror", "fender", "grille",
             "door", "hood", "windshield", "glass", "body panel", "tail lamp"],
    "filters": ["filter", "oil filter", "air filter", "fuel filter", "cabin filter"],
}


def norm_family(raw):
    if not raw:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    if "," in s:
        for part in s.split(","):
            fam = BRAND_FAMILY.get(part.strip())
            if fam:
                return fam
        return None
    return BRAND_FAMILY.get(s)


def norm_system(raw):
    if not raw:
        return None
    return SYSTEM_ALIASES.get(str(raw).strip().lower())


def slugify(t, maxlen=70):
    t = re.sub(r"<[^>]+>", "", t or "")
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:maxlen].rstrip("-")


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def subcat_phrases(subcat):
    """子分类的匹配短语：全称 + 去限定词的核心词（复数容忍）。"""
    if not subcat:
        return []
    full = str(subcat).strip().lower()
    out = [full]
    if full.endswith("s") and not full.endswith("ss"):
        out.append(full[:-1])
    core = full
    for lead in ("front ", "rear ", "left ", "right ", "inner ", "outer ",
                 "upper ", "lower ", "engine ", "transmission "):
        if core.startswith(lead):
            core = core[len(lead):]
            break
    if core != full:
        out.append(core)
        if core.endswith("s") and not core.endswith("ss"):
            out.append(core[:-1])
    # 去重
    seen, res = set(), []
    for p in out:
        if p and p not in seen:
            seen.add(p)
            res.append(p)
    return res


def detect_families(text):
    low = " " + (text or "").lower() + " "
    hits = []
    for fam, kws in FAMILY_KEYWORDS.items():
        if not kws:
            continue
        score = sum(low.count(k) for k in kws)
        if score:
            hits.append((fam, score))
    hits.sort(key=lambda x: (-x[1], x[0]))
    return [f for f, _ in hits]


def detect_systems(text):
    low = " " + (text or "").lower() + " "
    hits = []
    for sysname, kws in SYSTEM_KEYWORDS.items():
        score = sum(low.count(k) for k in kws)
        if score:
            hits.append((sysname, score))
    hits.sort(key=lambda x: (-x[1], x[0]))
    return [s for s, _ in hits]


# ── 数据装载 ────────────────────────────────────────────
def load_catalog():
    if not os.path.exists(CATALOG):
        return []
    d = json.load(open(CATALOG, encoding="utf-8"))
    items = d["products"] if isinstance(d, dict) and "products" in d else d
    out = []
    for x in items:
        if not isinstance(x, dict):
            continue
        fam = norm_family(x.get("brand"))
        sysn = norm_system(x.get("system") or x.get("part_system"))
        if not fam or not sysn:
            continue
        imgs = []
        for im in (x.get("images") or []):
            if isinstance(im, str) and im.startswith("assets/"):
                imgs.append(im.lstrip("/"))
        li = x.get("local_image")
        if isinstance(li, str) and li.startswith("assets/") and li not in imgs:
            imgs.insert(0, li)
        refs = []
        for r in (x.get("oem_refs") or []):
            if isinstance(r, str) and r.strip():
                refs.append(r.strip())
            elif isinstance(r, dict):
                for key in ("oe", "oem", "ref", "number", "part_number", "oe_number"):
                    if r.get(key):
                        refs.append(str(r[key]).strip())
                        break
        sub = str(x.get("sub_category") or "").strip()
        out.append({
            "family": fam, "system": sysn, "subcat": sub,
            "slug": x.get("slug") or "",
            "name": x.get("name") or "",
            "url": ("/parts/%s.html" % x.get("slug")) if x.get("slug") else "",
            "images": imgs, "fitment": [str(v) for v in (x.get("fitment") or [])],
            "oem_refs": refs, "sub_category": sub,
            "specs": x.get("specs") or {}, "moq": x.get("moq") or "",
            "features": [str(v) for v in (x.get("features") or [])][:6],
            "faq": x.get("faq") or [],
            "source": x.get("source") or "",
        })
    return out


def load_master():
    if not os.path.exists(MASTER):
        return {}
    db = json.load(open(MASTER, encoding="utf-8"))
    out = {}
    for oe, rec in db.items():
        if not isinstance(rec, dict):
            continue
        if not (rec.get("fitment") or rec.get("system")):
            continue
        fam = norm_family(",".join(rec.get("brand") or []))
        sysn = norm_system(rec.get("system"))
        if not fam or not sysn:
            continue
        imgs = [i.lstrip("/") for i in (rec.get("images") or [])
                if isinstance(i, str) and i.startswith("assets/")]
        out[oe] = {
            "oe": rec.get("oe") or oe,
            "part_name": strip_tags(rec.get("part_name") or "")[:120],
            "family": fam, "system": sysn,
            "fitment": [str(v) for v in (rec.get("fitment") or [])],
            "images": imgs, "origin": "master",
        }
    return out


def load_oe_index():
    candidates = defaultdict(list)
    if not os.path.isdir(OE_DIR):
        return {}
    for filename in os.listdir(OE_DIR):
        if filename.endswith('.html'):
            key = re.sub(r'[^a-z0-9]', '', filename[:-5].lower())
            candidates[key].append(filename[:-5])
    return {key: names[0] for key, names in candidates.items() if len(names) == 1}


def load_posts():
    if not os.path.exists(POSTS):
        return []
    return json.load(open(POSTS, encoding="utf-8"))


def load_demand():
    if not os.path.exists(GSC_LEDGER):
        return {}
    try:
        d = json.load(open(GSC_LEDGER, encoding="utf-8"))
    except Exception:
        return {}
    rows = d.get("queries") or d.get("top_queries") or []
    out = {}
    if isinstance(rows, list):
        for r in rows:
            if isinstance(r, dict):
                q = str(r.get("query") or r.get("keys") or "").strip().lower()
                imp = r.get("impressions") or r.get("imp") or 0
                if q:
                    try:
                        out[q] = int(imp)
                    except Exception:
                        pass
    return out


def find_oe_url(oe, oe_index):
    key = re.sub(r'[^a-z0-9]', '', str(oe).lower())
    slug = oe_index.get(key)
    return '/oe/%s.html' % slug if slug else ''


def load_intent_slots():
    """意图槽位统一从 blog-contract.json 读（生成器 / 评分卡 / 改写脚本同一份）。"""
    try:
        with open(CONTRACT, encoding="utf-8") as f:
            c = json.load(f)
    except Exception:
        return {}
    slots = ((c.get("title_intents") or {}).get("slots") or {})
    out = {}
    for kind, lst in slots.items():
        for s in lst:
            s = dict(s)
            s["kind"] = kind
            out[s["id"]] = s
    return out


def main():
    ap = argparse.ArgumentParser(description="blog topic planner")
    ap.add_argument("--count", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--print-topics", action="store_true")
    ap.add_argument("--max-products", type=int, default=8)
    ap.add_argument("--max-oe", type=int, default=14)
    ap.add_argument("--no-mix", dest="mix", action="store_false",
                    help="don't force a mix of article types")
    args = ap.parse_args()

    if not os.path.exists(CONTRACT):
        print("contract not found: %s" % CONTRACT)
        return 1
    contract = json.load(open(CONTRACT, encoding="utf-8"))

    catalog = load_catalog()
    # Do not turn placeholder fitment or decoding corruption into published claims.
    rejected = []
    usable = []
    for product in catalog:
        evidence = json.dumps({k: product.get(k) for k in ('name', 'fitment', 'specs')}, ensure_ascii=False)
        fitment = [str(v).strip() for v in product.get('fitment', [])]
        if '\ufffd' in evidence or not any(v.lower() not in ('other', 'unknown', 'universal', '', 'n/a') for v in fitment):
            rejected.append(product.get('slug', product.get('name')))
        else:
            usable.append(product)
    print('Fact-source filter: kept=%d withheld=%d' % (len(usable), len(rejected)))
    catalog = usable
    master = load_master()
    oe_index = load_oe_index()
    posts = load_posts()
    demand = load_demand()
    print("catalog=%d  master_enriched=%d  oe_pages=%d  posts=%d  demand_keys=%d"
          % (len(catalog), len(master), len(oe_index), len(posts), len(demand)))

    # 存量文章的覆盖索引（标题级判定优先，body 只做轻量兜底）
    post_titles = []
    post_bodies = []
    for p in posts:
        post_titles.append((p.get("title") or "").lower())
        post_bodies.append(strip_tags(p.get("content") or "")[:4000].lower())

    # 簇：产品按「品牌族 × 系统 × 子分类」，母库记录落到「品牌族 × 系统 × ''」
    clusters = defaultdict(lambda: {"products": [], "oe": {}})
    for p in catalog:
        key = (p["family"], p["system"], p["subcat"])
        clusters[key]["products"].append(p)
        for ref in p["oem_refs"]:
            rk = ref.lower()
            if rk not in clusters[key]["oe"]:
                clusters[key]["oe"][rk] = {
                    "oe": ref, "part_name": p["name"][:120], "family": p["family"],
                    "system": p["system"], "fitment": p["fitment"][:4],
                    "images": p["images"][:2], "origin": "product_ref",
                }
    for oe, rec in master.items():
        key = (rec["family"], rec["system"], "")
        if rec["oe"].lower() not in clusters[key]["oe"]:
            clusters[key]["oe"][rec["oe"].lower()] = rec

    ranked = []
    for (fam, sysn, subcat), c in clusters.items():
        prods = c["products"]
        oes = list(c["oe"].values())
        if len(prods) < 2 or len(oes) < 2:
            continue
        link_oe = sum(1 for r in oes if find_oe_url(r["oe"], oe_index))
        # 覆盖：标题级判定优先（标题撞题才是真撞题），body 只做轻量兜底
        phrases = subcat_phrases(subcat)
        fams = FAMILY_KEYWORDS.get(fam, [])
        syskws = SYSTEM_KEYWORDS.get(sysn, [])
        cov_title_sub = 0
        cov_title_brand = 0
        for t in post_titles:
            if phrases and any(p in t for p in phrases):
                cov_title_sub += 1
            elif fams and any(k in t for k in fams):
                cov_title_brand += 1
        cov_body = 0
        for b in post_bodies:
            if fams and any(k in b for k in fams) and any(k in b for k in syskws):
                cov_body += 1
        dem = 0
        fslug = FAMILY_SLUG.get(fam, fam).replace("-", " ")
        for q, imp in demand.items():
            if fslug in q or any(k in q for k in fams):
                if any(k in q for k in syskws) or (phrases and any(p in q for p in phrases)):
                    dem += imp
        atype = "oem_cross_reference" if link_oe >= 2 else "product_guide"
        supply = len(prods) * 3 + len(oes)
        score = (supply + link_oe * 4 + min(dem, 500) * 0.4
                 - cov_title_sub * 80 - cov_title_brand * 18 - min(cov_body, 10) * 4)
        ranked.append({
            "family": fam, "system": sysn, "subcat": subcat,
            "products": len(prods), "oe": len(oes), "link_oe": link_oe,
            "cov_sub": cov_title_sub, "cov_brand": cov_title_brand, "cov_body": cov_body,
            "demand": dem, "article_type": atype, "score": round(score, 1),
        })
    ranked.sort(key=lambda x: (-x["score"], x["family"], x["system"], x["subcat"]))

    print("\n--- ranked clusters ---")
    shown = ranked if args.print_topics else ranked[:30]
    for r in shown:
        print("  %-20s %-11s %-26s prods=%-4d oe=%-4d linkOE=%-4d covT=%d/%d covB=%-3d type=%-19s score=%s"
              % (FAMILY_LABEL.get(r["family"], r["family"]), r["system"],
                 r["subcat"][:26], r["products"], r["oe"], r["link_oe"],
                 r["cov_sub"], r["cov_brand"], r["cov_body"],
                 r["article_type"], r["score"]))
    by_type = defaultdict(int)
    for r in ranked:
        by_type[r["article_type"]] += 1
    print("  [cluster count] total=%d  %s"
          % (len(ranked), "  ".join("%s=%d" % (k, v) for k, v in sorted(by_type.items()))))

    if args.print_topics:
        return 0

    picked, seen = [], set()

    def key_of(r):
        return (r["family"], r["system"], r["subcat"])

    # 第一轮：标题零撞题的簇里挑最高分
    for r in ranked:
        if r["cov_sub"] == 0 and key_of(r) not in seen:
            picked.append(r); seen.add(key_of(r))
        if len(picked) >= args.count:
            break
    # 第二轮：不够就用剩下的高分簇补
    for r in ranked:
        if len(picked) >= args.count:
            break
        if key_of(r) not in seen:
            picked.append(r); seen.add(key_of(r))

    # 类型混合：全挑到同一类时，换一个另一类的零撞题簇进来
    if args.mix and args.count >= 2 and picked:
        types = set(r["article_type"] for r in picked)
        if len(types) == 1:
            want = "product_guide" if types == {"oem_cross_reference"} else "oem_cross_reference"
            for r in ranked:
                if r["article_type"] == want and r["cov_sub"] == 0 and key_of(r) not in seen:
                    picked[-1] = r
                    break

    topics = []
    intent_slots = load_intent_slots()
    used_slots = defaultdict(list)

    def pick_slot(r, used):
        """标题意图槽位：同一品系内不重复占用同一个槽位。

        标题按「意图矩阵 × 主体」铺开（兄弟站点 kingmay 的做法）：
        同一个零件家族下的不同文章落在不同买家意图上，而不是共用一条标题模板。
        """
        kind = "export" if r.get("family") in ("vehicle", "export") else "parts"
        pool = [s for s in intent_slots.values() if s.get("kind") == kind]
        if not pool:
            pool = list(intent_slots.values())
        if not pool:
            return {"id": "", "desc": "", "title_template": ""}
        ctx = ("%s %s %s" % (r.get("family", ""), r.get("system", ""),
                              r.get("subcat", "") or "")).lower()
        used_ids = set(used.get("__all__", []))

        def key(s):
            hits = sum(1 for kw in (s.get("body_kws") or []) if kw in ctx)
            return (0 if s["id"] in used_ids else 1, hits)

        s = sorted(pool, key=lambda x: (-key(x)[0], -key(x)[1]))[0]
        used.setdefault("__all__", []).append(s["id"])
        return s

    for r in picked:
        key = (r["family"], r["system"], r["subcat"])
        c = clusters[key]
        prods = sorted(c["products"], key=lambda x: (-len(x["images"]), -len(x["fitment"]), x["slug"]))
        oes = sorted(c["oe"].values(),
                     key=lambda x: (0 if find_oe_url(x["oe"], oe_index) else 1,
                                    -len(x["fitment"]), -len(x["images"]), x["oe"]))

        oe_numbers = []
        for rec in oes[: args.max_oe]:
            oe_numbers.append({
                "oe": rec["oe"], "part_name": rec["part_name"],
                "fitment": rec["fitment"][:4], "images": rec["images"][:2],
                "oe_url": find_oe_url(rec["oe"], oe_index),
                "origin": rec.get("origin", ""),
            })
        product_pages, images = [], []
        for p in prods[: args.max_products]:
            product_pages.append({
                "slug": p["slug"], "url": p["url"], "name": p["name"],
                "brand": FAMILY_LABEL.get(p["family"], p["family"]),
                "system": p["system"], "sub_category": p["sub_category"],
                "images": p["images"][:2], "fitment": p["fitment"][:5],
                "oem_refs": p["oem_refs"][:6], "specs": p["specs"],
                "moq": p["moq"], "features": p["features"],
            })
            images.extend(p["images"][:1])

        oe_pages = []
        for rec in oes:
            u = find_oe_url(rec["oe"], oe_index)
            if u:
                oe_pages.append({"slug": u.rsplit("/", 1)[-1][:-5], "url": u})
            if len(oe_pages) >= 12:
                break

        fitment_all = []
        for p in prods:
            for v in p["fitment"]:
                if v not in fitment_all:
                    fitment_all.append(v)
        for rec in oes:
            for v in rec["fitment"]:
                if v not in fitment_all:
                    fitment_all.append(v)
        fitment_all = fitment_all[:14]

        label = FAMILY_LABEL.get(r["family"], r["family"])
        sub = r["subcat"] or SYSTEM_LABEL[r["system"]]
        slot = pick_slot(r, used_slots)
        tpl = slot.get("title_template") or "OE Number Cross-Reference and Sourcing Guide"
        head = "%s %s: " % (label, sub)
        title = head + tpl
        if len(title) > 70:
            # 先砍模板的副标题，再砍模板尾巴，最后才砍主体
            short = tpl.split(":")[0].strip()
            if len(head + short) <= 70:
                title = head + short
            else:
                title = (head + short)[:70].rsplit(" ", 1)[0]
        topic_id = "t-%s-%s-%s" % (TODAY, FAMILY_SLUG.get(r["family"], r["family"])[:16],
                                   slugify(sub)[:22])
        cat = "OEM Parts Reference" if r["article_type"] == "oem_cross_reference" else "Auto Parts Sourcing"

        topics.append({
            "id": topic_id,
            "created": TODAY,
            "topic": {
                "title": title,
                "primary_keyword": "%s %s wholesale" % (
                    FAMILY_SLUG.get(r["family"], r["family"]).replace("-", " "),
                    (sub or r["system"]).lower()),
                "intent": "commercial",
                "category": cat,
                "article_type": r["article_type"],
                "title_intent": slot.get("id", ""),
                "title_intent_desc": slot.get("desc", ""),
                "why_now": ("%d catalog product pages and %d cross-referenced OE numbers already "
                            "published for %s %s; %d of them have live OE detail pages; demand "
                            "signal %d impressions; existing coverage %d articles."
                            % (r["products"], r["oe"], label, sub, r["link_oe"],
                               r["demand"], r["cov_sub"])),
                "brand_family": r["family"],
                "brand_label": label,
                "system": r["system"],
                "sub_category": sub,
            },
            "factpack": {
                "oe_numbers": oe_numbers,
                "product_pages": product_pages,
                "oe_pages": oe_pages,
                "fitment_vehicles": fitment_all,
                "images": images[:10],
                "moq": contract.get("facts", {}).get("moq_default", 10),
                "lead_time": contract.get("facts", {}).get("lead_time_default", ""),
                "notes": ("Only use OE numbers, fitment and specs listed here. Never invent a part "
                          "number. No numeric unit price. No competitor brand names. "
                          "Every OE number must come from oe_numbers[].oe."),
            },
            "scores": {
                "supply": r["products"] * 3 + r["oe"],
                "linkable_parts": r["products"],
                "linkable_oe": r["link_oe"],
                "coverage": r["cov_sub"],
                "demand_impressions": r["demand"],
                "total": r["score"],
            },
        })

    out = {
        "generated_at": "%sT19:30:00" % TODAY,
        "contract_version": contract.get("version"),
        "topics": topics,
    }
    print("\n--- planned topics ---")
    for t in topics:
        print("  [%s] %s" % (t["id"], t["topic"]["title"]))
        print("      keyword=%s  category=%s  type=%s"
              % (t["topic"]["primary_keyword"], t["topic"]["category"],
                 t["topic"]["article_type"]))
        print("      parts=%d  oe_facts=%d  oe_links=%d  images=%d  coverage=%d  score=%s"
              % (t["scores"]["linkable_parts"], len(t["factpack"]["oe_numbers"]),
                 t["scores"]["linkable_oe"], len(t["factpack"]["images"]),
                 t["scores"]["coverage"], t["scores"]["total"]))

    if args.dry_run:
        print("\nDRY-RUN: nothing written")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nwrote %s (%d topics)" % (OUT, len(topics)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
