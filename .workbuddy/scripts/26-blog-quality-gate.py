# -*- coding: utf-8 -*-
"""
26-blog-quality-gate.py —— OE 博客文章质量评分卡（100 分制）

用途
----
对 .workbuddy/data/blog-drafts.json 里的每一篇草稿做 100 分制质量评分，结果写回
草稿对象的 "gate" 字段（score / publish / verdict / components / issues），
供发布流水线决定"这篇能不能发"。

设计原则
--------
1. 阈值、权重、白名单、禁词、锚文本规则、去重阈值全部从
   .workbuddy/scripts/blog-contract.json 读取 —— 脚本里不写死数值。
   改规范只改契约，不改脚本。
2. 六个维度各自独立打分：维度得分 = 满分 × (通过规则权重占比)。
   每条规则单独记录"扣在哪一条"，逐项可解释。
3. 契约 scoring.hard_fail_zero_out 里的维度（facts / uniqueness）一旦触发致命违规
   （事实编造 / 与存量重复），该维度直接 0 分，并且整篇 publish=false。
4. 幂等：连续跑两次，blog-drafts.json 的内容完全一致
   （规则顺序固定，issues 按固定次序输出，不依赖 set 的迭代顺序）。

用法
----
  set PYTHONIOENCODING=utf-8
  C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python313\\python.exe ^
      G:\\ucars\\.workbuddy\\scripts\\26-blog-quality-gate.py [--verbose]

  可选参数：--contract / --drafts / --posts / --site-root
  默认值即生产路径：.workbuddy/scripts/blog-contract.json、.workbuddy/data/blog-drafts.json、
  .workbuddy/data/blog-posts.json。用 --drafts 指向别处即可跑自检而不碰生产草稿，例如：
    python 26-blog-quality-gate.py --drafts .workbuddy/data/_gate-selftest.json
  （自检夹具：.workbuddy/data/_gate-selftest.json，含 1 篇应通过 / 1 篇应淘汰 / 1 篇边界草稿）

退出码
------
  0  评分完成（哪怕所有草稿都不达标也是 0 —— 评分器只做筛选，不该让流水线崩）
  1  输入缺失或 JSON 损坏

维度归属（一条规则只归一个维度，避免重复扣分）
  structure   词数、H2 数量、每 H2 段落数、表格数、FAQ 条数、Quick Answer、H1 唯一、空 H2
  facts       OE 号必须有 factpack 支撑、交叉号表格、交叉号表内 OE 号、数字单价、库存宣称、
              禁词、禁模式、自称
  links       正文链接数量、锚文本长度/重复/泛化/截断、/parts/ 与 /oe/ 数量（按文章类型取门槛）、
              落地页存在、站外外链
  images      正文图片数量、alt 质量、alt 指向 factpack 品类、src 文件存在、src 落在自有目录
  metadata    title/description 长度、keywords/tags 数量、category 白名单、date、readtime、image、slug
  uniqueness  与存量文章的标题 Jaccard、关键词 Jaccard、段落重复率、标题首词间隔

文章类型（契约 article_types / article_type_field / article_type_default）
  oem_cross_reference  min_parts_links=2, min_oe_links=2, min_crossref_rows=4
  product_guide        min_parts_links=4, min_oe_links=0, min_crossref_rows=6
  读取路径默认 draft.article_type（契约 article_type_field 可改）；缺失时用 article_type_default。
  min_parts_links / min_oe_links 优先取 article_types[type]，契约里没有该 type 时才回落到
  internal_link_targets。min_oe_links=0 的类型不因缺 /oe/ 链接扣分（该条规则直接跳过）。
  min_crossref_rows 取自 article_types[type]，缺失时回落到 crossref_table.min_rows。

实现口径（脚本内常量，非契约阈值）
  MIN_PARA_CHARS = 40   段落重复率比对时的最短段落（太短的样板句不算重复）
  FUZZY_PARA_RATIO = 0.92  段落近似重复的相似度阈值
  STOPWORDS            标题/关键词 token 化的停用词表（避免 "the/a/for" 稀释 Jaccard）
  OE_IGNORE / UNIT_SUFFIX / STANDARD_PREFIX  OE 号提取的降噪名单
"""
import argparse
import difflib
import html as html_lib
import json
import os
import re
import sys
import unicodedata
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CONTRACT = os.path.join(BASE, '.workbuddy', 'scripts', 'blog-contract.json')
DEFAULT_DRAFTS = os.path.join(BASE, '.workbuddy', 'data', 'blog-drafts.json')
DEFAULT_POSTS = os.path.join(BASE, '.workbuddy', 'data', 'blog-posts.json')
DEFAULT_SITE_ROOT = BASE

DIMENSIONS = ('structure', 'facts', 'links', 'images', 'metadata', 'uniqueness')

# ---------------------------------------------------------------- 常量 / 正则

MIN_PARA_CHARS = 40
FUZZY_PARA_RATIO = 0.92

STOPWORDS = {
    'a', 'an', 'the', 'of', 'for', 'to', 'in', 'on', 'and', 'or', 'with', 'from',
    'by', 'at', 'as', 'is', 'are', 'be', 'it', 'its', 'your', 'you', 'yours',
    'how', 'what', 'why', 'when', 'can', 'do', 'does', 'vs', 'about', 'into',
    'that', 'this', 'these', 'those', 'their', 'them', 'they', 'his', 'her',
}

# OE 号提取（对正文大写后的文本生效）
OE_HYPHEN_RE = re.compile(r'\b[0-9A-Z]{2,8}-[0-9A-Z]{1,8}(?:-[0-9A-Z]{1,4})?\b')
OE_PLAIN_RE = re.compile(r'\b[A-Z0-9]{2,16}\b')
OE_IGNORE = {'J1939', 'J1939-11'}
UNIT_SUFFIXES = {
    'KM', 'KG', 'MM', 'CM', 'M', 'L', 'ML', 'CC', 'V', 'A', 'W', 'KW', 'HP',
    'NM', 'BAR', 'PSI', 'RPM', 'MPH', 'KMH', 'T', 'MM2', 'MM3', 'EA', 'PCS',
}
STANDARD_PREFIX_RE = re.compile(r'^(?:ISO|IATF|SAE|ECE|UNECE|DOT|ASTM|IEC|ANSI|GB|ROHS|REACH)\d')

# 自有站点域名：正文里的绝对外链（竞品热链）以此判定
SITE_DOMAIN = 'global-ucars.com'

# 价格 / 库存 / 自称
PRICE_RES = [
    re.compile(r'(?:US\s*)?[$€£¥]\s?\d[\d,]*(?:\.\d{1,2})?'),
    re.compile(r'\b(?:USD|EUR|CNY|RMB)\s?[:=]?\s?\d[\d,]*(?:\.\d{1,2})?', re.I),
    re.compile(r'\b\d[\d,]*(?:\.\d{1,2})?\s?(?:USD|EUR|CNY|RMB|dollars?)\b', re.I),
]
STOCK_RES = [
    re.compile(r'\bin[- ]stock\b', re.I),
    re.compile(r'\bstocks?\s+(?:is\s+|are\s+)?available\b', re.I),
    re.compile(r'\bavailable\s+(?:in\s+)?stock\b', re.I),
    re.compile(r'\bhave\s+stock\b', re.I),
    re.compile(r'\binventory\s+(?:is\s+)?available\b', re.I),
]
SELF_RES = {
    'we': re.compile(r'\bwe\b', re.I),
    'our': re.compile(r'\bour\b', re.I),
    # 只匹配小写 us，避免把表示"美国"的 US 当成自称
    'us': re.compile(r'\bus\b'),
    'i': re.compile(r'\bi\b', re.I),
    'my': re.compile(r'\bmy\b', re.I),
}

