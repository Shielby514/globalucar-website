# -*- coding: utf-8 -*-
"""
25-blog-generate.py —— 按契约生成博客正文（调用 MiniMax LLM）

输入
  .workbuddy/data/blog-topics.json      选题 + 事实包（由 24-blog-topic-planner.py 产出）
  .workbuddy/scripts/blog-contract.json 文章契约（结构门槛 / 禁项 / 评分权重）

输出
  .workbuddy/data/blog-drafts.json      待评分草稿（由 26-blog-quality-gate.py 评分）

设计要点
  · 事实约束：OE 号 / 适配车型 / 规格 **只能**取自 factpack，prompt 里逐条列出并要求不得杜撰
  · 结构约束：把契约的结构门槛翻译成明确的 H2 大纲 + 表格/FAQ/图片/链接数量要求
  · 链接约束：只允许使用 factpack 里给出的 /parts/ 与 /oe/ URL，锚文本 ≥5 字符
  · 图片约束：只允许使用 factpack.images 里给出的本地路径（禁竞品热链）
  · 失败降级：单篇失败不影响其它篇；失败稿标记 generate_error，不进发布队列
  · 幂等：同样 topics + 同样模型 → 同样草稿（已生成的 topic_id 默认跳过，用 --force 重跑）

用法
  python 25-blog-generate.py                 # 生成缺失的草稿
  python 25-blog-generate.py --force         # 全部重生成
  python 25-blog-generate.py --limit 1       # 本轮只生成 1 篇
  python 25-blog-generate.py --dry-run       # 只打印 prompt 摘要
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA = os.path.join(BASE, ".workbuddy", "data")
CONTRACT = os.path.join(SCRIPT_DIR, "blog-contract.json")
TOPICS = os.path.join(DATA, "blog-topics.json")
DRAFTS = os.path.join(DATA, "blog-drafts.json")

sys.path.insert(0, SCRIPT_DIR)
from llm_client import LLMClient, LLMError, parse_json_loose  # noqa: E402

SYSTEM_PROMPT = """You are a senior B2B automotive-parts editor writing for overseas parts importers \
and distributors (not retail shoppers).

Hard writing rules:
1. Write in English only. No Chinese characters.
2. Use ONLY the OE numbers, vehicle fitment and specs given in the FACTS block. Never invent, \
guess or extrapolate a part number. If a fact is not in FACTS, do not state it.
3. Never state a numeric unit price. Say the price is FOB quotation on request.
4. Never claim availability ("in stock", "ready to ship", "available now"). The catalogue does \
not confirm stock. Only state MOQ and the quotation lead time.
5. Never name competitor brands. Never use "we", "our", "us", "I".
6. No hype: no "best price", "cheapest", "100% original", "world's largest", "guaranteed".
7. Be specific and practical: what the part is, how to identify it, what it replaces, \
what to check on arrival, MOQ and lead time.
8. Return ONE JSON object and nothing else. No markdown fences, no commentary."""


def build_prompt(topic, contract, factpack):
    """把契约 + 事实包翻译成一条自包含的生成指令。"""
    st = contract.get("structure", {})
    md = contract.get("metadata", {})
    at = contract.get("article_types", {}).get(topic["topic"].get("article_type", ""), {})
    req_links = contract.get("internal_link_targets", {})

    min_parts = at.get("min_parts_links", req_links.get("min_parts_links", 2))
    min_oe = at.get("min_oe_links", req_links.get("min_oe_links", 2))
    min_rows = at.get("min_crossref_rows", 4)
    min_faq = contract.get("faq_min", 4)
    min_img = st.get("min_body_images", 4)
    min_links = st.get("min_body_links", 6)
    max_links = st.get("max_body_links", 30)

    sections = contract.get("required_sections", [])
    banned = contract.get("banned_phrases", [])[:8]
    banned_pat = contract.get("banned_patterns", [])[:5]
    anchor = contract.get("anchor_rules", {})

    parts = factpack.get("product_pages", [])
    oe_pages = factpack.get("oe_pages", [])
    oe_numbers = factpack.get("oe_numbers", [])
    images = factpack.get("images", [])
    fitment = factpack.get("fitment_vehicles", [])
    moq = factpack.get("moq", 10)
    lead = factpack.get("lead_time", "")

    parts_list = "\n".join(
        "- %s | url=%s | oem_refs=%s | fitment=%s | specs=%s"
        % (p.get("name", "")[:70], p.get("url", ""),
           ", ".join(p.get("oem_refs", [])[:4]),
           ", ".join(p.get("fitment", [])[:3]),
           json.dumps(p.get("specs", {}), ensure_ascii=False)[:220])
        for p in parts) or "(none)"

    oe_list = "\n".join(
        "- %s | %s | fitment=%s | oe_page=%s"
        % (o.get("oe", ""), o.get("part_name", "")[:70],
           ", ".join(o.get("fitment", [])[:3]), o.get("oe_url") or "(no published page)")
        for o in oe_numbers) or "(none)"

    oe_page_list = "\n".join("- %s" % o.get("url", "") for o in oe_pages) or "(none)"
    img_list = "\n".join("- %s" % i for i in images) or "(none)"
    fit_list = "\n".join("- %s" % f for f in fitment) or "(none)"

    parts_urls = "\n".join("- %s  (anchor text should describe the product, min %d chars)"
                            % (p.get("url", ""), anchor.get("min_len", 5))
                            for p in parts) or "(none)"
    oe_urls = "\n".join("- %s" % o.get("url", "") for o in oe_pages) or "(none)"

    section_lines = "\n".join("  %d. %s" % (i + 1, s) for i, s in enumerate(sections))

    return """Write one complete blog article as a single JSON object.

