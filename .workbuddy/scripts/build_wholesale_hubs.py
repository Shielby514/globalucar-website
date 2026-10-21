# -*- coding: utf-8 -*-
"""wholesale 聚合页生成器 —— 内容由主站 OE 库真实数据驱动。

数据源: <wholesale>/_data/main-oe-index.json（由 build_main_oe_index.py 产出）
输出:   <wholesale>/wholesale-<brand>-parts/index.html
        <wholesale>/wholesale-<cat>-parts/index.html
        <wholesale>/_data/wholesale-hubs.json（供主站反链注入）

设计原则（避免 thin content 与与主站内耗）：
  1. 只做「批发意图」聚合页，绝不复制主站 OE 详情页
  2. 每页含真实 OE 清单（60-90 条，按品类均匀取样）+ 品类专属文案
  3. 外链指向主站 /oe/<file>（权重下灌给详情页）
  4. 每页 unique：品牌/品类知识库文案 + 真实件号 + 定制 FAQ

用法:
  python build_wholesale_hubs.py            # 全量重建
  python build_wholesale_hubs.py --limit 4  # 试跑
"""
import os, re, sys, json, time, random, html, collections

WS = r'C:\Users\123\WorkBuddy\wholesale-portal'
DATA = os.path.join(WS, '_data', 'main-oe-index.json')
OUT_JSON = os.path.join(WS, '_data', 'wholesale-hubs.json')
MAIN = 'https://www.global-ucars.com'
QIN = 'https://www.qinparts.com'
SITE = 'https://wholesale.global-ucars.com'

