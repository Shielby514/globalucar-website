# Google 3月核心算法更新应对策略 — Globalucar 内容质量指南

> 📅 制定日期：2026年4月14日
> 🎯 目标：确保 global-ucars.com 全站内容符合 Google 2026年3月核心算法更新的质量要求

---

## 一、算法更新核心要点（已学习并融入规则）

| 规则 | 具体执行标准 |
|------|------------|
| ✍️ **原创详实** | 产品描述、参数、用途、优势必须具体、真实、有价值。不直接复制竞品，不套用模板简单拼凑 |
| ✅ **信息真实** | 不夸大、不虚假、不误导。所有数据可验证，增强页面信任度 |
| 🧹 **清理低质** | 旧产品页/文章及时优化或下架，低质页面拉低整站质量 |
| 💡 **文章深度** | 博客要有实用信息、有独特视角，少抄少改，原创度优先 |
| 🔑 **自然关键词** | 关键词自然融入，读起来通顺优先，避免堆砌 |
| 📢 **内容打理** | 定期检查旧文章，清理无用内容，为核心内容腾空间 |

---

## 二、现有博客质量审查结果

### 总览

| 评级 | 数量 | 占比 | 文章 |
|------|------|------|------|
| **A/A+** | 4篇 | 36% | id=1(OEM vs Aftermarket), id=9(PHEV东南亚), id=10(刹车件), id=11(澳洲二手车) |
| **A-** | 4篇 | 36% | id=2(新车进口), id=5(二手车出口), id=7(悬挂件), id=12(电气件) |
| **B+/B** | 3篇 | 27% | id=3(传感器), id=4(南沙港), id=6(冷却系统) |
| **⚠️ 高风险** | 1篇 | 9% | id=8(EV出口) — 内容最薄，需紧急优化 |

### 共性问题

1. **图片不足**：仅 id=12 配有4张内嵌图片，其余11篇纯文字+表格
2. **数据来源缺失**：多篇文章引用市场规模数据但未标注来源
3. **CTA格式雷同**：每篇结尾都是"Browse catalog / Contact us"硬链接
4. **作者信息缺失**：Schema author 标记为 Organization，无数值化 E-E-A-T
5. **内链不够**：文章间缺少交叉引用

---

## 三、紧急优化任务（优先级排序）

### 🔴 P0 — 立即处理

#### 1. 扩充 id=8（EV出口2026）
- **现状**：~950词，6章节中3个过于简短（充电标准/电池法规/RoRo vs Container各仅1段）
- **目标**：扩展至 1,800+ 词
- **具体措施**：
  - 增加分市场（非洲/中东/拉美）的具体EV认证要求
  - 增加「主要EV品牌出口就绪状态对比」（BYD / MG / NIO / GWM / XPENG）
  - 充实 RoRo vs Container 章节（增加成本对比表、保险考量、航线案例）
  - 增加售后备件供应链规划章节
  - 或考虑与 id=9（PHEV东南亚）整合为「中国新能源车出口综合指南」

#### 2. 优化 id=3（发动机传感器）
- **现状**：5个传感器结构完全一致（原理→故障码→价格），读起来像产品目录
- **目标**：打破模板化，增加深度
- **具体措施**：
  - 增加传感器类型对比分析（如 O2 宽带 vs 窄带的采购选择）
  - 增加「如何辨别劣质传感器」实操内容（外观/重量/连接器做工）
  - 增加「同一OE号不同供应商价格差3倍」的行业分析
  - 目标扩展至 1,300+ 词

#### 3. 优化 id=6（冷却系统零部件）
- **现状**：AC压缩机仅2段，各部件段落高度模板化
- **目标**：充实 AC压缩机，增加供应商评估案例
- **具体措施**：
  - 扩展 AC压缩机章节至与水泵章节同等深度
  - 增加「好/差样品对比」经验分享
  - 增加市场数据来源标注
  - 目标扩展至 1,500+ 词

### 🟡 P1 — 本月内完成

