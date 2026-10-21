# -*- coding: utf-8 -*-
"""wholesale 聚合页体检：外链有效性 + 内容唯一性 + thin content。

用法: python verify_wholesale_hubs.py
输出: <wholesale>/_data/verify-wholesale.json
"""
import os, re, sys, json, math, collections

WS = r'C:\Users\123\WorkBuddy\wholesale-portal'
MAIN_OE = r'C:\Users\123\WorkBuddy\20260324111450\oe'
MAIN = 'https://www.global-ucars.com'
SITE = 'https://wholesale.global-ucars.com'

TITLE = re.compile(r'<title>([^<]*)</title>')
CANON = re.compile(r'<link rel="canonical" href="([^"]*)"')
META = re.compile(r'<meta name="description" content="([^"]*)"')
H1 = re.compile(r'<h1[^>]*>([\s\S]{0,200}?)</h1>')
TXT = re.compile(r'<[^>]+>')
OEHREF = re.compile(r'href="https://www\.global-ucars\.com/oe/([^"]+)"')


def text_of(h):
    b = re.sub(r'<(script|style)[\s\S]*?</\1>', '', h)
    b = re.sub(r'<a[^>]*href="[^"]*"[^>]*>', ' ', b)
    return re.sub(r'\s+', ' ', TXT.sub(' ', b)).strip()


def words(t):
    return len(re.findall(r"[A-Za-z][A-Za-z'-]+", t))


def shingles(t, n=8):
    w = re.findall(r"[a-z][a-z'-]+", t.lower())
    return set(tuple(w[i:i + n]) for i in range(len(w) - n + 1))


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    dirs = [d for d in os.listdir(WS)
            if d.startswith('wholesale-') and os.path.isdir(os.path.join(WS, d))]
    dirs.sort()
    print(f'聚合页 {len(dirs)} 个')

    # 主站 OE 文件集合（用于验证外链）
    real = set(f for f in os.listdir(MAIN_OE) if f.endswith('.html'))
    print(f'主站 OE 页 {len(real)} 个（用于外链校验）')

    info = {}
    bad_link = collections.Counter()
    docs = {}
    for d in dirs:
        f = os.path.join(WS, d, 'index.html')
        h = open(f, encoding='utf-8').read()
        t = TITLE.search(h)
        c = CANON.findall(h)
        links = OEHREF.findall(h)
        miss = [l for l in links if l not in real]
        for m in miss:
            bad_link[m] += 1
        body = text_of(h)
        docs[d] = shingles(body)
        info[d] = {'title': t.group(1) if t else '', 'title_len': len(t.group(1)) if t else 0,
                   'canon': c, 'canon_n': len(c),
                   'canon_ok': (len(c) == 1 and c[0] == f'{SITE}/{d}/'),
                   'oe_links': len(set(links)), 'dead_links': len(set(miss)),
                   'words': words(body), 'bytes': len(h),
                   'desc': len(META.search(h).group(1)) if META.search(h) else 0,
                   'h1': (H1.search(h).group(1).strip()[:70] if H1.search(h) else '')}

    # 内容相似度（两两）
    keys = list(docs)
    sims = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            sims.append((jaccard(docs[keys[i]], docs[keys[j]]), keys[i], keys[j]))
    sims.sort(reverse=True)
    vals = [s[0] for s in sims]

    print('\n=== 逐页 ===')
    for d in dirs:
        v = info[d]
        flag = '' if (v['canon_ok'] and v['dead_links'] == 0 and v['words'] >= 450) else '  <<<'
        print(f"  {d:32s} 词={v['words']:4d} 链接={v['oe_links']:3d} 死链={v['dead_links']:2d} "
              f"canon={'OK' if v['canon_ok'] else 'BAD'} desc={v['desc']:3d}{flag}")

    print(f'\n=== 汇总 ===')
    print(f"  死链总数 {sum(bad_link.values())}（涉及 {len(bad_link)} 个目标）")
    print(f"  canonical 异常 {sum(1 for d in dirs if not info[d]['canon_ok'])}")
    print(f"  正文 <450 词 {sum(1 for d in dirs if info[d]['words'] < 450)}")
    if vals:
        med = sorted(vals)[len(vals) // 2]
        print(f"  8-gram 相似度: 中位 {med:.3f}  最高 {vals[0]:.3f}  最低 {vals[-1]:.3f}")
        print('  最相似的 5 对:')
        for s, a, b in sims[:5]:
            print(f'    {s:.3f}  {a} <-> {b}')
    if bad_link:
        print('  死链样例:')
        for k, v in bad_link.most_common(5):
            print(f'    {v}x {k}')

    out = {'pages': info,
           'dead_links_total': sum(bad_link.values()),
           'sim_median': (sorted(vals)[len(vals) // 2] if vals else 0),
           'sim_max': (vals[0] if vals else 0),
           'sim_pairs': [{'s': round(s, 4), 'a': a, 'b': b} for s, a, b in sims[:10]]}
    os.makedirs(os.path.join(WS, '_data'), exist_ok=True)
    json.dump(out, open(os.path.join(WS, '_data', 'verify-wholesale.json'), 'w',
                        encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'\n已写入 _data/verify-wholesale.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