TOPIC
  working title (you may sharpen it, keep it <= {title_max} chars):
    {title}
  primary keyword: {keyword}
  intent: {intent}
  category: {category}
  article type: {atype}
  why this topic now: {why_now}

FACTS - the ONLY facts you may use
OE numbers (use these exact strings):
{oe_list}
Published OE detail pages you may link to:
{oe_page_list}
Products with their detail pages (you may link to these urls):
{parts_list}
Vehicles / fitment mentioned in the catalogue:
{fit_list}
Images you may use (local paths only, copy them verbatim into src):
{img_list}
MOQ: {moq} pieces. Quotation lead time: {lead}

STRUCTURE REQUIREMENTS (the quality gate checks every one of these)
  body words: {min_words}-{max_words}
  H2 sections: {min_h2}-{max_h2} (use these headings, adapt the wording slightly if needed):
{section_lines}
  every H2 must have at least {min_par} paragraphs
  include at least {min_tables} HTML <table> - one of them MUST be a cross-reference table with \
header row "OE Number" and "Part Name" and at least {min_rows} data rows, every OE number in it \
must come from the OE numbers list above
  include at least {min_faq} FAQ entries as a visible <section> with class "faq" and \
heading "FAQ", each Q&A written as <h3>Question</h3><p>Answer</p>
  include at least {min_img} images inside the body using only the local paths listed above, each \
with a descriptive alt attribute (>= {alt_min} chars) that contains the part name or the OE number
  include at least {min_links} and at most {max_links} in-body links, of which at least \
{min_parts} must point to the product pages listed below and at least {min_oe} must point to the \
published OE pages listed below
  every anchor text must be at least {anchor_min} characters and must describe the target
  never link to a url that is not listed below
  do not use the words "read more", "click here", "here", "more", "link", "source" as anchor text

Product page urls you may link to (and only these):
{parts_urls}
OE page urls you may link to (and only these):
{oe_urls}

WRITING REQUIREMENTS
  - do not use any of these banned phrases: {banned}
  - do not use these patterns: {banned_pat}
  - do not use first person or "we/our/us"
  - MOQ {moq} pieces, FOB quotation on request, {lead}
  - mention at least 2 of the OE numbers above in the body text
  - mention at least 2 entries from the fitment list
  - copy every OE number EXACTLY as written above, including any suffix such as -EA, -CC, -D or /R.
    Never shorten it, never drop a segment, and never invent a similar-looking number.
  - never claim availability: no "in stock", "available now", "ready to ship", "we ship from stock".
    The catalogue does not confirm stock. Say "MOQ {moq} pieces, FOB quotation on request".
  - never state a warranty period in months or years unless it appears in the FACTS block
  - use at least {min_img} images in the body (aim for 5); every src must be one of the local
    paths listed above, and every alt must name the part or quote the OE number

