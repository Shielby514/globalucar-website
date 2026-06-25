# Google Search Console SEO 周报

**检查日期**：2026-05-18 (周一)  
**网站**：https://www.global-ucars.com/  
**检查方式**：非登录自动化检查（服务器可达性、sitemap、robots.txt、线上内容、Git 提交记录对比）  
**数据来源**：HTTP 探测、线上 sitemap、Git 日志、历史报告对比  

---

## 一、基础设施与站点可达性

| 项目 | 状态 | 备注 |
|------|------|------|
| HTTPS | ✅ 正常 | Let's Encrypt 有效，证书正常 |
| robots.txt | ✅ 正常 | 允许全部抓取，sitemap 已声明 |
| sitemap.xml | ⚠️ 可访问但**未更新** | 26 个 URL，上次更新 2026-04-21 |
| 首页响应 | ✅ 200 OK | 104KB，GitHub Pages 托管，Last-Modified: May 16 |
| 全站 HTTP 状态 | ✅ 全部正常 | 测试 id=14~28 均返回 200 |

---

## 二、Sitemap 索引覆盖率

### 当前 Sitemap 状态

| 指标 | 数值 | 变化（对比 05-11） |
|------|------|-------------------|
| Sitemap URL 总数 | 26 | 无变化 |
| 实际博客文章数 | **28** | +10（新增 id=19~28） |
| Sitemap 缺失文章数 | **15** | +10（恶化） |

### 页面类型分布

| 类型 | 数量 | 详情 |
|------|------|------|
| 核心页面 | 7 | Home, Products, Parts Finder, Kingmay, Services, About, Contact |
| 产品详情 | 1 | product-detail.html（动态参数页） |
| 汽配分类 | 4 | parts-engine/cooling/suspension/electrical |
| 博客索引 | 1 | blog.html |
| 博客文章 | 13 | blog-post.html?id=1~13 |

### 🔴 关键问题：15 篇博客文章未提交到 Sitemap

Sitemap 中**完全缺失**的博客文章（按发布时间排序）：

| ID | 标题 | 发布日期 | 分类 | SEO 重要性 |
|----|------|----------|------|-----------|
| 14 | China Used Car Exports to Africa in 2026 | Apr 21 | Vehicles | 目标市场关键词 |
| 15 | Geely Coolray, VW T-Roc, Skoda Tharu XR & Jetta VS5 | Apr 22 | Vehicles | 多车型长尾词 |
| 16 | Exhaust System & Catalytic Converter Parts from China | May 8 | Auto Parts | 排气系统高需求品类 |
| 17 | Hyundai Tucson vs Chery Tiggo 8: Korean vs Chinese SUV | May 8 | Vehicles | 韩系 vs 国产对比 |
| 18 | 2026 ROX ADAMAS: Extended Range Electric SUV | May 8 | Vehicles | 主推车型 |
| 19 | Transmission & Drivetrain Parts Export Guide | May 8 | Auto Parts | 传动系统 |
| 20 | JETTA VS5: The Budget SUV for Emerging Markets | May 11 | Vehicles | 主推车型 |
| 21 | Volkswagen T-Roc: Compact SUV Export Guide | May 11 | Vehicles | 欧洲品牌 |
| 22 | Skoda Tharu XR: Value SUV for Global Markets | May 11 | Vehicles | 欧系性价比 |
| 23 | Geely Coolray: Small SUV for Urban Africa & SE Asia | May 11 | Vehicles | 主推车型 |
| 24 | Chery Tiggo 8 vs Jetta VS5: Chinese SUV Comparison | May 11 | Vehicles | 国产对比 |
| 25 | Top 20 Most Profitable Auto Parts for African Importers | May 15 | Auto Parts | **SEO Topic Matrix #3** |
| 26 | Top 15 Auto Parts That Fail Before 150,000 km | May 15 | Auto Parts | **SEO Topic Matrix #13** |
| 27 | Private Label Auto Parts: OEM Branding for Distributors | May 15 | Auto Parts | **SEO Topic Matrix #1** |
| 28 | Auto Parts Import Duty Cheat Sheet: Kenya, Nigeria, Ghana, UAE & Saudi Arabia | May 15 | Auto Parts | **SEO Topic Matrix #4** |

> **影响**：15 篇新文章未在 sitemap 中声明，Google 无法通过 sitemap 发现这些内容，可能导致严重延迟索引。特别是 id=25-28 是 SEO Topic Matrix Phase 1 的核心文章，直接影响目标关键词排名。

---

## 三、线上页面可访问性（全量检查）

| 页面 | HTTP 状态 | 内容渲染 |
|------|-----------|----------|
| blog-post?id=14~18 | ✅ 200 | ✅ 正常（4月发布） |
| blog-post?id=19~24 | ✅ 200 | ✅ 正常（5月11日发布） |
| blog-post?id=25~28 | ✅ 200 | ✅ 正常（5月15日发布） |
| 所有核心页面 | ✅ 200 | ✅ 正常 |

