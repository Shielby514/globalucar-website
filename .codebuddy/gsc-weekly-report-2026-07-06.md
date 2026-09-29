# Google Search Console 收录检查周报

**网站**: https://www.global-ucars.com
**检查日期**: 2026-07-06 16:38 (GMT+8)
**任务类型**: 每周一定期自动化检查
**检查状态**: ⚠️ 部分完成（GSC 后台需登录/API 未配置）

---

## 执行摘要

本次自动化检查无法直接登录 Google Search Console 后台获取精确的点击次数、展示次数、平均排名和覆盖范围数据，原因如下：

1. **浏览器登录态缺失**：访问 `search.google.com/search-console` 被重定向到 Google 账号登录页。
2. **GSC API 服务账号未配置**：未找到 `gsc-service-account-key.json` 密钥文件，且缺少 `google-api-python-client` / `google-auth` 依赖。
3. **Playwright `site:` 搜索被 CAPTCHA 拦截**：6 月 29 日的自动化脚本因 Google 反爬虫机制失败。

因此，本次报告基于以下**间接数据源**：
- `site:global-ucars.com` 搜索结果抽样（WebFetch，显示约 **156 条结果**）
- `sitemap.xml` 直接抓取分析
- `robots.txt` 与首页可访问性检查
- 与历史记录的对比

---

## 1. 网站基础健康检查

| 检查项 | 结果 | 备注 |
|--------|------|------|
| 首页可访问性 | ✅ 正常 | `China Car Exporter – New & Used Cars, Auto Parts \| Globalucar & Kingmay` |
| robots.txt | ✅ 正常 | `User-agent: * Allow: /`，已引用 sitemap |
| sitemap.xml 可访问性 | ✅ 正常 | 共 **93 个 URL**，101,398 字符 |
| 首页 Title / 品牌关键词 | ✅ 正常 | 包含 Globalucar / Kingmay / China Car Exporter |

### Sitemap 结构（93 个 URL）

| 页面类型 | 数量 | 占比 | 备注 |
|----------|------|------|------|
| 博客文章（blog-post.html?id=*） | 80 | 86% | 最新 lastmod: 2026-07-01（id=84/85） |
| 核心页面（首页/产品/服务/关于/联系） | 7 | 7.5% | 含 products, services, about, contact, kingmay 等 |
| 配件系统分类页 | 4 | 4.3% | parts-engine, parts-cooling, parts-suspension, parts-electrical |
| 配件查找器 / 博客列表 / 产品详情模板 | 2 | 2.2% | parts-finder, blog.html, product-detail.html |

**与上次对比**：sitemap 从 87 个 URL（6 月 29 日）增加到 **93 个 URL**，新增 6 个 URL，主要来自博客文章（id=83~85 等）。

---

## 2. Google 收录估算（基于 `site:` 搜索）

### 2.1 搜索结果概览

| 指标 | 本次（2026-07-06） | 上次（2026-06-29） | 变化 |
|------|--------------------|--------------------|------|
| `site:global-ucars.com` 估算结果数 | **约 156 条** | 被 CAPTCHA 拦截 | 新增可用数据 |
| Sitemap 提交 URL 数 | 93 | 87 | +6 |
| 搜索可见核心页数 | 10 个 | 7~9 个（估算） | 略有增加 |

> ⚠️ 注意：Google `site:` 操作符返回的“约 X 条结果”是估算值，可能包含重复、翻译结果或子资源，不完全等于 GSC 中的“已收录页面数”。

### 2.2 已确认在 Google 搜索中出现的页面（10 个）

通过 `site:global-ucars.com` 第一页结果抽样确认：

| # | 页面 URL | 类型 | 备注 |
|---|----------|------|------|
| 1 | `https://www.global-ucars.com/` | 首页 | 持续收录，摘要正常 |
| 2 | `https://www.global-ucars.com/products.html` | 产品目录 | 持续收录 |
| 3 | `https://www.global-ucars.com/kingmay.html` | 品牌页 | 持续收录 |
| 4 | `https://www.global-ucars.com/contact.html` | 联系页 | 5 月下旬首次确认后保持 |
| 5 | `https://www.global-ucars.com/parts-cooling.html` | 配件分类 | 收录 |
| 6 | `https://www.global-ucars.com/blog-post.html?id=` | 博客模板（无参数） | ⚠️ canonical 历史问题残留 |
| 7 | `https://www.global-ucars.com/blog-post.html?id=31` | 博客文章 | 已单篇收录 |
| 8 | `https://www.global-ucars.com/blog-post.html?id=21` | 博客文章 | 已单篇收录 |
| 9 | `https://www.global-ucars.com/blog-post.html?id=35` | 博客文章 | 已单篇收录 |
| 10 | `https://www.global-ucars.com/blog-post.html?id=81` | 博客文章 | 🆕 7 天前被抓取，近期活跃 |

### 2.3 未在抽样中确认的页面

- `about.html`：历史曾收录，本次 `site:` 第一页未直接出现
- `services.html`：历史曾收录，本次未直接出现
- `parts-finder.html`：历史曾收录，本次未直接出现
- `parts-engine.html`、`parts-suspension.html`、`parts-electrical.html`：未在抽样中出现
- 绝大多数博客单篇文章（id=1~80 中除 21/31/35/81 外）未在 `site:` 结果中单独出现

> 这并不意味着未收录，可能只是排名较低未进入前 10，或未被 `site:` 操作符展示。

---

## 3. 与历史数据对比

### 3.1 长期趋势

