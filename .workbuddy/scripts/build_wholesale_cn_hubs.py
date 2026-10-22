# -*- coding: utf-8 -*-
"""生成 wholesale 的「中国车品牌」批发聚合页。

数据源是 qinparts 国产 OE 库（798 个已生成详情页），不是主站韩系库。
wholesale 只做批发意图聚合，详情页留给 qinparts，两站不复制内容。

用法：
    python build_wholesale_cn_hubs.py            # 全量
    python build_wholesale_cn_hubs.py --limit 2 # 试跑
"""
import collections
import importlib.util
import json
import os
import random
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WS = r'C:\Users\123\WorkBuddy\wholesale-portal'
SITE = 'https://wholesale.global-ucars.com'
QIN = 'https://www.qinparts.com'
MAIN = 'https://www.global-ucars.com'

# 复用主批发页生成器（同一套模板：FAQ schema / 贸易条款 / RFQ / chips）
_spec = importlib.util.spec_from_file_location(
    'wh', os.path.join(BASE, '.workbuddy', 'scripts', 'build_wholesale_hubs.py'))
wh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wh)

MIN_COUNT = 20          # 低于此数不单独成页，合并进综合页
LIST_LIMIT = 60         # 每页最多展示多少条件号

# 国产品牌文案：面向中国车出口的真实采购场景
CN_BRAND = {
    'chery': dict(disp='Chery',
                  lead='Chery is China\'s largest passenger-vehicle exporter and has been for two decades. Its parts network is deep but fragmented — most overseas buyers end up sourcing from three or four traders because no single desk carries the full range.',
                  body='We consolidate Chery genuine and OE-quality parts across Tiggo, Arrizo, QQ and eQ lines from the Guangzhou and Wuhu supply base. Because Chery shares platforms across several of its own marques, a single part number frequently covers multiple nameplates — we flag those cross-applications on every line so you can widen coverage without widening inventory.',
                  tip='Chery part numbers beginning with the same five digits usually belong to the same assembly group. If you are building a first order, pick one number from each prefix group rather than ten from the same group.',
                  markets='Main export markets: Russia, Iran, Egypt, Brazil, Chile.'),
    'geely': dict(disp='Geely',
                  lead='Geely supplies parts for its own marques plus Volvo and Polestar co-developed platforms, which means tolerances and material specs run tighter than the China-market average.',
                  body='Our Geely line covers Emgrand, Coolray, Azkarra, Boyue and Geometry parts. Platform sharing with Volvo means several chassis and electrical components follow European specification — worth knowing when you quote against a European aftermarket alternative, because the comparison is closer than buyers expect.',
                  tip='Geometry and other Geely EV lines use high-voltage components that most general traders will not ship. Ask specifically about DG-certified packing before you quote an EV part.',
                  markets='Main export markets: Russia, Belarus, Saudi Arabia, Philippines, Malaysia.'),
    'byd': dict(disp='BYD',
                lead='BYD moved from being a battery maker to the world\'s largest plug-in manufacturer in under a decade. Its parts catalog is younger than Chery\'s or Geely\'s, and that is exactly why supply is tight outside China.',
                body='We hold BYD parts across the Dynasty and Ocean series, including the sealing, thermal-management and brake components that EV fleets wear out fastest. Blade-pack-adjacent components carry extra packing and documentation requirements; we handle the DG declaration for air and sea rather than leaving it to the buyer.',
                  tip='For BYD, trim level matters more than model year. Two cars of the same year can take different brake or suspension parts depending on battery size. Send the VIN rather than the year.',
                  markets='Main export markets: Brazil, Thailand, Israel, Australia, Mexico.'),
    'jetour': dict(disp='Jetour',
                   lead='Jetour is Chery\'s value SUV line and one of the fastest-growing Chinese nameplates in Russia and the Middle East. Parts supply outside the dealer network is still thin.',
                   body='Jetour shares its underlying architecture with Chery Tiggo models, so a large share of service parts cross-reference to Chery numbers already in stock. We map that relationship explicitly so a Jetour order can often be filled the same day rather than waiting on a factory run.',
                   tip='If a Jetour number is not in stock, ask for the Chery equivalent before assuming a long lead time — cross-reference coverage on this line is unusually high.',
                   markets='Main export markets: Russia, UAE, Saudi Arabia, Kazakhstan.'),
    'exeed': dict(disp='Exeed',
                  lead='Exeed is Chery\'s premium marque. Part quality runs closer to European spec and the catalog is smaller and more tightly controlled.',
                  body='Exeed service parts overlap substantially with Chery and Jetour on the mechanical side, while body, trim and lighting are marque-specific and slower to source. We keep the shared mechanical range on the shelf and quote the marque-specific items against factory lead time.',
                  tip='Body and lighting numbers on Exeed are the ones worth ordering ahead. Mechanical parts can usually be substituted from the wider Chery pool.',
                  markets='Main export markets: Russia, Kazakhstan, UAE.'),
    'fangchengbao': dict(disp='Fang Cheng Bao',
                         lead='Fang Cheng Bao is BYD\'s premium off-road and performance line. It is new enough that independent parts supply barely exists outside China.',
                         body='We carry the Fang Cheng Bao range through the same BYD supply channel, which means the documentation and DG handling already meet export standard. Given how new the marque is, we recommend consolidating these numbers with BYD parts into one shipment rather than ordering them standalone.',
                         tip='Freight is the dominant cost on small Fang Cheng Bao orders. Consolidate with BYD numbers going to the same port.',
                         markets='Main export markets: China domestic, UAE, Russia (early).'),
}