# HTML 解析
_RE_SCRIPT_STYLE = re.compile(r'<(script|style)\b.*?</\1>', re.I | re.S)
_RE_TAG = re.compile(r'<[^>]+>')
_RE_BLOCK_END = re.compile(r'<(?:br|/p|/div|/li|/tr|/td|/th|/h[1-6]|/ul|/ol|/table)\s*/?>', re.I)
_RE_H1 = re.compile(r'<h1\b[^>]*>(.*?)</h1>', re.I | re.S)
_RE_H2 = re.compile(r'<h2\b[^>]*>(.*?)</h2>', re.I | re.S)
_RE_H3 = re.compile(r'<h3\b[^>]*>(.*?)</h3>', re.I | re.S)
_RE_P_OPEN = re.compile(r'<p\b[^>]*>', re.I)
_RE_LIST_OPEN = re.compile(r'<(?:ul|ol)\b[^>]*>', re.I)
_RE_TABLE_OPEN = re.compile(r'<table\b[^>]*>', re.I)
_RE_DT = re.compile(r'<dt\b[^>]*>', re.I)
_RE_A = re.compile(r'<a\b([^>]*)>(.*?)</a>', re.I | re.S)
_RE_IMG = re.compile(r'<img\b([^>]*)>', re.I)
_RE_P_BLOCK = re.compile(r'<p\b[^>]*>(.*?)</p>', re.I | re.S)
_RE_TABLE_BLOCK = re.compile(r'<table\b[^>]*>(.*?)</table>', re.I | re.S)
_RE_ROW = re.compile(r'<tr\b[^>]*>(.*?)</tr>', re.I | re.S)
_RE_CELL = re.compile(r'<(td|th)\b[^>]*>(.*?)</\1>', re.I | re.S)
_RE_FAQ_Q = re.compile(r'(?:<strong[^>]*>\s*)?\bQ(?:uestion)?\s*[:.]', re.I)
_RE_ATTR = re.compile(
    r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'>]+))')
_RE_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\u2019\u2013\-]*")
_RE_WS = re.compile(r'\s+')
_RE_NONWORD = re.compile(r"[^a-z0-9\u4e00-\u9fff]+")


# ---------------------------------------------------------------- 基础工具

def _ascii(text, limit=None):
    """终端输出用：非 ASCII 一律降级为 '?'，避免 GBK 控制台崩。"""
    s = str(text or '').encode('ascii', 'replace').decode('ascii')
    if limit and len(s) > limit:
        s = s[:max(0, limit - 1)] + '~'
    return s


def _num(value):
    """分数格式化：整数就输出整数（和契约示例一致），否则保留一位小数。"""
    r = round(float(value), 1)
    if abs(r - round(r)) < 1e-9:
        return int(round(r))
    return r


def load_json(path):
    # utf-8-sig：兼容 PowerShell 写出的带 BOM 的 JSON（无 BOM 时行为一致）
    with open(path, 'r', encoding='utf-8-sig') as fh:
        return json.load(fh)


def get_attr(attr_text, name):
    for m in _RE_ATTR.finditer(attr_text or ''):
        if m.group(1).lower() == name.lower():
            return html_lib.unescape(m.group(2) or m.group(3) or m.group(4) or '')
    return ''


def strip_tags(html_text):
    t = _RE_SCRIPT_STYLE.sub(' ', html_text or '')
    t = _RE_BLOCK_END.sub(' ', t)
    t = _RE_TAG.sub(' ', t)
    return html_lib.unescape(t)


def visible_text(html_text):
    return _RE_WS.sub(' ', strip_tags(html_text)).strip()


def word_count(html_text):
    return len(_RE_WORD.findall(visible_text(html_text)))


def normalize_list(value):
    """keywords / tags 既可能是数组也可能是逗号串，统一成列表。"""
    if value is None:
        return []
    if isinstance(value, str):
        return [p.strip() for p in value.split(',') if p.strip()]
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


def body_of(draft):
    """草稿的文章体（title / content / keywords…）在 draft['draft'] 里；没有就退回草稿本身。"""
    inner = draft.get('draft') if isinstance(draft, dict) else None
    return inner if isinstance(inner, dict) else draft


def pick(draft, name, default=None):
    """取文章体字段：先看嵌套的 draft 对象，再看草稿顶层。"""
    inner = body_of(draft)
    if isinstance(inner, dict) and name in inner:
        return inner[name]
    if isinstance(draft, dict) and name in draft:
        return draft[name]
    return default


def normalize_anchor(text):
    t = unicodedata.normalize('NFKC', text or '').lower()
    t = _RE_NONWORD.sub(' ', t)
    return _RE_WS.sub(' ', t).strip()


def normalize_para(text):
    t = unicodedata.normalize('NFKC', text or '').lower()
    t = _RE_NONWORD.sub(' ', t)
    return _RE_WS.sub(' ', t).strip()


def tokenize(text):
    t = unicodedata.normalize('NFKC', text or '').lower()
    t = _RE_NONWORD.sub(' ', t)
    return [w for w in t.split() if w and w not in STOPWORDS]


def keyword_phrase_set(value):
    out = set()
    for item in normalize_list(value):
        t = _RE_WS.sub(' ', item.strip().lower())
        if t:
            out.add(t)
    return out


def jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / float(len(sa | sb))


def headword_gap(tokens_a, tokens_b):
    """标题 token 的最小位置间隔（>=1 表示首词没在同一位置撞车）。"""
    idx_b = {}
    for j, t in enumerate(tokens_b):
        idx_b.setdefault(t, j)
    best = None
    for i, t in enumerate(tokens_a):
        if t in idx_b:
            gap = abs(i - idx_b[t])
            if best is None or gap < best:
                best = gap
    return best


# ---------------------------------------------------------------- HTML 结构

def h2_sections(content):
    """按 H2 切成 [(标题文字, 小节 HTML)]，不含 H2 之前的引言段。"""
    content = content or ''
    matches = list(_RE_H2.finditer(content))
    if not matches:
        return []
    sections = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sections.append((visible_text(m.group(1)), content[m.end():end]))
    return sections


def para_count(section_html):
    """段落等价数：<p> 计 1，<ul>/<ol> 列表块计 1（纯列表小节不该被判成空小节）。"""
    return len(_RE_P_OPEN.findall(section_html or '')) + len(_RE_LIST_OPEN.findall(section_html or ''))


def extract_links(content):
    out = []
    for m in _RE_A.finditer(content or ''):
        out.append((get_attr(m.group(1), 'href'), visible_text(m.group(2))))
    return out


def extract_images(content):
    out = []
    for m in _RE_IMG.finditer(content or ''):
        out.append((get_attr(m.group(1), 'src'), get_attr(m.group(1), 'alt')))
    return out