#### 4. 全站博客补充图片
- 每篇文章至少添加 2-3 张图片
- 优先使用现有 `assets/parts/` 和 `assets/products/` 库存图
- 图文搭配类型：产品特写、参数对比图、流程示意

#### 5. 数据来源标注
- 所有市场规模数据旁加注来源
- 格式参考：`Source: IHS Markit, 2025` 或 `Source: China Customs Statistics`

#### 6. CTA多样化
- 交替使用不同 CTA 形式：
  - 「分享你的采购经验」
  - 「下载验货检查清单」
  - 「联系我们获取定制方案」
  - 「免费获取产品对比报告」
  - 保留部分现有硬链接但混排

### 🟢 P2 — 持续改进

#### 7. 作者署名增强 E-E-A-T
- 技术文章添加具名作者 + Expertise 标签
- 格式：`Written by [Name], [Title] at Globalucar`
- 更新 Schema.org author 为 Person 类型

#### 8. 文章间交叉内链
- id=1 (OEM vs Aftermarket) → 链接 id=7(悬挂件) / id=10(刹车件)
- id=5 (二手车出口) → 链接 id=11(澳洲市场)
- id=8 (EV出口) → 链接 id=9 (PHEV东南亚)
- id=6 (冷却系统) → 链接 id=3 (传感器)

---

## 四、后续内容创作规则（新文章必须遵守）

### 质量标准

| 维度 | 最低要求 | 理想状态 |
|------|---------|---------|
| **字数** | 1,500 词 | 2,000+ 词 |
| **原创度** | 行业知识重构，不抄不改 | 独家数据/案例/经验 |
| **数据支撑** | 关键声明有出处 | 表格+案例+计算示例 |
| **图片** | ≥2张配图 | ≥4张（产品+场景+图表） |
| **关键词** | 自然融入，不堆砌 | 核心词出现在H2/首段/图片alt |
| **E-E-A-T** | 作者署名+公司背书 | 专家作者+引用第三方 |

### 内容创作红线

- ❌ 不直接复制竞品文章（Google 检测重复内容的门槛极低）
- ❌ 不使用"streamlined / seamless / cutting-edge / game-changer"等AI高频词
- ❌ 不虚构数据或夸大效果
- ❌ 不堆砌关键词（密度控制在 1-2%）
- ❌ 不发布纯列表/目录型内容（至少有一段深度分析）
- ❌ 不使用完全相同的CTA模板

---

## 五、内容发布方向（2026年5月-9月）

> ⚠️ **重要更新（2026-05-21）**：根据业务方向调整，取消二手车文章计划，聚焦**新车出口**和**汽配采购**两条主线。
>
> ⚠️ **SEO方向调整（2026-05-22）**：基于 KingMay 月度策略报告，**韩系车配件（Hyundai/Kia）+ KSA中东市场**上升为汽配内容核心支柱。Amazon汽配搜索SOV暴跌41%，独立站SEO迎来黄金窗口期。

### 🔧 汽配方向 — SEO流量优先级最高（每月1-2篇）

> **核心理由**：策略报告显示 "Hyundai spare parts wholesale" 月搜索量 3,500+、"aftermarket Hyundai brake pads" 4,500+、"Hyundai Elantra parts online" 6,000+、"Hyundai Tucson spare parts price" 5,000+——这些都是B2B交易型高价值关键词，当前独立站竞品少、排名机会大。

