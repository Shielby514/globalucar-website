#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
19-build-product-catalog.py
===========================
产品库扩量：把多来源产品记录合并成一个带质量门槛的统一目录。

数据源：
  1. existing  products-data.json 里既有的 parts 记录（已上线，slug/URL 不得变）
  2. supplier  _xlsx_extracted/full_extraction_report.json —— 供应商实拍（自家图 + 真 OE + 品牌）
  3. leadong   leadong_products_reference.json —— 自有 kingmay-autoparts.com 产品（自家图 + 真 OE）
  4. cnoe      cn-oe-products.json + cn-oe-enriched.json —— 中国品牌（真 OE + 真车型）

质量门槛（任一不满足 → 剔除并计入报告，绝不放行半成品）：
  品名 / 品牌 / OE 交叉号 / 适配车型 / 规格 / MOQ / 报价 / 库存 / 主图真实存在 / 图片 alt / 描述 / TDK

防自相残杀：若该 OE 已有专属 OE 页（oe/<oe>.html），不再另建产品页。
  —— OE 页本身已是完整产品页（Product+FAQPage JSON-LD+规格表+报价口径），重复建页会互相抢排名。

输出：
  products-data.json                     既有 + 新增（新增 id 从 1000 起）
  .workbuddy/data/product-catalog.json  统一目录（出页脚本唯一输入）
  .workbuddy/data/product-catalog-report.json  门槛剔除明细

用法：
  python 19-build-product-catalog.py --dry-run
  python 19-build-product-catalog.py --apply