def extract_paragraphs(content):
    return [visible_text(m.group(1)) for m in _RE_P_BLOCK.finditer(content or '')]


def count_faq_items(content):
    """FAQ 条数：优先统计 FAQ 小节内的 <h3>/<dt>/"Q:" 问句，取三者最大。"""
    scope = content or ''
    for head, body in h2_sections(content):
        if 'faq' in head.lower():
            scope = body
            break
    n_h3 = len(_RE_H3.findall(scope))
    n_dt = len(_RE_DT.findall(scope))
    n_q = len(_RE_FAQ_Q.findall(scope))
    return max(n_h3, n_dt, n_q)


def site_path(href):
    """href → 站点相对路径（去掉域名/协议、query、fragment、开头斜杠）。"""
    if not href:
        return ''
    h = str(href).strip()
    if not h or h.startswith('#'):
        return ''
    h = re.sub(r'^[a-zA-Z][a-zA-Z0-9+.\-]*://[^/]*', '', h)
    h = h.split('#', 1)[0].split('?', 1)[0]
    h = h.replace('\\', '/')
    h = h.lstrip('/')
    return h


def local_file(site_rel, site_root):
    if not site_rel:
        return ''
    return os.path.normpath(os.path.join(site_root, site_rel.replace('/', os.sep)))


def resolve_article_type(draft, contract):
    """读契约 article_type_field 指向的字段（默认 'draft.article_type'），取不到就用 article_type_default。"""
    field = str(contract.get('article_type_field') or 'draft.article_type')
    value = None
    node = draft
    for part in field.split('.'):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            node = None
            break
    if isinstance(node, str) and node.strip():
        value = node.strip()
    elif isinstance(draft.get('article_type'), str) and draft['article_type'].strip():
        value = draft['article_type'].strip()
    if not value:
        value = str(contract.get('article_type_default') or 'product_guide').strip()
    return value


def link_thresholds(draft, contract):
    """文章类型 → 链接门槛与交叉号行数门槛。

    article_types[type] 里的 min_parts_links / min_oe_links / min_crossref_rows 优先；
    契约里没有该 type 时才回落到 internal_link_targets / crossref_table.min_rows。
    """
    atype = resolve_article_type(draft, contract)
    spec = (contract.get('article_types') or {}).get(atype) or {}
    targets = contract.get('internal_link_targets') or {}
    crossref = contract.get('crossref_table') or {}

    min_parts = int(spec.get('min_parts_links', targets.get('min_parts_links', 0)))
    min_oe = int(spec.get('min_oe_links', targets.get('min_oe_links', 0)))
    if spec.get('requires_linked_oe'):
        min_oe = max(min_oe, 1)
    min_rows = int(spec.get('min_crossref_rows', crossref.get('min_rows', 0)))
    return atype, min_parts, min_oe, min_rows


def analyze_crossref_tables(content, contract):
    """找出正文里的交叉号表格（表头含 'OE Number'），返回表头、数据行与表内 OE 号。"""
    crossref = contract.get('crossref_table') or {}
    required_columns = [str(c) for c in (crossref.get('required_columns') or [])]
    marker = required_columns[0] if required_columns else 'OE Number'
    tables = []
    for m in _RE_TABLE_BLOCK.finditer(content or ''):
        parsed = []
        for row in _RE_ROW.findall(m.group(1)):
            is_header = '<th' in row.lower()
            cells = [visible_text(c) for _tag, c in _RE_CELL.findall(row)]
            parsed.append({'header': is_header, 'cells': cells})
        headers = [' | '.join(r['cells']) for r in parsed if r['header']]
        data_rows = [r for r in parsed if not r['header']]
        tables.append({
            'headers': headers,
            'header_text': ' | '.join(headers),
            'row_count': len(data_rows),
            'cells': [c for r in data_rows for c in r['cells']],
        })
    candidates = [t for t in tables if marker.lower() in t['header_text'].lower()]
    for t in candidates:
        missing_columns = [c for c in required_columns if c.lower() not in t['header_text'].lower()]
        t['missing_columns'] = missing_columns
        t['oe_numbers'] = extract_oe_numbers(' '.join(t['cells']))
    return candidates, required_columns


# ---------------------------------------------------------------- OE 号 / 价格 / 库存

def _hyphen_oe_ok(candidate):
    left, right = candidate.split('-', 1)
    if not any(c.isdigit() for c in candidate):
        return False
    has_letter_right = any(c.isalpha() for c in right)
    if not has_letter_right:
        # 纯数字右侧：排除 "10-20" 这种数量区间
        if left.isdigit() and len(left) < 4:
            return False
        # 排除 "2017-2020" 这种年份区间
        if (left.isdigit() and len(left) == 4 and right.isdigit() and len(right) == 4
                and 1970 <= int(left) <= 2099):
            return False
    else:
        # 右侧是纯字母时，左侧必须也是 OE 形态（至少 4 位或含字母），
        # 否则 "10-PIECE" / "12-MONTH" 这种表格写法会被误当成 OE 号
        if not any(c.isdigit() for c in right) and left.isdigit() and len(left) < 4:
            return False
        if not any(c.isdigit() for c in right) and not any(c.isalpha() for c in left):
            return False
    return True


def _plain_oe_ok(token):
    """无连字符的 OE 号：字母+数字 / 数字+字母 / 字母数字混合（至少两次字母数字切换）。"""
    if len(token) < 5 or len(token) > 16:
        return False
    if not any(c.isdigit() for c in token) or not any(c.isalpha() for c in token):
        return False
    if STANDARD_PREFIX_RE.match(token):
        return False
    suffix = ''.join(c for c in token if c.isalpha())
    if suffix in UNIT_SUFFIXES:
        return False
    if re.match(r'^[A-Z][0-9]{4,10}$', token):
        return True                      # J423501080 / K0136743
    if re.match(r'^[0-9]{4,9}[A-Z]{1,4}[0-9]?$', token):
        return True                      # 204002030AA
    if token[0].isalpha():
        if len(token) < 7:
            return False                 # ZP50A / AB12 这类太短，不可能是 OE 号
        transitions = 0
        for a, b in zip(token, token[1:]):
            if a.isdigit() != b.isdigit():
                transitions += 1
        if transitions >= 2:
            return True                  # T1E3501080 / S113AH3501080BC
    return False


def extract_oe_numbers(text):
    """从正文抽取疑似 OE 号（已归一化为无分隔符大写形式）。"""
    upper = (text or '').upper()
    found = []
    for m in OE_HYPHEN_RE.finditer(upper):
        cand = m.group(0)
        if cand in OE_IGNORE:
            continue
        if not _hyphen_oe_ok(cand):
            continue
        found.append(cand)
    for m in OE_PLAIN_RE.finditer(upper):
        tok = m.group(0)
        if tok in OE_IGNORE:
            continue
        if '-' in tok:
            continue
        if not _plain_oe_ok(tok):
            continue
        found.append(tok)
    out = []
    for cand in found:
        norm = re.sub(r'[^A-Z0-9]', '', cand)
        if norm and norm not in out:
            out.append(norm)
    return sorted(out)


def norm_oe(value):
    return re.sub(r'[^A-Z0-9]', '', str(value or '').upper())


