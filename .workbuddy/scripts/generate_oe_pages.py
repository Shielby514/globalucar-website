# -*- coding: utf-8 -*-
"""
L3 单 OE 落地页批量生成器
输入: .workbuddy/data/oe-master-db.json (confidence A/B/B2)
输出: oe/{oe}.html (单OE页) + oe/index.html (hub) + oe/{system}.html (L2) + sitemap 更新
规范: SOP 4.5 改写(文字为自有模板生成,仅用同行结构化事实数据) / GEO-AEO 事实块 / FAQPage+Product schema
"""
import json, os, re, hashlib, glob
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_P = os.path.join(BASE, '.workbuddy', 'data', 'oe-master-db.json')
OE_DIR = os.path.join(BASE, 'oe')
SITE = 'https://www.global-ucars.com'

# ── OE 前缀族谱图(数据驱动差异化内容) ──
try:
    PREFIX_MAP = json.load(open(os.path.join(BASE, '.workbuddy', 'data', 'oe-prefix-map.json'), encoding='utf-8'))
except Exception:
    PREFIX_MAP = {}

# ── 系统归桶 ──
SYSTEM_BUCKET = {
    'Engine': 'engine', 'engine': 'engine',
    'Suspension/Steering/Brake': 'suspension-steering',
    'Suspension & Steering': 'suspension-steering', 'Suspension': 'suspension-steering',
    'Suspension System': 'suspension-steering', 'Steering': 'suspension-steering',
    'Electrical': 'electrical', 'Electrical/Ignition': 'electrical',
    'Electrical System': 'electrical', 'Body/Electrical': 'electrical',
    'Brake': 'brake', 'Brake System': 'brake',
    'Cooling': 'cooling', 'Cooling System': 'cooling',
    'Transmission': 'transmission', 'Transmission System': 'transmission',
    'Body': 'body', 'Body/Interior': 'body',
    'Fuel': 'engine', 'Ignition': 'engine', 'Fuel System': 'engine',
    'Sensors (NA line)': 'sensors-na',
}
BUCKET_TITLE = {
    'engine': 'Engine & Fuel System',
    'suspension-steering': 'Suspension, Steering & Brake',
    'electrical': 'Electrical & Sensors',
    'brake': 'Brake System',
    'cooling': 'Cooling System',
    'transmission': 'Transmission & Drivetrain',
    'body': 'Body & Interior',
    'sensors-na': 'North America Sensor Line (GM / Ford)',
}

# ── 部件类型 → SKU 图片映射 ──
IMG_RULES = [
    # AI 生成部件类型图(已去水印) - 2026-09-26 批次2
    (r'door handle|door lock|latch|actuator', 'assets/parts/gen/gen-door-handle-latch-set.png'),
    (r'hood hinge|bonnet hinge', 'assets/parts/gen/gen-hood-hinge-pair.png'),
    (r'cross-?pull bar|stable connecting rod|link assemb|connecting rod', 'assets/parts/gen/gen-stabilizer-link-bars.png'),
    (r'insulator assemb|bushing|bush-|rubber mount', 'assets/parts/gen/gen-rubber-bushing-insulator-set.png'),
    (r'drive shaft|driveshaft|propeller shaft|shaft assy.?drive|cv joint|axle', 'assets/parts/gen/gen-drive-shaft-cv-joint.png'),
    (r'steering rack|rack & pinion|rack and pinion', 'assets/parts/gen/gen-steering-rack-pinion.png'),
    (r'wheel bearing|hub bearing|wheel hub', 'assets/parts/gen/gen-wheel-hub-bearing-assembly.png'),
    (r'cooling fan|radiator fan|fan assemb|fan assy', 'assets/parts/gen/gen-radiator-cooling-fan.png'),
    (r'oil pan|oil sump|pan assemb.?engine', 'assets/parts/gen/gen-engine-oil-pan.png'),
    (r'ball joint', 'assets/parts/gen/gen-ball-joint-pair.png'),
    (r'piston|ring set', 'assets/parts/gen/gen-piston-ring-set.png'),
    # AI 生成部件类型图(已去水印) - 批次1
    (r'wheel speed|abs sens', 'assets/parts/gen/gen-abs-wheel-speed-sensor.png'),
    (r'window switch|door switch|power switch', 'assets/parts/gen/gen-power-window-switch.png'),
    (r'hood lifter|gas spring|hood stay|bonnet stay', 'assets/parts/gen/gen-hood-lifter-gas-strut.png'),
    (r'timing belt|v-?belt|fan belt|drive belt|ribbed belt|\bbelt\b', 'assets/parts/gen/gen-timing-belt.png'),
    (r'coil spring|suspension spring|\bspring\b', 'assets/parts/gen/gen-coil-spring.png'),
    (r'brake pad|break pad|disc pad|pad kit|brake shoe', 'assets/parts/gen/gen-brake-pad-set.png'),
    (r'head ?light|head ?lamp|\blamp\b|tail light|fog light', 'assets/parts/gen/gen-headlight-assembly.png'),
    (r'ignition coil|coil pack', 'assets/parts/part_031_ignition_coil.jpg'),
    (r'spark plug', 'assets/parts/part_032_spark_plug.jpg'),
    (r'fuel injector|injector', 'assets/parts/part_033_fuel_injector.jpg'),
    (r'fuel pump ass', 'assets/parts/part_035_fuel_pump_assembly.jpg'),
    (r'fuel pump', 'assets/parts/part_034_fuel_pump.jpg'),
    (r'fuel filter', 'assets/parts/part_034_fuel_pump.jpg'),
    (r'throttle body', 'assets/parts/part_036_throttle_body.jpg'),
    (r'gasket', 'assets/parts/part_037_cylinder_head_gasket.jpg'),
    (r'engine mount|mounting', 'assets/parts/part_038_engine_mount.jpg'),
    (r'oxygen sensor|o2 sensor', 'assets/parts/part_039_oxygen_sensor.jpg'),
    (r'vvt|variable valve', 'assets/parts/part_040_vvt_solenoid.jpg'),
    (r'pcv', 'assets/parts/part_041_pcv_valve.jpg'),
    (r'ignition wire|plug wire', 'assets/parts/part_043_ignition_wire.jpg'),
    (r'piston', 'assets/parts/part_044_engine_piston.jpg'),
    (r'camshaft', 'assets/parts/part_045_camshaft.jpg'),
    (r'water pump', 'assets/parts/part_046_water_pump.jpg'),
    (r'radiator fan|fan assy', 'assets/parts/part_047_radiator_fan_assembly.jpg'),
    (r'fan motor', 'assets/parts/part_048_radiator_fan_motor.jpg'),
    (r'blower', 'assets/parts/part_049_heater_blower_motor.jpg'),
    (r'oil cooler', 'assets/parts/part_050_oil_cooler.jpg'),
    # 节温器 / 节温器壳：原映射到「中文标注冷却系统原理图」与「设计占位图」，2026-09-29 换实拍
    (r'thermostat hous', 'assets/parts/part_051_coolant_thermostat.jpg'),
    (r'thermostat', 'assets/parts/part_051_coolant_thermostat.jpg'),
    # 空气悬挂压缩机(Airmatic)：原误用 A/C 压缩机实拍图(语义不符)，2026-09-29 换专用 AI 实拍风图
    (r'airmatic|suspension compressor', 'assets/parts/part_090_air_suspension_compressor.jpg'),
    # 压缩机：原映射到设计占位图(ID-053)，2026-09-29 换实拍
    (r'compressor|a/c comp', 'assets/parts/part_053_a_c_compressor.jpg'),
    (r'radiator', 'assets/parts/part_054_radiator.jpg'),
    # 水温传感器：原映射到设计占位图(ID-055)，2026-09-29 换实拍
    (r'coolant (temp|sensor)', 'assets/parts/part_055_coolant_temperature_sensor.jpg'),
    (r'shock absorber|strut', 'assets/parts/lp/front-right-shock-absorber-54660-4h050-01.webp'),
    (r'control arm', 'assets/parts/lp/front-left-control-arm-54500-a7100-01.webp'),
    (r'clock spring|spiral cable', 'assets/parts/lp/aftermarket-clock-spring-93490-2v310-01.webp'),
    (r'wheel hub|hub bearing|wheel bearing', 'assets/parts/lp/front-wheel-hub-bearing-51750-2b010-01.webp'),
    (r'stabilizer|sway bar', 'assets/parts/lp/stabilizer-link-bar-55530-2s200-01.webp'),
    (r'tie rod|rack end', 'assets/parts/rack-end-inner-tie-rod-hyundai-kia-wholesale-product.jpg'),
    (r'ball joint', 'assets/parts/rack-end-inner-tie-rod-hyundai-kia-wholesale-product.jpg'),
    # 兜底: 泛传感器
    (r'\bsensor\b', 'assets/parts/gen/gen-abs-wheel-speed-sensor.png'),
    # 2026-09-30 新增：补 IMG_RULES 覆盖 — 让 89 页 placeholder 断链归零
    (r'air filter|air cleaner|cabin filter|carbin filter|activated carbon filter', 'assets/parts/part_091_air_filter.jpg'),
    (r'glow plug', 'assets/parts/part_092_glow_plug.jpg'),
    (r'crankshaft oil seal|front oil seal|\boil seal\b', 'assets/parts/part_093_crankshaft_oil_seal.jpg'),
    (r'oil filter', 'assets/parts/part_094_oil_filter.jpg'),
    (r'fuel filter|a/t filter|at filter|transmission filter', 'assets/parts/part_095_fuel_filter.jpg'),
    (r'corner light|cornering light|side marker', 'assets/parts/part_096_corner_light.jpg'),
    (r'valve tappet|tappet|lifter', 'assets/parts/part_097_valve_tappet.jpg'),
    (r'rubber sleeve for spark plug|rubber sleeve|spark plug sleeve', 'assets/parts/part_098_rubber_sleeve_spark_plug.jpg'),
    # 2026-09-30 补 IMG_RULES 覆盖 17 条未匹配兜底
    (r'idler pulley|tensioner pulley|generator pulley|pulley', 'assets/parts/gen/gen-timing-belt.png'),
    (r'fuel tank breather|crankcase breather|breather valve|pcv valve', 'assets/parts/part_041_pcv_valve.jpg'),
    (r'wheel bolt|wheel stud', 'assets/parts/gen/gen-ball-joint-pair.png'),
    (r'timing kit', 'assets/parts/gen/gen-timing-belt.png'),
    (r'turbo air intake duct|intake duct', 'assets/parts/gen/gen-radiator-cooling-fan.png'),
    (r'heat exchanger', 'assets/parts/part_054_radiator.jpg'),
    (r'voltage regulator', 'assets/parts/gen/gen-abs-wheel-speed-sensor.png'),
    (r'flange cover|flange lid|thrust washer', 'assets/parts/part_037_cylinder_head_gasket.jpg'),
    (r'guide rail', 'assets/parts/gen/gen-ball-joint-pair.png'),
    # 2026-10-02 新增：覆盖储备队列 6 大类未匹配部件（约 7 万条）。
    # 此前这些只能拿到语义不符的「系统级兜底图」（如 Wiring Harness 显示活塞）。
    # ⚠️ 顺序即在先优先：新规则一律追加在尾部，不改变既有匹配结果。
    (r'wiring|wire harness|wiring harness|harness', 'assets/parts/part_090_automotive_wiring_harness.jpg'),
    (r'torque conv|tq conv|torque converter', 'assets/parts/part_228_torque_converter.jpg'),
    (r'wheel assy steering|steering wheel', 'assets/parts/part_226_steering_wheel.jpg'),
    (r'wheel assy aluminium|wheel assy aluminum|alloy wheel|wheel disc', 'assets/parts/part_227_alloy_wheel.jpg'),
    (r'instrument cluster|cluster assy inst|cluster instr|\bcluster\b', 'assets/parts/part_225_instrument_cluster.jpg'),
    (r'electronic control|control unit|\becu\b|\btcm\b|abs control', 'assets/parts/part_224_ecu_control_unit.jpg'),
    (r'trim|headlining|carpet|sunvisor|sun visor|console|panel', 'assets/parts/part_223_interior_trim_panel.jpg'),
    (r'\bhose\b|hose assy|hose comp|\bpipe\b|\btube\b', 'assets/parts/part_221_hose_coolant.jpg'),
    (r'\bbolt\b|\bscrew\b|tapping|\bnut\b|\bclip\b|ring snap|snap ring|o ring|o-ring|spacer|washer|rivet', 'assets/parts/part_222_fastener_kit.jpg'),
    # 2026-10-02 第二批：长尾大类（座椅/支架/保险杠/玻璃/音响主机/后视镜/保险丝盒/词序反的 Seal Oil）
    (r'seal oil|seal assy oil', 'assets/parts/part_093_crankshaft_oil_seal.jpg'),
    (r'valve seat|seat valve', 'assets/parts/part_044_engine_piston.jpg'),
    (r'\bseat\b|cushion', 'assets/parts/part_229_seat_assembly.jpg'),
    (r'bracket', 'assets/parts/part_230_mounting_bracket.jpg'),
    (r'bumper', 'assets/parts/part_231_bumper_cover.jpg'),
    (r'mirror', 'assets/parts/part_234_door_mirror.jpg'),
    (r'glass|windshield|windscreen', 'assets/parts/part_232_window_glass.jpg'),
    (r'head unit|avn|audio|speaker|\bradio\b|navigation|display unit', 'assets/parts/part_233_head_unit.jpg'),
    (r'junction box|fuse box|relay box', 'assets/parts/part_224_ecu_control_unit.jpg'),
]
# 系统级兜底图(保证 100% 配图覆盖)
BUCKET_IMG = {
    'engine': 'assets/parts/part_044_engine_piston.jpg',
    'suspension-steering': 'assets/parts/gen/gen-ball-joint-pair.png',
    'electrical': 'assets/parts/gen/gen-abs-wheel-speed-sensor.png',
    'brake': 'assets/parts/gen/gen-brake-pad-set.png',
    'cooling': 'assets/parts/part_054_radiator.jpg',
    'transmission': 'assets/parts/gen/gen-drive-shaft-cv-joint.png',
    'body': 'assets/parts/gen/gen-door-handle-latch-set.png',
    'sensors-na': 'assets/parts/part_039_oxygen_sensor.jpg',
}
def find_image(e, bucket=None):
    # A级: SKU 自带图
    if e.get('images'):
        for im in e['images']:
            if os.path.exists(os.path.join(BASE, im)):
                return im
    nm = (e.get('part_name') or '') + ' ' + (e.get('part_name_cn') or '')
    for pat, img in IMG_RULES:
        if re.search(pat, nm, re.I):
            p = os.path.join(BASE, img)
            if os.path.exists(p):
                return img
    # 系统级兜底
    fb = BUCKET_IMG.get(bucket)
    if fb and os.path.exists(os.path.join(BASE, fb)):
        return fb
    return None