OUTPUT FORMAT - return exactly this JSON object, nothing else:
{{
  "title": "<= {title_max} chars",
  "description": "<= {desc_max} chars, one or two sentences, includes the primary keyword",
  "keywords": [3 to {kw_max} short keyword strings],
  "tags": [3 to {tags_max} short tag strings],
  "category": "{category}",
  "date": "{today}",
  "readtime": <integer minutes>,
  "image": "<one of the local image paths above>",
  "toc": ["<h2 text>", "..."],
  "article_type": "{atype}",
  "content": "<html string: h2/h3/p/ul/li/table/img/a>"
}}
""".format(
        title_max=md.get("title_max", 70),
        desc_max=md.get("description_max", 160),
        kw_max=md.get("keywords_max", 8),
        tags_max=md.get("tags_max", 6),
        title=topic["topic"]["title"],
        keyword=topic["topic"]["primary_keyword"],
        intent=topic["topic"].get("intent", "commercial"),
        category=topic["topic"]["category"],
        atype=topic["topic"].get("article_type", "product_guide"),
        why_now=topic["topic"].get("why_now", ""),
        oe_list=oe_list, oe_page_list=oe_page_list, parts_list=parts_list,
        fit_list=fit_list, img_list=img_list,
        moq=moq, lead=lead,
        min_words=st.get("min_words", 1400), max_words=st.get("max_words", 4200),
        min_h2=st.get("min_h2", 8), max_h2=st.get("max_h2", 14),
        min_par=st.get("min_paragraphs_per_h2", 2),
        min_tables=st.get("min_tables", 1),
        min_faq=min_faq, min_img=min_img,
        min_links=min_links, max_links=max_links,
        min_parts=min_parts, min_oe=min_oe, min_rows=min_rows,
        alt_min=st.get("min_image_alt_len", 12),
        anchor_min=anchor.get("min_len", 5),
        parts_urls=parts_urls, oe_urls=oe_urls,
        section_lines=section_lines,
        banned=", ".join(banned) or "(none)",
        banned_pat=" | ".join(banned_pat) or "(none)",
        today=date.today().isoformat(),
    )


REQUIRED_KEYS = ("title", "description", "keywords", "tags", "category",
                 "date", "readtime", "image", "content")


def normalize_draft(d, topic):
    """模型输出不一定规整，补齐缺失字段并做基本清洗。"""
    out = {}
    for k in REQUIRED_KEYS:
        out[k] = d.get(k)
    out["content"] = str(out.get("content") or "")
    out["title"] = str(out.get("title") or topic["topic"]["title"])
    out["description"] = str(out.get("description") or "")[:300]
    kw = out.get("keywords")
    if isinstance(kw, str):
        kw = [x.strip() for x in kw.split(",") if x.strip()]
    out["keywords"] = [str(x).strip() for x in (kw or []) if str(x).strip()]
    tg = out.get("tags")
    if isinstance(tg, str):
        tg = [x.strip() for x in tg.split(",") if x.strip()]
    out["tags"] = [str(x).strip() for x in (tg or []) if str(x).strip()]
    out["category"] = str(out.get("category") or topic["topic"]["category"])
    out["date"] = str(out.get("date") or date.today().isoformat())
    try:
        out["readtime"] = int(out.get("readtime") or 8)
    except Exception:
        out["readtime"] = 8
    out["image"] = str(out.get("image") or "")
    toc = out.get("toc")
    if isinstance(toc, str):
        toc = [x.strip() for x in toc.split("\n") if x.strip()]
    out["toc"] = [str(x).strip() for x in (toc or []) if str(x).strip()]
    out["article_type"] = str(out.get("article_type") or topic["topic"].get("article_type", "product_guide"))
    out["slug"] = d.get("slug") or slugify(out.get("title") or topic["topic"]["title"])
    return out


def slugify(t, maxlen=78):
    t = re.sub(r"<[^>]+>", "", t or "")
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:maxlen].rstrip("-")


def build_repair_prompt(draft, contract):
    """把评分卡的扣分项喂回模型，让它改稿（自愈，不直接丢弃）。"""
    gate = draft.get("gate") or {}
    art = draft.get("draft") or {}
    lines = []
    for comp, c in (gate.get("components") or {}).items():
        for iss in (c.get("issues") or []):
            if iss.get("level") == "fail":
                lines.append("- [%s] %s : %s" % (comp, iss.get("rule"), iss.get("detail")))
    if not lines:
        return None
    st = contract.get("structure", {})
    md = contract.get("metadata", {})
    return """This article was rejected by our quality gate. Fix it and return the corrected article \