def find_prices(text):
    hits = []
    for rx in PRICE_RES:
        for m in rx.finditer(text or ''):
            frag = _RE_WS.sub(' ', m.group(0)).strip()
            if frag and frag not in hits:
                hits.append(frag)
    return hits


def find_stock_claims(text):
    hits = []
    for rx in STOCK_RES:
        for m in rx.finditer(text or ''):
            frag = m.group(0).strip()
            if frag and frag not in hits:
                hits.append(frag)
    return hits


def count_self_references(text):
    total = 0
    samples = []
    for word, rx in SELF_RES.items():
        for m in rx.finditer(text or ''):
            total += 1
            if len(samples) < 5:
                samples.append(word)
    return total, samples


def factpack_allows_stock(draft):
    fp = draft.get('factpack') or {}
    truthy = (1, True, '1', 'yes', 'true')
    if fp.get('stock') in truthy:
        return True
    for item in fp.get('oe_numbers') or []:
        if isinstance(item, dict) and item.get('stock') in truthy:
            return True
    if re.search(r'stock\s*[=:]\s*1', str(fp.get('notes') or ''), re.I):
        return True
    return False


# ---------------------------------------------------------------- 存量文章语料

class ExistingCorpus(object):
    """已发布文章的标题/关键词/段落语料，用于 uniqueness 比对。"""

    def __init__(self, posts):
        self.entries = []
        self.para_set = set()
        self.para_buckets = {}
        self.para_owner = {}
        for post in posts or []:
            if not isinstance(post, dict):
                continue
            slug = str(post.get('slug') or '')
            content = post.get('content') or ''
            norm_paras = [normalize_para(p) for p in extract_paragraphs(content)]
            norm_paras = [p for p in norm_paras if len(p) >= MIN_PARA_CHARS]
            for para in norm_paras:
                self.para_set.add(para)
                self.para_buckets.setdefault(para[:12], []).append((para, slug))
                self.para_owner.setdefault(para, set()).add(slug)
            self.entries.append({
                'slug': slug,
                'title': str(post.get('title') or ''),
                'tokens': tokenize(post.get('title') or ''),
                'keywords': keyword_phrase_set(post.get('keywords')),
                'paras': norm_paras,
            })

    def closest_title(self, tokens, exclude_slug=None):
        best = (0.0, None)
        for entry in self.entries:
            if exclude_slug and entry['slug'] == exclude_slug:
                continue
            sim = jaccard(tokens, entry['tokens'])
            if sim > best[0]:
                best = (sim, entry)
        return best

    def closest_keywords(self, phrases, exclude_slug=None):
        best = (0.0, None)
        for entry in self.entries:
            if exclude_slug and entry['slug'] == exclude_slug:
                continue
            sim = jaccard(phrases, entry['keywords'])
            if sim > best[0]:
                best = (sim, entry)
        return best

    def paragraph_overlap(self, paragraphs, exclude_slug=None):
        """草稿段落里有多少比例能在存量文章里找到（精确或近似）相同段落。

        exclude_slug：草稿自己已发布的那一篇。重评已发布草稿时，
        它和自己的已发布版本比相似度必然是 1.0，那是自我比较，不是重复内容。
        """
        eligible = [normalize_para(p) for p in paragraphs]
        eligible = [p for p in eligible if len(p) >= MIN_PARA_CHARS]
        if not eligible:
            return 0.0, []
        matched = 0
        examples = []
        for para in eligible:
            owners = self.para_owner.get(para) or set()
            if exclude_slug and owners and exclude_slug in owners and owners <= {exclude_slug}:
                continue
            if para in self.para_set:
                matched += 1
                examples.append(para[:70])
                continue
            best = 0.0
            for cand, cslug in self.para_buckets.get(para[:12], []):
                if exclude_slug and cslug == exclude_slug:
                    continue
                if abs(len(cand) - len(para)) > max(40, int(len(para) * 0.35)):
                    continue
                ratio = difflib.SequenceMatcher(None, para, cand).ratio()
                if ratio > best:
                    best = ratio
            if best >= FUZZY_PARA_RATIO:
                matched += 1
                examples.append(para[:70])
        denom = len(eligible)
        if exclude_slug:
            owned = sum(1 for p in eligible
                        if (self.para_owner.get(p) or set()) <= {exclude_slug})
            denom -= owned
        if denom <= 0:
            return 0.0, []
        return matched / float(denom), examples


# ---------------------------------------------------------------- 规则模型

def rule(name, weight, ok, detail='', fatal=False, level='fail'):
    return {'rule': name, 'weight': float(weight), 'ok': bool(ok),
            'detail': detail, 'fatal': bool(fatal), 'level': level}


def apply_rules(rules, max_score):
    """维度得分 = 满分 × (通过规则权重占比)；命中致命违规则该维度直接 0 分。"""
    total_w = sum(r['weight'] for r in rules)
    got_w = sum(r['weight'] for r in rules if r['ok'])
    score = (max_score * got_w / total_w) if total_w else 0.0
    issues = []
    fatal_hit = False
    for r in rules:
        if r['ok']:
            continue
        issues.append({'level': r['level'], 'rule': r['rule'],
                       'detail': r['detail'], 'fatal': r['fatal']})
        if r['fatal']:
            fatal_hit = True
    if fatal_hit:
        score = 0.0
    return score, issues, fatal_hit


# ---------------------------------------------------------------- 六个维度

def is_question_heading(head, markers):
    """H2 是否写成买家问句：句尾问号，或以疑问词开头。"""
    h = (head or '').strip().lower()
    if not h:
        return False
    if h.endswith('?'):
        return True
    first = re.split(r'[\s:—\-]+', h, 1)[0].strip()
    return first in markers