# ── 文案库(自有措辞,10变体轮转防重复) ──
def h(oe, salt=''):
    return int(hashlib.md5((oe + salt).encode()).hexdigest(), 16)

INTROS = [
    "The part number {oe} is a factory-reference {part} used across selected {brand} models. This page gathers the cross-reference data, application list and sourcing details buyers usually need before placing a wholesale order with KingMay.",
    "Looking for a dependable supply of {oe}? This {part} fits a range of {brand} vehicles and is stocked through our Guangzhou warehouse network. Below you will find the full fitment list, interchangeable numbers and commercial terms.",
    "{oe} is the original-equipment reference for this {part}. Importers and repair chains source it from KingMay in mixed container loads, alongside other {system_l} components. Check the tables below to confirm vehicle coverage.",
    "Buyers searching {oe} typically need three things fast: correct application data, a stable factory source and clear MOQ terms. This page covers all three for the {part} used on {brand} vehicles.",
    "As a core item in our {system_l} program, {oe} covers the {part} demanded by aftermarket distributors serving {brand} platforms. Full specifications, replacement numbers and packaging options follow.",
    "The {oe} {part} is part of KingMay's Hyundai-Kia specialty line. Distributors in the Middle East, Africa and Latin America combine it with other fast-moving {system_l} parts to reach full-container thresholds.",
    "If your procurement list includes {oe}, this reference page summarizes everything we can confirm: vehicle applications, equivalent part numbers, quality grade and export packing for the {part}.",
    "{brand} platforms rely on this {part} — reference {oe}. Our export team ships it worldwide with documented QC checks. Verify fitment in the table below before requesting a quotation.",
    "This page is a complete sourcing brief for OE number {oe}: a {part} within the {system_l} category, available for wholesale export with flexible order quantities and consolidated freight.",
    "Sourcing {oe} for your catalog? The {part} shown here matches factory references for several {brand} models, and our team supports both sample orders and volume contracts for this line.",
    "The {oe} reference comes up regularly on {brand} repair orders. Our Guangzhou desk handles it as a standing line item — stock checks, photo confirmation and dimension reports are done before any PI is issued.",
    "Not sure whether {oe} is the number you need? Read the prefix analysis below first: the 5-digit head of a Hyundai-Kia part number identifies the component family, which is often enough to rule out a mis-copied code before you email us.",
    "We quote {oe} weekly. The {part} sits in the {system_l} range most distributors reorder every quarter, so packaging and stock positions are updated on a rolling basis rather than per shipment.",
    "A word on how we list {oe}: the tables below separate what is verified (application rows, cross references) from what is advisory (ordering terms). If a row matters to your decision, ask our export desk to re-confirm it in writing.",
    "Importers comparing suppliers on {oe} usually ask for three documents — packing photos, a dimension sheet and a material certificate. All three are on file for this {part} line; request them with your inquiry.",
    "{oe} belongs to the {part} family in our catalog. Because the reference also appears on several {brand} variants, check the suffix characters carefully: one letter off and you are quoting a different mounting configuration.",
    "Dealers in the Gulf and East Africa move {oe} steadily year-round. If you are building a first order, this {part} pairs well with other {system_l} references — the combined table below shows what ships together most often.",
]
# ─────────────────────────────────────────────────────────────
# PAA (People Also Ask) 热词问题库 ─ 2026-09-29 热词扩充版
# 规范: 每页 6 问, 从 8 类问题桶里按 OE 哈希各取 1; 同页问题绝不重复;
#       schema.org FAQPage / Question / Answer (+ author + datePublished)
# 8 桶: fitment 适配 / diagnostic 故障 / verify 真伪 / interchange 互替
#       pricing 价格 / sourcing 采购 / logistics 交易 / warranty 质保
# 热词来源: OE 号 x 车型 x 品类 x 采购意图 的四层长尾组合, 全部写成
#           真实搜索句式(what/will/how much/where/why/can), 便于命中 PAA 位
# ─────────────────────────────────────────────────────────────
PAA_FRAMES = [
    # ── 1 fitment 车型适配 ──
    ("What vehicles does OE {oe} fit?",
     "OE {oe} is the factory reference for this {part} on selected {brand} models. The Applications table on this page lists the confirmed rows — check trim level and build year against your own fleet before ordering, because one reference can cover several body variants."),
    ("Will OE {oe} fit my {brand}?",
     "Match three things: the code on the part you are removing, the build-year range in the Applications table, and the mounting points visible in the reference photo. If all three line up, {oe} is a confirmed fit. Send your VIN and our export desk will double-check the ambiguous cases."),
    ("Which model years use OE {oe}?",
     "Build-year coverage is listed row by row in the Applications table above. Where several generations share one number, the newer rows usually carry a revised suffix — compare the last four characters before buying, since a suffix change often means a different connector or bracket."),
    ("Where is this {part} located on a {brand}?",
     "Position depends on the platform. On most {brand} applications the {part} sits on the {system_l} assembly and can be reached from the engine bay or the underbody without removing the dashboard. Torque figures and disassembly order are given in the workshop manual for each model."),

    # ── 2 diagnostic 故障诊断 ──
    ("What are the signs of a failing {part}?",
     "Watch for noise on cold start, vibration under load, warning lights, fluid seepage or uneven operation. Once any of those appears the {part} should be inspected, and reference {oe} replaced if it measures outside specification."),
    ("How long does a {part} last on a {brand}?",
     "Treat it as a wear item: inspect every 20,000-30,000 km and replace at the first sign of leakage, noise or performance loss. Real service life swings widely with climate, road surface and duty cycle, so mileage on its own is a weak indicator."),
    ("Can I keep driving with a worn {part}?",
     "For a short distance at reduced load, usually yes — but the risk compounds. A degraded {part} transfers stress to neighbouring components, so a small repair can grow into a full {system_l} rebuild. Book the replacement once the symptom is repeatable."),
    ("Why is my {brand} making noise from the {part}?",
     "Noise normally traces to worn internal surfaces, a loose mount, a dry bearing or contact with a neighbouring part. Isolate it by reproducing the sound at a fixed speed, then compare against the reference photo for {oe} to confirm the right replacement."),

    # ── 3 verify 真伪核验 ──
    ("Is OE {oe} genuine or aftermarket?",
     "KingMay supplies OEM-grade aftermarket parts built to the {oe} factory specification: material grade, dimensional tolerance and surface finish follow the original tooling. They are not dealer-boxed genuine parts, and we quote them that way so there is no ambiguity at customs."),
    ("How do I verify OE {oe} is the correct number?",
     "Three checks: the code printed on your old part must read {oe}; the number must fall inside the build-year range in the Applications table; and the connector, thread or bolt pattern must match the reference photo. Codes cast into the housing are the most reliable source."),
    ("What is the difference between OEM and aftermarket {part}?",
     "OEM means the part was produced for the vehicle maker's assembly line; aftermarket means it is made independently to the same engineering drawing. For a {part} the practical gap is usually tooling age and packaging rather than fit, provided the tolerance class matches."),

    # ── 4 interchange 交叉参考 ──
    ("What part numbers cross-reference to OE {oe}?",
     "The Related OE References table above lists the alternates we see most often in trade inquiries. Cross-references work because the engineering envelope is shared across the {system_l} family — always confirm dimensions and connector layout before you swap."),
    ("What is the supersession for OE {oe}?",
     "A supersession happens when the maker revises a {part} and issues a new tail number. The revision normally changes a small physical detail rather than the fit. Where we know a supersession chain for {oe} we list the current reference; ask our desk for written confirmation before a large order."),
    ("Can I swap OE {oe} with another reference?",
     "Yes, if the alternate shares the same engineering envelope. Shortlist candidates from the Related OE References table, then check bolt pattern, electrical pinout and material grade. A difference in any of those three means it is a different part, not a substitute."),

    # ── 5 pricing 价格热词 ──
    ("How much does OE {oe} cost wholesale?",
     "Wholesale pricing for {oe} depends on order quantity, surface treatment and packing. Standard references are quoted ex-Guangzhou with tiered pricing from 10 pieces upward — send quantity and destination port and a quotation usually returns within one business day."),
    ("What is the bulk price for this {part}?",
     "Bulk pricing is tiered: 10 pieces, 50 pieces and full-carton quantities each carry a different unit rate. Piece price also moves with packing format and whether your own brand is printed on the carton, so tell us the landed quantity you are planning."),
    ("Why does {part} pricing vary between suppliers?",
     "Four variables explain most of the spread: material grade, whether the goods are new production or clearance stock, packing format, and whether the quote is ex-works or landed. Ask for the material certificate alongside the price — that is what makes a comparison like-for-like."),

    # ── 6 sourcing 采购热词 ──
    ("Where can I buy OE {oe} in bulk?",
     "KingMay Auto Parts ships {oe} wholesale from Guangzhou to importers, distributors and workshops. Order directly from this page, or send the reference to our export desk for pricing, samples and documentation."),
    ("Who manufactures aftermarket {part} for {brand}?",
     "Aftermarket {part} comes from tooling houses that hold the original drawings or licensed equivalents. KingMay sources from vetted factories and inspects each batch; the manufacturer name is available on request where your market requires origin documentation."),
    ("How do I look up an OE number for a {brand} {part}?",
     "Start from the code cast or printed on the part you are removing — that is the authoritative source. If it is illegible, use the Applications table on the closest {system_l} reference and narrow by build year. Send photos and we will cross-check the number for you."),

    # ── 7 logistics 交易条款 ──
    ("What is the MOQ for OE {oe}?",
     "Standard minimum order is 10 pieces per part number. Mixed orders that combine {oe} with other {system_l} references are welcome — that is how most clients fill an LCL or FCL container without over-stocking a single line."),
    ("What is the lead time for OE {oe}?",
     "Stock references leave Guangzhou within 7 working days. If {oe} needs a production run, allow 25-35 days depending on quantity and surface treatment. The schedule is confirmed in writing when the order is placed."),
    ("How is OE {oe} packed and shipped?",
     "Export packing is a neutral carton with inner protection; custom labels, barcodes and box specifications are available for volume orders. Shipments move FOB Guangzhou or Shenzhen, with CIF and DDP terms negotiable."),
    ("Can KingMay supply samples of OE {oe}?",
     "Yes. Sample lots of {oe} are used by QC teams to benchmark dimension, material and finish before a volume commitment. Send the reference and we will quote the sample alongside the production price."),

    # ── 8 warranty 质保与品控 ──
    ("Does OE {oe} come with a warranty?",
     "Every shipment of {oe} leaves with a packing list, photo documentation and a QC report. Warranty terms are agreed per contract and reference that inspection record; claims are settled in writing against the documentation."),
    ("How is OE {oe} quality tested before shipment?",
     "Incoming batches pass a dimensional check, a material look-up against the {system_l} specification, and a visual inspection for finish defects. Critical dimensions are measured per carton and the photographs are archived against the order number."),
    ("What if OE {oe} arrives defective?",
     "Report it with the order number and packing-list line plus photographs. Because every carton is photographed before loading, we can trace the batch immediately and settle the claim against the inspection record instead of arguing from memory."),
]