| 指标 | 2026-05-11 | 2026-05-18 | 2026-05-25 | 2026-05-26 | 2026-06-01 | 2026-06-29 | **2026-07-06** |
|------|------------|------------|------------|------------|------------|------------|----------------|
| Sitemap URL 总数 | 24 | 25 | 62 | 62 | 71 | 87 | **93** |
| `site:` 搜索估算收录 | — | — | — | — | — | CAPTCHA | **~156** |
| 搜索可见核心页 | 3-4 | 9 | 7-8 | 9-10 | 11-12 | 7-9 | **10** |
| 博客单篇搜索可见 | 0 | 1 | 0-1 | 0 | 1 | 0 | **4** |

### 3.2 本周关键变化

| 变化 | 说明 | 影响 |
|------|------|------|
| 🟢 Sitemap 增至 93 个 URL | 新增 6 个 URL（主要来自博客 id=83~85） | 内容规模继续扩大 |
| 🟢 `site:` 搜索首次返回约 156 条估算结果 | 此前被 CAPTCHA 拦截，本次获得可用数据 | 收录规模可能显著扩大 |
| 🟢 blog-post.html?id=81 显示“7 天前” | 说明 Google 近期仍在活跃抓取博客 | 积极信号 |
| 🟡 仍有大量博客单篇未在 `site:` 中单独出现 | 约 76/80 篇博客未出现在前 10 结果 | 需要持续提交和观察 |
| 🟡 `blog-post.html?id=`（无参数）仍出现 | canonical 修复后仍被索引，可能为历史残留 | 一般无害，但不够干净 |

---

## 4. 技术 SEO 健康度

| 检查项 | 结果 | 说明 |
|--------|------|------|
| robots.txt 阻止爬虫 | ✅ 无阻止 | `Allow: /` 对所有 User-agent |
| sitemap 引用 | ✅ 已引用 | robots.txt 中正确指向 sitemap.xml |
| 首页 noindex | ✅ 无 | 首页可正常索引 |
| 核心页面可访问 | ✅ 正常 | 服务器响应正常 |
| 动态 URL (?id=X) | 🟡 可收录但抓取效率低 | 需要手动提交加速 |

---

## 5. 重大问题与风险判断

### 5.1 是否触发警报阈值？

根据预设阈值：

| 阈值 | 本次情况 | 是否触发 |
|------|----------|----------|
| 收录量下降 > 10% | 无法获取精确 GSC 数据，但 `site:` 估算约 156 条，无明显下降信号 | ❌ 未触发 |
| 大量新出现错误页面 > 5 | 无 GSC 错误数据，间接检查未发现服务器错误 | ❌ 未触发 |
| 点击次数骤降 > 30% | 无法自动获取 | ⚠️ 数据缺失 |
| 展示次数骤降 > 30% | 无法自动获取 | ⚠️ 数据缺失 |

### 5.2 当前最大问题

1. **🔴 GSC 后台/API 仍未配置**：这是自动化检查的最大瓶颈。没有登录态或 API 密钥，无法获取精确的点击、展示、排名、覆盖范围数据。
2. **🟡 博客单篇收录可见度低**：80 篇博客中仅 4 篇在 `site:` 搜索中单独出现。虽然 `site:` 操作符不能代表全部收录，但这是一个值得关注的信号。
3. **🟡 无法确认新增 6 个 URL 的收录情况**：需要手动在 GSC 中提交或检查。

---

## 6. 建议行动

### 立即行动（本周）

1. **配置 GSC API 服务账号**（推荐长期方案）
   - 在 Google Cloud Console 创建项目并启用 Search Console API
   - 创建服务账号，下载 JSON 密钥文件
   - 将密钥文件保存为 `.workbuddy/automations/google/gsc-service-account-key.json`
   - 在 GSC 中将服务账号邮箱添加为“完整权限”用户
   - 安装依赖：`pip install google-api-python-client google-auth`

2. **手动登录 GSC 后台确认本周数据**
   - 查看“效果”报告：总点击次数、展示次数、平均 CTR、平均排名
   - 查看“覆盖范围”报告：已收录 / 未收录 / 错误页面数量
   - 重点关注新增博客文章（id=83~85 等）是否已被索引

3. **手动提交新增博客文章**
   - 将 sitemap 中新增的 6 个 URL 提交到 GSC URL 检查工具，请求编入索引

### 中期行动（本月）

4. **继续发布高质量博客内容**并立即手动提交
5. **监控 canonical 标签**确保 `blog-post.html?id=X` 和 `product-detail.html?id=X` 正确设置
6. **考虑为重要落地页增加内链**，提升 Google 发现和抓取效率

---

## 7. 数据缺失说明

以下数据因无法自动登录 GSC 或调用 API 而缺失：

| 缺失指标 | 原因 |
|----------|------|
| 总点击次数 | 需 GSC 登录态或 API |
| 总展示次数 | 需 GSC 登录态或 API |
| 平均 CTR | 需 GSC 登录态或 API |
| 平均排名 | 需 GSC 登录态或 API |
| 覆盖范围 / 已收录页面精确数 | 需 GSC 登录态或 API |
| 未收录页面原因分类 | 需 GSC 登录态或 API |
| 错误页面列表 | 需 GSC 登录态或 API |

---

## 8. 结论

本周网站基础健康度良好：
- ✅ 首页、robots.txt、sitemap 均可正常访问
- ✅ sitemap 规模持续增长至 93 个 URL
- ✅ Google `site:` 搜索估算显示约 156 条结果，且近期有博客文章被抓取（id=81，7 天前）
- ⚠️ 但精确的 GSC 数据仍无法自动获取，自动化检查受限

**未触发重大收录骤降或大量错误的紧急警报**，但建议尽快配置 GSC API 或提供登录凭据，以便下周实现完整自动化监控。

---

*报告生成时间：2026-07-06 16:38:44 (自动)*