def score_structure(draft, contract):
    st = contract.get('structure') or {}
    content = pick(draft, 'content') or ''
    rules = []

    min_words = int(st.get('min_words', 0))
    max_words = int(st.get('max_words', 10 ** 9))
    wc = word_count(content)
    rules.append(rule('word_count', 8, min_words <= wc <= max_words,
                      'body has %d words, required %d-%d' % (wc, min_words, max_words)))

    min_h2 = int(st.get('min_h2', 0))
    max_h2 = int(st.get('max_h2', 10 ** 9))
    sections = h2_sections(content)
    rules.append(rule('h2_count', 5, min_h2 <= len(sections) <= max_h2,
                      'found %d H2 sections, required %d-%d' % (len(sections), min_h2, max_h2)))

    # H2 写成买家问句（兄弟站点 kingmay 最值得学的一条）
    if st.get('h2_style') == 'buyer_question':
        markers = [m.lower() for m in (st.get('h2_question_markers') or [])]
        min_ratio = float(st.get('min_h2_question_ratio', 0) or 0)
        if markers and sections:
            heads = [h for h, _b in sections]
            qs = [h for h in heads if is_question_heading(h, markers)]
            ratio = len(qs) / float(len(heads))
            flat = [h[:48] for h in heads if h not in qs]
            detail = ('%d/%d H2 are buyer questions (%.0f%%, required >= %.0f%%); '
                      'non-question headings: %s'
                      % (len(qs), len(heads), ratio * 100, min_ratio * 100,
                         '; '.join(flat[:6]) or 'none'))
            rules.append(rule('h2_buyer_question', 6, ratio >= min_ratio, detail))

    min_p = int(st.get('min_paragraphs_per_h2', 1))
    thin = ['%s (%d)' % (head[:45] or '(untitled section)', para_count(body))
            for head, body in sections if para_count(body) < min_p]
    if thin:
        detail = 'sections under the %d-paragraph minimum: %s' % (min_p, '; '.join(thin[:8]))
    else:
        detail = 'all %d sections carry at least %d paragraph(s)' % (len(sections), min_p)
    rules.append(rule('paragraphs_per_h2', 4, not thin, detail))

    min_tables = int(st.get('min_tables', 0))
    n_tables = len(_RE_TABLE_OPEN.findall(content))
    rules.append(rule('min_tables', 3, n_tables >= min_tables,
                      'found %d <table>, required >= %d' % (n_tables, min_tables)))

    min_faq = int(st.get('min_faq', contract.get('faq_min', 0)))
    n_faq = count_faq_items(content)
    rules.append(rule('min_faq', 3, n_faq >= min_faq,
                      'found %d FAQ entries, required >= %d' % (n_faq, min_faq)))

    if st.get('require_quick_answer'):
        # Quick Answer 框是**出页模板**用 description 自动生成的（render_post 里
        # <div class="qa-box">），正文里再写一份会出现两个框。
        # → 判定口径改为「有可用的 description」，正文自带 qa-box 也算通过。
        low = content.lower()
        has_qa = ('<div class="qa-box"' in low) or ('<strong>quick answer' in low)
        has_desc = bool(str(pick(draft, 'description') or '').strip())
        ok = has_qa or has_desc
        rules.append(rule('require_quick_answer', 3, ok,
                          'quick answer source: %s' % ('body qa-box' if has_qa else
                                                       ('description (template renders qa-box)' if has_desc
                                                        else 'missing'))))

    if st.get('require_h1_unique'):
        n_h1 = len(_RE_H1.findall(content))
        rules.append(rule('h1_unique', 2, n_h1 <= 1,
                          'body has %d <h1>, at most 1 allowed' % n_h1))

    if st.get('forbid_empty_h2'):
        empty = []
        for head, body in sections:
            if not head.strip():
                empty.append('(empty heading text)')
            elif para_count(body) == 0 and not _RE_TABLE_OPEN.search(body):
                empty.append('%s (no content)' % head[:45])
        rules.append(rule('forbid_empty_h2', 2, not empty,
                          'no empty H2 section' if not empty
                          else 'empty H2 section(s): %s' % '; '.join(empty[:8])))

    return rules


def score_facts(draft, contract):
    facts = contract.get('facts') or {}
    content = pick(draft, 'content') or ''
    text = visible_text(content)
    rules = []

    fact_oes = set()
    for item in (draft.get('factpack') or {}).get('oe_numbers') or []:
        if isinstance(item, dict):
            norm = norm_oe(item.get('oe'))
            if norm:
                fact_oes.add(norm)

    if facts.get('require_oe_number_in_factpack', True):
        body_oes = extract_oe_numbers(text)
        missing = [oe for oe in body_oes if oe not in fact_oes]
        if missing:
            detail = 'OE number(s) in the body are not backed by factpack.oe_numbers: %s' % ', '.join(missing[:10])
        else:
            detail = 'all %d OE number(s) in the body are backed by the factpack' % len(body_oes)
        rules.append(rule('oe_numbers_in_factpack', 7, not missing, detail, fatal=True))

    # 交叉号表格：正文必须有一个带 'OE Number' 表头的表，行数按文章类型门槛，
    # 表内 OE 号必须全部来自 factpack.oe_numbers（归 facts 维度，不另开维度）。
    _atype, _min_parts, _min_oe, min_rows = link_thresholds(draft, contract)
    tables, required_columns = analyze_crossref_tables(content, contract)
    cross_ok = _crossref_ok(tables, min_rows, required_columns)
    if not tables:
        cross_detail = ('no cross-reference table found (need a <table> whose header contains "%s")'
                        % (required_columns[0] if required_columns else 'OE Number'))
    else:
        best = max(tables, key=lambda t: t['row_count'])
        problems = []
        if best['missing_columns']:
            problems.append('missing required column(s): %s' % ', '.join(best['missing_columns']))
        if best['row_count'] < min_rows:
            problems.append('only %d data row(s), required >= %d for article type "%s"'
                            % (best['row_count'], min_rows, _atype))
        cross_detail = ('cross-reference table with %d data row(s) and the required columns'
                        % best['row_count']) if not problems else \
                       ('cross-reference table problem: %s' % '; '.join(problems))
    rules.append(rule('crossref_table_present', 3, cross_ok, cross_detail))

    table_oes = []
    for t in tables:
        table_oes.extend(t['oe_numbers'])
    missing_table_oes = sorted(set(oe for oe in table_oes if oe not in fact_oes))
    if not tables:
        table_detail = 'no cross-reference table to check'
    elif missing_table_oes:
        table_detail = 'cross-reference table contains OE number(s) absent from the factpack: %s' % ', '.join(
            missing_table_oes[:10])
    else:
        table_detail = 'all %d OE number(s) in the cross-reference table are backed by the factpack' % len(
            set(table_oes))
    rules.append(rule('crossref_table_oe_numbers', 1, not missing_table_oes, table_detail, fatal=True))

    if facts.get('forbid_fabricated_price'):
        hits = find_prices(text)
        rules.append(rule('no_fabricated_price', 6, not hits,
                          'no numeric unit price in the body' if not hits
                          else 'numeric unit price found: %s' % ', '.join(hits[:6]), fatal=True))

    if facts.get('forbid_fabricated_stock_claim'):
        allowed = factpack_allows_stock(draft)
        hits = find_stock_claims(text)
        ok = allowed or not hits
        if allowed:
            detail = 'stock claim allowed: the factpack states stock=1'
        elif hits:
            detail = 'stock claim not supported by the factpack: %s' % ', '.join(hits[:6])
        else:
            detail = 'no stock claim in the body'
        rules.append(rule('no_fabricated_stock_claim', 2, ok, detail, fatal=True))

    phrases = contract.get('banned_phrases') or []
    low = text.lower()
    hit_phrases = [p for p in phrases if p and str(p).lower() in low]
    rules.append(rule('no_banned_phrases', 3, not hit_phrases,
                      'no banned phrase in the body' if not hit_phrases
                      else 'banned phrase(s): %s' % ', '.join(str(p) for p in hit_phrases[:6])))

    patterns = contract.get('banned_patterns') or []
    hit_patterns = []
    for pat in patterns:
        try:
            rx = re.compile(pat, re.I)
        except re.error:
            continue
        m = rx.search(text)
        if m:
            hit_patterns.append('%s -> "%s"' % (pat, _RE_WS.sub(' ', m.group(0))[:40]))
    rules.append(rule('no_banned_patterns', 2, not hit_patterns,
                      'no banned pattern in the body' if not hit_patterns
                      else 'banned pattern hit: %s' % '; '.join(hit_patterns[:5])))

    self_words = contract.get('banned_self_reference') or []
    if self_words:
        count, samples = count_self_references(text)
        rules.append(rule('no_self_reference', 1, count == 0,
                          'no first-person reference in the body' if not count
                          else 'first-person reference(s) found: %s' % ', '.join(sorted(set(samples))),
                          level='warn'))

    return rules


