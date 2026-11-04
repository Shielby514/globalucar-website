# -*- coding: utf-8 -*-
"""
27-blog-publish.py —— 把通过评分卡的草稿并入 blog-posts.json 并出静态页

输入
  .workbuddy/data/blog-drafts.json      待发布草稿（26-blog-quality-gate.py 已评分）
  .workbuddy/data/blog-posts.json        存量文章
  .workbuddy/scripts/blog-contract.json  契约（阈值来源）

输出
  .workbuddy/data/blog-posts.json        合并后的全量文章元数据
  blog/<slug>.html                       新文章静态页

关键安全约束
  · **只发布 gate.publish == true 的草稿**，低于阈值的进草稿队列不动
  · **只生成新页**：调用生成器时带 --only-new，磁盘上已有的 155 篇一个字节都不碰
    （线上页是「生成器 + 后续注入（锚文本模块）」两层叠出来的，重跑生成器会抹掉注入层）
  · slug 必须唯一，且不能与已有文章撞车
  · 写 blog-posts.json 前先备份
  · 幂等：同一个草稿重复发布不会产生第二篇

用法
  python 27-blog-publish.py                # 发布
  python 27-blog-publish.py --dry-run      # 只报告
  python 27-blog-publish.py --max 3        # 本轮最多发 3 篇
  python 27-blog-publish.py --no-pages     # 只并元数据不出页
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA = os.path.join(BASE, ".workbuddy", "data")
CONTRACT = os.path.join(SCRIPT_DIR, "blog-contract.json")
DRAFTS = os.path.join(DATA, "blog-drafts.json")
POSTS = os.path.join(DATA, "blog-posts.json")
POSTS_BAK = os.path.join(DATA, "blog-posts.json.bak")
BLOG_DIR = os.path.join(BASE, "blog")
GENERATOR = os.path.join(SCRIPT_DIR, "generate_blog_static_pages.py")
TODAY = __import__("datetime").date.today().isoformat()

sys.path.insert(0, SCRIPT_DIR)
from llm_client import LLMError  # noqa: E402  (only for its exception type; unused otherwise)


def slugify(t, maxlen=78):
    t = re.sub(r"<[^>]+>", "", t or "")
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:maxlen].rstrip("-")


def norm_category(raw, contract):
    """把分类归一到契约的受控词表（走别名映射）。"""
    c = (raw or "").strip()
    if not c:
        return contract.get("categories", ["Auto Parts Sourcing"])[0]
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
        for k, v in aliases.items():
            if k.lower() == plain.lower():
                return v
    return allowed[0] if allowed else c


def gen_slugs(posts):
    """复刻 generate_blog_static_pages.post_slug 的命名规则（含去重后缀）。"""
    slugs = {}
    for p in posts:
        s = p.get("slug") or slugify(p.get("title") or "untitled")
        s = re.sub(r"[^a-zA-Z0-9-]+", "-", s).strip("-").lower()
        if s in slugs.values():
            s = s + "-" + str(p.get("id"))
        slugs[p.get("id")] = s
    return slugs


def main():
    ap = argparse.ArgumentParser(description="blog publisher")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max", type=int, default=5, help="max articles to publish this run")
    ap.add_argument("--no-pages", action="store_true", help="merge metadata only")
    ap.add_argument("--min-score", type=int, default=0,
                    help="override publish threshold (0 = use contract)")
    args = ap.parse_args()

    if not os.path.exists(POSTS):
        print("posts not found: %s" % POSTS)
        return 1
    if not os.path.exists(DRAFTS):
        print("drafts not found: %s (run 25-blog-generate.py / 26-blog-quality-gate.py)" % DRAFTS)
        return 1

    contract = json.load(open(CONTRACT, encoding="utf-8"))
    threshold = args.min_score or contract.get("scoring", {}).get("publish_threshold", 85)
    posts = json.load(open(POSTS, encoding="utf-8"))
    drafts = json.load(open(DRAFTS, encoding="utf-8"))

    existing_slugs = set(gen_slugs(posts).values())
    existing_slugs |= {f[:-5] for f in os.listdir(BLOG_DIR) if f.endswith(".html")}

    passed, rejected = [], []
    for d in drafts:
        tid = (d.get("topic") or {}).get("id") or d.get("id")
        gate = d.get("gate") or {}
        dr = d.get("draft") or {}
        score = gate.get("score", 0)
        if d.get("generate_error"):
            rejected.append((tid, "generate_error"))
            continue
        if not gate.get("publish"):
            rejected.append((tid, "score=%s not published" % score))
            continue
        if score < threshold:
            rejected.append((tid, "score=%s < threshold=%s" % (score, threshold)))
            continue
        if not dr.get("content") or len(dr.get("content", "")) < 800:
            rejected.append((tid, "content too short"))
            continue
        passed.append(d)

    print("posts=%d  drafts=%d  publishable=%d  rejected=%d  threshold=%d"
          % (len(posts), len(drafts), len(passed), len(rejected), threshold))
    for tid, why in rejected:
        print("  [skip] %s : %s" % (tid, why))

    if not passed:
        print("nothing to publish")
        return 0

    # 按 id 排序保证顺序稳定
    passed.sort(key=lambda d: ((d.get("topic") or {}).get("id") or ""))
    passed = passed[: args.max]

    next_id = max((p.get("id") or 0) for p in posts) + 1
    to_add = []
    already = []
    for d in passed:
        tid = (d.get("topic") or {}).get("id") or d.get("id")
        dr = dict(d.get("draft") or {})
        slug = re.sub(r"[^a-zA-Z0-9-]+", "-",
                      str(dr.get("slug") or slugify(dr.get("title") or ""))).strip("-").lower()
        # 幂等守卫：这个 slug 已经在 blog-posts.json 里 → 之前发布过，别再并一遍
        if slug and slug in existing_slugs:
            already.append((tid, slug))
            continue
        if not slug:
            slug = slugify((dr.get("title") or "") + "-" + str(tid))
        if slug in existing_slugs:
            slug = slug + "-" + str(next_id)
        existing_slugs.add(slug)
        dr["slug"] = slug
        dr["id"] = next_id
        dr["article_type"] = dr.get("article_type") or (d.get("topic") or {}).get("article_type", "")
        # 分类归一到受控词表；发布日由发布器写，模型给的日期不可信
        dr["category"] = norm_category(dr.get("category"), contract)
        dr["date"] = TODAY
        dr["source"] = "blog_pipeline"
        dr["published_at"] = TODAY
        dr["gate_score"] = (d.get("gate") or {}).get("score", 0)
        to_add.append(dr)
        next_id += 1

    for tid, slug in already:
        print("  [skip] %s : 已发布过（%s），本轮不重复合并" % (tid, slug))

    print("\n--- to publish ---")
    for dr in to_add:
        print("  id=%-5s score=%-4s %-62s /blog/%s.html"
              % (dr["id"], dr.get("gate_score"), dr.get("title", "")[:62], dr["slug"]))
    if not to_add and not already:
        print("  (nothing new)")

    if args.dry_run:
        print("\nDRY-RUN: nothing written")
        return 0

    # 备份 + 合并
    shutil.copyfile(POSTS, POSTS_BAK)
    merged = posts + to_add
    merged.sort(key=lambda x: x.get("id") or 0)
    with open(POSTS, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    print("\nmerged blog-posts.json: %d -> %d (backup: %s)"
          % (len(posts), len(merged), os.path.basename(POSTS_BAK)))

    if args.no_pages:
        return 0

    # 出页：--only-new 只生成磁盘上还没有的页，存量 155 篇不动
    print("\n--- generating static pages (--only-new) ---")
    cmd = [sys.executable, GENERATOR, "--only-new"]
    r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    for line in (r.stdout or "").splitlines():
        print("  " + line)
    if r.stderr and r.stderr.strip():
        print("  [stderr] " + r.stderr.strip()[:500])
    if r.returncode != 0:
        print("!! generator failed rc=%s —— 已合并的 blog-posts.json 保留，页面未出" % r.returncode)
        return 2

    missing = [dr["slug"] for dr in to_add
               if not os.path.exists(os.path.join(BLOG_DIR, dr["slug"] + ".html"))]
    if missing:
        print("!! 以下文章没有生成静态页: %s" % missing)
        return 3
    print("verified: %d new page(s) on disk (already published: %d)"
          % (len(to_add), len(already)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