| 优先级 | 周次 | 选题方向 | 核心SEO关键词（预估月搜索量） | 目标客户 | 融入品牌 |
|--------|------|---------|---------------------------|---------|---------|
| 🔥🔥🔥 | W4 May | **Hyundai/Kia刹车片采购指南：OEM vs Aftermarket** | aftermarket Hyundai brake pads (4.5K) / Kia Sportage brake pads (3K) | 维修店/批发商/渠道商 | Hyundai/Kia |
| 🔥🔥🔥 | W2 Jun | **Hyundai Tucson/Santa Fe配件价格指南** | Hyundai Tucson spare parts price (5K) / Santa Fe parts online (2K) | 批发商/中间商 | Hyundai |
| 🔥🔥🔥 | W4 Jun | **中国汽配发货沙特：物流、关税与清关指南** | auto spare parts China to Saudi Arabia (1.2K) / shipping auto parts KSA (800) | 批发商/中间商 | 多品牌 |
| 🔥🔥 | W1 Jul | **Hyundai/Kia夏季高更换配件清单（中东高温适配）** | summer car maintenance Middle East (800) / Hyundai AC parts Dubai (1.5K) | 维修店/渠道商 | Hyundai/Kia |
| 🔥🔥 | W2 Jul | **Hyundai Elantra配件全目录：进口商采购手册** | Hyundai Elantra parts online (6K) / Elantra spare parts wholesale (2K) | 批发商/维修店 | Hyundai |
| 🔥🔥 | W3 Jul | **悬挂系统年度采购指南** | control arm replacement cost / suspension parts wholesale | 批发商/维修店 | 丰田/本田/Hyundai |
| 🔥🔥 | W1 Aug | **Kia Sportage/Seltos配件批发商完整指南** | Kia Sportage parts wholesale (2.5K) / Kia Seltos parts (1.5K) | 批发商/渠道商 | Kia |
| 🔥🔥 | W2 Aug | **OEM-Grade中国汽配品质认证与验货指南** | Chinese auto parts quality (1.5K) / OEM grade parts China (800) | 所有B2B | 多品牌 |
| 🔥 | W3 Aug | **发电机/起动机/电气系统：B2B采购指南** | alternator wholesale China / starter motor supplier | 批发商/维修店 | 丰田/本田/Hyundai |
| 🔥 | W1 Sep | **中国汽配出口沙特：2026进口法规与SABER认证** | Saudi Arabia auto parts import / SABER certification (1K) | 大型批发商 | 多品牌 |

### 🚗 新车出口方向（每月1篇）

| 优先级 | 周次 | 选题方向 | 核心SEO关键词 | 融入品牌 |
|--------|------|---------|-------------|---------|
| 🔥 | W1 Jun | 中东EV充电基础设施 | 中东EV充电标准, BYD, 充电桩 | BYD/极氪 |
| 🔥 | W3 Jun | 国产新能源SUV出口东南亚 | 奇瑞瑞虎, 长安CS75, 东南亚进口 | 奇瑞/长安/BYD |
| 🔥 | W3 Jul | 墨西哥/巴西市场中国品牌准入 | INMETRO, NOM, 拉美认证 | BYD/奇瑞/名爵 |
| 🔥 | W2 Aug | 拉美市场整车进口关税指南 | 拉美关税, CIF价格, 清关 | 多品牌 |

### 📅 发布节奏（自动化任务）

- **每周一**：定时提醒选题
- **每周三前**：完成初稿
- **每周四**：审核发布
- **每周五**：git push 部署
- **频率**：每两周1篇（整车与汽配交替）或两周连续汽配（当汽配优先级更高时）
- **SEO优先原则**：当月如果发现新的高搜索量关键词缺口，优先安排汽配文章

---

## 六、产品页优化方向

### 现有产品数据（202条）

需要确保所有产品描述符合新算法要求：

1. **描述非模板化**：每款产品至少有一句差异化描述（不是所有"High quality, competitive price"）
2. **参数真实准确**：确保发动机参数、尺寸、价格区间真实
3. **低质产品页清理**：检查是否有内容单薄的产品页（少于50字描述），适当补充或下架
4. **图片完整性**：所有202条产品都应有对应图片

### 汽配产品图片-OEM一致性校验（2026-04-14 启动）

**问题**：100款汽配产品图片与OEM号标题不完全匹配，专业客户可能认为不够专业。

**校验工具**：`auto-parts-image-audit.xlsx`（自动生成，包含以下字段）