> 所有页面线上均可正常访问，BLOG_POSTS 数据完整（28 篇文章）。

---

## 四、Git 提交与部署状态

### 最近 5 次提交

| 提交 | 日期 | 内容 |
|------|------|------|
| `07d3f75` | May 16 | Fix: 修复 product-detail.js 重复变量导致崩溃 |
| `6d78ff9` | May 15 | Blog: 发布 SEO Topic Matrix Phase 1 (id=25-28, 4 篇文章) |
| `2067c30` | May 15 | 新增汽配产品模板（Stabilizer Link Assembly KIA 54830-0U000） |
| `a8a76f0` | May 11 | 新增 4 篇拆分博客文章 (id=21-24) |
| `b8860e7` | May 11 | 更新 blog id=18 ROX Adamas SEO 重写 |

### ⚠️ 部署状态
- **最新提交已 push**：✅ 是（GitHub Pages Last-Modified: May 16）
- **sitemap.xml 未随内容更新**：❌ 仍然停留在 Apr 21 版本
- **本地未提交更改**：存在大量未跟踪文件（xlsx 提取的汽配图片，约 200+ 张）

---

## 五、与上两周数据对比（05-11 vs 05-18）

| 指标 | 05-11 | 05-18 | 变化 | 状态 |
|------|-------|-------|------|------|
| Sitemap URL 数 | 26 | 26 | 0 | ⚠️ 未更新 |
| 实际博客文章数 | 18 | 28 | **+10** | 📈 内容增长 |
| Sitemap 缺失文章数 | 5 (id=14~18) | 15 (id=14~28) | **+10** | 🔴 **恶化** |
| 核心页面状态 | 全部正常 | 全部正常 | 无变化 | ✅ 稳定 |
| robots.txt | 正常 | 正常 | 无变化 | ✅ 稳定 |
| 新发布文章 | 0 | 10 篇 | +10 | 📈 内容活跃 |

### 显著变化标记
- 📈 **内容产出活跃**：过去 7 天发布 10 篇新文章（id=19~28）
- 🔴 **索引覆盖恶化**：sitemap 未同步更新，缺失文章从 5 篇增至 15 篇
- ⚠️ **技术债务累积**：sitemap.xml 自 4 月 21 日以来未更新，已滞后 27 天

---

## 六、发现的问题与建议

### 🔴 高优先级（需立即处理）

1. **紧急更新 sitemap.xml**
   - 当前 sitemap 仅到 id=13，遗漏了 15 篇新文章（id=14~28）
   - 特别是 id=25~28 是 SEO Topic Matrix 核心文章，直接影响关键词排名
   - **建议**：立即在 sitemap 中添加 blog-post.html?id=14~28
   - 添加后需在 GSC 重新提交 sitemap 或使用 URL Inspection 单独提交

2. **清理本地未跟踪文件**
   - 本地存在大量 `assets/parts/xlsx_*` 未跟踪文件（约 200+ 张图片）
   - 这些文件可能用于 Kingmay 产品目录更新，建议确认后 commit 或加入 .gitignore

### 🟡 中优先级

3. **article:published_time 为空**
   - `post-og-pubtime` 的 content 为空字符串，影响文章结构化数据
   - 应填充文章实际发布日期（ISO 8601 格式）

4. **建议配置 GSC API 自动化**
   - 当前自动化无法登录 GSC 获取精确点击/展示/排名数据
   - 如需完整性能数据，建议配置 Google OAuth API 或使用第三方 SEO 工具（如 Ahrefs/Semrush API）

---

## 七、周报摘要

| 指标 | 数值/状态 |
|------|----------|
| 网站可访问性 | ✅ 全部正常 |
| robots.txt | ✅ 无抓取限制 |
| Sitemap URL 数量 | 26（应更新为 41） |
| 实际博客文章数 | 28 |
| Sitemap 缺失文章数 | **15**（id=14~28） |
| 本周新发布文章 | 10 篇（id=19~28） |
| 核心问题 | sitemap.xml 严重滞后 |
| 需要手动操作 | 更新 sitemap + GSC 重新提交 |

### 总体评估

🔴 **存在需要关注的问题**：网站基础设施和页面可访问性全部正常，内容产出非常活跃（本周新增 10 篇）。但 **sitemap.xml 已严重滞后**，15 篇新文章（包括 4 篇 SEO Topic Matrix 核心文章）未向 Google 声明，这将显著延迟索引和排名获取。

**建议立即执行**：
1. 更新 sitemap.xml 添加 id=14~28
2. git commit + push 部署
3. 在 GSC 中重新提交 sitemap 或对 id=25~28 执行 Request Indexing

---

*报告由自动化任务 google-3 生成 | 下次检查：2026-06-01 (周一)*