# 8 个问题桶(在 PAA_FRAMES 中的索引区间), 顺序与上面的分类注释一致
PAA_BUCKETS = [
    [0, 1, 2, 3],      # fitment      车型适配
    [4, 5, 6, 7],      # diagnostic   故障诊断
    [8, 9, 10],        # verify       真伪核验
    [11, 12, 13],      # interchange  交叉参考
    [14, 15, 16],      # pricing      价格热词
    [17, 18, 19],      # sourcing     采购热词
    [20, 21, 22, 23],  # logistics    交易条款
    [24, 25, 26],      # warranty     质保与品控
]
PAA_BUCKET_NAMES = ['fitment', 'diagnostic', 'verify', 'interchange',
                    'pricing', 'sourcing', 'logistics', 'warranty']
PAA_PER_PAGE = 6                  # 每页 PAA 问题数(热词扩充: 4 → 6)
PAA_SCHEMA_DATE = '2026-09-29'    # 常量而非 today(): 重跑必须字节一致
PAA_SCHEMA_AUTHOR = 'KingMay Auto Parts'

# 兼容老调用点
FAQ_TEMPLATES = PAA_FRAMES

def _select_paa_idx(oe, n=PAA_PER_PAGE):
    """热词扩充版选择器: 从 8 个问题桶里按 OE 哈希确定性挑 n 个不同的桶, 每桶取 1 条.
    返回 [(PAA_FRAMES 索引, 问题桶名), ...]

    保证三件事:
      1. 同一页问题绝不重复(桶区间互斥);
      2. 同一个 OE 每次生成结果完全一致(纯哈希, 无随机);
      3. 不同 OE 落在不同的桶组合上 → 全站问题覆盖面最大化,
         而不是所有页面都问同样几句话(那正是 PAA 被判模板化的原因)。
    """
    order = sorted(range(len(PAA_BUCKETS)),
                   key=lambda b: hashlib.md5(('%s|bucket|%d' % (oe, b)).encode('utf-8')).hexdigest())
    out, seen = [], set()
    for slot, b in enumerate(order[:n]):
        pool = PAA_BUCKETS[b]
        idx = pool[int(hashlib.md5(('%s|slot|%d|%d' % (oe, slot, b)).encode('utf-8')).hexdigest(), 16) % len(pool)]
        if idx not in seen:
            seen.add(idx)
            out.append((idx, PAA_BUCKET_NAMES[b]))
    # 兜底(理论上不会触发): 按顺序补齐到 n 条
    if len(out) < n:
        for i in range(len(PAA_FRAMES)):
            if i not in seen:
                seen.add(i)
                out.append((i, PAA_BUCKET_NAMES[-1]))
            if len(out) >= n:
                break
    return out[:n]


