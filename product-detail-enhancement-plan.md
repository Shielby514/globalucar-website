# 主打车型产品详情页深化方案

## 一、背景与目标

极石（ROX Adamas）和方程豹（Fang Cheng Bao）已成功从官网引流到线下客户面谈，说明产品页内容有效。现需进一步提升这些优势车型的产品详情页，通过**真实交付流程图片**增强买家信任度，同时符合 SEO 标准获取更高自然流量。

### 本月重点车型

| 优先级 | 车型 | ID | 价格带 | 引流状态 |
|--------|------|-----|--------|---------|
| ⭐⭐⭐ | ROX Adamas 7座 | 131 | $51,500 | ✅ 已引流 |
| ⭐⭐⭐ | ROX Adamas 6座 | 132 | $53,000 | ✅ 已引流 |
| ⭐⭐⭐ | 方程豹 豹8 | 112 | $55,528 | ✅ 已引流 |
| ⭐⭐⭐ | 方程豹 钛7 | 111 | $30,528 | ✅ 已引流 |
| ⭐⭐⭐ | 方程豹 豹5 | 110 | $18,028 | ✅ 已引流 |
| ⭐⭐⭐ | JETTA VS5 Premium | 114 | $16,931 | ✅ 已引流 |
| ⭐⭐ | JETTA VS5 Comfort | 113 | $15,264 | ✅ 已引流 |
| ⭐⭐ | Geely Coolray | 新建 | 待定 | ❌ 需新建 |

---

## 二、核心改动：新增"交付信任板块"（Delivery Proof Section）

### 2.1 设计理念

在现有产品详情页的 **Specifications Table 之后、Related Products 之前**，新增一个"交付证明"板块，展示车辆从工厂到客户手中的完整流程。

**买家心理**：B2B 海外买家最关心的三个问题：
1. "这车真的存在吗？" → 验车照片
2. "你们会好好装运吗？" → 装柜/笼车照片
3. "有其他客户买过吗？" → 客户接待照片

### 2.2 板块结构（4个Tab）

```
┌─────────────────────────────────────────────────────┐
│  📸 Delivery & Inspection — How We Ensure Quality    │
├─────────────────────────────────────────────────────┤
│  [Factory to Port] [Container Loading] [Inspection]  [Client Reception] │
├─────────────────────────────────────────────────────┤
│                                                     │
│   ┌─────┐  ┌─────┐  ┌─────┐                        │
│   │ img │  │ img │  │ img │  (当前Tab下的照片网格)    │
│   └─────┘  └─────┘  └─────┘                        │
│   caption1  caption2  caption3                       │
│                                                     │
│   💡 描述文字：解释这个环节的意义                     │
│   (例如："Every vehicle undergoes 200-point pre-    │
│    shipment inspection before loading...")          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 2.3 四个Tab内容

| Tab | 图标 | 内容 | 示例Caption |
|-----|------|------|-------------|
| Factory to Port | 🏭→⚓ | 笼车运输到码头的照片/视频截图 | "Vehicle loaded on transport carrier at factory" |
| Container Loading | 📦 | 装货柜现场照片 | "Secure container loading at Nansha Port" |
| Pre-Shipment Inspection | 🔍 | 验车照片（外观/内饰/铭牌/里程） | "200-point pre-shipment quality check" |
| Client Reception | 🤝 | 客户接待/签合同/交钥匙照片 | "Client vehicle handover at our Guangzhou office" |

### 2.4 技术实现

```html
<!-- 位置：pd-specs-section 之后、pd-related 之前 -->
<section class="pd-delivery-proof" id="pd-delivery-proof" style="display:none;">
  <h2 class="pd-delivery-title">
    <span class="pd-delivery-icon">📸</span>
    Delivery & Inspection — How We Ensure Quality
  </h2>
  
  <p class="pd-delivery-subtitle">
    Every vehicle shipped by Globalucar goes through a rigorous quality assurance process — from factory gate to your destination port.
  </p>
  
  <!-- Tab Navigation -->
  <div class="pd-delivery-tabs">
    <button class="pd-delivery-tab active" data-tab="factory">
      🏭 Factory to Port
    </button>
    <button class="pd-delivery-tab" data-tab="loading">
      📦 Container Loading
    </button>
    <button class="pd-delivery-tab" data-tab="inspection">
      🔍 Quality Inspection
    </button>
    <button class="pd-delivery-tab" data-tab="client">
      🤝 Client Reception
    </button>
  </div>
  
  <!-- Tab Content (JS动态渲染) -->
  <div class="pd-delivery-content" id="pd-delivery-content">
    <!-- 由JS根据 proof_images 数据渲染 -->
  </div>
</section>
```

### 2.5 CSS样式

- 整体背景：`#f8f9fa`，与页面其他板块一致
- Tab按钮：类似产品列表页的筛选器样式，Active状态用品牌红 `#c8102e`
- 照片网格：3列响应式，hover放大，点击Lightbox
- 视频图标：如果是视频链接，右下角叠加播放按钮SVG

---

## 三、产品数据结构扩展

### 3.1 新增 `proof_images` 字段

在 `products-data.json` 中为每款主打车型新增：

```json
{
  "proof_images": {
    "factory": [
      {
        "src": "assets/gallery/factory-rox-adamas-01.jpg",
        "caption": "ROX Adamas loaded on transport carrier at Chengdu factory"
      },
      {
        "src": "assets/gallery/factory-rox-adamas-02.jpg",
        "caption": "Vehicle convoy departing factory for Nansha Port"
      }
    ],
    "loading": [
      {
        "src": "assets/gallery/loading-rox-adamas-01.jpg",
        "caption": "Container loading — ROX Adamas secured in 40ft container"
      }
    ],
    "inspection": [
      {
        "src": "assets/gallery/inspect-rox-adamas-01.jpg",
        "caption": "200-point pre-shipment quality inspection in progress"
      }
    ],
    "client": [
      {
        "src": "assets/gallery/client-rox-adamas-01.jpg",
        "caption": "Client handover ceremony at Globalucar Guangzhou office"
      }
    ]
  }
}
```