| 字段 | 用途 |
|------|------|
| ID / System | 产品编号 + 4大系统分类 |
| Current Image | 当前产品图片文件名 |
| Product Title | 产品标题（含品牌+OE号） |
| Current OEM Part Number | 当前OEM号 |
| Product Link | 网站详情页超链接（可直接点击查看） |
| **Correct OEM** | ⬅️ 同事填写正确OEM号 |
| **Image Match?** | ⬅️ 同事判断图片是否匹配（Yes/No） |
| **Correct Image** | ⬅️ 同事提供正确图片文件名 |
| **Image Source** | ⬅️ 图片来源（实拍/供应商/1688等） |
| Alt Text / Meta Title / Meta Description | 现有SEO字段（供参考/优化） |

**工作流程**：
1. 产品同事填写 Excel 黄色列（G-J）
2. 标记图片不匹配的产品
3. 同事提供正确产品图片（实拍或供应商原图）
4. AI 基于人工提供的正确图片进行背景美化（统一风格、专业背景）
5. 更新 `products-data.json` 中的图片路径、OEM号、alt_text、meta_title、meta_description
6. 运行 `regen_inline_from_json.py` 重新生成 `products-inline.js`
7. Git push 部署到 GitHub Pages

**4大系统产品分布**：

| 系统 | 数量 | 主要子类 |
|------|------|---------|
| 🔴 Engine | 31款 | 传感器、点火线圈、喷油嘴、燃油泵、节气门、密封件等 |
| 🔵 Cooling | 11款 | 水泵、散热器、风扇、恒温器、AC压缩机、油冷器等 |
| 🟡 Suspension | 52款 | 控制臂、球头、转向拉杆、减震器、轮毂轴承、衬套等 |
| ⚡ Electrical | 6款 | 发电机、起动机、ABS传感器、线束等 |

---

## 七、品牌融入策略（SEO方向覆盖）

### 目标品牌矩阵

| 地区 | 代表品牌 | 覆盖产品线 | 优先级 |
|------|---------|-----------|--------|
| 🇨🇳 国产 | BYD, 奇瑞, 长安, 吉利, MG, 捷途, 极氪, 小米, Wuling | 整车出口 | ⭐⭐⭐ |
| 🇯🇵 日系 | Toyota, Nissan, Honda, Mazda, Subaru | 整车+汽配(OEM件) | ⭐⭐⭐ |
| 🇰🇷 韩系 | Hyundai, Kia | 整车+汽配(OEM件) | ⭐⭐ |
| 🇩🇪🇪🇺 欧系 | BMW, Mercedes, VW, Audi, Porsche | 二手车+汽配 | ⭐⭐ |
| 🇺🇸 美系 | Ford, Chevrolet, GMC | 二手车+汽配 | ⭐ |

### 内容融入方式

- **整车文章**：直接以品牌+车型为主角（如 "Exporting BYD Seal U to Middle East"）
- **汽配文章**：以品牌OEM兼容性为切入点（如 "Control Arms for Toyota Hilux: OEM vs Quality Aftermarket"）
- **产品详情**：在描述中自然融入兼容车型信息
- **博客标签**：每篇文章至少关联 2-3 个汽车品牌标签

---

## 八、内容双线长期规划（2026年Q2-Q4）

> ⚠️ **调整说明（2026-05-22）**：基于 KingMay 月度策略报告和 Google 搜索数据分析，**韩系车配件（Hyundai/Kia）作为汽配内容核心支柱**，以 KSA/中东市场为主要流量目标。同时抓住 Amazon SOV 暴跌 41% 的独立站 SEO 黄金窗口期。

### SEO关键词分级策略

