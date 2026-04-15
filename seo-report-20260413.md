# Global-UCars SEO 周报

**检查日期**: 2026年4月13日（周一）  
**报告周期**: 2026-03-30 ~ 2026-04-12（过去14天）  
**网站**: https://www.global-ucars.com/

---

## 一、执行摘要

| 检查项 | 状态 | 备注 |
|--------|------|------|
| Sitemap 可访问性 | ✅ 正常 | 21个URL已提交 |
| 网站可访问性 | ✅ 正常 | 页面正常加载 |
| Robots.txt | ⚠️ 缺失 | 返回404 |
| GSC 性能数据 | 🔒 无法获取 | 需要认证 |
| 索引覆盖率 | 🔒 无法获取 | 需要认证 |

---

## 二、Sitemap 分析

### 已提交页面统计

| 页面类型 | 数量 | 优先级 | 更新频率 |
|----------|------|--------|----------|
| 首页 | 1 | 1.0 | weekly |
| 产品页 | 2 | 0.9 | weekly |
| 品牌页 (Kingmay) | 1 | 0.9 | monthly |
| 服务/关于/联系 | 3 | 0.8 | monthly |
| 配件分类页 | 4 | 0.8 | monthly |
| 博客首页 | 1 | 0.7 | weekly |
| 博客文章 | 8 | 0.6 | monthly |
| **总计** | **21** | - | - |

### 页面更新时间
- 所有页面最后更新: **2026-04-01**

---

## 三、网站 SEO 基础检查

### 3.1 首页 SEO 标签

| 元素 | 状态 | 内容 |
|------|------|------|
| Title | ✅ 良好 | CHINA'S ONE-STOP CAR & AUTO PARTS EXPORTER — Globalucar Vehicle & Kingmay Auto Parts |
| H1 | ✅ 正确 | CHINA'S ONE-STOP CAR & AUTO PARTS EXPORTER |
| H2 层级 | ✅ 清晰 | 202 EXPORT-READY PRODUCTS / TWO BRANDS / WHY BUYERS CHOOSE US 等 |
| Meta Description | ⚠️ 未检测 | 建议补充 |

### 3.2 Open Graph / 社交分享
| 标签 | 状态 |
|------|------|
| og:title | ⚠️ 未检测 |
| og:description | ⚠️ 未检测 |
| og:image | ⚠️ 未检测 |
| Twitter Card | 🔍 待验证 |

### 3.3 结构化数据
| 类型 | 状态 |
|------|------|
| Organization Schema | ⚠️ 建议添加 |
| Product Schema | ⚠️ 建议添加 |
| FAQPage JSON-LD | ✅ 已有（services.html / parts-finder.html） |

---

## 四、发现的问题

### 🔴 高优先级

#### 1. Robots.txt 缺失
- **问题**: `https://www.global-ucars.com/robots.txt` 返回 404
- **影响**: 无法指导爬虫行为，可能导致爬虫无限制抓取或忽略重要页面
- **建议**: 创建 robots.txt 文件，内容参考:

```
User-agent: *
Allow: /
Disallow: /admin/

Sitemap: https://www.global-ucars.com/sitemap.xml
```

### 🟡 中优先级

#### 2. 社交分享标签缺失
- **问题**: 未检测到 Open Graph 标签
- **影响**: 在 Facebook、LinkedIn 等平台分享时显示不友好
- **建议**: 为所有页面添加 og:title、og:description、og:image 标签

#### 3. Canonical URL 缺失
- **问题**: 首页未指定 canonical URL
- **影响**: 可能产生重复内容问题（index.html vs /）
- **建议**: 添加 `<link rel="canonical" href="https://www.global-ucars.com/">"`

### 🟢 低优先级

#### 4. 图片 ALT 属性
- **建议**: 检查所有产品图片是否包含描述性 alt 属性

---

## 五、手动检查指南

### 查看 Google Search Console（需要您手动操作）

由于自动化无法访问 Google 账户认证数据，请手动检查以下内容：

#### 1. 性能报告
1. 访问 https://search.google.com/search-console
2. 选择 `www.global-ucars.com` 属性
3. 查看「效果」报告
4. 记录：点击数、展示数、平均排名

#### 2. 索引覆盖率
1. 点击左侧「编制索引」>「网页」
2. 检查以下状态：
   - ✅ 已编入索引
   - ⚠️ 已发现但未编入索引
   - ❌ 爬网错误

#### 3. 对比两周数据
- 设置日期范围为「过去28天」
- 对比「3月30日-4月5日」与「4月6日-4月12日」的数据

---

## 六、下次检查计划

- **执行时间**: 2026年4月27日（周一）
- **待解决问题**: 
  - 创建 robots.txt
  - 添加 Open Graph 标签
  - 尝试获取 GSC API 访问权限

---

## 七、联系信息

如需帮助，请联系：
- **Mr Didi**: ucars@global-ucars.com
- **Miss UU (Kingmay)**: ku@kingmay-autoparts.com

---

*报告生成时间: 2026-04-13 15:30*