as ONE JSON object with the same fields as before (title, description, keywords, tags, category, \
date, readtime, image, toc, article_type, content).

WHY IT WAS REJECTED — every item below must be fixed:
{issues}

RULES FOR THE REVISION
  - keep the same topic and the same facts; do not introduce any new OE number, vehicle or spec
  - every OE number you write must be copied character-for-character from the original article
    or from the FACTS list below; never shorten it and never invent a similar-looking one
  - do not add any availability statement ("in stock", "ready to ship")
  - keep the article between {min_words} and {max_words} words, {min_h2}-{max_h2} H2 sections
  - keep at least {min_links} in-body links and at least {min_img} images with descriptive alt text
  - title must be {tmin}-{tmax} characters, description {dmin}-{dmax} characters
  - keep the same JSON keys, no markdown fences, no commentary

FACTS (the ONLY facts you may use):
{facts}

CURRENT CONTENT (HTML):
{content}
""".format(
        issues="\n".join(lines[:25]),
        min_words=st.get("min_words", 1400), max_words=st.get("max_words", 4200),
        min_h2=st.get("min_h2", 8), max_h2=st.get("max_h2", 14),
        min_links=st.get("min_body_links", 6), min_img=st.get("min_body_images", 4),
        tmin=md.get("title_min", 25), tmax=md.get("title_max", 70),
        dmin=md.get("description_min", 70), dmax=md.get("description_max", 160),
        facts=json.dumps(draft.get("factpack") or {}, ensure_ascii=False)[:6000],
        content=(art.get("content") or "")[:24000],
    )


def main():
    ap = argparse.ArgumentParser(description="blog article generator")
    ap.add_argument("--force", action="store_true", help="regenerate topics that already have drafts")
    ap.add_argument("--limit", type=int, default=0, help="max topics to generate this run")
    ap.add_argument("--dry-run", action="store_true", help="print prompt summary only")
    ap.add_argument("--repair", action="store_true",
                    help="retry drafts rejected by the quality gate, feeding the failures back")
    ap.add_argument("--model", default="MiniMax-M3")
    ap.add_argument("--max-tokens", type=int, default=12000)
    args = ap.parse_args()

    if not os.path.exists(CONTRACT):
        print("contract not found: %s" % CONTRACT)
        return 1
    if not os.path.exists(TOPICS):
        print("topics not found: %s (run 24-blog-topic-planner.py first)" % TOPICS)
        return 1
    contract = json.load(open(CONTRACT, encoding="utf-8"))
    tdoc = json.load(open(TOPICS, encoding="utf-8"))
    topics = tdoc.get("topics") or []
    if not topics:
        print("no topics to generate")
        return 0

    topic_ids = set(t.get("id") for t in topics if t.get("id"))
    drafts = []
    if os.path.exists(DRAFTS):
        try:
            raw = json.load(open(DRAFTS, encoding="utf-8"))
        except Exception:
            raw = []
        kept = {}
        for d in raw if isinstance(raw, list) else []:
            if not isinstance(d, dict):
                continue
            tid = (d.get("topic") or {}).get("id") or d.get("id")
            # 只保留属于当前选题集的草稿（清掉历史遗留 / 外部夹具）；
            # 同一个 topic id 只留最后一条，避免重复
            if tid and tid in topic_ids:
                kept[tid] = d
        drafts = [kept[k] for k in sorted(kept)]
    have = set()
    for d in drafts:
        tid = (d.get("topic") or {}).get("id") or d.get("id")
        if tid:
            have.add(tid)

    # ---------- 改稿模式（自愈） ----------
    if args.repair:
        cli = LLMClient(model=args.model, verbose=True)
        n = 0
        for d in list(drafts):
            gate = d.get("gate") or {}
            if gate.get("publish") or d.get("generate_error"):
                continue
            tid = (d.get("topic") or {}).get("id") or d.get("id")
            topic_obj = next((t for t in topics if t.get("id") == tid), None)
            if not topic_obj:
                continue
            prompt = build_repair_prompt(d, contract)
            if not prompt:
                continue
            print("\n[repair] %s" % tid)
            try:
                raw = cli.chat(prompt, system=SYSTEM_PROMPT,
                               max_tokens=args.max_tokens, temperature=0.35, retries=1)
                obj = parse_json_loose(raw)
                if not isinstance(obj, dict):
                    raise ValueError("top-level JSON is %s" % type(obj).__name__)
                art = normalize_draft(obj, topic_obj)
                if len(art["content"]) < 800:
                    raise ValueError("content too short (%d)" % len(art["content"]))
                d["draft"] = art
                d.pop("gate", None)          # 让评分卡重新打分
                d["repaired_at"] = date.today().isoformat()
                n += 1
                print("  ok: %r content=%d" % (art["title"][:50], len(art["content"])))
            except Exception as e:
                print("  REPAIR FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))
        with open(DRAFTS, "w", encoding="utf-8") as f:
            json.dump(drafts, f, ensure_ascii=False, indent=1)
        print("\nrepaired %d draft(s) -> %s" % (n, DRAFTS))
        return 0

    todo = []
    for t in topics:
        tid = t.get("id")
        if tid in have and not args.force:
            continue
        todo.append(t)
        if args.limit and len(todo) >= args.limit:
            break

    print("topics=%d  existing_drafts=%d  to_generate=%d" % (len(topics), len(drafts), len(todo)))
    if not todo:
        print("nothing to do (use --force to regenerate)")
        return 0

    if args.dry_run:
        for t in todo:
            p = build_prompt(t, contract, t.get("factpack") or {})
            print("\n=== %s ===\n%s" % (t.get("id"), p[:1500]))
        return 0

    cli = LLMClient(model=args.model, verbose=True)
    ok, failed = 0, 0
    for t in todo:
        tid = t.get("id")
        print("\n[generate] %s" % tid)
        prompt = build_prompt(t, contract, t.get("factpack") or {})
        try:
            raw = cli.chat(prompt, system=SYSTEM_PROMPT,
                           max_tokens=args.max_tokens, temperature=0.45, retries=1)
            obj = parse_json_loose(raw)
            if not isinstance(obj, dict):
                raise ValueError("top-level JSON is %s, expected object" % type(obj).__name__)
            draft_article = normalize_draft(obj, t)
            if len(draft_article["content"]) < 800:
                raise ValueError("content too short (%d chars)" % len(draft_article["content"]))
            draft = {
                "id": tid,
                "topic": dict(t["topic"], id=tid),
                "factpack": t.get("factpack") or {},
                "draft": draft_article,
                "generated_at": date.today().isoformat(),
            }
            drafts = [d for d in drafts
                      if ((d.get("topic") or {}).get("id") or d.get("id")) != tid]
            drafts.append(draft)
            ok += 1
            print("  ok: title=%r content=%d chars" % (draft_article["title"][:50],
                                                       len(draft_article["content"])))
        except (LLMError, ValueError, Exception) as e:
            failed += 1
            print("  FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))
            err = {
                "id": tid, "topic": dict(t["topic"], id=tid), "factpack": t.get("factpack") or {},
                "draft": {}, "generate_error": "%s: %s" % (type(e).__name__, str(e)[:300]),
            }
            drafts = [d for d in drafts
                      if ((d.get("topic") or {}).get("id") or d.get("id")) != tid]
            drafts.append(err)

    drafts.sort(key=lambda d: ((d.get("topic") or {}).get("id") or ""))
    with open(DRAFTS, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=1)
    print("\ngenerated ok=%d failed=%d  usage=%s" % (ok, failed, cli.usage_total))
    print("wrote %s (%d drafts)" % (DRAFTS, len(drafts)))
    return 0 if failed == 0 else 0   # 单篇失败不阻断流水线


if __name__ == "__main__":
    sys.exit(main())
