# -*- coding: utf-8 -*-
"""
oe_seo_tdk —— OE 详情页 TDK 与正文的买家形态改写（模块）

背景（2026-11-04 GSC 实测）：
  · OE 详情页是全站最大曝光来源：28 天 6,834 曝光（占 48%），平均排名 8.0，
    但只有 36 次点击 → CTR 0.53%，是全站最差的转化点。
  · 线上页面的 title 是几代模板拼出来的，最差的一代会把零件名重复写两遍：
      "OE 54661-C2800 Shock Absorber 54661-C2800 | Hyundai / Kia"
    —— 因为供应商原始 part_name 里就嵌着自己的 OE 号，还带 "For {品牌} {车型}" 尾巴。
  · meta description 在 160 字符处硬截断，停在 "...MOQ and export terms from"，
    句子残缺；twitter:title 还多一个孤立的 "|"。
  · 买家真实查询全是裸零件号（ai54661 / ai26870 / 18841-11051 …），
    页面已经能排到 pos 1~8，说明"找得到"，只差"点得进"。

本模块提供：
  clean_part_name()  清洗供应商原始零件名（去 OE 号 / 品牌车型尾巴 / 营销词）
  build_title()       买家形态 title（OE 号 + 干净零件名 + 品牌车型 + 批发意图）
  build_desc()        完整不截断的 description（适配 + 交叉号 + MOQ + FOB + 交期）
  build_keywords()    关键词 meta
  apply_to_page()     对单页做幂等改写

被 15-oe-seo-tdk.py（批量 CLI）与 generate_oe_pages.py（出页模板）共用，
保证「存量页」和「11-06 起的新页」样式一致，不会被下一轮出页覆盖回旧版。
"""
import os
import re

# ── 品牌词表（用于剥离零件名尾部的 "For {BRAND} {MODELS}"） ──
BRAND_WORDS = [
    'HYUNDAI-KIA', 'MERCEDES-BENZ', 'GREAT WALL', 'SSANGYONG', 'VOLKSWAGEN',
    'HYUNDAI', 'KIA', 'NISSAN', 'TOYOTA', 'MERCEDES', 'BMW', 'AUDI', 'SUBARU',
    'PORSCHE', 'HONDA', 'MAZDA', 'VW', 'FORD', 'CHEVROLET', 'CHERY', 'GEELY',
    'BYD', 'JAC', 'GWM', 'FOTON', 'DONGFENG', 'LIFAN', 'SUZUKI', 'MITSUBISHI',
    'ISUZU', 'PROTON', 'BAIC', 'JINPENG', 'AVATR', 'LYNK', 'ZEKR', 'ROX',
    'ADAMAS', 'CHANA', 'GONOW', 'KINGSTEEL', 'CHANGAN', 'HAVAL', 'TIGGO',
]
_BRAND_ALT = '|'.join(re.escape(b) for b in sorted(BRAND_WORDS, key=len, reverse=True))

# 渠道/供应商噪音词（不是零件本体描述）
_CHANNEL_WORDS = (r'(?:Auto Performance Parts|Auto Spare|Automobile Parts|Suspension Parts|'
                  r'Auto Parts|Car Parts|Spare Parts)')

# 营销/广告词（供应商标题噪音，会稀释标题并让页面对比更差）
_ADS_WORDS = (r'(?:High Performance|Top Quality|High Quality|Best Price|Cheap Price|'
              r'Hot Sale|Factory Sales|New Brand|OEM Quality|Good Quality|'
              r'Auto Performance|Auto Spare|Automobile Parts|Spare Parts|'
              r'High[- ]Grade|Premium Quality)')

# 常见拼写错误
_TYPO_FIX = [
    (r'\bAseembly\b', 'Assembly'), (r'\bAsembly\b', 'Assembly'),
    (r'\bAseembley\b', 'Assembly'), (r'\bAccecory\b', 'Accessory'),
    (r'\bShok Absorber\b', 'Shock Absorber'),
]

# ── 品牌显示名归一 ──
_BRAND_DISPLAY = {
    'HYUNDAI-KIA': 'Hyundai / Kia', 'MERCEDES-BENZ': 'Mercedes-Benz',
    'GREAT WALL': 'Great Wall', 'SSANGYONG': 'SsangYong', 'VOLKSWAGEN': 'Volkswagen',
}


def _brand_display(b):
    b = (b or '').strip()
    if not b:
        return ''
    up = b.upper()
    if up in _BRAND_DISPLAY:
        return _BRAND_DISPLAY[up]
    return b.title() if b.isupper() else b