# ---------- 品牌知识库（每品牌独立文案，保证 uniqueness） ----------
BRAND_INFO = {
    'Hyundai': dict(
        disp='Hyundai', slug='hyundai',
        lead='Hyundai and Kia share the majority of their powertrain and chassis architecture, which is why a single container of Hyundai parts usually covers Kia applications at the same time.',
        body='The highest-volume items we ship for Hyundai are suspension and steering wear parts — control arms, ball joints, stabilizer links and shock absorbers — followed by engine timing components and cooling system parts. Tucson, Elantra, Accent, Santa Fe and Sonata make up most of the demand we see from Africa and the Middle East, with i10 and Creta volumes growing fast in Latin America.',
        tip='For Tucson and Santa Fe, always confirm whether the vehicle is a diesel or petrol variant before ordering engine parts — the 2.0 CRDi and 2.4 GDI share almost nothing downstream of the head.',
        markets='Strongest demand: Nigeria, Ghana, Saudi Arabia, UAE, Chile, Peru.'),
    'Kia': dict(
        disp='Kia', slug='kia',
        lead='Kia parts are interchangeable with Hyundai across most mechanical systems, so buyers consolidating both brands into one container get better freight rates per unit.',
        body='Sportage, Rio, Cerato and Sorento dominate Kia parts demand. Rio and Cerato volumes come mostly from fleet operators and taxi companies, which means brake pads, discs, filters and suspension arms turn over fastest. Sorento and Sportage demand skews toward suspension bushings, wheel bearings and cooling parts.',
        tip='Kia OE numbers with an 0K or 0K9 prefix are older-format numbers. Our catalogue carries both the old and the superseded number, so send whichever is on your customer invoice.',
        markets='Strongest demand: Poland, Romania, Nigeria, Kenya, UAE, Iraq.'),
    'Mercedes': dict(
        disp='Mercedes-Benz', slug='mercedes',
        lead='Mercedes parts demand is less about volume and more about margin — a single container of W204 and W211 service parts can cover a full year of a specialist workshop ordering.',
        body='The bulk of our Mercedes shipments are service and wear parts for the C-Class (W203/W204), E-Class (W210/W211/W212) and Sprinter van platform. Air suspension components, brake discs and sensors are the highest-value lines. Sprinter parts are a separate, very steady business for commercial fleet operators.',
        tip='Mercedes OE numbers are often replaced by an A-number (e.g. A 000 180 26 09). We cross-reference both formats, so the A-prefix number from a dealer invoice is enough for us to quote.',
        markets='Strongest demand: Germany, Poland, Lithuania, Nigeria, UAE, Kazakhstan.'),
    'BMW': dict(
        disp='BMW', slug='bmw',
        lead='BMW parts move in two distinct streams: high-turnover service items for the E90 and E60 platform, and slower, higher-margin cooling and suspension assemblies.',
        body='The E46, E90 and E60 platforms generate the most enquiries in our export markets because these vehicles are now in the independent-workshop stage of life. Cooling system parts — radiators, expansion tanks, water pumps, thermostats — are the single most frequent BMW spare part order we handle. Suspension control arms and bushings follow closely.',
        tip='BMW revised its cooling system several times within the same chassis code. Always give us the last 7 digits of the VIN and we will match the exact radiator and hose routing for that production date.',
        markets='Strongest demand: Germany, Poland, UK, Nigeria, Georgia, Chile.'),
    'Audi': dict(
        disp='Audi', slug='audi',
        lead='Audi shares platforms and part numbers with Volkswagen and Skoda, so most Audi containers also carry VW-group applications and vice versa.',
        body='A4 (B6/B7/B8), A6 (C5/C6) and A3 (8P) dominate our Audi shipments. Timing chain and tensioner assemblies, suspension control arm kits, and brake components are the volume lines. Quattro drivetrain parts move more slowly but at much higher unit value.',
        tip='Audi timing chain jobs should always be quoted as a complete kit — chain, tensioner, guides and sprockets. Partial kits arrive and fail within 20,000 km, which is the main warranty claim we see.',
        markets='Strongest demand: Germany, Poland, Czechia, Russia, Kazakhstan, UAE.'),
    'Volkswagen': dict(
        disp='Volkswagen', slug='volkswagen',
        lead='Volkswagen is the single widest-fitting brand we handle — a VW parts container almost always also covers Skoda, Seat and Audi applications on the same platform.',
        body='Golf IV, Golf V, Passat B5/B6, Polo and Jetta generate the most volume. These vehicles are everywhere in Eastern Europe, Russia and Latin America, so brake parts, suspension, timing belts and cooling components move continuously. The Amarok pickup is a smaller but very profitable line in Africa and Australia.',
        tip='Passat B5 and B6 share the name but almost nothing under the skin. Confirm the VIN before ordering control arms or engine mounts — the two platforms are the most commonly misordered VW parts we see.',
        markets='Strongest demand: Russia, Kazakhstan, Poland, Brazil, Mexico, Algeria.'),
    'Toyota': dict(
        disp='Toyota', slug='toyota',
        lead='Toyota parts are the safest stock a distributor can carry — Hilux, Land Cruiser and Corolla service parts sell in every market we ship to without exception.',
        body='Hilux and Land Cruiser parts are the backbone of our Toyota business in Africa and the Middle East. Corolla, Camry and RAV4 volumes come from fleet and taxi operators. Brake pads, filters, suspension bushes, ball joints and radiator assemblies are the fastest-moving items, followed by timing chain kits for the diesel engines.',
        tip='Hilux rear brake and suspension parts differ between the 2WD and 4WD versions and between pre- and post-2005 chassis. Always state the drive configuration when you send a Hilux parts list.',
        markets='Strongest demand: Nigeria, Kenya, Tanzania, UAE, Saudi Arabia, South Africa.'),
    'Nissan': dict(
        disp='Nissan', slug='nissan',
        lead='Nissan demand clusters around the pickup and SUV platforms, which means fewer part numbers per container but larger quantities per part number.',
        body='Navara, Patrol, X-Trail and Qashqai generate most of our Nissan enquiries. Navara and Patrol parts dominate in the Middle East and Africa where these vehicles work as commercial and government fleet vehicles. X-Trail and Qashqai volumes come from Eastern Europe and are concentrated in suspension and brake components.',
        tip='Patrol Y61 and Y62 share the model name but not the chassis. Suspension and steering parts for these two are never interchangeable — check the VIN before ordering.',
        markets='Strongest demand: UAE, Saudi Arabia, Nigeria, Poland, Libya, Chile.'),
}

