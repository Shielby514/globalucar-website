# -*- coding: utf-8 -*-
"""主站 OE 库轻量索引 —— wholesale 聚合页的数据源，支持增量。

扫描 主站/oe/*.html，抽出 (oe号, 零件名, 品牌列表, 品类, 车型)，
存到 <wholesale>/_data/main-oe-index.json，并记录已索引文件用于增量。

用法:
  python build_main_oe_index.py            # 增量（只扫上次之后新增/改动的页）
  python build_main_oe_index.py --full     # 全量重建
输出: C:\\Users\\123\\WorkBuddy\\wholesale-portal\\_data\\main-oe-index.json
"""
import os, re, sys, json, time, collections

MAIN = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '20260324111450'))
OEDIR = os.path.join(MAIN, 'oe')
OUTDIR = r'C:\Users\123\WorkBuddy\wholesale-portal\_data'
OUT = os.path.join(OUTDIR, 'main-oe-index.json')
STATE = os.path.join(OUTDIR, 'main-oe-index.state.json')

TITLE = re.compile(r'<title>OE\s+([^<\s]+)\s+([\s\S]{0,160}?)</title>', re.I)
BRANDS = ['Hyundai', 'Kia', 'Mercedes', 'BMW', 'Audi', 'Volkswagen', 'Toyota', 'Nissan',
          'Honda', 'Mazda', 'Mitsubishi', 'Subaru', 'Suzuki', 'Ford', 'Chevrolet',
          'Geely', 'BYD', 'Chery', 'MG', 'Great Wall', 'Changan', 'Haval', 'Jetour',
          'Exeed', 'Denza', 'Jaecoo', 'Peugeot', 'Renault', 'Skoda', 'Opel', 'Daewoo', 'Isuzu']
CATS = {
    'brake': ['brake', 'disc', 'rotor', 'caliper'],
    'suspension': ['shock', 'absorber', 'strut', 'control arm', 'bush', 'stabilizer',
                   'sway bar', 'ball joint', 'spring', 'suspension', 'c.v boot', 'cv boot'],
    'engine': ['engine', 'piston', 'gasket', 'crankshaft', 'camshaft', 'cylinder',
               'timing', 'oil pump', 'water pump', 'valve cover', 'pulley'],
    'electrical': ['alternator', 'starter', 'sensor', 'switch', 'lamp', 'headlamp',
                   'wiring', 'ignition coil', 'relay', 'fuse', 'air flow meter', 'maf'],
    'cooling': ['radiator', 'coolant', 'thermostat', 'fan', 'condenser', 'evaporator'],
    'filters': ['filter'],
    'transmission': ['clutch', 'gearbox', 'transmission', 'axle', 'cv joint', 'drive shaft'],
    'body': ['door', 'bumper', 'fender', 'grille', 'mirror', 'window', 'hood', 'tailgate'],
    'exhaust': ['exhaust', 'muffler', 'catalytic', 'silencer'],
    'steering': ['steering', 'rack', 'tie rod'],
    'fuel': ['fuel pump', 'injector', 'fuel tank'],
    'hvac': ['compressor', 'air conditioning', 'heater', 'ac '],
}
# 品类判定顺序：先专后泛，避免 Engine 吃掉一切
CAT_ORDER = ['filters', 'brake', 'suspension', 'steering', 'cooling', 'transmission',
             'exhaust', 'fuel', 'hvac', 'electrical', 'body', 'engine']


def cat_of(name):
    n = ' ' + name.lower() + ' '
    for c in CAT_ORDER:
        if any((' ' + k if not k.endswith(' ') else k) in n or k in n for k in CATS[c]):
            return c
    return None


def parse(path):
    try:
        h = open(path, encoding='utf-8', errors='ignore').read()
    except Exception:
        return None
    m = TITLE.search(h)
    if not m:
        return None
    oe = m.group(1).strip()
    rest = m.group(2)
    # 去掉尾部 "| KingMay" 与 "for <brands>"
    rest = re.sub(r'\s*\|\s*KingMay\s*$', '', rest, flags=re.I).strip()
    brands = [b for b in BRANDS if re.search(r'\b' + re.escape(b) + r'\b', rest, re.I)]
    name = re.sub(r'\bfor\s+for\b|\bfor\b', '|', rest, flags=re.I).split('|')[0].strip()
    name = re.sub(r'\s+', ' ', name).strip(' -')
    if not name:
        return None
    # 车型：从 h1/正文里找 model 线索太不可靠（互参表污染），这里只存品牌
    return {'oe': oe, 'name': name, 'brands': brands, 'cat': cat_of(name or rest),
            'file': os.path.basename(path)}


def main():
    full = '--full' in sys.argv
    t0 = time.time()
    os.makedirs(OUTDIR, exist_ok=True)

    old = {}
    if not full and os.path.exists(OUT):
        try:
            old = {r['file']: r for r in json.load(open(OUT, encoding='utf-8'))['items']}
        except Exception:
            old = {}
    st = {}
    if not full and os.path.exists(STATE):
        try:
            st = json.load(open(STATE, encoding='utf-8'))
        except Exception:
            st = {}

    files = sorted(f for f in os.listdir(OEDIR) if f.endswith('.html'))
    todo = [f for f in files if full or st.get(f) != os.path.getmtime(os.path.join(OEDIR, f))]
    print(f'OE 页共 {len(files)}，本次需索引 {len(todo)}')

    recs = dict(old)
    done = 0
    for f in todo:
        r = parse(os.path.join(OEDIR, f))
        if r:
            recs[f] = r
        st[f] = os.path.getmtime(os.path.join(OEDIR, f))
        done += 1
        if done % 1000 == 0:
            print(f'  ...{done}/{len(todo)}  {time.time()-t0:.0f}s', flush=True)

    items = list(recs.values())
    bc = collections.Counter()
    cc = collections.Counter()
    bcn = collections.Counter()
    for r in items:
        for b in r['brands']:
            bc[b] += 1
            if r['cat']:
                bcn[(b, r['cat'])] += 1
        if r['cat']:
            cc[r['cat']] += 1

    out = {'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
           'total_pages': len(items),
           'indexed_now': done,
           'brands': dict(bc.most_common()),
           'cats': dict(cc.most_common()),
           'brand_cat': {f'{a}|{b}': v for (a, b), v in bcn.most_common()},
           'items': items}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(st, open(STATE, 'w', encoding='utf-8'))

    print(f"\n=== 品牌 ({len(bc)}) ===")
    for k, v in bc.most_common(14):
        print(f'  {k:14s} {v:6d}')
    print(f"\n=== 品类 ({len(cc)}) ===")
    for k, v in cc.most_common(14):
        print(f'  {k:14s} {v:6d}')
    print(f'\n无品牌 {sum(1 for r in items if not r["brands"])}  无品类 {sum(1 for r in items if not r["cat"])}')
    print(f'耗时 {time.time()-t0:.0f}s -> {OUT}')


if __name__ == '__main__':
    main()