def _crossref_ok(tables, min_rows, required_columns):
    """交叉号表格是否达标：至少一张表，表头列齐全，数据行数够门槛。"""
    if not tables:
        return False
    for t in tables:
        if t['missing_columns']:
            continue
        if t['row_count'] < min_rows:
            continue
        return True
    return False


def score_links(draft, contract):
    anchor_rules = contract.get('anchor_rules') or {}
    st = contract.get('structure') or {}
    content = pick(draft, 'content') or ''
    links = extract_links(content)
    atype, min_parts, min_oe, _min_rows = link_thresholds(draft, contract)
    rules = []

    min_links = int(st.get('min_body_links', 0))
    max_links = int(st.get('max_body_links', 10 ** 9))
    rules.append(rule('body_link_count', 2, min_links <= len(links) <= max_links,
                      'body has %d <a href>, required %d-%d' % (len(links), min_links, max_links)))

    min_len = int(anchor_rules.get('min_len', 0))
    short = sorted(set(t for _h, t in links if len(t.strip()) < min_len))
    rules.append(rule('anchor_min_len', 2, not short,
                      'every anchor text is at least %d characters' % min_len if not short
                      else 'anchor text shorter than %d characters: %s' % (min_len, ', '.join(short[:8]))))

    max_occ = int(anchor_rules.get('max_occurrences_per_term', 10 ** 6))
    counts = Counter(normalize_anchor(t) for _h, t in links if t.strip())
    over = sorted(k for k, v in counts.items() if v > max_occ)
    rules.append(rule('anchor_max_occurrences', 1, not over,
                      'no anchor text repeats more than %d times' % max_occ if not over
                      else 'anchor text used more than %d times: %s' % (max_occ, ', '.join(over[:6]))))

    generic = [normalize_anchor(g) for g in (anchor_rules.get('forbid_generic_anchors') or [])]
    generic = [g for g in generic if g]
    bad_generic = sorted(set(t for _h, t in links if normalize_anchor(t) in generic))
    rules.append(rule('anchor_not_generic', 2, not bad_generic,
                      'no generic anchor text' if not bad_generic
                      else 'generic anchor text: %s' % ', '.join(bad_generic[:8])))

    if anchor_rules.get('forbid_truncated_terms'):
        terms = build_anchor_terms(draft)
        anchor_norms = [normalize_anchor(t) for _h, t in links if t.strip()]
        truncated = []
        for norm in anchor_norms:
            if norm in terms:
                # 锚文本本身就是一条完整词（keyword / tag / 品类名）→ 不是被截断的词
                continue
            for term in sorted(terms):
                if term != norm and term.startswith(norm):
                    truncated.append('%s -> "%s"' % (norm, term))
                    break
            else:
                for other in anchor_norms:
                    if other != norm and other.startswith(norm):
                        truncated.append('%s -> "%s"' % (norm, other))
                        break
        rules.append(rule('anchor_not_truncated', 2, not truncated,
                          'no truncated anchor text' if not truncated
                          else 'truncated anchor text: %s' % '; '.join(sorted(set(truncated))[:8])))

    parts_links = [h for h, _t in links if site_path(h).lower().startswith('parts/')]
    if min_parts > 0:
        rules.append(rule('min_parts_links', 2, len(parts_links) >= min_parts,
                          'found %d /parts/ link(s), required >= %d for article type "%s"'
                          % (len(parts_links), min_parts, atype)))

    oe_links = [h for h, _t in links if site_path(h).lower().startswith('oe/')]
    if min_oe > 0:
        rules.append(rule('min_oe_links', 1, len(oe_links) >= min_oe,
                          'found %d /oe/ link(s), required >= %d for article type "%s"'
                          % (len(oe_links), min_oe, atype)))
    # min_oe == 0（product_guide）：交叉号只进表格、不链 /oe/ 页，按 0 门槛判定，不扣分

    missing = []
    for href, _text in links:
        rel = site_path(href)
        low = rel.lower()
        if low.startswith('parts/') or low.startswith('oe/') or low.startswith('blog/'):
            if not os.path.isfile(local_file(rel, SITE_ROOT[0])):
                missing.append('/' + rel)
    rules.append(rule('link_target_exists', 2, not missing,
                      'every /parts/, /oe/ and /blog/ link resolves to a local file' if not missing
                      else 'link target(s) not found on disk: %s' % ', '.join(sorted(set(missing))[:8])))

    external = []
    for href, _text in links:
        h = str(href or '').strip()
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.\-]*://', h):
            continue
        host = re.sub(r'^[a-zA-Z][a-zA-Z0-9+.\-]*://', '', h).split('/')[0].lower()
        if host.startswith('www.'):
            host = host[4:]
        if host and not host.endswith(SITE_DOMAIN):
            external.append(h)
    rules.append(rule('no_external_links', 1, not external,
                      'no off-site link in the body' if not external
                      else 'off-site link(s) found (competitor hotlink risk): %s' % ', '.join(
                          sorted(set(external))[:8]), level='warn'))

    return rules


def build_anchor_terms(draft):
    """用于判断"锚文本是不是被截断的词"的长词表。"""
    terms = set()
    for value in (pick(draft, 'keywords'), pick(draft, 'tags')):
        for item in normalize_list(value):
            terms.add(normalize_anchor(item))
    fp = draft.get('factpack') or {}
    for page in fp.get('product_pages') or []:
        if isinstance(page, dict):
            terms.add(normalize_anchor(page.get('name') or ''))
    for item in fp.get('oe_numbers') or []:
        if isinstance(item, dict):
            terms.add(normalize_anchor(item.get('part_name') or ''))
    terms.discard('')
    return terms