def _select_paa(oe, n=PAA_PER_PAGE):
    """兼容入口: 只返回问题文本(老调用点用)"""
    return [PAA_FRAMES[i] for i, _ in _select_paa_idx(oe, n)]


CTAS = [
    "Request a wholesale quote for {oe} through our contact page — most quotations return within one business day.",
    "Send your {oe} requirement and destination port to our export desk for a landed-cost estimate.",
    "Ask for the {oe} sample kit: photo confirmation, dimension report and material grade documentation included.",
]

def esc(s):
    # 兜底: 部分记录 moq/sku_id 是 int/float, 直接 .replace 会 AttributeError 中断整批出页。
    # 对 str 输入行为与旧实现一致; None -> ''; 数值 -> 字面量。
    return ('' if s is None else str(s)).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def slug_oe(oe):
    return oe.lower()

# 聚合页/非单 OE 页的文件名前缀, 不计入 sitemap 的 OE 明细
_AGG_RE = re.compile(r'^(index|engine|cooling|electrical|body|brake|transmission|'
                     r'suspension-steering|sensors-na|stats)')

def live_oe_pages():
    """磁盘上实际存在的单 OE 页文件名(小写, 含连字符), 供 sitemap / 统计使用"""
    return sorted(f for f in os.listdir(OE_DIR)
                  if f.endswith('.html') and not _AGG_RE.match(f)
                  and re.match(r'^[0-9a-z][0-9a-z\-]*\.html$', f))

BRAND_WORDS = ['NISSAN','TOYOTA','MERCEDES-BENZ','MERCEDES','BMW','AUDI','HYUNDAI','KIA','SUBARU','PORSCHE','MAZDA','HONDA','VOLKSWAGEN','SUZUKI','MITSUBISHI','ISUZU','DAIHATSU','LEXUS','INFINITI','SSANGYONG','CHEVROLET','BUICK','GM','FORD']

