# -*- coding: utf-8 -*-
"""批量清理 OE 页 title/h1/description 里的 "for for" 重复介词。

根因：源数据 part_name 残缺（如 "Bushing Iron Hose for"），尾部孤立 for 剥不掉，
与模板 "{part} for {brand}" 拼成 "for for"。源脚本已修，本脚本修正存量页。
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OEDIR = os.path.join(BASE, 'oe')

# 连续重复的 for（大小写不敏感），如 "for for" / "For for for"
DUP = re.compile(r'(?i)\b(for)(?:\s+\1)+\b')


def main():
    apply = '--apply' in sys.argv
    files = sorted(f for f in os.listdir(OEDIR) if f.endswith('.html'))
    hit_files = 0
    hit_total = 0
    samples = []
    for f in files:
        p = os.path.join(OEDIR, f)
        h = open(p, encoding='utf-8', errors='ignore').read()
        n = len(DUP.findall(h))
        if not n:
            continue
        hit_files += 1
        hit_total += n
        if len(samples) < 5:
            t = re.search(r'<title>([^<]*)</title>', h)
            samples.append((f, t.group(1) if t else '', DUP.sub(r'\1', t.group(1)) if t else ''))
        if apply:
            h2 = DUP.sub(r'\1', h)
            if h2 != h:
                open(p, 'w', encoding='utf-8', newline='').write(h2)
    print(f'扫描 {len(files)} 页')
    print(f'命中页 {hit_files}   重复实例 {hit_total}')
    print(f'模式 {"APPLY 已写入" if apply else "DRY-RUN（加 --apply 才写盘）"}')
    for f, a, b in samples:
        print(f'  {f}\n    旧 {a}\n    新 {b}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