| 级别 | 关键词举例 | 预估月搜索量 | 竞争度 | 内容策略 |
|------|-----------|-------------|--------|---------|
| **Tier 1 — 核心交易词** | Hyundai Elantra parts online | 6,000+ | 中等 | 专题文章 + 产品页内链 |
| **Tier 1 — 核心交易词** | Hyundai Tucson spare parts price | 5,000+ | 中等 | 价格对比文章 + FAQ Schema |
| **Tier 1 — 核心交易词** | aftermarket Hyundai brake pads | 4,500+ | 中高 | 刹车片专题 + 产品页 |
| **Tier 1 — 核心交易词** | OEM Hyundai parts catalog | 2,800+ | 低 | 产品目录页 + 博客引导 |
| **Tier 1 — 核心交易词** | Hyundai spare parts wholesale | 3,500+ | 低-中 | B2B专题 + 联系表单 |
| **Tier 2 — 品牌批发词** | Kia auto parts supplier China | 2,200+ | 低 | 供应商介绍 + 案例文章 |
| **Tier 2 — 品牌批发词** | Korean car parts Dubai | 1,800+ | 低 | 迪拜市场文章 |
| **Tier 2 — 品牌批发词** | wholesale auto parts Middle East | 2,000+ | 中 | 批发指南文章 |
| **Tier 3 — 物流交易词** | auto spare parts China to KSA | 1,200+ | 低 | 物流指南文章 |
| **Tier 3 — 物流交易词** | shipping auto parts to Saudi Arabia | 800+ | 低 | 物流+清关文章 |

### 🔧 汽配方向 — 韩系配件专题序列（每月1-2篇）

> **策略逻辑**：围绕 Hyundai/Kia 热门车型（Tucson/Elantra/Santa Fe/Sportage/Seltos），以配件品类为主线，每个品类一篇深度文章，形成**车型×品类**的内容矩阵。

| 月份 | 选题 | 核心SEO关键词 | 车型覆盖 | 文章ID |
|------|------|-----------|---------|--------|
| 2026 May | ~~发动机大修件全套采购~~ → ✅ id=45 已发布 | 活塞/曲轴/气缸垫/大修包 | 通用 | 45 |
| 2026 Jun | **Hyundai/Kia刹车片采购：OEM vs Aftermarket** | aftermarket brake pads Hyundai/Kia (7.5K) | Tucson/Sportage/Elantra/Seltos | 50 |
| 2026 Jun | **Hyundai Tucson/Santa Fe配件价格对比** | Tucson parts price (5K) | Tucson/Santa Fe | 51 |
| 2026 Jul | **中国汽配发货沙特物流清关指南** | China to KSA auto parts (1.2K) | 全品牌 | 52 |
| 2026 Jul | **Hyundai Elantra配件进口商采购手册** | Elantra parts online (6K) | Elantra/Sonata | 53 |
| 2026 Jul | **悬挂系统年度采购指南** | suspension parts wholesale | 丰田/Hyundai/Honda | 54 |
| 2026 Aug | **Kia Sportage/Seltos配件批发指南** | Kia Sportage wholesale (2.5K) | Sportage/Seltos | 55 |
| 2026 Aug | **OEM-Grade中国汽配品质认证与验货** | Chinese parts quality (1.5K) | 全品牌 | 56 |
| 2026 Aug | **发电机/起动机电气系统采购** | alternator/starter wholesale | 丰田/Hyundai | 57 |
| 2026 Sep | **沙特汽配进口法规与SABER认证** | Saudi auto parts import (1K) | 全品牌 | 58 |
| 2026 Sep | **Hyundai/Kia滤清器全套采购指南** | Hyundai oil filter/OEM parts (2K) | 全系 | 59 |

### 🚗 新车出口方向（每月1篇）

| 月份 | 选题 | 核心关键词 | 品牌融入 | 文章ID |
|------|------|-----------|---------|--------|
| 2026 May | ~~俄罗斯市场准入~~ → ✅ id=49 已发布 | GOST/EAC/俄罗斯 | 奇瑞/长城/吉利 | 49 |
| 2026 Jun | 中东EV充电基础设施 | 中东EV充电/BYD/充电标准 | BYD/极氪 | 60 |
| 2026 Jul | 国产新能源SUV出口东南亚 | 奇瑞瑞虎/长安CS75/东南亚 | 奇瑞/长安 | 61 |
| 2026 Aug | 墨西哥/巴西市场准入 | INMETRO/NOM/拉美认证 | BYD/奇瑞/名爵 | 62 |
| 2026 Sep | 中国品牌轿车出口非洲 | MG/吉利/长安/非洲 | MG/吉利/长安 | 63 |