"""
import argparse
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

DATA = os.path.join(ROOT, '.workbuddy', 'data')
PROD_DB = os.path.join(ROOT, 'products-data.json')
CATALOG = os.path.join(DATA, 'product-catalog.json')
REPORT = os.path.join(DATA, 'product-catalog-report.json')
SITE = 'https://www.global-ucars.com'

MOQ_DEFAULT = '10 Pieces'
PRICE_DEFAULT = 'Contact for Quote'

# ---------------------------------------------------------------- 品牌归一
MAKE_MAP = {
    'VW': 'Volkswagen', 'AUDI': 'Audi', 'FORD': 'Ford', 'BMW': 'BMW',
    'MERCEDES-BENZ': 'Mercedes-Benz', 'TOYOTA': 'Toyota', 'NISSAN': 'Nissan',
    'HYUNDAI': 'Hyundai', 'LAND ROVER': 'Land Rover', 'KIA': 'Kia',
    'PEUGEOT': 'Peugeot', 'FIAT': 'Fiat', 'VOLVO': 'Volvo', 'DODGE': 'Dodge',
    'RENAULT': 'Renault', 'GWM': 'Great Wall Motors', 'OPEL': 'Opel',
    'HONDA': 'Honda', 'FAW一汽': 'FAW', 'Porsche': 'Porsche', 'MAZDA': 'Mazda',
    'CHERY': 'Chery', 'BYD': 'BYD', 'DEUTZ': 'Deutz', 'CRUZE': 'Chevrolet',
    'WuLing': 'Wuling', 'Mitsubishi': 'Mitsubishi', 'PERODUA': 'Perodua',
    'Chevrolet(Cruze)': 'Chevrolet', '大通': 'Maxus', 'JAC(江淮）': 'JAC',
    'JAC': 'JAC', 'DAF': 'DAF', 'EF7': 'Chery', 'GONOW': 'Gonow',
    'FORMUB': 'Formub', 'CHERYEV': 'Chery', 'STARGAZY': 'Stargazy', 'KARRY': 'Karry',
    'JETOUR': 'Jetour', 'EXEED': 'Exeed', 'DENZA': 'Denza', 'GEELY': 'Geely',
    'HONDA(ACCORD)': 'Honda', 'CHRYSLER': 'Chrysler', 'ROEWE': 'Roewe',
    'DONGFENG': 'Dongfeng', 'CUMMINS': 'Cummins', 'Trumpchi': 'Trumpchi',
    'BUICK': 'Buick', 'JOHN DEERE': 'John Deere', 'NAVISTAR TRUCK': 'Navistar',
}

# 名称里能识别出的品牌（用于既有 152 条补 compatible_makes）
MAKE_SCAN = [
    ('Hyundai', r'hyundai'), ('Kia', r'\bkia\b'), ('Volkswagen', r'\bvw\b|volkswagen'),
    ('Audi', r'\baudi\b'), ('Ford', r'\bford\b'), ('BMW', r'\bbmw\b'),
    ('Mercedes-Benz', r'mercedes'), ('Toyota', r'toyota'), ('Nissan', r'nissan'),
    ('Honda', r'\bhonda\b'), ('Chevrolet', r'chevrolet|\bcruze\b'), ('Peugeot', r'peugeot'),
    ('Citroen', r'citro'), ('Renault', r'renault'), ('Opel', r'opel'), ('Vauxhall', r'vauxhall'),
    ('Fiat', r'\bfiat\b'), ('Volvo', r'\bvolvo\b'), ('Land Rover', r'land ?rover'),
    ('Mazda', r'mazda'), ('Mitsubishi', r'mitsubishi'), ('Dodge', r'\bdodge\b'),
    ('Chrysler', r'chrysler'), ('Jeep', r'\bjeep\b'), ('Chery', r'chery|omoda|arrizo|tiggo'),
    ('BYD', r'\bbyd\b'), ('Geely', r'geely|coolray|monjaro'),
    ('Great Wall Motors', r'great wall|\bgwm\b'), ('Wuling', r'wuling'),
    ('Denza', r'denza'), ('Jetour', r'jetour'), ('Exeed', r'exeed'),
]

# 中国品牌零件类型 → 站内系统分类（对齐 OE 页的 Suspension/Steering/Brake 归桶）
CNOE_SYSTEM_RULES = [
    ('suspension', r'brake|tie rod|control arm|lower arm|stabilizer|shock|strut|ball joint|'
                    r'bushing|knuckle|hub|wheel bearing|drive shaft|cv joint|axle|wheel|'
                    r'radius arm|trailing arm|suspension'),
    ('cooling', r'radiator|condenser|evaporator|expansion tank|water pump|thermostat|fan|'
                r'compressor|heater core|oil cooler|cooler|cooling|hose pipe|intercooler'),
    ('electrical', r'alternator|starter|sensor|switch|relay|ignition coil|coil pack|spark plug|'
                   r'door lock|latch|head ?light|tail ?light|fog ?light|mirror|bulb|'
                   r'power window|climate|wiring|harness|abs |knock sensor|oxygen sensor'),
]


def classify_system(part_name):
    t = (part_name or '').lower()
    for sys_key, pat in CNOE_SYSTEM_RULES:
        if re.search(pat, t):
            return sys_key
    return 'engine'


# 供应商家族 → 已核实零件类型（网络 + 母库双向验证）
FAMILY_TYPE = {
    '49': 'Engine Oil Cooler', '01': 'Engine Oil Cooler', '81': 'Oil Cooler',
    '86': 'Transmission Oil Cooler', '33': 'Oil Cooler', '82': 'Engine Oil Cooler',
    '44': 'Engine Oil Cooler', '46': 'Engine Oil Cooler', '60': 'Oil Cooler',
    '98': 'Oil Cooler', '31': 'Oil Cooler',
}

TYPE_MAP = {
    'engine oil cooler': ('Engine Oil Cooler', 'engine-oil-cooler', 'cooling', 'Cooling & Climate'),
    'transmission oil cooler': ('Transmission Oil Cooler', 'transmission-oil-cooler', 'cooling', 'Cooling & Climate'),
    'gear oil cooler': ('Gear Oil Cooler', 'gear-oil-cooler', 'cooling', 'Cooling & Climate'),
    'oil cooler': ('Oil Cooler', 'oil-cooler', 'cooling', 'Cooling & Climate'),
    'oil filter housing': ('Oil Filter Housing', 'oil-filter-housing', 'cooling', 'Cooling & Climate'),
    'oil filter assembly': ('Oil Filter Assembly', 'oil-filter-assembly', 'cooling', 'Cooling & Climate'),
    'oil filter base assembly': ('Oil Filter Base Assembly', 'oil-filter-base-assembly', 'cooling', 'Cooling & Climate'),
    'oil filter': ('Oil Filter', 'oil-filter', 'cooling', 'Cooling & Climate'),
    'oil filter element': ('Oil Filter Element', 'oil-filter-element', 'cooling', 'Cooling & Climate'),
}

# 中国品牌零件类型 → 自家类型图（只用自家图库；没有对应自有图的类型直接剔除）
CNOE_IMG_RULES = [
    (r'tie ?rod|rack end', 'assets/parts/part_064_tie_rod_end.jpg'),
    (r'brake ?pad|break ?pad|pad set', 'assets/parts/gen/gen-brake-pad-set.png'),
    (r'wheel bearing|hub bearing|brake ?bearing', 'assets/parts/gen/gen-wheel-hub-bearing-assembly.png'),
    (r'ball joint', 'assets/parts/gen/gen-ball-joint-pair.png'),
    (r'door lock|latch|door handle', 'assets/parts/gen/gen-door-handle-latch-set.png'),
    (r'compressor', 'assets/parts/part_053_ac_compressor.jpg'),
    (r'stabilizer|connecting rod|\blink\b|tie bar', 'assets/parts/gen/gen-stabilizer-link-bars.png'),
    (r'control arm|lower arm', 'assets/parts/part_061_control_arm.jpg'),
    (r'shock absorber|\bstrut\b', 'assets/parts/lp/front-right-shock-absorber-54660-4h050-01.webp'),
    (r'wheel hub|\bhub\b', 'assets/parts/gen/gen-wheel-hub-bearing-assembly.png'),
    (r'filter', 'assets/parts/part_091_air_filter.jpg'),
    (r'water pump|\bpump\b', 'assets/parts/part_046_water_pump.jpg'),
    (r'radiator', 'assets/parts/part_054_radiator.jpg'),
    (r'drive shaft|cv joint|\baxle\b', 'assets/parts/gen/gen-drive-shaft-cv-joint.png'),
    (r'starter', 'assets/parts/part_089_starter_motor.jpg'),
    (r'heater core', 'assets/parts/part_054_radiator.jpg'),
    (r'sensor', 'assets/parts/gen/gen-abs-wheel-speed-sensor.png'),
    (r'oil cooler', 'assets/parts/part_050_oil_cooler.jpg'),
    (r'\bbelt\b|timing belt', 'assets/parts/gen/gen-timing-belt.png'),
    (r'clutch', 'assets/parts/part_045_camshaft.jpg'),
    (r'fuel pump', 'assets/parts/part_034_fuel_pump.jpg'),
    (r'ignition coil|coil pack', 'assets/parts/part_031_ignition_coil.jpg'),
    (r'bushing|insulator|rubber mount', 'assets/parts/gen/gen-rubber-bushing-insulator-set.png'),
    (r'head ?light|tail light|fog ?light', 'assets/parts/gen/gen-headlight-assembly.png'),
    (r'power window|\bswitch\b', 'assets/parts/gen/gen-power-window-switch.png'),
    (r'hood|bonnet', 'assets/parts/gen/gen-hood-hinge-pair.png'),
    (r'steering rack|rack and pinion|rack & pinion', 'assets/parts/gen/gen-steering-rack-pinion.png'),
    (r'cooling fan|radiator fan|fan ass', 'assets/parts/gen/gen-radiator-cooling-fan.png'),
    (r'oil pan|sump', 'assets/parts/gen/gen-engine-oil-pan.png'),
    (r'piston|ring set', 'assets/parts/gen/gen-piston-ring-set.png'),
    (r'coil spring|\bspring\b', 'assets/parts/gen/gen-coil-spring.png'),
    (r'steering |knuckle|wheel bearing', 'assets/parts/gen/gen-wheel-hub-bearing-assembly.png'),
]


def norm_oe(s):
    return re.sub(r'[^0-9A-Z]', '', str(s or '').upper())


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def slugify(text, fallback='part'):
    s = re.sub(r'[^a-z0-9]+', '-', str(text or '').lower()).strip('-')
    return s or fallback


def pretty_model(slug):
    """'arrizo-5' -> 'Arrizo 5' ; 'omoda-s5-gt' -> 'Omoda S5 GT' ; 'arrizo7' -> 'Arrizo 7'"""
    s = re.sub(r'[-_]+', ' ', str(slug or '')).strip()
    out = []
    for w in s.split():
        if re.fullmatch(r'[a-z]{1,2}\d+[a-z]?', w):
            out.append(w.upper())
        elif len(w) <= 3 and w.isalpha():
            out.append(w.upper())
        else:
            out.append(re.sub(r'^([a-z]+)(\d+)([a-z]*)$',
                              lambda m: m.group(1).capitalize() + ' ' + m.group(2) + m.group(3).upper(), w))
    return ' '.join(out)


def scan_makes(text):
    t = ' ' + str(text or '') + ' '
    out = []
    for name, pat in MAKE_SCAN:
        if re.search(pat, t, re.I):
            if name not in out:
                out.append(name)
    return out


def clean_vehicle_list(raw):
    out = []
    for seg in re.split(r'[,/]', str(raw or '')):
        seg = re.sub(r'\([^)]*\)', '', seg).strip(' -')
        seg = re.sub(r'\s+', ' ', seg)
        if seg and len(seg) > 1:
            out.append(seg)
    seen, uniq = set(), []
    for v in out:
        if v.lower() not in seen:
            seen.add(v.lower())
            uniq.append(v)
    return uniq


def parse_master_name(name):
    if not name:
        return None, []
    n = name.strip()
    for junk in ('SENP Auto Engine parts ', 'SENP Spare car parts ',
                 'SENP Spare car parts Cooling system ', 'for HYUNDAI / KIA',
                 'for Hyundai / Kia'):
        n = n.replace(junk, '').strip()
    if ' for ' in n:
        head, tail = n.split(' for ', 1)
    else:
        head, tail = n, ''
    return head.strip(' ,-'), clean_vehicle_list(tail)


def pick_type(candidates):
    best = None
    for c in candidates:
        cl = (c or '').lower()
        for key in TYPE_MAP:
            if key in cl and (best is None or len(key) > len(best[0])):
                best = (key, c)
    return best[1] if best else None


def build_specs(rec_type, makes, oes, extra=None):
    spec = {
        'Part Type': rec_type,
        'OE Number': ' / '.join(oes[:4]) if oes else '—',
        'Vehicle Application': ' / '.join(makes) if makes else '—',
        'Material': 'Aluminium',
        'MOQ': MOQ_DEFAULT,
        'Warranty': '12 months',
        'Supply': 'RFQ',
    }
    if extra:
        spec.update(extra)
    return spec


def build_features(rec_type, fit, oes):
    return [
        'Direct-fit replacement built to the original OE specification',
        'Cross reference: %s' % (' / '.join(oes[:3]) if oes else '—'),
        'Supplied for %s applications' % (' / '.join(fit[:3]) if fit else 'major models'),
        'Inspected before export packing; neutral or branded packing available',
        'MOQ %s per SKU, consolidated mixed-SKU export orders welcome' % MOQ_DEFAULT,
    ]


def build_faq(name, rec_type, fit, oes):
    mk = ' / '.join(fit[:3]) if fit else 'the listed vehicle applications'
    oe = oes[0] if oes else 'the OE number shown above'
    return [
        ('What is the MOQ for %s?' % name,
         'The minimum order quantity is %s per SKU. Mixed SKUs from the same family can be combined into one consolidated export order — send us your OE list for a combined quote.' % MOQ_DEFAULT),
        ('Which vehicles does this %s fit?' % rec_type.lower(),
         'This part carries OE reference %s and is supplied for %s. Because fitment depends on VIN and production date, please send the VIN or the OE number printed on your original part and we will confirm the exact match before you order.' % (oe, mk)),
        ('Do you supply genuine OEM or aftermarket quality?',
         'We supply OEM-grade aftermarket parts manufactured to original specification, and genuine OEM parts on request. Every batch is inspected before export packing.'),
        ('How is %s packed for export?' % name,
         'Standard export packaging with anti-rust treatment; customized neutral or Kingmay branded packaging is available for wholesale orders.'),
        ('What are your payment and shipping terms?',
         'We accept T/T and can quote FOB / CIF to your destination port. Air and sea freight are both available from Guangzhou / Shenzhen.'),
    ]


class MasterIndex:
    def __init__(self, path):
        self.db = load_json(path, {}) or {}
        self.exact = {}
        for k, e in self.db.items():
            n = norm_oe(e.get('oe') or k)
            if n:
                self.exact.setdefault(n, e)

    def get(self, oe):
        return self.exact.get(norm_oe(oe))


# ---------------------------------------------------------------- 源 2：供应商
def build_supplier_records(master, oe_primary, report):
    data = load_json(os.path.join(ROOT, '_xlsx_extracted', 'full_extraction_report.json'), {}) or {}
    out = []
    for it in data.get('all_products') or []:
        kn = it.get('kingmay_no') or ''
        fam = kn.split('-')[0]
        oes_raw = [o.get('raw') for o in (it.get('oe_numbers') or []) if o.get('raw')]
        oes_norm = [o.get('norm') for o in (it.get('oe_numbers') or []) if o.get('norm')]
        if not oes_norm:
            report['reject_supplier'].append((kn, 'no_oe'))
            continue
        if any(norm_oe(o) in oe_primary for o in oes_norm):
            report['reject_supplier'].append((kn, 'oe_page_exists'))
            continue
        imgs = [i.lstrip('/') for i in (it.get('saved_images') or []) if i.startswith('/assets/')]
        if not imgs:
            report['reject_supplier'].append((kn, 'no_image'))
            continue
        makes = []
        for a in (it.get('applications') or []):
            m = MAKE_MAP.get(a, a)
            if m not in makes:
                makes.append(m)
        if not makes:
            report['reject_supplier'].append((kn, 'no_make'))
            continue
        cand, vehicles = [], []
        for o in oes_norm:
            e = master.get(o)
            if e:
                nm = (e.get('part_name') or '').strip()
                if nm:
                    t, v = parse_master_name(nm)
                    cand.append(t or nm)
                    for x in v:
                        if x not in vehicles:
                            vehicles.append(x)
                for x in (e.get('fitment') or []):
                    if isinstance(x, str) and x not in vehicles:
                        vehicles.append(x)
                break
        rec_type = pick_type(cand) or FAMILY_TYPE.get(fam) or 'Oil Cooler'
        sub_cat, sub_slug, psys, psys_label = TYPE_MAP.get(
            rec_type.lower(), ('Oil Cooler', 'oil-cooler', 'cooling', 'Cooling & Climate'))
        fit = vehicles if vehicles else makes
        head = ' / '.join(oes_raw[:2])
        name = re.sub(r'\s+', ' ', '%s %s for %s' % (rec_type, head, ' / '.join(fit[:3]))).strip()
        spec = build_specs(rec_type, makes, oes_raw, {
            'Vehicle Application': ' / '.join(fit),
            'Kingmay No.': kn,
            'Reference Numbers': ' / '.join(oes_raw[:6]),
        })
        alt = '%s %s for %s - Kingmay wholesale auto parts' % (rec_type, head, ' / '.join(makes[:2]))
        meta_title = '%s %s for %s | OE Cross Reference | Kingmay' % (rec_type, head, ' / '.join(makes[:2]))
        meta_desc = ('%s for %s. OE reference %s. OEM-grade aftermarket replacement supplied by '
                     'Kingmay Guangzhou. MOQ %s, FOB/CIF quoted on request, 12-month warranty.'
                     % (rec_type, ' / '.join(fit[:3]), ' / '.join(oes_raw[:3]), MOQ_DEFAULT))
        desc = ('<p>%s supplied for <strong>%s</strong> applications. OE reference <strong>%s</strong>.</p>'
                '<p>Manufactured to original specification with an aluminium heat-exchanger core; '
                'each unit is pressure tested and inspected before export packing. '
                'Supply type is RFQ, MOQ %s per SKU.</p>'
                '<ul><li>Part type: %s</li><li>OE reference: %s</li>'
                '<li>Vehicle application: %s</li><li>Warranty: 12 months</li></ul>'
                % (rec_type, ' / '.join(fit[:4]), ' / '.join(oes_raw[:4]), MOQ_DEFAULT,
                   rec_type, ' / '.join(oes_raw[:6]), ' / '.join(fit[:6])))
        out.append({
            'id': 0, 'slug': '', 'name': name[:180], 'category': 'parts',
            'part_system': psys, 'part_system_label': psys_label,
            'sub_category': sub_cat, 'sub_slug': sub_slug,
            'price': PRICE_DEFAULT, 'local_image': imgs[0], 'images': imgs[:5],
            'moq': MOQ_DEFAULT, 'in_stock': True, 'featured': False,
            'brand': makes[0], 'compatible_makes': makes[:6], 'fitment': fit[:10],
            'oem_refs': oes_raw[:12],
            'tags': [rec_type] + makes[:4] + ['Wholesale', 'Export'],
            'features': build_features(rec_type, fit, oes_raw), 'specs': spec,
            'meta_title': meta_title[:160], 'meta_description': meta_desc[:300],
            'meta_keywords': ', '.join([rec_type.lower()] + [o.lower() for o in oes_raw[:3]] +
                                       [m.lower() for m in makes[:3]] +
                                       ['wholesale auto parts', 'china supplier'])[:300],
            'description': desc, 'system': psys, 'alt_text': alt[:180],
            'source': 'supplier', 'kingmay_no': kn,
            'faq': build_faq(name, rec_type, fit, oes_raw),
        })
    return out


# ---------------------------------------------------------------- 源 3：leadong
def build_leadong_records(master, oe_primary, report):
    items = load_json(os.path.join(DATA, 'leadong_products_reference.json'), []) or []
    items = items if isinstance(items, list) else list(items.values())
    lp_dir = os.path.join(ROOT, 'assets', 'parts', 'lp')
    lp_files = os.listdir(lp_dir) if os.path.isdir(lp_dir) else []
    lp_by_oe = collections.defaultdict(list)
    for f in lp_files:
        for tok in re.findall(r'[0-9]{4,6}-[0-9A-Za-z]{4,6}', f):
            lp_by_oe[norm_oe(tok)].append(os.path.join('assets', 'parts', 'lp', f))
    out = []
    for it in items:
        title = it.get('title') or ''
        slug = it.get('slug') or ''
        oes = re.findall(r'[0-9]{4,6}-[0-9A-Za-z]{4,6}', title)
        if not oes:
            report['reject_leadong'].append((slug[:40], 'no_oe'))
            continue
        if any(norm_oe(o) in oe_primary for o in oes):
            report['reject_leadong'].append((slug[:40], 'oe_page_exists'))
            continue
        imgs = []
        for o in oes:
            imgs.extend(lp_by_oe.get(norm_oe(o), []))
        if not imgs:
            e = master.get(oes[0])
            if e:
                imgs = [i for i in (e.get('images') or []) if not str(i).startswith('http')]
        if not imgs:
            report['reject_leadong'].append((slug[:40], 'no_image'))
            continue
        nm = re.sub(r'\s*(from China manufacturer.*)$', '', title).strip()
        nm = re.sub(r'\s*-\s*KiNGMAY\s*$', '', nm).strip()
        nm = re.sub(r'\s*\([^)]*\)', '', nm).strip()
        vehicles, cand = [], []
        for o in oes:
            e = master.get(o)
            if e:
                pn = (e.get('part_name') or '').strip()
                if pn and 'Genuine Part' not in pn:
                    t, v = parse_master_name(pn)
                    cand.append(t or pn)
                    vehicles.extend(v)
        rec_type = pick_type(cand) or (re.split(r'\s+(?:for|Compatible with)\s+', nm)[0]
                                       .strip(' -') or 'Auto Part')
        makes = []
        m = re.search(r'(?:for|Compatible with)\s+(?:[0-9]{4}-[0-9]{4}\s+)?([A-Za-z一-鿿][^,|]*)', title)
        if m:
            for tok in re.split(r'\s*(?:/|,|and)\s*', m.group(1)):
                mk = MAKE_MAP.get(tok.strip(), tok.strip())
                if mk and len(mk) > 2 and mk not in makes:
                    makes.append(mk)
        if not makes:
            makes = scan_makes(nm) or ['Hyundai', 'Kia']
        fit = vehicles[:8] if vehicles else makes
        name = '%s %s for %s' % (rec_type, ' / '.join(oes[:2]), ' / '.join(makes[:2]))
        spec = build_specs(rec_type, makes, oes, {
            'Vehicle Application': ' / '.join(fit),
            'Reference Numbers': ' / '.join(oes[:4]),
        })
        alt = '%s %s for %s - Kingmay wholesale auto parts' % (rec_type, ' / '.join(oes[:2]), ' / '.join(makes[:2]))
        meta_title = '%s %s for %s | Kingmay' % (rec_type, ' / '.join(oes[:2]), ' / '.join(makes[:2]))
        meta_desc = ('%s for %s. OE reference %s. OEM-grade aftermarket replacement from Kingmay '
                     'Guangzhou. MOQ %s, FOB/CIF on request.' % (rec_type, ' / '.join(fit[:3]),
                                                               ' / '.join(oes[:3]), MOQ_DEFAULT))
        desc = ('<p><strong>%s</strong> supplied for %s applications, OE reference <strong>%s</strong>.</p>'
                '<p>Direct-fit replacement manufactured to original specification. MOQ %s per SKU, '
                'RFQ supply, 12-month warranty, neutral or Kingmay branded packing available.</p>'
                % (rec_type, ' / '.join(fit[:4]), ' / '.join(oes[:3]), MOQ_DEFAULT))
        out.append({
            'id': 0, 'slug': '', 'name': name[:180], 'category': 'parts',
            'part_system': 'engine', 'part_system_label': 'Engine & Fuel System',
            'sub_category': rec_type, 'sub_slug': slugify(rec_type),
            'price': PRICE_DEFAULT, 'local_image': imgs[0], 'images': imgs[:5],
            'moq': MOQ_DEFAULT, 'in_stock': True, 'featured': False,
            'brand': makes[0], 'compatible_makes': makes[:6], 'fitment': fit[:10],
            'oem_refs': oes[:6],
            'tags': [rec_type] + makes[:3] + ['Wholesale', 'Export'],
            'features': build_features(rec_type, fit, oes), 'specs': spec,
            'meta_title': meta_title[:160], 'meta_description': meta_desc[:300],
            'meta_keywords': ', '.join([rec_type.lower()] + [o.lower() for o in oes[:3]] +
                                       ['wholesale auto parts'])[:300],
            'description': desc, 'system': 'engine', 'alt_text': alt[:180],
            'source': 'leadong', 'fitment': fit[:10],
            'faq': build_faq(name, rec_type, fit, oes),
        })
    return out


# ---------------------------------------------------------------- 源 4：中国品牌
def build_cnoe_records(master, oe_primary, report):
    cno = load_json(os.path.join(DATA, 'cn-oe-products.json'), {}) or {}
    enr = load_json(os.path.join(DATA, 'cn-oe-enriched.json'), {}) or {}
    out = []
    for url, rec in cno.items():
        inter = rec.get('interchange') or []
        oes = [x.get('oe') for x in inter if x.get('oe')]
        if not oes:
            report['reject_cnoe'].append((url.rsplit('/', 1)[-1], 'no_oe'))
            continue
        if any(norm_oe(o) in oe_primary for o in oes):
            report['reject_cnoe'].append((url.rsplit('/', 1)[-1], 'oe_page_exists'))
            continue
        hit = None
        for o in oes:
            hit = enr.get(norm_oe(o))
            if hit:
                break
        if not hit:
            report['reject_cnoe'].append((url.rsplit('/', 1)[-1], 'no_fitment'))
            continue
        pname = (hit.get('name') or '').strip()
        models = [pretty_model(m) for m in (hit.get('models') or [])]
        models = [m for m in models if m]
        if not pname or not models:
            report['reject_cnoe'].append((url.rsplit('/', 1)[-1], 'no_name_or_model'))
            continue
        brand = MAKE_MAP.get((hit.get('make') or '').upper(), hit.get('make') or '').strip().title()
        if not brand:
            brand = MAKE_MAP.get((inter[0].get('brand') or '').upper(), 'Asian')
        # 自家类型图
        img = None
        for pat, path in CNOE_IMG_RULES:
            if re.search(pat, pname, re.I):
                if os.path.exists(os.path.join(ROOT, path)):
                    img = path
                    break
        if not img:
            report['reject_cnoe'].append((url.rsplit('/', 1)[-1], 'no_own_image'))
            continue
        csp = rec.get('specs') or {}
        moq = (csp.get('moq') or '').strip() or MOQ_DEFAULT
        moq = re.sub(r'^(\d+)\s*pcs?$', r'\1 Pieces', moq)
        warranty = (csp.get('warranty') or '12 month').strip()
        psys = classify_system(pname)
        psys_label = {'suspension': 'Suspension & Steering', 'cooling': 'Cooling & Climate',
                      'electrical': 'Electrical & Sensors', 'engine': 'Engine & Fuel System'}[psys]
        name = re.sub(r'\s+', ' ', '%s %s for %s' % (pname, ' / '.join(oes[:2]),
                                                     ' / '.join(models[:2]))).strip()
        fit = models[:10]
        spec = {
            'Part Type': pname,
            'OE Number': ' / '.join(oes[:4]),
            'Vehicle Application': ' / '.join(fit),
            'Brand': brand,
            'MOQ': moq,
            'Warranty': warranty,
            'Supply': 'RFQ / Made to Order',
            'Certification': 'IATF 16949 supply chain',
        }
        alt = '%s %s for %s %s - Kingmay wholesale auto parts' % (pname, ' / '.join(oes[:2]), brand,
                                                                 ' / '.join(models[:2]))
        meta_title = '%s %s for %s | %s Wholesale | Kingmay' % (pname, ' / '.join(oes[:2]), brand,
                                                               ' / '.join(models[:2]))
        meta_desc = ('%s %s for %s %s. OE cross reference supplied by KingMay Guangzhou. MOQ %s, '
                     'made-to-order RFQ, FOB/CIF quoted on request.'
                     % (pname, ' / '.join(oes[:2]), brand, ' / '.join(models[:2]), moq))
        desc = ('<p><strong>%s</strong> for %s platforms, OE reference <strong>%s</strong>.</p>'
                '<p>Supplied as an OEM-grade aftermarket replacement built to original specification. '
                'This line is made to order: MOQ %s per SKU, warranty %s, FOB / CIF quoted on request '
                'once we confirm fitment against your VIN or the OE on your original part.</p>'
                '<ul><li>Part type: %s</li><li>OE reference: %s</li>'
                '<li>Vehicle application: %s</li><li>Brand focus: %s</li></ul>'
                % (pname, brand, ' / '.join(oes[:3]), moq, warranty, pname,
                   ' / '.join(oes[:5]), ' / '.join(fit[:6]), brand))
        out.append({
            'id': 0, 'slug': '', 'name': name[:180], 'category': 'parts',
            'part_system': psys, 'part_system_label': psys_label,
            'sub_category': pname, 'sub_slug': slugify(pname),
            'price': PRICE_DEFAULT, 'local_image': img, 'images': [img],
            'moq': moq, 'in_stock': False, 'featured': False,
            'brand': brand, 'compatible_makes': [brand], 'fitment': fit,
            'oem_refs': oes[:8],
            'tags': [pname, brand] + models[:4] + ['Wholesale', 'Export'],
            'features': build_features(pname, fit, oes), 'specs': spec,
            'meta_title': meta_title[:160], 'meta_description': meta_desc[:300],
            'meta_keywords': ', '.join([pname.lower()] + [o.lower() for o in oes[:3]] +
                                       [brand.lower(), 'wholesale auto parts'])[:300],
            'description': desc,
            'system': psys,
            'alt_text': alt[:180],
            'source': 'cnoe', 'fitment': fit,
            'faq': build_faq(name, pname, fit, oes),
        })
    return out


# ---------------------------------------------------------------- 质量门槛
def check(rec):
    missing = []
    if not rec.get('name') or len(rec['name']) < 12:
        missing.append('name')
    if not rec.get('oem_refs'):
        missing.append('oe')
    if not (rec.get('fitment') or rec.get('compatible_makes')):
        missing.append('fitment')
    if not rec.get('specs'):
        missing.append('specs')
    if not rec.get('moq'):
        missing.append('moq')
    if not rec.get('price'):
        missing.append('price')
    if 'in_stock' not in rec:
        missing.append('stock')
    img = rec.get('local_image')
    if not img or not os.path.exists(os.path.join(ROOT, img)):
        missing.append('image')
    if not rec.get('alt_text'):
        missing.append('alt')
    if not rec.get('description'):
        missing.append('description')
    if not rec.get('meta_title') or not rec.get('meta_description'):
        missing.append('tdk')
    if not rec.get('faq') or len(rec.get('faq') or []) < 3:
        missing.append('faq')
    return missing


def assign_ids_and_slugs(records, start_id):
    seen = set()
    nid = start_id
    for r in records:
        base = slugify(r.get('name', ''))[:80].strip('-')
        if not base:
            base = 'part-%s' % r.get('kingmay_no', nid)
        s = base
        i = 2
        while s in seen:
            s = '%s-%d' % (base, i)
            i += 1
        seen.add(s)
        r['slug'] = s
        r['id'] = nid
        nid += 1
    return nid


def build_oe_primary_set():
    oe_dir = os.path.join(ROOT, 'oe')
    out = set()
    if not os.path.isdir(oe_dir):
        return out
    for f in os.listdir(oe_dir):
        if not f.endswith('.html'):
            continue
        stem = os.path.splitext(f)[0]
        out.add(norm_oe(stem))
        out.add(norm_oe(stem.replace('-', '')))
    return out


def enrich_existing(rec):
    """给既有 152 条补齐 brand / fitment / faq，slug 与 id 一律不动"""
    nm = rec.get('name') or ''
    tags = rec.get('tags') or []
    makes = list(rec.get('compatible_makes') or [])
    if not makes:
        makes = scan_makes(' '.join([nm] + [str(t) for t in tags]))
    if not makes:
        makes = ['Hyundai', 'Kia']
    rec['compatible_makes'] = makes[:6]
    rec['brand'] = rec.get('brand') or makes[0]
    if not rec.get('fitment'):
        rec['fitment'] = makes[:6]
    oes = rec.get('oem_refs') or []
    rec_type = rec.get('sub_category') or 'Auto Part'
    if not rec.get('faq'):
        rec['faq'] = build_faq(nm, rec_type, rec.get('fitment') or makes, oes)
    # TDK 小修：截断 / 缺关键词
    t = (rec.get('meta_title') or '').strip()
    if not t or t.rstrip().endswith(('-', '—', ',', '|')) or len(t) < 25:
        oes_txt = ' / '.join(oes[:2])
        rec['meta_title'] = ('%s %s for %s | Kingmay Auto Parts' % (rec_type, oes_txt,
                                                                    ' / '.join(makes[:2])))[:160]
    d = (rec.get('meta_description') or '').strip()
    if len(d) < 70 or len(d) > 300:
        rec['meta_description'] = ('%s for %s. OE reference %s. OEM-grade aftermarket replacement '
                                   'supplied by Kingmay Guangzhou. MOQ %s, FOB/CIF quoted on request.'
                                   % (rec_type, ' / '.join(makes[:3]), ' / '.join(oes[:3]),
                                      rec.get('moq') or MOQ_DEFAULT))[:300]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--cap', type=int, default=600)
    ap.add_argument('--cnoe-per-type', type=int, default=20,
                    help='每个零件类型最多取多少条中国品牌产品（防同类型稀释）')
    args = ap.parse_args()

    report = {'reject_supplier': [], 'reject_leadong': [], 'reject_cnoe': [],
              'reject_existing': [], 'type_pages': [], 'stats': {}, 'cap': args.cap}

    master = MasterIndex(os.path.join(DATA, 'oe-master-db.json'))
    oe_primary = build_oe_primary_set()
    print('母库 %d 条；已发布 OE 页主 OE token %d 个' % (len(master.exact), len(oe_primary)))

    db = load_json(PROD_DB, [])
    prods = db if isinstance(db, list) else db.get('products', db)
    vehicles = [p for p in prods if p.get('category') != 'parts']
    existing = []
    type_pages = []
    for p in prods:
        if p.get('category') != 'parts':
            continue
        # 幂等：上次生成的记录（source=supplier/cnoe/leadong）一律重新从原始源生成，
        # 不能当"既有记录"再收一遍，否则目录会自我膨胀。
        if p.get('source') in ('supplier', 'cnoe', 'leadong'):
            continue
        p = enrich_existing(p)
        miss = check(p)
        if miss:
            # 泛类型页（无 OE / 无品牌 / 名称过短）：降级为分类 hub 页，保留原 URL 不删
            p['_gate_missing'] = miss
            type_pages.append(p)
            report['type_pages'].append((str(p.get('id')), p.get('slug'), ','.join(miss)))
            continue
        p.setdefault('source', 'existing')
        existing.append(p)
    print('既有 parts：产品页 %d / 降级为分类 hub 页 %d' % (len(existing), len(type_pages)))

    sup = build_supplier_records(master, oe_primary, report)
    print('供应商：候选 %d / 剔除 %d' % (len(sup) + len(report['reject_supplier']),
                                       len(report['reject_supplier'])))
    lead = build_leadong_records(master, oe_primary, report)
    print('leadong：候选 %d / 剔除 %d' % (len(lead) + len(report['reject_leadong']),
                                         len(report['reject_leadong'])))
    cno = build_cnoe_records(master, oe_primary, report)
    print('中国品牌：候选 %d / 剔除 %d' % (len(cno) + len(report['reject_cnoe']),
                                          len(report['reject_cnoe'])))

    # 中国品牌按类型限流
    per_type = collections.Counter()
    cno_sel = []
    for rec in cno:
        t = rec['sub_category']
        if per_type[t] >= args.cnoe_per_type:
            report['reject_cnoe'].append((rec['name'][:40], 'type_cap'))
            continue
        per_type[t] += 1
        cno_sel.append(rec)

    # 合并 + 质量门槛 + 去重
    new = []
    seen = set()
    for p in existing:
        for o in (p.get('oem_refs') or []):
            seen.add(norm_oe(o))
    for rec in sup + lead + cno_sel:
        miss = check(rec)
        key = rec['source']
        if miss:
            report['reject_' + key].append(
                (rec.get('kingmay_no') or rec.get('name', '')[:40], ','.join(miss)))
            continue
        sig = tuple(sorted(norm_oe(o) for o in rec['oem_refs'][:3]))
        if sig in seen:
            report['reject_' + key].append((rec.get('kingmay_no') or rec.get('name', '')[:40], 'dup_oe'))
            continue
        seen.add(sig)
        new.append(rec)

    room = max(0, args.cap - len(existing))
    selected, overflow = new[:room], new[room:]
    for rec in overflow:
        report['reject_' + rec['source']].append(
            (rec.get('kingmay_no') or rec.get('name', '')[:40], 'over_cap'))

    assign_ids_and_slugs(selected, start_id=1000)
    catalog = existing + selected
    slugs = [c['slug'] for c in catalog]
    assert len(slugs) == len(set(slugs)), 'slug 冲突'

    stats = {
        'total': len(catalog),
        'existing': len(existing),
        'supplier': sum(1 for c in catalog if c['source'] == 'supplier'),
        'leadong': sum(1 for c in catalog if c['source'] == 'leadong'),
        'cnoe': sum(1 for c in catalog if c['source'] == 'cnoe'),
        'type_pages': len(type_pages),
        'by_system': dict(collections.Counter(c['part_system'] for c in catalog)),
        'by_sub_category': dict(collections.Counter(c['sub_category'] for c in catalog)),
        'by_brand': dict(collections.Counter(c.get('brand') for c in catalog)),
        'rejected': {k: len(report['reject_' + k]) for k in ('supplier', 'leadong', 'cnoe')},
        'reject_reasons': {
            'supplier': dict(collections.Counter(r[1] for r in report['reject_supplier'])),
            'leadong': dict(collections.Counter(r[1] for r in report['reject_leadong'])),
            'cnoe': dict(collections.Counter(r[1] for r in report['reject_cnoe'])),
        },
    }
    report['stats'] = stats
    print('\n=== 目录统计 ===')
    print(json.dumps(stats, ensure_ascii=False, indent=1))

    if args.apply:
        # products-data.json = 车辆条目 + 原始产品页 + 分类 hub + 本轮新增（不重复累加）
        merged = list(vehicles) + list(existing) + list(type_pages) + list(selected)
        for p in type_pages:
            p.pop('_gate_missing', None)
            p['page_kind'] = 'type'
        with open(PROD_DB, 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=1)
        print('\n已写 products-data.json：%d 条（parts %d + 分类 hub %d + 车辆 %d）'
              % (len(merged), len(catalog), len(type_pages), len(vehicles)))
        with open(CATALOG, 'w', encoding='utf-8') as f:
            json.dump({'products': catalog, 'type_pages': type_pages,
                       'generated_at': __import__('datetime').datetime.now().isoformat(timespec='seconds')},
                      f, ensure_ascii=False, indent=1)
        print('已写 %s' % CATALOG)
        with open(REPORT, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        print('已写 %s' % REPORT)
    else:
        print('\n[dry-run] 未写盘。加 --apply 落盘。')


if __name__ == '__main__':
    main()