def _oe_pattern(oe):
    """把 OE 号编成"允许任意分隔符"的正则，用来从零件名里把自身编号抠掉。

    "038117021B" → 038[\\s\\-\\.]*117[\\s\\-\\.]*021[\\s\\-\\.]*B
    """
    groups = re.findall(r'[A-Z]+|\d+', (oe or '').upper())
    if not groups:
        return None
    return r'\b' + r'[\s\-\.]*'.join(re.escape(g) for g in groups) + r'\b'


def clean_part_name(raw, oe=''):
    """把供应商原始 part_name 清洗成"买家看得懂的零件本体名"。

    处理顺序（顺序不能换）：
      1. 尾部 "For {BRAND} {MODELS...}"（原生成器的正则要求品牌后面跟一个句点，
         所以 "For HYUNDAI SONATA KIA OPTIMA" 根本没被剥掉 —— 这是线上标题重复的根因）
      2. 尾部 "for {全大写车型串}"
      3. 尾部孤立 "for" / "OEM xxx" 段
      4. 头部渠道词（KINGSTEEL / Cheap Price / OEM）
      5. 头部裸编号（"2053301705 Suspension Parts ..."）
      6. 零件名里嵌的自身 OE 号（含 038 117 021 B 这种带空格写法）
      7. 营销词与渠道词
      8. 常见拼写错误 + 收尾
    """
    s = (raw or '').strip()
    if not s:
        return ''

    # 1) 尾部 "for <BRAND> ..."（品牌后不必有句点）
    s = re.sub(r'\s+for\s+(%s)\b[\s\S]*$' % _BRAND_ALT, '', s, flags=re.I)
    # 2) 尾部 "for <全大写车型/系列串>"
    s = re.sub(r'\s+for\s+[A-Z][A-Z0-9\-]{1,}(?:\s+[A-Z][A-Z0-9\-]{1,})*\s*$', '', s)
    # 3) 尾部孤立 for / OEM 段
    s = re.sub(r'\s+for\s*$', '', s, flags=re.I)
    s = re.sub(r'\s+OEM\s+[A-Z0-9\-/\s]+$', '', s)
    # 4) 头部渠道/品牌词
    s = re.sub(r'^(?:KINGSTEEL|KING\s*MAY|OEM)\s*[-–—:]?\s*', '', s, flags=re.I)
    s = re.sub(r'^Cheap\s+Price\s*', '', s, flags=re.I)
    # 5) 头部裸编号
    s = re.sub(r'^\d{6,}[A-Z0-9]*\s+', '', s)
    # 6) 自身 OE 号（允许任意分隔符）
    pat = _oe_pattern(oe)
    if pat:
        s = re.sub(pat, ' ', s, flags=re.I)
    # 7) 营销词 / 渠道词（先渠道后营销，否则 "Auto Performance Parts" 会被拆成 "Parts"）
    s = re.sub(r'\b%s\b' % _CHANNEL_WORDS, ' ', s, flags=re.I)
    s = re.sub(r'\b%s\b' % _ADS_WORDS, ' ', s, flags=re.I)
    # 8) 拼写 + 收尾
    for a, b in _TYPO_FIX:
        s = re.sub(a, b, s)
    s = re.sub(r'\s{2,}', ' ', s).strip(' -–,.:;')
    s = re.sub(r'\s+(for|of|with|and|the)\s*$', '', s, flags=re.I).strip(' -–,.:;')
    # 整串就是介词/噪音 → 视为无有效零件名
    if s.lower() in ('for', 'of', 'with', 'and', 'the', 'auto part', 'parts', 'part'):
        return ''
    return s


def display_brand(entry, part_name='', fallback='Hyundai / Kia'):
    """品牌显示名：优先 DB brand 字段，其次从零件名反推，都没有就用 fallback。

    fallback 沿用站点既有约定（韩系专供线）：全站正文模板（Brand Coverage / FAQ / 导语）
    都按有品牌写，查不到品牌时若留空会产出 "for  models" 这种断句，
    且与 11-06 起新页模板不一致，故统一回落到 Hyundai / Kia。
    """
    brands = [b for b in (entry.get('brand') or []) if b]
    if brands:
        seen, out = set(), []
        for b in brands:
            d = _brand_display(b)
            if d and d.lower() not in seen:
                seen.add(d.lower())
                out.append(d)
        return ' / '.join(out)
    nm = (part_name or '').upper()
    found = [_brand_display(b) for b in BRAND_WORDS if b in nm]
    if found:
        return found[0]
    return fallback or ''