def score_images(draft, contract):
    image_rules = contract.get('image_rules') or {}
    st = contract.get('structure') or {}
    content = pick(draft, 'content') or ''
    images = extract_images(content)
    rules = []

    min_images = int(st.get('min_body_images', 0))
    rules.append(rule('min_body_images', 3, len(images) >= min_images,
                      'body has %d <img>, required >= %d' % (len(images), min_images)))

    min_alt = int(st.get('min_image_alt_len', 0))
    bad_alt = ['%s (alt="%s")' % (src or '(no src)', alt) for src, alt in images
               if not alt.strip() or len(alt.strip()) < min_alt]
    rules.append(rule('image_alt_quality', 2, not bad_alt,
                      'every image has an alt of at least %d characters' % min_alt if not bad_alt
                      else 'image alt too short or empty: %s' % '; '.join(bad_alt[:8])))

    hints = build_alt_hints(draft)
    if hints:
        # alt 里出现「零件名整串」或「零件名里 ≥5 字符的实词」都算通过
        # （模型写的 alt 通常是改写过的，"Front Wheel Hub Bearing – Hyundai Elantra"
        #  写成 "Elantra Cerato i30 front hub bearing" 是合规的，不该判负）
        hint_tokens = set()
        for h in hints:
            for t in re.split(r'[^A-Za-z0-9]+', h or ''):
                tl = t.lower()
                if len(tl) >= 5 and tl not in ('parts', 'part', 'wheel', 'front', 'rear'):
                    hint_tokens.add(tl)

        def alt_ok(alt):
            al = (alt or '').lower()
            if any(h.lower() in al for h in hints):
                return True
            return any(t in al for t in hint_tokens)

        bad_hint = ['%s (alt="%s")' % (src or '(no src)', alt) for src, alt in images
                    if not alt_ok(alt)]
        rules.append(rule('image_alt_mentions_part', 1, not bad_hint,
                          'every image alt names a factpack part or OE number' if not bad_hint
                          else 'image alt without a factpack part name / OE number: %s' % '; '.join(bad_hint[:8])))
    else:
        rules.append(rule('image_alt_mentions_part', 1, True,
                          'no part name / OE number in the factpack, alt content not checked',
                          level='warn'))

    missing = []
    for src, _alt in images:
        rel = site_path(src)
        if not rel:
            missing.append(src or '(empty src)')
        elif not os.path.isfile(local_file(rel, SITE_ROOT[0])):
            missing.append('/' + rel)
    rules.append(rule('image_src_exists', 2, not missing,
                      'every image src resolves to a local file' if not missing
                      else 'image file(s) not found on disk: %s' % ', '.join(sorted(set(missing))[:8])))

    roots = [r.lower().rstrip('/') + '/' for r in (image_rules.get('own_roots') or [])]
    if roots:
        outside = sorted(set(src for src, _alt in images
                             if not any(site_path(src).lower().startswith(r) for r in roots)))
        rules.append(rule('image_src_own_root', 2, not outside,
                          'every image src is under %s' % ', '.join(roots) if not outside
                          else 'image src outside the own roots (hotlink risk): %s' % ', '.join(outside[:8])))
    else:
        rules.append(rule('image_src_own_root', 2, True, 'no own_roots configured', level='warn'))

    return rules


def build_alt_hints(draft):
    hints = set()
    fp = draft.get('factpack') or {}
    for item in fp.get('oe_numbers') or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get('part_name') or '').strip()
        if len(name) >= 4:
            hints.add(name)
        oe = str(item.get('oe') or '').strip()
        if oe:
            hints.add(oe)
    for page in fp.get('product_pages') or []:
        if isinstance(page, dict):
            name = str(page.get('name') or '').strip()
            if len(name) >= 4:
                hints.add(name)
    return hints


def score_metadata(draft, contract):
    md = contract.get('metadata') or {}
    categories = contract.get('categories') or []
    aliases = contract.get('category_aliases') or {}
    rules = []

    title = str(pick(draft, 'title') or '')
    t_min, t_max = int(md.get('title_min', 0)), int(md.get('title_max', 10 ** 9))
    rules.append(rule('title_length', 2, t_min <= len(title) <= t_max,
                      'title is %d characters, required %d-%d' % (len(title), t_min, t_max)))

    desc = str(pick(draft, 'description') or '')
    d_min, d_max = int(md.get('description_min', 0)), int(md.get('description_max', 10 ** 9))
    rules.append(rule('description_length', 1, d_min <= len(desc) <= d_max,
                      'description is %d characters, required %d-%d' % (len(desc), d_min, d_max)))

    keywords = normalize_list(pick(draft, 'keywords'))
    k_min, k_max = int(md.get('keywords_min', 0)), int(md.get('keywords_max', 10 ** 9))
    rules.append(rule('keywords_count', 1, k_min <= len(keywords) <= k_max,
                      '%d keyword(s), required %d-%d' % (len(keywords), k_min, k_max)))

    tags = normalize_list(pick(draft, 'tags'))
    t_min2, t_max2 = int(md.get('tags_min', 0)), int(md.get('tags_max', 10 ** 9))
    rules.append(rule('tags_count', 1, t_min2 <= len(tags) <= t_max2,
                      '%d tag(s), required %d-%d' % (len(tags), t_min2, t_max2)))

    raw_cat = str(pick(draft, 'category') or '').strip()
    resolved = aliases.get(raw_cat, raw_cat)
    ok_cat = resolved in categories
    if ok_cat and resolved != raw_cat:
        detail = 'category "%s" mapped through category_aliases to "%s"' % (raw_cat, resolved)
    elif ok_cat:
        detail = 'category "%s" is on the whitelist' % resolved
    else:
        detail = 'category "%s" is not on the whitelist %s' % (raw_cat, categories)
    rules.append(rule('category_allowed', 2, ok_cat, detail))

    date_value = str(pick(draft, 'date') or '').strip()
    fmt = str(md.get('date_format', 'YYYY-MM-DD'))
    ok_date = False
    if fmt.upper() == 'YYYY-MM-DD':
        m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', date_value)
        if m:
            try:
                import datetime
                datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                ok_date = True
            except ValueError:
                ok_date = False
    else:
        ok_date = bool(date_value)
    rules.append(rule('date_format', 1, ok_date,
                      'date "%s" matches %s' % (date_value, fmt) if ok_date
                      else 'date "%s" does not match %s' % (date_value, fmt)))

    rt = pick(draft, 'readtime')
    rt_value = None
    if isinstance(rt, bool):
        rt_value = None
    elif isinstance(rt, int):
        rt_value = rt
    elif isinstance(rt, float) and float(rt).is_integer():
        rt_value = int(rt)
    elif isinstance(rt, str):
        m = re.match(r'^\s*(\d+)', rt)
        if m:
            rt_value = int(m.group(1))
    r_min, r_max = int(md.get('readtime_min', 0)), int(md.get('readtime_max', 10 ** 9))
    ok_rt = rt_value is not None and r_min <= rt_value <= r_max
    rules.append(rule('readtime_range', 1, ok_rt,
                      'readtime %s, required %d-%d' % (rt_value, r_min, r_max)))

    image = str(pick(draft, 'image') or '').strip()
    rules.append(rule('image_present', 0.5, bool(image),
                      'image "%s" is set' % image if image else 'image field is empty'))

    slug = str(pick(draft, 'slug') or '').strip()
    ok_slug = bool(slug) and re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug) is not None
    rules.append(rule('slug_valid', 0.5, ok_slug,
                      'slug "%s" is a-z0-9 with dashes only' % slug if ok_slug
                      else 'slug "%s" is empty or contains illegal characters' % slug))

    return rules


def draft_slug(draft):
    """草稿自己的 slug（规则与 27-blog-publish.py 保持一致）。"""
    dr = draft.get('draft') if isinstance(draft.get('draft'), dict) else draft
    raw = dr.get('slug') or ''
    if not raw:
        raw = re.sub(r"[^a-zA-Z0-9]+", "-", str(dr.get('title') or '')).strip('-').lower()
    return raw[:78].rstrip('-')