### 3.2 图片命名规范

```
assets/gallery/
├── factory-{brand}-{model}-{编号}.jpg    # 工厂→码头
├── loading-{brand}-{model}-{编号}.jpg    # 装柜
├── inspect-{brand}-{model}-{编号}.jpg    # 验车
└── client-{brand}-{model}-{编号}.jpg     # 客户接待
```

**优先复用现有 `assets/gallery/` 中的照片**（已有19张），新车型的照片需要用户提供。

---

## 四、SEO 优化策略

### 4.1 现有问题诊断

| 问题 | 影响车型 | 解决方案 |
|------|---------|---------|
| meta_title 中文混英文 | 113(VS5 Comfort), 121-122(Geely) | 重写为纯英文，核心车型名前置 |
| meta_description 模板化 | 所有车型 | 手写差异化描述，突出具体卖点和认证 |
| description 内嵌规格表 | 所有车型 | 保留但优化HTML标签，添加FAQ段落 |
| 缺少 FAQPage 结构化数据 | 所有产品页 | 在交付板块下方增加 FAQ（3-4条买家常见问题） |

### 4.2 meta_title 优化标准

格式：`{Year} {Brand} {Model} {Key Feature} for Export | Globalucar`

示例：
- `2026 ROX Adamas EREV 7-Seat Luxury SUV for Export | Globalucar`
- `2026 Fang Cheng Bao Leopard 5 PHEV Off-Road SUV Export | Globalucar`
- `2026 JETTA VS5 1.4T German Engineering SUV Export | Globalucar`
- `2026 Geely Coolray 1.5T Compact SUV for Export | Globalucar`

### 4.3 新增 FAQPage 结构化数据

每个主打车型增加3条FAQ（通过JS动态注入JSON-LD）：

```
Q1: "What export certification does the {Model} have?"
A1: "MIIT Announcement {chassis}, modification-export certified, CCC documentation included."

Q2: "How is the vehicle shipped from China?"
A2: "FOB Nansha Port, Guangzhou. Container (40ft) or RoRo available. Lead time {X} weeks."

Q3: "Can I visit your showroom before ordering?"
A3: "Yes, welcome to visit our Guangzhou office. We arrange factory tours and live vehicle inspections."
```

---

## 五、Geely Coolray 新建计划

### 5.1 产品定位

| 项目 | 内容 |
|------|------|
| 车型 | 2026 Geely Coolray（吉利缤越） |
| 定位 | 入门级运动型紧凑SUV，面向亚非拉大众市场 |
| 竞品对比 | Hyundai Creta, Kia Seltos, VW T-Cross |
| 核心卖点 | BMA架构、1.5TD 181hp、低油耗、高性价比 |
| 目标价格 | ~$12,000-14,000 FOB |

### 5.2 需要用户提供的素材

- [ ] Geely Coolray 官方产品图（或让我用AI生成）
- [ ] 具体配置/价格信息
- [ ] 如果有交付照片（factory/loading/inspection/client），也请提供

---

## 六、执行步骤

### Step 1：用户提供素材 ⏳
需要用户提供的图片素材：

**通用交付照片**（所有车型共用，放到 `assets/gallery/`）：
- [ ] 工厂笼车运输照片（2-3张）
- [ ] 装货柜照片（2-3张）
- [ ] 验车照片（2-3张，展示外观/内饰/铭牌检查）
- [ ] 客户接待照片（2-3张，签合同/交钥匙/合影）

**车型专用照片**（如有，按车型分文件夹或命名区分）：
- [ ] 极石 Adamas 相关交付照片
- [ ] 方程豹相关交付照片
- [ ] JETTA VS5 相关交付照片

### Step 2：代码开发（用户确认素材后执行）
1. 修改 `product-detail.html` — 添加 Delivery Proof Section（HTML + CSS + JS）
2. 修改 `products-data.json` — 为7款主打车型添加 `proof_images` 字段
3. 新建 Geely Coolray 产品数据（id=203）
4. 优化主打车型的 meta_title / meta_description
5. 添加 FAQPage JSON-LD 结构化数据

### Step 3：部署
1. 运行 `regen_inline_from_json.py` 重新生成 `products-inline.js`
2. `git add . && git commit && git push`
3. 在 Google Search Console 中对修改的页面执行 URL 检查

---

## 七、预期效果

| 指标 | 当前 | 目标（3个月内） |
|------|------|---------------|
| 产品页停留时间 | ~45秒 | +50%（交付图片增加浏览深度） |
| 询盘转化率 | ~2% | +30%（信任感提升） |
| Google产品页排名 | 第3-5页 | 进入第1-2页 |
| 每款车型FAQ覆盖 | 0 | 每款3条FAQ + FAQPage Schema |

---

## 八、时间线

| 阶段 | 时间 | 内容 |
|------|------|------|
| 素材准备 | 本周 | 用户整理交付照片，命名后放到 `assets/gallery/` |
| 代码开发 | 下周一 | 开发 Delivery Proof Section + 数据更新 |
| Coolray新建 | 下周三 | 新建产品数据 + 生成产品图 |
| SEO优化 | 下周四 | meta标签优化 + FAQ Schema |
| 部署上线 | 下周五 | regen + git push + GSC提交 |