# ---------- 品类知识库 ----------
CAT_INFO = {
    'brake': dict(disp='Brake', slug='brake',
                  lead='Brake parts are the highest-turnover line for any auto parts distributor, and the one where quality complaints cost the most. We supply ceramic, semi-metallic and low-metallic formulations and will quote all three on request.',
                  body='A working brake container usually mixes pads, discs, brake shoes and hydraulic components. Pads and discs are bought together; calipers, master cylinders and wheel cylinders are replacement items that move more slowly but at far higher unit value. We stock both economy-grade and OEM-equivalent grades and will not ship a grade you did not ask for.',
                  tip='Brake pads are graded by friction coefficient (FF, FG, GG). For hot-climate and mountainous markets, quote the GG grade — economy pads glaze and squeal within months in those conditions.'),
    'suspension': dict(disp='Suspension', slug='suspension',
                       lead='Suspension and steering wear parts are where road conditions translate directly into turnover. On rough roads, a control arm that lasts 80,000 km in Europe lasts 30,000 km.',
                       body='Control arms, ball joints, tie rod ends, stabilizer links, bushings and shock absorbers are the volume lines. We supply complete control arm kits with bushings and ball joints pre-fitted, which saves your workshop labour time and removes the risk of a mismatched bushing. Wheel hub bearing assemblies are a separate high-value line with steady demand.',
                       tip='Always order control arms in axle pairs. Fitting one side only is the single most common cause of a premature failure on the other side, and it is the most common warranty complaint in this category.'),
    'engine': dict(disp='Engine', slug='engine',
                   lead='Engine parts are the most technical category we handle and the one where a wrong number costs the most, because the labour to discover the error exceeds the part value many times over.',
                   body='Timing chains and belts, tensioners, gasket sets, water and oil pumps, pistons, crankshafts and cylinder head assemblies make up most of our engine parts shipments. Timing components should always ship as complete kits — a chain without its tensioner and guides will fail early and take the engine with it.',
                   tip='Timing chain jobs must be quoted as complete kits including guides, tensioner and sprockets. We will not split a timing kit, and neither should you — partial kits are the number one cause of engine warranty claims.'),
    'cooling': dict(disp='Cooling', slug='cooling',
                    lead='Cooling system parts are climate-sensitive: the same radiator that lasts a decade in Northern Europe fails in three years in the Gulf or West Africa.',
                    body='Radiators, condensers, evaporators, thermostats, water pumps, expansion tanks and cooling fans make up this category. Radiators for hot-climate markets should be specified with increased core thickness, which we can supply on request for container quantities. Air conditioning condensers and evaporators are a growing line as more markets demand working A/C as standard.',
                    tip='For Gulf, West African and Central Asian markets, order the heavy-duty core radiator. Standard cores are the most returned cooling part in those regions and the margin difference is small.'),
    'electrical': dict(disp='Electrical', slug='electrical',
                       lead='Electrical parts are the highest-return-rate category in the industry, which is why we bench-test every alternator and starter we ship and serialise each unit.',
                       body='Alternators, starters, ignition coils, sensors, switches, window regulators and lighting assemblies are the volume lines. Sensors in particular — oxygen sensors, MAF sensors, crankshaft position sensors, ABS wheel speed sensors — are high-turnover and individually packaged items that suit mixed containers well.',
                       tip='Electrical parts are non-returnable once fitted. Confirm the OE number and the VIN before ordering, and expect to keep a small buffer stock of sensors rather than ordering per job.'),
    'filters': dict(disp='Filters', slug='filters',
                    lead='Filters are the classic mixed-container filler: low unit value, high volume, and the item customers come back for most often.',
                    body='Oil filters, air filters, cabin (pollen) filters and fuel filters. Most distributors buy filters in mixed pallets covering 20 to 40 part numbers rather than in full cartons of one number. We can assemble a mixed filter pallet to your exact list and label each carton with your own part number and barcode.',
                    tip='Cabin filters have become a fast-moving item in markets with high dust and pollen loads. Include them in your opening order — they are cheap to ship and they are what brings a retail customer back.'),
    'transmission': dict(disp='Transmission', slug='transmission',
                         lead='Transmission and drivetrain parts are lower-volume but higher-value, and they are the category where getting the exact specification right matters most.',
                         body='Clutch kits, clutch discs and pressure plates, release bearings, CV joints, drive shafts, axles and gearbox mounts. Clutch kits should always be ordered complete — disc, pressure plate and release bearing — because partial replacement causes a comeback within months.',
                         tip='Clutch kits must be supplied complete with the release bearing. This is the most common specification error in this category and the most expensive one to put right.'),
    'steering': dict(disp='Steering', slug='steering',
                     lead='Steering parts are safety-critical and road-condition-sensitive, which makes them one of the most consistently reordering categories in a distributor catalogue.',
                     body='Steering racks, power steering pumps, tie rod ends, drag links, steering columns and clock springs. Tie rod ends and rack ends are the volume items; complete steering racks are slower-moving but high-value. We supply both new and remanufactured racks for selected applications.',
                     tip='After any steering component replacement, a wheel alignment is mandatory. Remind your workshop customers of this — it prevents the comeback that would otherwise be blamed on the part.'),
    'body': dict(disp='Body', slug='body',
                 lead='Body parts are the most shipping-space-intensive category, which is why they are usually consolidated into a container that already carries smaller mechanical parts.',
                 body='Bumpers, fenders, doors, bonnets, tailgates, grilles, mirrors, headlight and tail light assemblies. Body parts are bulky and their freight cost per unit is high, so most buyers consolidate them with smaller, denser parts to fill the same container.',
                 tip='Body panels ship best when consolidated with dense mechanical parts. A container of panels alone wastes most of its volume allowance on air.'),
    'fuel': dict(disp='Fuel', slug='fuel',
                 lead='Fuel system parts are precision items where the difference between a working part and a failed one is measured in microns.',
                 body='Fuel pumps, injectors, fuel filters, fuel rails, fuel tank caps and sender units. Diesel injectors and high-pressure fuel pumps are the highest-value items and the most specification-sensitive — common-rail components must be matched to the exact engine code.',
                 tip='Common-rail injectors are coded to the engine. Order by VIN, not by model year, and never substitute a "similar" injector — the flow rate difference will damage the engine.'),
}