### 已有文章对照（避免重复）

| 已覆盖选题 | 文章ID | 状态 |
|-----------|--------|------|
| OEM vs Aftermarket综合 | id=1 | ✅ 已有 |
| 刹车件采购（通用） | id=10 | ✅ 已有（但**缺少Hyundai/Kia车型聚焦**，可写Korean Car Brake Pads专题） |
| 悬挂件（通用） | id=7 | ✅ 已有 |
| 电气系统（通用） | id=12 | ✅ 已有 |
| 冷却系统（通用） | id=6 | ✅ 已有 |
| 传感器（通用） | id=3 | ✅ 已有 |
| 排气系统 | id=16 | ✅ 已有 |
| 传动系统 | id=19 | ✅ 已有 |
| Hyundai Tucson vs Chery Tiggo 8 | id=29 | ✅ 已有 |
| Hyundai & Kia OEM Parts eBay | id=29 | ✅ 已有 |
| Auto Parts Import Duty (KSA已覆盖) | id=26 | ✅ 已有（但**缺少物流实操细节**，可写Shipping Guide专题） |
| Filter Wholesale（通用） | id=48 | ✅ 已有 |

> **关键发现**：现有汽配文章都是**通用多品牌**写法（"丰田/本田/日产/大众"），缺少**单一品牌深度聚焦**的专题。策略报告显示 "Hyundai Tucson spare parts price" 月搜索 5K+、"Hyundai Elantra parts online" 6K+——这些都是精准高转化关键词。**将通用文章升级为品牌深度专题，是最大的SEO流量增长机会。**

### 📅 发布节奏（自动化任务）

- **Blog定期发布**：每两周周一 9:00 自动触发
- 轮流发布整车（奇数期）和汽配（偶数期）文章
- 每篇最低 1,500 词 + ≥2张配图

---

## 九、Google 算法监控

### 当前自动化任务

| 任务名 | 频率 | 状态 |
|--------|------|------|
| google-2（SEO收录监控） | 每周一 9:00 | ✅ 活跃 |
| Blog定期发布 | 每两周周一 9:00 | ✅ 活跃 |

### 应对措施

- 持续关注 Google Search Console 的收录/排名数据
- 如出现流量下降，优先检查：低质页面、过度优化、内容重复
- 定期清理无索引/低流量旧内容

---

*本文档将作为后续内容创作的永久参考标准。每次写新文章/新产品前，对照本文档检查。*
*最后更新：2026-05-22*

---

## 十、SEO 关键词研究附录（2026-05-22 更新）

> 基于 KingMay 策略报告 + Google 搜索分析 + 竞品对标，以下为汽配博客的**核心关键词库**。

### 🔥 高价值B2B交易型关键词（独立站流量目标）

| 关键词 | 预估月搜索量 | 搜索意图 | 竞争度 | 建议文章/页面 |
|--------|-------------|---------|--------|-------------|
| Hyundai Elantra parts online | 6,000+ | 交易型 | 中 | Elantra配件采购手册 |
| Hyundai Tucson spare parts price | 5,000+ | 交易型 | 中 | Tucson配件价格对比 |
| aftermarket Hyundai brake pads | 4,500+ | 交易型 | 中高 | Hyundai/Kia刹车片采购 |
| OEM Hyundai parts catalog | 2,800+ | 信息/交易 | 低 | OEM配件目录引导页 |
| Hyundai spare parts wholesale | 3,500+ | B2B交易 | 低-中 | 批发专题页 |
| Kia auto parts supplier China | 2,200+ | B2B交易 | 低 | 供应商介绍文章 |
| wholesale auto parts Middle East | 2,000+ | B2B交易 | 中 | 中东批发指南 |
| Korean car parts Dubai | 1,800+ | B2B本地 | 低 | 迪拜市场文章 |
| auto spare parts China to KSA | 1,200+ | B2B物流 | 低 | 中国发货沙特指南 |
| Chinese auto parts quality review | 1,500+ | 信息型 | 低 | OEM-Grade品质认证文章 |
| Hyundai AC compressor Dubai | 1,500+ | 交易型 | 低 | 中东高温适配配件 |
| Kia Sportage parts wholesale | 2,500+ | B2B交易 | 低 | Sportage配件批发指南 |
| Kia Seltos spare parts | 1,500+ | 交易型 | 低 | Seltos配件文章 |