def score_uniqueness(draft, contract, corpus):
    uq = contract.get('uniqueness') or {}
    rules = []

    # 草稿若已发布，它会出现在存量语料里；拿它跟自己比必然 1.0，那是自比不是重复。
    # 只按 slug 精确排除自己，不放宽「标题撞题」的判定。
    self_slug = draft_slug(draft)

    title_tokens = tokenize(pick(draft, 'title') or '')
    max_title = float(uq.get('max_title_jaccard', 1.0))
    sim_title, closest = corpus.closest_title(title_tokens, exclude_slug=self_slug)
    ok_title = sim_title <= max_title
    rules.append(rule('title_jaccard', 3, ok_title,
                      'closest published title "%s" similarity %.3f, max allowed %.2f'
                      % (closest['slug'] if closest else '-', sim_title, max_title), fatal=True))

    phrases = keyword_phrase_set(pick(draft, 'keywords'))
    max_kw = float(uq.get('max_keyword_jaccard', 1.0))
    sim_kw, closest_kw = corpus.closest_keywords(phrases, exclude_slug=self_slug)
    ok_kw = sim_kw <= max_kw
    rules.append(rule('keyword_jaccard', 2, ok_kw,
                      'closest published keyword set "%s" similarity %.3f, max allowed %.2f'
                      % (closest_kw['slug'] if closest_kw else '-', sim_kw, max_kw), fatal=True))

    max_par = float(uq.get('max_paragraph_overlap', 1.0))
    overlap, examples = corpus.paragraph_overlap(extract_paragraphs(pick(draft, 'content') or ''),
                                                 exclude_slug=self_slug)
    ok_par = overlap <= max_par
    rules.append(rule('paragraph_overlap', 3, ok_par,
                      'paragraph overlap with published posts %.3f, max allowed %.2f'
                      % (overlap, max_par), fatal=True))

    min_gap = int(uq.get('min_shared_title_headword_gap', 0))
    if min_gap > 0 and closest:
        gap = headword_gap(title_tokens, closest['tokens'])
        if gap is None:
            ok_gap = True
            detail = 'no shared headword with the closest published title'
        else:
            ok_gap = gap >= min_gap
            detail = ('closest published title shares a headword at gap %d, required >= %d'
                      % (gap, min_gap))
        rules.append(rule('title_headword_gap', 2, ok_gap, detail, level='warn'))

    return rules


# ---------------------------------------------------------------- 单篇评分

SITE_ROOT = [DEFAULT_SITE_ROOT]


def evaluate_draft(draft, contract, corpus):
    scoring = contract.get('scoring') or {}
    weights = scoring.get('weights') or {}
    hard_fail_dims = [str(d) for d in (scoring.get('hard_fail_zero_out') or [])]

    builders = {
        'structure': lambda: score_structure(draft, contract),
        'facts': lambda: score_facts(draft, contract),
        'links': lambda: score_links(draft, contract),
        'images': lambda: score_images(draft, contract),
        'metadata': lambda: score_metadata(draft, contract),
        'uniqueness': lambda: score_uniqueness(draft, contract, corpus),
    }

    components = {}
    all_issues = []
    total = 0.0
    hard_fail = []
    for dim in DIMENSIONS:
        max_score = float(weights.get(dim, 0))
        if max_score <= 0:
            continue
        rules = builders[dim]()
        score, issues, fatal_hit = apply_rules(rules, max_score)
        if fatal_hit and dim not in hard_fail_dims:
            # 契约没把该维度列入 hard_fail_zero_out → 不清零，只记致命问题
            score = (max_score * sum(r['weight'] for r in rules if r['ok'])
                     / max(1e-9, sum(r['weight'] for r in rules)))
            for iss in issues:
                iss['fatal'] = False
        components[dim] = {'score': _num(score), 'max': _num(max_score), 'issues': issues}
        total += score
        if fatal_hit and dim in hard_fail_dims:
            hard_fail.append(dim)
        for iss in issues:
            item = {'level': iss['level'], 'rule': iss['rule'],
                    'detail': iss['detail'], 'dimension': dim}
            if iss.get('fatal'):
                item['fatal'] = True
            all_issues.append(item)

    publish_threshold = float(scoring.get('publish_threshold', 85))
    draft_threshold = float(scoring.get('draft_threshold', 70))
    publish = (not hard_fail) and total >= publish_threshold
    if publish:
        verdict = 'publish'
    elif hard_fail or total < draft_threshold:
        verdict = 'reject'
    else:
        verdict = 'revise'

    return {
        'score': _num(total),
        'publish': bool(publish),
        'verdict': verdict,
        'hard_fail': hard_fail,
        'components': components,
        'issues': all_issues,
    }


# ---------------------------------------------------------------- 主流程

def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Score OE blog drafts against the blog contract (100 point gate).')
    parser.add_argument('--contract', default=DEFAULT_CONTRACT, help='path to blog-contract.json')
    parser.add_argument('--drafts', default=DEFAULT_DRAFTS, help='path to blog-drafts.json')
    parser.add_argument('--posts', default=DEFAULT_POSTS,
                        help='path to blog-posts.json')
    parser.add_argument('--site-root', default=DEFAULT_SITE_ROOT, help='site root for link/image checks')
    parser.add_argument('--verbose', action='store_true', help='print every issue detail')
    args = parser.parse_args(argv)

    SITE_ROOT[0] = args.site_root

    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    try:
        contract = load_json(args.contract)
    except Exception as exc:
        print('ERROR: cannot read contract file %s (%s)' % (_ascii(args.contract), exc))
        return 1
    try:
        drafts = load_json(args.drafts)
    except Exception as exc:
        print('ERROR: cannot read drafts file %s (%s)' % (_ascii(args.drafts), exc))
        return 1
    try:
        posts = load_json(args.posts)
    except Exception as exc:
        print('ERROR: cannot read posts file %s (%s)' % (_ascii(args.posts), exc))
        return 1

    if not isinstance(drafts, list):
        print('ERROR: drafts file %s must contain a JSON array' % _ascii(args.drafts))
        return 1
    if not isinstance(posts, list):
        print('ERROR: posts file %s must contain a JSON array' % _ascii(args.posts))
        return 1
    if not isinstance(contract, dict):
        print('ERROR: contract file %s must contain a JSON object' % _ascii(args.contract))
        return 1

    corpus = ExistingCorpus(posts)

    for draft in drafts:
        if not isinstance(draft, dict):
            continue
        draft['gate'] = evaluate_draft(draft, contract, corpus)

    with open(args.drafts, 'w', encoding='utf-8') as fh:
        json.dump(drafts, fh, ensure_ascii=False, indent=1)

    print('%-34s %-6s %-7s %-6s %s' % ('ID', 'SCORE', 'PUBLISH', 'FAILS', 'TITLE'))
    print('-' * 116)
    counts = {'publish': 0, 'revise': 0, 'reject': 0}
    for draft in drafts:
        if not isinstance(draft, dict):
            continue
        gate = draft.get('gate') or {}
        title = _ascii(pick(draft, 'title') or '', 40)
        fails = len([i for i in (gate.get('issues') or []) if i.get('level') == 'fail'])
        verdict = gate.get('verdict') or 'reject'
        counts[verdict] = counts.get(verdict, 0) + 1
        print('%-34s %-6s %-7s %-6d %s' % (
            _ascii(draft.get('id') or '', 34), _num(gate.get('score') or 0),
            'yes' if gate.get('publish') else 'no', fails, title))
        if args.verbose:
            for issue in (gate.get('issues') or []):
                print('      [%s] %s / %s: %s' % (
                    issue.get('level'), issue.get('dimension'), issue.get('rule'),
                    _ascii(issue.get('detail'))))
    print('-' * 116)
    print('Scored %d draft(s): publish=%d revise=%d reject=%d' % (
        len(drafts), counts.get('publish', 0), counts.get('revise', 0), counts.get('reject', 0)))
    print('Gate written to %s' % _ascii(args.drafts))
    return 0


if __name__ == '__main__':
    sys.exit(main())