TRADE = [
    ('MOQ', 'No minimum quantity per part number. Mixed containers across brands and categories are our normal working method.'),
    ('Packaging', 'Neutral white/brown boxes, Globalucar brand, or your own logo and barcode. Retail-ready labelling available.'),
    ('Lead time', 'Stock items ship within 7-12 days. Made-to-order or consolidated containers 25-35 days to FOB Nansha.'),
    ('Incoterms', 'FOB Nansha / Guangzhou, CIF to your port, or EXW for your own forwarder.'),
    ('Quality', 'Photo and video inspection of every SKU before loading. SGS or TUV certificates available on request.'),
    ('Payment', 'T/T 30% deposit, balance before shipment. L/C at sight for container orders above USD 20,000.'),
]

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;color:#1f2937;line-height:1.65;background:#fff}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
header{background:#0c2d50;color:#fff;padding:14px 0;position:sticky;top:0;z-index:10}
header .wrap{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
.logo{font-size:18px;font-weight:700;letter-spacing:.5px}
.logo span{color:#f5a623}
nav a{color:#cfe3f5;text-decoration:none;font-size:14px;margin-left:18px}
nav a:hover{color:#fff}
.hero{background:linear-gradient(160deg,#0c2d50 0%,#123a66 100%);color:#fff;padding:44px 0 48px}
.hero h1{font-size:30px;font-weight:800;line-height:1.28;max-width:900px}
.hero p{font-size:16px;color:#c9d9ec;max-width:760px;margin-top:14px}
.btns{display:flex;gap:12px;flex-wrap:wrap;margin-top:24px}
.btn{display:inline-block;padding:13px 26px;border-radius:8px;font-size:15px;font-weight:700;text-decoration:none}
.btn-wa{background:#25d366;color:#fff}
.btn-mail{background:#f5a623;color:#0c2d50}
section{padding:44px 0}
h2{font-size:24px;font-weight:800;color:#0c2d50;margin-bottom:6px}
h3{font-size:17px;color:#0c2d50;margin-bottom:6px}
.lead{font-size:16px;color:#374151;margin-bottom:14px}
p{font-size:15px;color:#4b5563;margin-bottom:12px}
.tblwrap{overflow-x:auto;border:1px solid #e5e7eb;border-radius:10px;margin-top:16px}
table{width:100%;border-collapse:collapse;font-size:14px}
th{background:#0c2d50;color:#fff;text-align:left;padding:11px 14px;font-weight:600;white-space:nowrap}
td{padding:9px 14px;border-top:1px solid #e5e7eb}
tr:nth-child(even) td{background:#f8fafc}
td a{color:#0c2d50;font-weight:600;text-decoration:none}
td a:hover{text-decoration:underline}
.oe{font-family:ui-monospace,Consolas,monospace;font-size:13px;white-space:nowrap}
.card{background:#f8fafc;border:1px solid #e5e7eb;border-radius:10px;padding:20px}
.tip{background:#fff8e6;border-left:4px solid #f5a623;padding:14px 18px;border-radius:6px;font-size:14.5px;color:#374151;margin:18px 0}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.chip{display:inline-block;padding:7px 14px;border:1px solid #d1d5db;border-radius:20px;font-size:13.5px;color:#0c2d50;text-decoration:none;background:#fff}
.chip:hover{border-color:#0c2d50;background:#f8fafc}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-top:14px}
dl.faq dt{font-weight:700;color:#0c2d50;font-size:15px;margin-top:16px}
dl.faq dd{font-size:14.5px;color:#4b5563;margin-top:4px}
footer{background:#0c2d50;color:#9fb8d4;padding:26px 0;font-size:13px}
footer a{color:#cfe3f5}
footer .wrap{text-align:center}
@media(max-width:640px){.hero h1{font-size:23px}}
"""


def esc(s):
    return html.escape(s or '', quote=True)


def wa_link(label):
    return ('https://wa.me/8613302408528?text=' +
            __import__('urllib.parse', fromlist=['quote']).quote(label))


def page(p, slug=''):
    is_brand = 'brand' in p
    info = p['brand'] if is_brand else p['cat']
    slug = slug or p['slug']
    disp = info['disp']
    items = p['items']
    n = p['count']

    if is_brand:
        title = f"Wholesale {disp} Parts — {n:,} OE Numbers in Stock | Globalucar Wholesale"
        h1 = f"Wholesale {disp} Parts — {n:,} OE Numbers, Consolidated from Guangzhou"
        lead = info['lead']
        body = info['body']
        tip = info['tip']
        markets = info.get('markets', '')
        desc = (f"Wholesale {disp} auto parts: {n:,} OE numbers in stock. "
                f"Mixed-brand container loading from Guangzhou, MOQ-free, quote in 24 hours. "
                f"{markets}")
        catline = 'Popular ' + disp + ' part groups'
    else:
        title = f"Wholesale {disp} Parts — {n:,} OE Numbers Across Multiple Brands | Globalucar Wholesale"
        h1 = f"Wholesale {disp} Parts — {n:,} OE Numbers, Mixed-Brand Container Loading"
        lead = info['lead']
        body = info['body']
        tip = info['tip']
        markets = ''
        desc = (f"Wholesale {disp.lower()} auto parts: {n:,} OE numbers across Hyundai, Kia, "
                f"Mercedes, BMW, Audi, VW and Toyota. MOQ-free, FOB Nansha, quote in 24h.")
        catline = disp + ' parts by vehicle brand'

    # 顶部交叉 chips
    chips = p['chips']
    chiphtml = ''.join(f'<a class="chip" href="{SITE}/{c[0]}/">{esc(c[1])}</a>' for c in chips)

    rows = ''.join(
        f'<tr><td class="oe"><a href="{MAIN}/oe/{esc(it["file"])}" rel="noopener">{esc(it["oe"])}</a></td>'
        f'<td><a href="{MAIN}/oe/{esc(it["file"])}" rel="noopener">{esc(it["name"])}</a></td>'
        f'<td>{esc(it["brandlabel"])}</td></tr>'
        for it in items)

    faq = p['faq']
    faqhtml = ''.join(f'<dt>{esc(q)}</dt><dd>{esc(a)}</dd>' for q, a in faq)

    tradehtml = ''.join(f'<div class="card"><h3>{esc(k)}</h3><p>{esc(v)}</p></div>'
                        for k, v in TRADE)
    rfqt = f"Wholesale RFQ - {disp} parts"
    wahref = 'https://wa.me/8613302408528?text=' + __import__('urllib.parse', fromlist=['quote']).quote(
        f"Hello Globalucar, I need a wholesale quotation for {disp} auto parts.")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}/{slug}/">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{SITE}/{slug}/">
<meta property="og:type" content="website">
<style>{CSS}</style>
</head>
<body>
<header>
  <div class="wrap">
    <div class="logo">Globalucar <span>Wholesale</span></div>
    <nav>
      <a href="#list">Part list</a>
      <a href="#trade">Trade terms</a>
      <a href="{SITE}/">Wholesale home</a>
      <a href="{MAIN}" rel="noopener">OE Library &rarr;</a>
    </nav>
  </div>
</header>

<div class="hero">
  <div class="wrap">
    <h1>{esc(h1)}</h1>
    <p>{esc(lead)}</p>
    <div class="btns">
      <a class="btn btn-wa" href="{esc(wahref)}" target="_blank" rel="noopener">WhatsApp RFQ for {esc(disp)} parts</a>
      <a class="btn btn-mail" href="mailto:ucars@global-ucars.com?subject=Wholesale%20RFQ%20-%20{esc(disp.replace(' ', '%20'))}">Email RFQ</a>
    </div>
  </div>
</div>

<section>
  <div class="wrap">
    <h2>What we stock for this range</h2>
    <p class="lead">{esc(body)}</p>
    {('<p>' + esc(markets) + '</p>') if markets else ''}
    <div class="tip"><b>Buying note:</b> {esc(tip)}</div>
    <h3>{esc(catline)}</h3>
    <div class="chips">{chiphtml}</div>
  </div>
</section>

<section id="list" style="background:#f8fafc">
  <div class="wrap">
    <h2>{esc(disp)} OE numbers we can quote</h2>
    <p>{len(items)} part numbers from our live catalogue. Each number links to its full specification page in our OE library. Send any of these numbers — or your own list — and we will quote the whole sheet at once.</p>
    <div class="tblwrap">
      <table>
        <thead><tr><th>OE number</th><th>Part name</th><th>Application</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <p style="margin-top:14px">This is a selection from {n:,} available {esc(disp)} OE numbers. Our catalogue grows every week — if the number you need is not listed, ask us directly.</p>
  </div>
</section>

<section id="trade">
  <div class="wrap">
    <h2>Trade terms for {esc(disp)} parts</h2>
    <div class="grid2">{tradehtml}</div>
  </div>
</section>

<section style="background:#f8fafc">
  <div class="wrap">
    <h2>Common questions</h2>
    <dl class="faq">{faqhtml}</dl>
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Send your {esc(disp)} parts list</h2>
    <p>We accept OE numbers, VINs, photos or a handwritten list. You receive one consolidated quote within 24 hours, with availability, tiered pricing and lead time on a single sheet.</p>
    <div class="btns">
      <a class="btn btn-wa" href="{esc(wahref)}" target="_blank" rel="noopener">WhatsApp your list</a>
      <a class="btn btn-mail" href="mailto:ucars@global-ucars.com?subject=Wholesale%20RFQ%20-%20{esc(disp.replace(' ', '%20'))}">Email your list</a>
    </div>
  </div>
</section>

<footer>
  <div class="wrap">
    <p><strong>Guangzhou Vehicle External Trade Co., Ltd</strong> — licensed vehicle &amp; auto parts exporter</p>
    <p>WhatsApp: +86 133-0240-8528 | Email: ucars@global-ucars.com | Guangzhou, Guangdong, China</p>
    <p><a href="{SITE}/">Wholesale home</a> | <a href="{MAIN}" rel="noopener">Full OE library</a></p>
  </div>
</footer>
</body>
</html>
"""


def pick_brand(recs, brand, limit=60):
    """从该品牌下按品类均匀取样，保证清单多样性。"""
    own = [r for r in recs if brand in r['brands']]
    bycat = collections.defaultdict(list)
    for r in own:
        bycat[r['cat'] or 'other'].append(r)
    for c in bycat:
        random.shuffle(bycat[c])
    cats = sorted(bycat, key=lambda c: -len(bycat[c]))
    # 交替取，保证每品类都出现
    out, i = [], 0
    while len(out) < limit and any(bycat[c] for c in cats):
        for c in cats:
            if bycat[c] and len(out) < limit:
                out.append(bycat[c].pop())
        i += 1
        if i > 40:
            break
    return out


def pick_cat(recs, cat, limit=60):
    own = [r for r in recs if r['cat'] == cat]
    bybrand = collections.defaultdict(list)
    for r in own:
        b = r['brands'][0] if r['brands'] else 'Other'
        bybrand[b].append(r)
    for b in bybrand:
        random.shuffle(bybrand[b])
    brands = sorted(bybrand, key=lambda b: -len(bybrand[b]))
    out, i = [], 0
    while len(out) < limit and any(bybrand[b] for b in brands):
        for b in brands:
            if bybrand[b] and len(out) < limit:
                out.append(bybrand[b].pop())
        i += 1
        if i > 40:
            break
    return out


def main():
    limit = None
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    random.seed(20261021)

    if not os.path.exists(DATA):
        print(f'缺少索引 {DATA}，请先跑 build_main_oe_index.py')
        return 1
    idx = json.load(open(DATA, encoding='utf-8'))
    recs = idx['items']
    print(f'索引载入 {len(recs)} 条（更新于 {idx["updated_at"]}）')

    # ---- 品牌页 ----
    bcounts = idx['brands']
    brands = []
    for key, info in BRAND_INFO.items():
        cnt = bcounts.get(key, 0)
        if cnt < 80:
            print(f'  跳过 {key}：仅 {cnt} 条，不足以单独成页')
            continue
        sel = pick_brand(recs, key, 60)
        for it in sel:
            it = dict(it)
        items = []
        for it in sel:
            items.append({'oe': it['oe'], 'name': it['name'],
                          'file': it['file'],
                          'brandlabel': ' / '.join(it['brands']) if it['brands'] else '-'})
        # chips: 该品牌下的品类页
        bc = collections.Counter(r['cat'] for r in recs if key in r['brands'] and r['cat'])
        chips = [(f'wholesale-{CAT_INFO[c]["slug"]}-parts',
                  f'{CAT_INFO[c]["disp"]} ({v:,})')
                 for c, v in bc.most_common(6)]
        faq = [
            (f'What is the minimum order for {info["disp"]} parts?',
             'There is no minimum quantity per part number. You can order a single unit or consolidate hundreds of numbers into one container — the container is what fixes the freight cost, not the part count.'),
            (f'Can I mix {info["disp"]} parts with other brands in one container?',
             'Yes, and most buyers do. Mixed-brand and mixed-category loading is our standard working method and it is what keeps your landed cost per unit down.'),
            (f'How do you confirm {info["disp"]} parts fitment?',
             'We cross-check every OE number against fitment data before quoting. If you send a VIN instead of a part number, we decode it and return the correct OE numbers for you.'),
            (f'How long does a {info["disp"]} parts order take?',
             'Stock items leave within 7-12 days. A consolidated container is typically 25-35 days to FOB Nansha, plus transit to your port.'),
            ('Can you put my own brand on the packaging?',
             'Yes. Neutral, Globalucar or your own logo and barcode, with retail-ready labels if you need them.'),
        ]
        brands.append({'slug': f"wholesale-{info['slug']}-parts", 'brand': info,
                       'items': items, 'count': cnt, 'chips': chips, 'faq': faq})

    # ---- 品类页 ----
    ccounts = idx['cats']
    cats = []
    for key, info in CAT_INFO.items():
        cnt = ccounts.get(key, 0)
        if cnt < 80:
            print(f'  跳过品类 {key}：仅 {cnt} 条')
            continue
        sel = pick_cat(recs, key, 60)
        items = [{'oe': r['oe'], 'name': r['name'], 'file': r['file'],
                  'brandlabel': ' / '.join(r['brands']) if r['brands'] else '-'} for r in sel]
        bb = collections.Counter(b for r in recs if r['cat'] == key for b in r['brands'])
        chips = [(f'wholesale-{BRAND_INFO[b]["slug"]}-parts', f'{BRAND_INFO[b]["disp"]} ({v:,})')
                 for b, v in bb.most_common(6) if b in BRAND_INFO]
        kw = info['disp'].lower()
        faq = [
            (f'What is the minimum order quantity for {kw} parts?',
             'No minimum per part number. Most buyers build a mixed list of 40-100 numbers instead of a large quantity of a single number.'),
            (f'Which brands do you cover for {kw} parts?',
             f'Hyundai, Kia, Mercedes-Benz, BMW, Audi, Volkswagen and Toyota are the deepest, and we add new applications to the catalogue every week.'),
            (f'Do you supply OEM-grade {kw} parts or aftermarket?',
             'Both. We quote OEM-equivalent and economy grades separately so you can choose the price point that fits your market — we never substitute a grade you did not order.'),
            (f'What is the lead time for {kw} parts?',
             'Stock items ship in 7-12 days. Consolidated containers take 25-35 days to FOB Nansha plus transit.'),
            (f'Can {kw} parts be consolidated with other categories?',
             'Yes. Consolidation across categories is how most of our containers are built and it is the main reason buyers use us rather than several separate suppliers.'),
        ]
        cats.append({'slug': f"wholesale-{info['slug']}-parts", 'cat': info,
                     'items': items, 'count': cnt, 'chips': chips, 'faq': faq})

    made = []
    for p in (brands + cats):
        if limit and len(made) >= limit:
            break
        d = os.path.join(WS, p['slug'])
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8', newline='').write(page(p))
        made.append(p)
        print(f"  OK {p['slug']:38s} 清单 {len(p['items']):3d} 条 / 库存 {p['count']:,}")

    json.dump({'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
               'pages': [{'slug': p['slug'],
                          'kind': 'brand' if 'brand' in p else 'cat',
                          'count': p['count'], 'listed': len(p['items'])} for p in
                         (brands + cats)]},
              open(OUT_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'\n生成 {len(made)} 页（品牌 {len(brands)} + 品类 {len(cats)}，可生成总数 {len(brands)+len(cats)}）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