### 📊 内容标题TDK模板（韩系配件文章）

**Title模板**（50-60字符）：
```
{Part Type} for {Car Model}: OEM vs Aftermarket — Wholesale from China
例: Brake Pads for Hyundai Tucson: OEM vs Aftermarket — Wholesale Buyer's Guide from China
```

**Description模板**（150-160字符）：
```
Complete wholesale guide to sourcing {part type} for {car model} from China. Compare OEM vs aftermarket prices, quality grades, MOQ, and shipping to {target market}.
例: Complete guide to sourcing brake pads for Hyundai Tucson 2015-2024 from China. Compare ceramic vs semi-metallic, OEM vs aftermarket quality grades, wholesale MOQ 200 sets, and shipping costs to Saudi Arabia and UAE.
```

**核心关键词布局规则**：
- 核心关键词必须出现在：H1标题、首段前100词、至少1个H2标题、图片alt text、Meta Description
- 次要关键词分布在：H2/H3标题、正文自然融入
- 长尾关键词用于FAQ Schema（People Also Ask覆盖）
- 每篇文章5-8个FAQ问题，覆盖PAA常见查询

### 🔍 竞品内容对标

| 竞品 | SEO优势 | 我们应学习的 |
|------|--------|-------------|
| mhjkiaautoparts.com | 20年Hyundai/Kia出口经验 | 品牌专注度、OE号精确匹配 |
| seoulparts.ae | 迪拜本地仓库+配送 | 本地化服务内容、车型适配工具 |
| mkena.com | 沙特全境配送+阿拉伯语 | KSA市场本地化内容 |
| ok.parts | "How to Source OEM-Quality"系列 | 长尾关键词+采购教育内容 |
| bladecommerce.com | Auto Parts SEO Top10策略 | 技术SEO结构（Schema/URL/CWV） |

### 📐 内容结构模板（韩系配件专题文章）

```markdown
# {Part Type} for {Car Model} ({Year Range}): Complete Wholesale Buyer's Guide

## 1. Why {Part Type} Demand Is Surging in {Target Market}
   → 市场数据（保有量+更换周期+气候因素）
   → 数据来源标注

## 2. {Car Model} {Part Type}: OEM vs Aftermarket Comparison
   → OEM/Quality Aftermarket/Budget 三级对比表
   → 价格区间（FOB China / Landed KSA）
   → 品质标准（IATF 16949 / ECE R90 等）

## 3. Top-Selling {Part Type} References for {Car Model}
   → 按年份分组的OE号对照表
   → 每组标注MOQ/FOB价格

## 4. How to Verify {Part Type} Quality from Chinese Suppliers
   → 外观/重量/尺寸/包装检验要点
   → IATF 16949工厂认证验证方法
   → 常见品质陷阱

## 5. Shipping {Part Type} from China to {Target Market}
   → 空运 vs 海运对比（成本/时效/适用场景）
   → 包装要求
   → 清关文件

## 6. FAQ (5-8 questions targeting PAA keywords)
   → 每个FAQ用<details>标签
   → FAQ Schema JSON-LD

## CTA
   → WhatsApp询盘 + 产品页链接 + 报价表单
```
