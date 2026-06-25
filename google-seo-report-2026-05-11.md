# Google Search Console 收录状态报告

**检查日期**：2026-05-11 (周一)
**网站**：https://www.global-ucars.com/
**检查方式**：非登录自动化检查（服务器可达性、sitemap、robots.txt、线上内容、Google索引外部分析）

---

## 一、基础设施检查

| 项目 | 状态 | 备注 |
|------|------|------|
| HTTPS | ✅ 正常 | Let's Encrypt 有效 |
| robots.txt | ✅ 正常 | 允许全部抓取，sitemap 已声明 |
| sitemap.xml | ✅ 可访问 | 26 个 URL 已提交 |
| 首页响应 | ✅ 200 OK | 104KB，GitHub Pages 托管 |

---

## 二、Sitemap 状态（26个 URL）

### 页面类型分布
| 类型 | 数量 | 详情 |
|------|------|------|
| 核心页面 | 7 | Home, Products, Parts Finder, Kingmay, Services, About, Contact |
| 产品详情 | 1 | product-detail.html（动态参数页） |
| 汽配分类 | 4 | parts-engine/cooling/suspension/electrical |
| 博客索引 | 1 | blog.html |
| 博客文章 | 13 | blog-post.html?id=1~13 |

### ⚠️ 关键问题：5篇博客文章未提交到 Sitemap

**Sitemap 中缺失的博客文章：**

| ID | 标题 | 发布日期 | 分类 |
|----|------|----------|------|
| 14 | China Used Car Exports to Africa in 2026 | Apr 21, 2026 | Vehicles |
| 15 | Geely Coolray, VW T-Roc, Skoda Tharu XR & Jetta VS5 | Apr 22, 2026 | Vehicles |
| 16 | Exhaust System & Catalytic Converter Parts from China | May 8, 2026 | Auto Parts |
| 17 | Hyundai Tucson vs Chery Tiggo 8: Korean vs Chinese SUV | May 8, 2026 | Vehicles |
| 18 | 2026 ROX ADAMAS: Extended Range Electric SUV | May 8, 2026 | Vehicles |

> **影响**：这些新文章未在 sitemap 中声明，Google 可能延迟发现和索引它们。

---

## 三、线上页面可访问性

| 页面 | HTTP 状态 | Meta Tags | 内容渲染 |
|------|-----------|-----------|----------|
| blog-post?id=14 | ✅ 200 | ✅ 动态注入 | ✅ JS渲染正常 |
| blog-post?id=15 | ✅ 200 | ✅ 动态注入 | ✅ JS渲染正常 |
| blog-post?id=16 | ✅ 200 | ✅ 动态注入 | ✅ JS渲染正常 |
| blog-post?id=17 | ✅ 200 | ✅ 动态注入 | ✅ JS渲染正常 |
| blog-post?id=18 | ✅ 200 | ✅ 动态注入 | ✅ JS渲染正常 |

> 所有页面线上均可正常访问，BLOG_POSTS 数据完整（18篇文章）。

---

## 四、SEO Meta 标签检查

blog-post 页面使用动态 meta 注入机制（`post-og-title`、`post-meta-desc` 等 ID 占位），由 JavaScript 在页面加载时根据 URL 参数替换实际内容。

| Meta 标签 | 状态 | 说明 |
|-----------|------|------|
| Title | ✅ 动态注入 | 根据文章ID更新 |
| Description | ✅ 动态注入 | `post-meta-desc` 占位 |
| OG Title | ✅ 动态注入 | `post-og-title` 占位 |
| OG Description | ✅ 动态注入 | `post-og-desc` 占位 |
| OG Image | ✅ 动态注入 | `post-og-img` 占位 |
| Twitter Card | ✅ 动态注入 | 全部覆盖 |
| JSON-LD | ✅ 动态注入 | Article + BreadcrumbList |
| article:published_time | ⚠️ 空值 | `content=""` 未填充 |

---

## 五、Google 索引外部分析

### 通过搜索引擎检测到的已索引页面

通过 Google 搜索 `"global-ucars.com"` 可确认：
- ✅ 首页已索引（title: "Globalucar - China Car Exporter"）
- ✅ blog.html 已索引（title: "Auto Parts & Car Export Blog | Industry Insights"）
- ✅ blog-post?id=1 已索引（title: "Auto Parts Export Insights | Globalucar Blog"）

### 上次检查（2026-05-08）以来的变化
- 上次报告：过去14天无新增收录
- 本次：由于无法登录 GSC，无法获取精确的新增收录数据
- 建议手动登录 GSC 确认 id=14~18 的索引进度

---

## 六、发现的问题与建议

### 🔴 高优先级

1. **更新 sitemap.xml** — 添加 blog-post.html?id=14~18 共5篇文章
   - 当前 sitemap 仅到 id=13，遗漏了4月21日-5月8日发布的5篇新文章
   - 添加后需在 GSC 重新提交 sitemap

2. **article:published_time 为空** — `post-og-pubtime` 的 content 为空字符串
   - 应填充文章实际发布日期（ISO 8601 格式）

### 🟡 中优先级

3. **建议在 GSC 手动提交 URL Inspection** — 对 id=14~18 五篇文章逐一提交，加速索引
   - 路径：GSC → URL Inspection → 输入URL → Request Indexing

4. **确认 GSC 账号登录状态** — 本次自动化无法登录 GSC 查看详细索引数据
   - 如需自动化 GSC 数据采集，建议配置 Google OAuth API 凭证

---

## 七、总结

| 指标 | 数值 |
|------|------|
| Sitemap URL 数量 | 26 |
| 实际博客文章数 | 18 |
| Sitemap 缺失文章数 | **5**（id=14~18） |
| 页面可访问性 | ✅ 全部正常 |
| robots.txt | ✅ 无抓取限制 |
| 需要手动操作 | 更新 sitemap + GSC 提交 |

**整体状态**：网站基础设施正常，核心问题是有5篇新文章未同步到 sitemap.xml，可能导致 Google 延迟索引。

---

*报告由自动化任务 google-2 生成 | 下次检查：2026-05-26 (周一)*