def page_html(e, related, bucket):
    oe = e['oe']
    part = (e.get('part_name') or 'Auto Part').strip()
    # 剥尾部应用信息: "Engine Mounting For NISSAN Serena ..." → "Engine Mounting"
    part = re.sub(r'\s+for\s+[A-Z][A-Za-z0-9\-\./ &(),+]{2,}$', '', part)
    part = re.sub(r'\s+for\s+(HYUNDAI|KIA|hyundai|kia|NISSAN|TOYOTA|MERCEDES|BMW|AUDI|SUBARU|PORSCHE|HONDA|MAZDA|VW|VOLKSWAGEN).*$', '', part)
    part = re.sub(r'\s+OEM\s+[A-Z0-9\-/\s]+$', '', part)
    # 剥尾部孤立 for（源数据残缺如 "Bushing Iron Hose for"），否则与模板的 "for {brand}" 拼成 "for for"
    part = re.sub(r'\s+for\s*$', '', part, flags=re.I)
    part = part[:80].strip(' -–,') or 'Auto Part'
    brands = e.get('brand') or []
    if not brands:
        # 从 part_name 原文提取品牌词兜底; 提不到 → 韩系目录默认(新瑞伟业线)
        nm_up = (e.get('part_name') or '').upper()
        found = [b.title() for b in BRAND_WORDS if b in nm_up]
        brands = found if found else ['Hyundai', 'Kia']
    brand = ' / '.join(dict.fromkeys([b.title() if b.isupper() else b for b in brands]))[:40]
    sys_l = (BUCKET_TITLE.get(bucket) or e.get('system') or 'Auto Parts').lower()
    idx = h(oe) % len(INTROS)
    intro = INTROS[idx].format(oe=oe, part=part.lower(), brand=brand, system_l=sys_l)

    # ── 前缀族谱(数据驱动差异化) ──
    oe_key = e.get('oe', oe).replace('-', '').upper()
    pfx = oe_key[:5] if re.match(r'^\d{5}', oe_key) else oe_key[:4]
    fam = PREFIX_MAP.get(pfx)
    fam_label = (fam['label'] if fam else '').strip()
    fam_count = fam['count'] if fam else 0
    norm_key = oe_key

    # GEO/AEO 直答块(40-60词, 可被 AI 引擎直接引用)
    if fam and fam_label:
        ans = (f"OE {oe} is a {part} reference. In the Hyundai-Kia numbering system the prefix {pfx} "
               f"denotes the {fam_label} family, which holds {fam_count} references in KingMay's Guangzhou catalog. "
               f"Wholesale MOQ is 10 pieces; quotes are issued within one business day.")
    else:
        ans = (f"OE {oe} is a {part} for {brand} vehicles, stocked and exported wholesale by KingMay Auto Parts "
               f"(Guangzhou, China). MOQ from 10 pieces, mixed orders welcome, quotations within one business day.")
    paa_picks = _select_paa_idx(oe)
    faq_sel = [PAA_FRAMES[i] for i, _ in paa_picks]
    faq_buckets = [t for _, t in paa_picks]
    faqs = [(q.format(oe=oe, system_l=sys_l, part=part.lower(), brand=brand), a.format(oe=oe, system_l=sys_l, part=part.lower(), brand=brand)) for q, a in faq_sel]
    # PAA 热词: 本页 Q&A 实际覆盖到的问题桶 + 四层长尾关键词(OE / 车型 / 品类 / 采购意图)
    paa_bucket_tags = list(dict.fromkeys(faq_buckets))
    hot_keywords = list(dict.fromkeys(
        [oe, part, f'{part} {brand}', f'OE {oe} price', f'{part} wholesale',
         f'{part} cross reference', f'{part} replacement', brand]
        + [f'{t} parts' for t in paa_bucket_tags]))
    cta = CTAS[h(oe, 'c') % len(CTAS)].format(oe=oe)
    img = find_image(e, bucket)
    url = f"{SITE}/oe/{slug_oe(oe)}.html"
    title = f"OE {oe} — {part} for {brand} | Wholesale from KingMay"
    if len(title) > 70:
        # 在 word boundary 处截断，避免 "| Wholesale from KingM" 这种断尾
        truncated = title[:70]
        if ' ' in truncated:
            truncated = truncated.rsplit(' ', 1)[0]
        title = truncated
    desc = (f"OE number {oe}: {part} for {brand} vehicles. Fitment list, cross-reference numbers, "
            f"MOQ and export terms from KingMay Auto Parts, Guangzhou.")
    if len(desc) > 160:
        truncated = desc[:160]
        if ' ' in truncated:
            truncated = truncated.rsplit(' ', 1)[0]
        desc = truncated

    # 表1: 速查
    price = e.get('price') or 'Contact for wholesale pricing'
    moq = e.get('moq') or '10 pieces (mixed orders welcome)'
    # 表2: fitment
    fit_rows = e.get('fitment') or []
    # 表3: cross-ref related
    rel_rows = [(r['oe'], (r.get('part_name') or '')[:60]) for r in related[:8]]

    img_html = ''
    if img:
        img_html = f'''
  <section class="oe-sec">
    <h2>Product Reference Image</h2>
    <figure class="oe-fig">
      <img src="../{img}" alt="OE {esc(oe)} {esc(part)} for {esc(brand)} — wholesale export from KingMay Auto Parts" loading="lazy" width="900" height="600">
      <figcaption>Reference photo for OE {esc(oe)} — {esc(part)}. Final goods are inspected and photographed per shipment.</figcaption>
    </figure>
  </section>'''

    fit_html = ''
    if fit_rows:
        rows = '\n'.join(
            f'<tr><td>{esc(" / ".join(r) if isinstance(r, list) else r)}</td></tr>'
            for r in fit_rows[:25])
        fit_html = f'''
  <section class="oe-sec">
    <h2>Vehicle Applications</h2>
    <p>Confirmed and reported applications for {esc(oe)}. Verify trim and build year against your local fleet before ordering.</p>
    <div class="oe-tbl-wrap"><table class="oe-tbl">
      <thead><tr><th>Make / Model / Years</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>
  </section>'''

    # PAA 热词 → 相关搜索(把真实搜索句式做成指向对应聚合页的内链锚文本,
    # 既让锚文本带上热词, 又给 hub/分桶页补内链, 不是无意义的关键词堆砌)
    rel_search_items = [
        (f'{bucket}.html', f'{esc(sys_l)} OE references — full catalog'),
        ('index.html', 'OE number lookup by prefix family'),
        ('../parts-finder.html', f'Find {esc(part)} by OE number or vehicle'),
        ('../products.html?cat=parts', f'{esc(brand)} auto parts — wholesale list'),
        ('../oem-parts-lookup.html', 'OEM parts number lookup tool'),
        ('../contact.html', f'Request a wholesale quote for OE {esc(oe)}'),
    ]
    rel_search_html = '''
  <section class="oe-sec">
    <h2>Related Searches</h2>
    <p>Buyers searching for OE ''' + esc(oe) + ''' most often land on these pages next.</p>
    <ul class="rel-search">
''' + '\n'.join(f'      <li><a href="{href}">{label}</a></li>' for href, label in rel_search_items) + '''
    </ul>
  </section>'''

    rel_html = ''
    if rel_rows:
        rows = '\n'.join(
            f'<tr><td><a href="{slug_oe(r0)}.html">{esc(r0)}</a></td><td>{esc(r1 or "Same category reference")}</td></tr>'
            for r0, r1 in rel_rows)
        rel_html = f'''
  <section class="oe-sec">
    <h2>Related OE References</h2>
    <p>Other part numbers frequently ordered together with {esc(oe)} by wholesale clients.</p>
    <div class="oe-tbl-wrap"><table class="oe-tbl">
      <thead><tr><th>OE Number</th><th>Component</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>
  </section>'''

    faq_json = json.dumps([
        {'@type': 'Question', 'name': q,
         'acceptedAnswer': {'@type': 'Answer',
                            'text': a,
                            'author': {'@type': 'Organization',
                                       'name': PAA_SCHEMA_AUTHOR,
                                       'url': SITE},
                            'datePublished': PAA_SCHEMA_DATE,
                            'upvoteCount': 1},
         # PAA 热词: 把每问归到问题桶, 让机器读出这页覆盖的搜索意图
         'about': {'@type': 'DefinedTerm', 'name': f'{bk} — {part} {brand}'}}
        for (q, a), bk in zip(faqs, faq_buckets)], ensure_ascii=False)
    speakable_json = json.dumps({'@context': 'https://schema.org', '@type': 'WebPage',
        'name': title, 'url': url,
        'keywords': ', '.join(hot_keywords),
        'about': [{'@type': 'Brand', 'name': b.strip()} for b in brand.split('/') if b.strip()]
                 + [{'@type': 'DefinedTerm', 'name': part}],
        'speakable': {'@type': 'SpeakableSpecification', 'cssSelector': ['.ans-p']},
        'mainEntity': {'@type': 'DefinedTerm', 'name': f'OE {oe}',
                       'description': ans,
                       'inDefinedTermSet': {'@type': 'DefinedTermSet',
                                            'name': 'KingMay Hyundai-Kia OE Reference Library',
                                            'url': f'{SITE}/oe/'}}}, ensure_ascii=False)
    schema = f'''
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Product","name":"OE {esc(oe)} — {esc(part)}",
"sku":"{esc(oe)}","brand":{{"@type":"Brand","name":"KingMay Auto Parts"}},
"description":"{esc(desc)}","category":"{esc(BUCKET_TITLE.get(bucket, 'Auto Parts'))}",
"offers":{{"@type":"Offer","priceCurrency":"USD","availability":"https://schema.org/InStock",
"seller":{{"@type":"Organization","name":"KingMay Auto Parts (Guangzhou Globalucar)"}}}}}}
</script>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"FAQPage","mainEntity":{faq_json}}}
</script>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
{{"@type":"ListItem","position":1,"name":"Home","item":"{SITE}/"}},
{{"@type":"ListItem","position":2,"name":"OE Reference Hub","item":"{SITE}/oe/"}},
{{"@type":"ListItem","position":3,"name":"{esc(BUCKET_TITLE.get(bucket, 'Parts'))}","item":"{SITE}/oe/{bucket}.html"}},
{{"@type":"ListItem","position":4,"name":"{esc(oe)}"}}]}}
</script>
<script type="application/ld+json">
{speakable_json}
</script>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="keywords" content="OE {esc(oe)}, {esc(oe)} part, {esc(part)}, {esc(brand)} parts, wholesale auto parts, China auto parts supplier">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="product">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="KingMay Auto Parts">
<meta property="og:image" content="{SITE}/{esc(img or 'assets/parts/part_044_engine_piston.jpg')}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{SITE}/{esc(img or 'assets/parts/part_044_engine_piston.jpg')}">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{--bg:#0a0e17;--card:#1a2234;--bd:#2a3550;--tx:#f1f5f9;--tx2:#94a3b8;--ac:#c8102e;--gold:#f59e0b;--r:12px}}
body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg);color:var(--tx);line-height:1.65}}
.navbar{{position:sticky;top:0;z-index:99;background:rgba(10,14,23,.96);border-bottom:1px solid var(--bd)}}
.nav-inner{{max-width:1200px;margin:0 auto;display:flex;align-items:center;gap:18px;padding:12px 20px}}
.nav-brand{{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--tx);font-weight:700}}
.nav-logo{{height:36px;border-radius:6px}}
.nav-tagline{{font-size:12px;color:var(--tx2)}}
.nav-menu{{display:flex;gap:4px;list-style:none;margin-left:auto;flex-wrap:wrap}}
.nav-menu a{{color:var(--tx2);text-decoration:none;font-size:13.5px;padding:8px 11px;border-radius:8px}}
.nav-menu a:hover{{color:var(--tx);background:var(--card)}}
.wrap{{max-width:1000px;margin:0 auto;padding:26px 20px 60px}}
.crumb{{font-size:13px;color:var(--tx2);margin-bottom:14px}}
.crumb a{{color:var(--tx2);text-decoration:none}}.crumb a:hover{{color:var(--gold)}}
h1{{font-size:clamp(22px,3.4vw,34px);line-height:1.25;margin-bottom:12px}}
h1 .oe-n{{color:var(--gold)}}
.lead{{color:var(--tx2);font-size:16px;max-width:820px}}
.ans-blk{{background:var(--card);border:1px solid var(--bd);border-left:4px solid var(--gold);border-radius:var(--r);padding:16px 20px}}
.ans-blk h2{{display:none}}
.ans-p{{color:var(--tx);font-size:15.5px;margin:0;max-width:none}}
.oe-sec{{margin-top:34px}}
.oe-sec h2{{font-size:21px;margin-bottom:10px;border-left:4px solid var(--ac);padding-left:10px}}
.oe-sec p{{color:var(--tx2);margin-bottom:12px;max-width:860px}}
.oe-card{{background:var(--card);border:1px solid var(--bd);border-radius:var(--r);padding:20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}}
.oe-kv{{display:flex;flex-direction:column;gap:2px}}
.oe-kv b{{font-size:12px;color:var(--tx2);text-transform:uppercase;letter-spacing:.06em}}
.oe-kv span{{font-size:15px;font-weight:600}}
.oe-kv .hl{{color:var(--gold);font-size:18px}}
.oe-tbl-wrap{{overflow-x:auto;border:1px solid var(--bd);border-radius:var(--r)}}
.oe-tbl{{width:100%;border-collapse:collapse;font-size:14px;background:var(--card)}}
.oe-tbl th{{background:#101827;color:var(--gold);text-align:left;padding:10px 14px;font-size:12.5px;text-transform:uppercase;letter-spacing:.05em}}
.oe-tbl td{{padding:10px 14px;border-top:1px solid var(--bd);color:var(--tx)}}
.oe-tbl a{{color:#60a5fa;text-decoration:none}}.oe-tbl a:hover{{text-decoration:underline}}
.oe-fig{{background:var(--card);border:1px solid var(--bd);border-radius:var(--r);overflow:hidden}}
.oe-fig img{{width:100%;display:block;aspect-ratio:3/2;object-fit:cover}}
.oe-fig figcaption{{padding:10px 14px;font-size:12.5px;color:var(--tx2)}}
.faq{{display:grid;gap:12px}}
.faq details{{background:var(--card);border:1px solid var(--bd);border-radius:var(--r);padding:14px 18px}}
.faq summary{{cursor:pointer;font-weight:600;font-size:15px}}
.faq details p{{margin:10px 0 0;color:var(--tx2);font-size:14.5px}}
.rel-search{{display:flex;flex-wrap:wrap;gap:8px;list-style:none;padding:0;margin:0}}
.rel-search li{{margin:0}}
.rel-search a{{display:inline-block;padding:8px 14px;border:1px solid var(--bd);border-radius:999px;background:var(--card);color:var(--tx);font-size:13.5px;text-decoration:none}}
.rel-search a:hover{{border-color:var(--ac);color:var(--ac)}}
.cta{{margin-top:38px;background:linear-gradient(135deg,#9b0c23,#c8102e);border-radius:var(--r);padding:26px;display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between}}
.cta h3{{font-size:19px}}
.cta p{{color:#fecaca;font-size:14px;margin-top:4px;max-width:560px}}
.btn{{background:#fff;color:#c8102e;font-weight:700;padding:12px 26px;border-radius:10px;text-decoration:none;font-size:15px;white-space:nowrap}}
.btn:hover{{background:var(--gold);color:#111}}
footer{{border-top:1px solid var(--bd);margin-top:60px;background:#070b12}}
.f-in{{max-width:1200px;margin:0 auto;padding:34px 20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:26px;font-size:13.5px;color:var(--tx2)}}
.f-in h4{{color:var(--tx);margin-bottom:8px;font-size:14px}}
.f-in a{{color:var(--tx2);text-decoration:none;display:block;padding:2px 0}}.f-in a:hover{{color:var(--gold)}}
.f-bot{{border-top:1px solid var(--bd);padding:14px 20px;text-align:center;font-size:12px;color:#64748b}}
@media(max-width:860px){{.nav-menu{{display:none}}}}
</style>
{schema}
</head>
<body>
<nav class="navbar"><div class="nav-inner">
  <a href="../index.html" class="nav-brand"><img src="../assets/VEHICLE-logo-nav.jpg" alt="Globalucar" class="nav-logo" onerror="this.style.display='none'"><span class="nav-tagline">Car &amp; Auto Parts One-Stop Solution</span></a>
  <ul class="nav-menu">
    <li><a href="../index.html">Home</a></li><li><a href="../products.html">Products</a></li>
    <li><a href="../parts-finder.html">Parts Finder</a></li><li><a href="../kingmay.html">Kingmay Parts</a></li>
    <li><a href="../services.html">Services</a></li><li><a href="../blog.html">Blog</a></li>
    <li><a href="../contact.html">Contact</a></li>
  </ul>
</div></nav>
<div class="wrap">
  <div class="crumb"><a href="../index.html">Home</a> › <a href="index.html">OE Reference</a> › <a href="{bucket}.html">{esc(BUCKET_TITLE.get(bucket, 'Parts'))}</a> › <span>{esc(oe)}</span></div>
  <h1>OE <span class="oe-n">{esc(oe)}</span> — {esc(part)} for {esc(brand)}</h1>
  <p class="lead">{esc(intro)}</p>

  <section class="oe-sec ans-blk">
    <h2>At a Glance</h2>
    <p class="ans-p">{esc(ans)}</p>
  </section>

  <section class="oe-sec">
    <h2>Quick Reference</h2>
    <div class="oe-card">
      <div class="oe-kv"><b>OE Number</b><span class="hl">{esc(oe)}</span></div>
      <div class="oe-kv"><b>Component</b><span>{esc(part)}</span></div>
      <div class="oe-kv"><b>Brand Coverage</b><span>{esc(brand)}</span></div>
      <div class="oe-kv"><b>System</b><span>{esc(BUCKET_TITLE.get(bucket, e.get('system') or 'Auto Parts'))}</span></div>
      <div class="oe-kv"><b>Wholesale Price</b><span>{esc(price)}</span></div>
      <div class="oe-kv"><b>MOQ</b><span>{esc(moq)}</span></div>
      <div class="oe-kv"><b>Availability</b><span>In stock — Guangzhou</span></div>
      <div class="oe-kv"><b>KingMay No.</b><span>{esc(e.get('kingmay_no') or 'On request')}</span></div>
    </div>
  </section>

  <section class="oe-sec">
    <h2>Part Number Structure</h2>
    <p>How {esc(oe)} decodes in the Hyundai-Kia catalog system. The prefix identifies the component family; the suffix carries model and variant information.</p>
    <div class="oe-tbl-wrap"><table class="oe-tbl">
      <thead><tr><th>Field</th><th>Value</th></tr></thead>
      <tbody>
        <tr><td>Full reference</td><td><b>{esc(oe)}</b></td></tr>
        <tr><td>Normalized (no hyphen)</td><td>{esc(norm_key)}</td></tr>
        <tr><td>Prefix (family code)</td><td>{esc(pfx)}</td></tr>
        <tr><td>Prefix maps to</td><td>{esc(fam_label if fam_label else part + ' (this reference)')}</td></tr>
        <tr><td>References sharing prefix {esc(pfx)}</td><td>{fam_count if fam_count else '1'} in KingMay catalog</td></tr>
        <tr><td>Numbering family</td><td>{'Hyundai-Kia 5+5 format' if re.match(r'^[0-9]{5}', oe_key) else 'Manufacturer reference format'}</td></tr>
      </tbody>
    </table></div>
  </section>
{img_html}
{fit_html}
{rel_html}
  <section class="oe-sec">
    <h2>Logistics &amp; Packaging</h2>
    <div class="oe-tbl-wrap"><table class="oe-tbl">
      <thead><tr><th>Item</th><th>Detail</th></tr></thead>
      <tbody>
        <tr><td>Export packing</td><td>Neutral carton, inner foam protection; custom labels on request</td></tr>
        <tr><td>Lead time</td><td>7 working days (stock) · 25-35 days (production run)</td></tr>
        <tr><td>Shipping terms</td><td>FOB Guangzhou / Shenzhen; CIF &amp; DDP negotiable</td></tr>
        <tr><td>Payment</td><td>T/T, LC at sight for contracts; sample orders by T/T</td></tr>
        <tr><td>QC documentation</td><td>Packing list + photo report + dimension check per shipment</td></tr>
      </tbody>
    </table></div>
  </section>

  <section class="oe-sec">
    <h2>People Also Ask</h2>
    <p>The questions below are the ones buyers raise most often about OE {esc(oe)} — fitment, fault symptoms, cross-references, pricing and export terms. Each answer is written to be quotable on its own.</p>
    <div class="faq">
{chr(10).join(f'      <details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in faqs)}
    </div>
  </section>
{rel_search_html}

  <section class="oe-sec">
    <h2>Sourcing &amp; Export Terms</h2>
    <p>{esc(cta)} All {esc(oe)} shipments leave with a packing list, photo documentation and QC report. Combined orders with other Hyundai-Kia references can share one container to cut landed cost. Payment terms are negotiable for established distributors; first-time buyers are welcome to start with a sample lot.</p>
  </section>

  <div class="cta">
    <div><h3>Get a quote on OE {esc(oe)}</h3><p>Send quantity + destination port. Quotations typically return within one business day.</p></div>
    <a class="btn" href="../contact.html">Request Quotation</a>
  </div>
</div>
<footer><div class="f-in">
  <div><h4>KingMay Auto Parts</h4>Guangzhou Globalucar Vehicle Trading Co., Ltd.<br>OEM-grade parts export since 2013.<br>30,000+ SKUs · 50+ brands.</div>
  <div><h4>Quick Links</h4><a href="../products.html">All Products</a><a href="../parts-finder.html">Parts Finder</a><a href="../kingmay.html">Kingmay Parts</a><a href="../blog.html">Blog</a></div>
  <div><h4>OE Reference</h4><a href="index.html">OE Number Hub</a><a href="engine.html">Engine &amp; Fuel</a><a href="suspension-steering.html">Suspension &amp; Steering</a><a href="electrical.html">Electrical &amp; Sensors</a></div>
  <div><h4>Contact</h4>Miss UU (Auto Parts)<br><a href="mailto:ku@kingmay-autoparts.com">ku@kingmay-autoparts.com</a><br>+86 133 0240 8528</div>
</div><div class="f-bot">&copy; 2013-2026 Guangzhou Globalucar Vehicle Trading Co., Ltd. All rights reserved.</div></footer>
</body>
</html>'''