def _titlecase_model(s):
    """车型名规整：全大写词转正常大小写，但含数字或短代号（VI/TSI/300）保持原样。"""
    keep = {'KIA': 'Kia', 'GM': 'GM', 'VW': 'VW', 'BMW': 'BMW', 'JEEP': 'Jeep',
            'GMC': 'GMC', 'RAM': 'Ram', 'FWD': 'FWD', 'AWD': 'AWD', 'EV': 'EV',
            'HEV': 'HEV', 'PHEV': 'PHEV', 'SUV': 'SUV', 'MPV': 'MPV'}
    out = []
    for tok in s.split():
        if tok.upper() in keep:
            out.append(keep[tok.upper()])
        elif any(c.isdigit() for c in tok) or (tok.isupper() and len(tok) <= 3):
            out.append(tok)
        else:
            out.append(tok.title())
    return ' '.join(out)


def fitment_models(entry):
    """从 fitment 列表取车型名（去掉代号/排量/年份尾巴）。"""
    out = []
    for f in (entry.get('fitment') or []):
        if isinstance(f, dict):
            f = f.get('model') or f.get('vehicle') or ''
        if not isinstance(f, str):
            continue
        s = f.strip()
        s = re.sub(r'\s*\([^)]*\)\s*', ' ', s)                  # 去 (HG) / (YF) 这类代号
        s = re.sub(r'\s+\d{4}\s*[-–~]\s*\d{0,4}\s*$', ' ', s)   # 去尾部年份区间 "2009-2015"
        s = re.sub(r'\s+\d{4}\s*$', ' ', s)                     # 去尾部单一年份
        s = re.sub(r'\s+[\d.]+\s*L\b.*$', ' ', s)               # 去 "1.6L 2.0L ..."
        s = re.sub(r'(?:[\s.]+[\d.]+)+\s*$', ' ', s)             # 去尾部排量 "2.0 2.4"
        s = re.sub(r'\s{2,}', ' ', s).strip(' -,')
        if not s or len(s) > 28:
            continue
        s = _titlecase_model(s)
        if s and s.lower() not in [x.lower() for x in out]:
            out.append(s)
    return out[:2]


def _trunc_words(text, room, min_words=2):
    """按词截断到 room 字符以内（至少保留 min_words 个词，且不留悬空的介词尾巴）。"""
    if room <= 0:
        return ''
    words = text.split()
    floor = min(min_words, len(words))
    while len(words) > floor and sum(len(w) + 1 for w in words) - 1 > room:
        words.pop()
    # 去掉悬空的介词尾巴（"Complete parts of" → "Complete parts"）
    while len(words) > 1 and words[-1].lower() in ('of', 'for', 'and', 'the', 'with', 'a', 'an', 'to', 'in'):
        words.pop()
    return ' '.join(words)


def _fit_title(oe, part, brand, models):
    """title 阶梯：按"买家信息量"从高到低取第一个不超过 70 字符的版本。

    两轮：第一轮先试所有"车型/品牌 × 尾巴"组合且**零件名完整**；
          都装不下时，第二轮才截零件名（至少保留 2 个词，避免出现 "Shock" 这种半截词）。
    铁律：OE 号永不截断；品牌/车型优先保留。
    """
    who_models = ' / '.join(models) if models else ''
    combos = []
    for who in (who_models, brand):
        if not who:
            continue
        combos.append((who, ' | Wholesale Parts'))
        combos.append((who, ''))

    # 第一轮：零件名完整
    for who, tail in combos:
        t = 'OE {oe} {part} for {who}{tail}'.format(oe=oe, part=part, who=who, tail=tail)
        if len(t) <= 70:
            return t

    # 第二轮：截零件名，保住品牌与尾巴
    for who, tail in combos:
        room = 70 - len('OE {oe}  for {who}{tail}'.format(oe=oe, who=who, tail=tail))
        p = _trunc_words(part, room)
        if not p:
            continue
        t = 'OE {oe} {p} for {who}{tail}'.format(oe=oe, p=p, who=who, tail=tail)
        if len(t) <= 70:
            return t

    # 连品牌都没有：只保留 OE 号 + 零件名
    t = 'OE {oe} {part}'.format(oe=oe, part=part)
    if len(t) <= 70:
        return t
    room = 70 - len('OE {oe} '.format(oe=oe))
    return ('OE {oe} {p}'.format(oe=oe, p=_trunc_words(part, room, min_words=1))).strip()