CN_MISC = dict(disp='Chinese EV & Emerging Brands',
               lead='Denza, Jaecoo and the newer Chinese marques share one problem for overseas buyers: volumes per part number are low, but the number of distinct part numbers is high.',
               body='We group these lines into a single consolidated catalogue so a small order still fills a container slot economically. Every number below ships from the same Guangzhou warehouse as our Chery, Geely and BYD stock, so mixed consolidation is standard rather than an exception.',
               tip='Low-volume marques are where consolidation matters most. Send the full list rather than ordering line by line.',
               markets='Main export markets: Russia, UAE, Southeast Asia.')


def build_records():
    """取国产库记录（复用 build_cn_oe_pages 的数据装配逻辑）。"""
    spec = importlib.util.spec_from_file_location(
        'bc', os.path.join(BASE, '.workbuddy', 'scripts', 'build_cn_oe_pages.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    prod, enr = m.load()
    return list(m.build_records(prod, enr).values())


def faq_for(disp):
    return [
        (f'What is the minimum order for {disp} parts?',
         'There is no minimum quantity per part number. Order a single unit or consolidate hundreds of numbers into one container — the container fixes the freight cost, not the part count.'),
        (f'Are these {disp} parts genuine or aftermarket?',
         'Both, and we state which on every quotation. Genuine parts come through the OE supply chain with original numbering; aftermarket lines are OE-specification parts from the same-tier factories. We never silently substitute one for the other.'),
        (f'How long does {disp} parts supply take?',
         'Numbers shown in the catalogue below are in stock and leave Guangzhou within three business days of payment. Numbers outside it are quoted against factory lead time, usually two to five weeks depending on the line.'),
        ('Can I mix Chinese-brand parts with Hyundai or Kia parts in one container?',
         'Yes, and this is the most common request we handle. One container, one customs entry, one freight bill — mixing Chinese and Korean lines is standard practice for distributors serving both.'),
        ('Which shipping documents do you provide?',
         'Commercial invoice, packing list, certificate of origin, and DG declaration where a part requires it. We ship FOB Nansha or Guangzhou by default and can arrange CIF to most ports.'),
    ]


def main():
    limit = None
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    random.seed(20261022)

    recs = build_records()
    print(f'国产库载入 {len(recs)} 条')

    counts = collections.Counter(r['make'] for r in recs)
    print('品牌分布:', dict(counts.most_common()))

    by_brand = collections.defaultdict(list)
    for r in recs:
        by_brand[r['make']].append(r)
    for b in by_brand:
        random.shuffle(by_brand[b])

    # 达标的品牌单独成页；其余合并进综合页
    solo = [b for b, n in counts.most_common() if n >= MIN_COUNT and b in CN_BRAND]
    misc = [b for b in counts if b not in solo]

    plan = []
    for b in solo:
        plan.append((b, CN_BRAND[b], by_brand[b], counts[b]))
    if misc:
        mr = [r for b in misc for r in by_brand[b]]
        random.shuffle(mr)
        plan.append(('misc', CN_MISC, mr, len(mr)))

    if limit:
        plan = plan[:limit]

    made = []
    for key, info, items_all, cnt in plan:
        slug = f'wholesale-chinese-{key}-parts'
        # 清单：优先展示有车型的记录，保证信息完整
        ranked = sorted(items_all, key=lambda r: (not r.get('models'), r['oe']))
        sel = ranked[:LIST_LIMIT]
        items = [{'oe': r['oe'], 'name': r['name'], 'file': r['slug'],
                  'brandlabel': (', '.join(r['models'][:3]) if r.get('models') else r['make_disp'])}
                 for r in sel]

        chips = [(f'wholesale-chinese-{o}-parts',
                  f'{CN_BRAND[o]["disp"]} ({counts[o]:,})')
                 for o in solo if o != key][:5]
        chips.append(('wholesale-brake-parts', 'Brake parts (main catalogue)'))
        chips.append(('wholesale-suspension-parts', 'Suspension parts (main catalogue)'))

        p = {'brand': info, 'slug': slug, 'items': items, 'count': cnt,
             'chips': chips, 'faq': faq_for(info['disp']), 'base': QIN}
        html = wh.page(p)
        d = os.path.join(WS, slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8', newline='').write(html)
        made.append((slug, cnt, len(items)))
        print(f'  {slug:38s} 库存 {cnt:4d}  展示 {len(items):3d}')

    json.dump({'updated_at': __import__('datetime').datetime.now().isoformat(timespec='seconds'),
               'source': 'qinparts cn-oe', 'pages': made},
              open(os.path.join(WS, '_data', 'wholesale-cn-hubs.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'共生成 {len(made)} 页')
    print('未单独成页的品牌（已并入综合页）:', misc)
    return 0


if __name__ == '__main__':
    sys.exit(main())