def hub_html(buckets):
    links = '\n'.join(
        f'      <a class="hub-card" href="{b}.html"><b>{esc(BUCKET_TITLE[b])}</b><span>{n} OE references</span></a>'
        for b, n in sorted(buckets.items(), key=lambda x: -x[1]))
    total = sum(buckets.values())
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OE Number Reference Hub — {total}+ Verified Part Numbers | KingMay</title>
<meta name="description" content="Search {total}+ verified OE numbers for Hyundai, Kia and other makes. Fitment data, cross references and wholesale sourcing from KingMay Auto Parts, Guangzhou.">
<link rel="canonical" href="{SITE}/oe/">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#0a0e17;color:#f1f5f9;line-height:1.6}}
.wrap{{max-width:1000px;margin:0 auto;padding:60px 20px}}
h1{{font-size:30px;margin-bottom:10px}}h1 span{{color:#f59e0b}}
.lead{{color:#94a3b8;max-width:760px;margin-bottom:30px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}}
.hub-card{{background:#1a2234;border:1px solid #2a3550;border-radius:12px;padding:18px;text-decoration:none;color:#f1f5f9;display:flex;flex-direction:column;gap:4px}}
.hub-card:hover{{border-color:#c8102e}}
.hub-card b{{font-size:16px}}.hub-card span{{color:#94a3b8;font-size:13px}}
</style>
</head>
<body><div class="wrap">
<h1>OE Number Reference Hub — <span>{total}+ references</span></h1>
<p class="lead">Verified OE part numbers with fitment notes, cross references and export terms. KingMay specialises in Hyundai-Kia parts and sources other makes through its verified multi-brand supplier network. Browse by system, or search an OE number directly from the <a href="../oem-parts-lookup.html" style="color:#f59e0b">OE lookup tool</a>.</p>
<div class="grid">
{links}
</div>
</div></body></html>'''

def bucket_html(b, items):
    rows = '\n'.join(
        f'      <tr><td><a href="{slug_oe(e["oe"])}.html">{esc(e["oe"])}</a></td><td>{esc((e.get("part_name") or "—")[:70])}</td><td>{esc("/".join(e.get("brand") or [])[:30])}</td></tr>'
        for e in items)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(BUCKET_TITLE[b])} OE Numbers — {len(items)} References | KingMay Auto Parts</title>
<meta name="description" content="Browse {len(items)} OE part numbers for {esc(BUCKET_TITLE[b].lower())}. Hyundai-Kia wholesale sourcing with fitment data from KingMay Auto Parts.">
<link rel="canonical" href="{SITE}/oe/{b}.html">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#0a0e17;color:#f1f5f9;line-height:1.6}}
.wrap{{max-width:1000px;margin:0 auto;padding:50px 20px}}
h1{{font-size:26px;margin-bottom:8px}}.lead{{color:#94a3b8;margin-bottom:24px}}
a{{color:#60a5fa;text-decoration:none}}a:hover{{text-decoration:underline}}
.tblw{{overflow-x:auto;border:1px solid #2a3550;border-radius:12px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th{{background:#101827;color:#f59e0b;text-align:left;padding:10px 14px;font-size:12.5px;text-transform:uppercase}}
td{{padding:9px 14px;border-top:1px solid #2a3550}}
</style>
</head>
<body><div class="wrap">
<h1>{esc(BUCKET_TITLE[b])} — {len(items)} OE References</h1>
<p class="lead">OE references in this category, each with a dedicated sourcing page. KingMay specialises in Hyundai-Kia parts and sources other brands through its verified multi-brand supplier network. <a href="index.html">All categories</a>.</p>
<div class="tblw"><table><thead><tr><th>OE Number</th><th>Component</th><th>Brand</th></tr></thead>
<tbody>
{rows}
</tbody></table></div>
</div></body></html>'''

def update_sitemap(urls):
    p = os.path.join(BASE, 'sitemap.xml')
    s = open(p, encoding='utf-8').read()
    # 幂等: 先移除旧的 /oe/ 条目
    import re as _re
    s = _re.sub(r'\n?\s*<url><loc>' + _re.escape(SITE) + r'/oe/[^<]*</loc>.*?</url>', '', s)
    add = ''.join(
        f'\n  <url><loc>{SITE}/oe/{u}</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>'
        for u in urls)
    s = s.replace('</urlset>', add + '\n</urlset>')
    open(p, 'w', encoding='utf-8').write(s)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--allowlist', default=None,
                    help='单个 allowlist 文件名(相对 .workbuddy/data/), 不传则默认 batch1+batch2')
    ap.add_argument('--allowlists', default='ALL',
                    help="多个 allowlist 文件名, 逗号分隔; 'ALL' = 自动发现 .workbuddy/data/ 下所有 oe-*-allowlist.json")
    ap.add_argument('--strict-allowlist', action='store_true',
                    help='只出 allowlist 内的条目, 不再自动包含 confidence=A/B/B2 的全部条目 (用于分批逐步发布)')
    ap.add_argument('--limit', type=int, default=0,
                    help='限制出页数量(测试用), 0 = 全部')
    args = ap.parse_args()

    db = json.load(open(DB_P, encoding='utf-8'))
    os.makedirs(OE_DIR, exist_ok=True)
    # A/B/B2 出页 + 批次 allowlist (C/C2 分批上线, 见 prepare_oe_batch*.py)
    names = [args.allowlist] if args.allowlist else [n.strip() for n in args.allowlists.split(',') if n.strip()]
    if names == ['ALL']:
        names = sorted(os.path.basename(p) for p in
                       glob.glob(os.path.join(BASE, '.workbuddy', 'data', 'oe-*allowlist*.json')))
    allow = set()
    loaded = []
    for name in names:
        p = os.path.join(BASE, '.workbuddy', 'data', name)
        if os.path.exists(p):
            s = set(json.load(open(p, encoding='utf-8')))
            allow |= s
            loaded.append(f'{name}({len(s)})')
        else:
            loaded.append(f'{name}(missing)')
    # allowlist 存 DB key(无连字符); e['oe'] 字段可能带连字符, 两种都匹配
    if args.strict_allowlist:
        # 逐步发布模式: 出页范围完全由 allowlist 决定, 避免 A/B/B2 一次全量上线
        elig = [e for k, e in db.items() if k in allow or e.get('oe') in allow]
    else:
        elig = [e for k, e in db.items() if e['confidence'] in ('A', 'B', 'B2') or k in allow or e.get('oe') in allow]
    if args.limit > 0:
        elig = elig[:args.limit]
    print(f'出页范围: A/B/B2 + {" + ".join(loaded)} → {len(elig)} 页')
    by_bucket = defaultdict(list)
    for e in elig:
        b = SYSTEM_BUCKET.get(e.get('system') or '', None)
        if not b:
            # 按部件名猜
            nm = (e.get('part_name') or '').lower()
            if re.search(r'shock|arm|rod|joint|stabili|bearing|bushing|spring', nm): b = 'suspension-steering'
            elif re.search(r'sensor|coil|switch|alternator|starter|window|motor', nm): b = 'electrical'
            elif re.search(r'pump|radiator|thermostat|coolant|fan|compressor', nm): b = 'cooling'
            elif re.search(r'brake|pad|caliper|disc', nm): b = 'brake'
            elif re.search(r'belt|chain|gear|clutch|transmiss', nm): b = 'transmission'
            elif re.search(r'gasket|piston|camshaft|engine|mount|injector|plug|vvt|pcv', nm): b = 'engine'
            elif re.search(r'mirror|lamp|bumper|handle|glass', nm): b = 'body'
            else: b = 'engine'
        e['_bucket'] = b
        by_bucket[b].append(e)
    # 桶内按 OE 排序 —— 让输出完全确定。
    # 坑: 不排序的话顺序取决于 oe-master-db.json 的键顺序, 而并库脚本重 dump 一次
    #     顺序就会变, 导致「Related OE References」表整体重排 → 数千页无意义重写,
    #     sitemap 的 lastmod 也会被整体刷新, 稀释 Google 的抓取优先级。
    for b in by_bucket:
        by_bucket[b].sort(key=lambda x: (x.get('oe') or '').lower())
    # 生成单页
    n = 0
    skipped = 0
    for b, items in by_bucket.items():
        for i, e in enumerate(items):
            # 防护: OE 必须是合法文件名字符
            if not re.match(r'^[0-9A-Za-z\-]+$', e.get('oe') or ''):
                skipped += 1
                continue
            related = [r for j, r in enumerate(items) if j != i and
                       (r.get('part_name') or '')[:18] == (e.get('part_name') or '')[:18]]
            if len(related) < 3:
                same_sys = [r for j, r in enumerate(items) if j != i]
                related = (related + same_sys)[:8]
            html = page_html(e, related[:8], b)
            open(os.path.join(OE_DIR, slug_oe(e['oe']) + '.html'), 'w', encoding='utf-8').write(html)
            n += 1
    if skipped:
        print(f'跳过非法 OE 条目: {skipped}')
    # hub + L2
    counts = {b: len(items) for b, items in by_bucket.items()}
    open(os.path.join(OE_DIR, 'index.html'), 'w', encoding='utf-8').write(hub_html(counts))
    for b, items in by_bucket.items():
        open(os.path.join(OE_DIR, b + '.html'), 'w', encoding='utf-8').write(bucket_html(b, items))
    # sitemap ── 以磁盘实际存在的 OE 页为准
    # 坑: 若只写本次 elig, 换用 --strict-allowlist / 分批发布时会收窄 sitemap, 把
    # 历史批次(以及 DB 里已无对应记录的存量页)从 sitemap 里抹掉。改为扫盘最稳。
    bucket_pages = sorted(set([b + '.html' for b in by_bucket]) |
                          {f for f in os.listdir(OE_DIR) if f.endswith('.html') and f[:-5] in BUCKET_TITLE})
    urls = [''] + bucket_pages + live_oe_pages()
    update_sitemap(urls)
    print(f'生成 {n} 个单OE页 + 1 hub + {len(by_bucket)} 个系统页')
    print('桶分布:', {b: len(v) for b, v in sorted(by_bucket.items(), key=lambda x: -len(x[1]))})
    # 配图覆盖: 必须带 bucket 才能触发系统兜底图, 否则会严重低估(历史误报 58% vs 实际 100%)
    n_img = sum(1 for e in elig if find_image(e, e.get('_bucket')))
    print(f'配图覆盖: {n_img}/{len(elig)}')
    # 全站 OE 数字同步: 一律以 live_oe_pages() 扫盘为准(允许无连字符的纯数字 OE,
    # 之前用 '^[0-9a-z]+(?:-[0-9a-z]+)+\.html$' 会漏掉 0000901651.html 这类, 数字虚低)
    actual_n = len(live_oe_pages())
    sync_site_stats(max(actual_n, n))


def sync_site_stats(n):
    """写 oe/stats.json + assets/data/site-stats.json, 同步全站 [data-*] 静态回退数字
    (index / lookup / parts-finder / products 等). 自动从 products-data.json 统计
    新车/二手车/配件 + parts/*.html 实际数. 数字会真实反映当前目录, 与历史批次无关."""
    import datetime
    # ── 1) OE 页数 = 本次跑过的 n + 磁盘已存在的其他历史 OE 页 (含本次未在 elig 的)
    # 坑: 不能只匹配"含连字符"的文件名——纯数字 OE(0000901651.html)会被漏掉导致数字虚低
    _non_oe = {'index.html'}
    actual_oe = len([f for f in os.listdir(OE_DIR)
                     if f.endswith('.html')
                     and re.match(r'^[0-9a-z]+(?:-[0-9a-z]+)*\.html$', f)
                     and f not in _non_oe
                     and not re.match(r'^(engine|cooling|electrical|body|brake|transmission|'
                                      r'suspension-steering|sensors-na|stats|sitemap)', f)])
    oe_pages = max(n, actual_oe)
    # ── 2) 产品页数 (parts/<slug>.html)
    parts_dir = os.path.join(BASE, 'parts')
    parts_skus = len([f for f in os.listdir(parts_dir)
                      if f.endswith('.html') and not f.endswith('-sitemap.html')])
    # ── 3) 新车/二手车/配件分类数 (从 products-data.json)
    prod_data_p = os.path.join(BASE, 'products-data.json')
    new_cars = used_cars = 0
    if os.path.exists(prod_data_p):
        try:
            d = json.load(open(prod_data_p, encoding='utf-8'))
            new_cars = sum(1 for p in d if p.get('category') == 'new_car')
            used_cars = sum(1 for p in d if p.get('category') == 'used_car')
        except Exception:
            pass
    products_total = parts_skus + new_cars + used_cars

    # ── 4) 写两份 stats: 旧的 oe/stats.json (兼容老 fetch) + 新的统一端点
    stats = {
        'oe_pages': oe_pages,
        'parts_skus': parts_skus,
        'new_cars': new_cars,
        'used_cars': used_cars,
        'products_total': products_total,
        'oe_hub_url': SITE + '/oe/',
        'updated': datetime.date.today().isoformat(),
    }
    # 旧端点
    open(os.path.join(OE_DIR, 'stats.json'), 'w', encoding='utf-8').write(
        json.dumps({'oe_pages': oe_pages,
                    'oe_hub_url': SITE + '/oe/',
                    'updated': stats['updated']},
                   ensure_ascii=False, indent=2))
    # 新端点 - 统一 site-stats
    site_stats_p = os.path.join(BASE, 'assets', 'data', 'site-stats.json')
    os.makedirs(os.path.dirname(site_stats_p), exist_ok=True)
    open(site_stats_p, 'w', encoding='utf-8').write(
        json.dumps(stats, ensure_ascii=False, indent=2))

    oe_label = f'{oe_pages:,}+'
    parts_label = f'{parts_skus:,}+'
    new_label = f'{new_cars:,}+'
    used_label = f'{used_cars:,}+'
    total_label = f'{products_total:,}+'

    pages = [
        # ── OE 数字 (老机制) ──
        ('index.html', [
            (r'(<strong data-oe-count>)[\d,]+\+?(</strong>)', r'\g<1>' + oe_label + r'\g<2>'),
            (r'(<strong data-oe-count-inline>)[\d,]+\+?(</strong>)', r'\g<1>' + oe_label + r'\g<2>'),
            # ── 配件 SKU 数字 ──
            (r'(<span data-parts-skus>)[\d,]+\+?(</span>)', r'\g<1>' + parts_label + r'\g<2>'),
            (r'(<strong data-parts-skus>)[\d,]+\+?(</strong>)', r'\g<1>' + parts_label + r'\g<2>'),
            # ── 总产品数 (支持 <span data-products-total> 和 <span class="stat-num" data-products-total>) ──
            (r'(<span data-products-total>)[\d,]+\+?(</span>)', r'\g<1>' + total_label + r'\g<2>'),
            (r'(<strong data-products-total>)[\d,]+\+?(</strong>)', r'\g<1>' + total_label + r'\g<2>'),
            (r'(<span class="[^"]*" data-products-total>)[\d,]+\+?(</span>)', r'\g<1>' + total_label + r'\g<2>'),
            # ── 新车 / 二手车 ──
            (r'(<span data-new-cars>)[\d,]+\+?(</span>)', r'\g<1>' + new_label + r'\g<2>'),
            (r'(<span data-used-cars>)[\d,]+\+?(</span>)', r'\g<1>' + used_label + r'\g<2>'),
        ]),
        ('oem-parts-lookup.html', [
            (r'(<div class="stat-number" data-oe-count>)[\d,]+\+?(</div>)', r'\g<1>' + oe_label + r'\g<2>'),
            (r'(<div class="stat-number" data-parts-skus>)[\d,]+\+?(</div>)', r'\g<1>' + parts_label + r'\g<2>'),
        ]),
        ('parts-finder.html', [
            (r'(<span data-oe-count>)[\d,]+\+?(</span>)', r'\g<1>' + oe_label + r'\g<2>'),
            (r'(<span data-parts-skus>)[\d,]+\+?(</span>)', r'\g<1>' + parts_label + r'\g<2>'),
        ]),
        ('products.html', [
            (r'(<span data-parts-skus>)[\d,]+\+?(</span>)', r'\g<1>' + parts_label + r'\g<2>'),
            (r'(<span data-products-total>)[\d,]+\+?(</span>)', r'\g<1>' + total_label + r'\g<2>'),
            (r'(<span data-new-cars>)[\d,]+\+?(</span>)', r'\g<1>' + new_label + r'\g<2>'),
            (r'(<span data-used-cars>)[\d,]+\+?(</span>)', r'\g<1>' + used_label + r'\g<2>'),
        ]),
    ]
    n_synced = 0
    for page, rules in pages:
        p = os.path.join(BASE, page)
        if not os.path.exists(p):
            continue
        src = open(p, encoding='utf-8').read()
        out = src
        for pat, rep in rules:
            out = re.sub(pat, rep, out)
        if out != src:
            open(p, 'w', encoding='utf-8', newline='').write(out)
            n_synced += 1
    print(f'全站数字已同步: OE {oe_label} | parts {parts_label} | new {new_label} | used {used_label} | total {total_label}')
    print(f'  → {n_synced} 页面 + 2 个 stats.json (oe/stats.json + assets/data/site-stats.json)')

if __name__ == '__main__':
    main()