def build_title(oe, part, brand, models=None):
    return _fit_title(oe, part, brand, models or [])


def build_desc(oe, part, brand, models=None):
    """description：完整句子，含适配 + 交叉号 + MOQ + FOB + 交期，绝不半句截断。"""
    who = ' / '.join(models) if models else brand
    if not who:
        who = 'Hyundai / Kia vehicles'
    d = ('OE {oe} {part} for {who}. Fitment, cross-references, MOQ 10 pcs and FOB price on request '
         'from KingMay, Guangzhou. Quotes in 1 business day.').format(oe=oe, part=part, who=who)
    if len(d) <= 158:
        return d
    d = ('OE {oe} {part} for {who}. Fitment, MOQ 10 pcs and FOB price on request from KingMay, '
         'Guangzhou.').format(oe=oe, part=part, who=who)
    if len(d) <= 158:
        return d
    d = 'OE {oe} {part}. Wholesale supply from KingMay, Guangzhou. MOQ 10 pcs, FOB on request.'.format(
        oe=oe, part=part)
    if len(d) <= 158:
        return d
    return 'OE {oe} {part} from KingMay, Guangzhou. MOQ 10 pcs, FOB on request.'.format(
        oe=oe, part=part[:60])


def build_keywords(oe, part, brand):
    bits = ['OE {oe}'.format(oe=oe), '{oe} part'.format(oe=oe), part]
    if brand:
        bits += ['{p} {b}'.format(p=part, b=brand), '{b} parts'.format(b=brand)]
    bits += ['{p} wholesale'.format(p=part), '{p} supplier'.format(p=part),
             'auto parts China', 'KingMay']
    return ', '.join(dict.fromkeys([b for b in bits if b]))


# ── 单页改写 ──
def _esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def apply_to_page(html, oe, entry):
    """对单个 OE 页做买家形态改写，返回 (新内容, 是否变化, 明细)。"""
    info = {}
    raw = (entry.get('part_name') or '').strip()
    part = clean_part_name(raw, oe)
    if not part:
        part = 'Auto Part'
    brand = display_brand(entry, raw)
    models = fitment_models(entry)

    title = build_title(oe, part, brand, models)
    desc = build_desc(oe, part, brand, models)
    kw = build_keywords(oe, part, brand)
    who = ' / '.join(models) if models else brand
    h1 = 'OE <span class="oe-n">{oe}</span> — {part}{w}'.format(
        oe=oe, part=part, w=(' for ' + who if who else ''))

    out = html

    # 1) 正文里所有"脏零件名"换成干净名（含小写变体与 HTML 转义变体）
    if raw and raw != part:
        for src, dst in ((raw, part), (raw.lower(), part.lower()),
                         (_esc(raw), _esc(part)), (_esc(raw.lower()), _esc(part.lower()))):
            if src and src in out:
                out = out.replace(src, dst)

    # 2) head 区
    out = re.sub(r'<title>.*?</title>', '<title>{t}</title>'.format(t=_esc(title)), out, count=1, flags=re.S)
    out = re.sub(r'<meta\s+name="description"\s+content="[^"]*"\s*/?>',
                 '<meta name="description" content="{d}" />'.format(d=_esc(desc)), out, count=1)
    out = re.sub(r'<meta\s+name="keywords"\s+content="[^"]*"\s*/?>',
                 '<meta name="keywords" content="{k}" />'.format(k=_esc(kw)), out, count=1)
    out = re.sub(r'<meta\s+property="og:title"\s+content="[^"]*"\s*/?>',
                 '<meta property="og:title" content="{t}" />'.format(t=_esc(title)), out, count=1)
    out = re.sub(r'<meta\s+property="og:description"\s+content="[^"]*"\s*/?>',
                 '<meta property="og:description" content="{d}" />'.format(d=_esc(desc)), out, count=1)
    out = re.sub(r'<meta\s+name="twitter:title"\s+content="[^"]*"\s*/?>',
                 '<meta name="twitter:title" content="{t}" />'.format(t=_esc(title)), out, count=1)
    out = re.sub(r'<meta\s+name="twitter:description"\s+content="[^"]*"\s*/?>',
                 '<meta name="twitter:description" content="{d}" />'.format(d=_esc(desc)), out, count=1)

    # 3) H1
    out = re.sub(r'<h1>.*?</h1>', '<h1>{h}</h1>'.format(h=h1), out, count=1, flags=re.S)

    info.update(title=title, desc=desc, keywords=kw, h1=h1, part=part,
                raw=raw, brand=brand, models=models)
    return out, (out != html), info
