# Google Search Console 收录状态报告

**检查时间**: 2026年5月8日 14:58
**网站**: https://www.global-ucars.com/
**检查周期**: 过去14天 (2026年4月24日 - 2026年5月8日)
**对比周期**: 上两周 (2026年4月7日 - 2026年4月21日)

---

## 📊 总体状态概览

| 项目 | 状态 | 备注 |
|------|------|------|
| robots.txt | ✅ 正常 | 允许所有爬虫抓取 |
| sitemap.xml | ✅ 已提交 | 26个URL (最后更新: 2026-04-21) |
| HTTPS | ✅ 已启用 | Let's Encrypt 自动签发 |
| Search Console验证 | ✅ 已验证 | HTML文件验证方式 |
| 网站可访问性 | ✅ 正常 | 核心页面全部可访问 |

> ⚠️ **说明**: 由于 GSC 性能数据（点击数/展示数/平均排名）需要 Google 账号认证，无法通过自动化脚本直接获取。实际数据请登录 https://search.google.com/search-console 手动查看。

---

## 📅 Sitemap 分析

### 已提交URL统计

| 指标 | 上两周 (04-21报告) | 本次 (05-08报告) | 变化 |
|------|-------------------|------------------|------|
| URL总数 | 21个 | 26个 | ⬆️ +5 |
| 主页面 | 11个 | 8个 | ⬇️ -3* |
| 分类页 | 未单独统计 | 4个 | 新增统计 |
| 博客文章 | 8个 | 13个 | ⬆️ +5 |
| 产品详情 | 未单独统计 | 1个 | 新增统计 |
| 最后更新 | 2026-04-14 | 2026-04-21 | ⬆️ 更新 |

> *注：主页面数量差异可能因 sitemap.xml 结构重分类所致，不影响实际收录。

### URL类型分布

| 类型 | 数量 | 占比 |
|------|------|------|
| 主页面 | 8个 | 31% |
| 零部件分类页 | 4个 | 15% |
| 博客文章 | 13个 | 50% |
| 产品详情 | 1个 | 4% |

---

## ⚠️ 发现的问题

### 1. 🔴 两篇新博客文章未加入 sitemap (高优先级)

**id=14 和 id=15 两篇博客文章尚未添加到 sitemap.xml**

| 文章ID | 标题 | 发布日期 | sitemap状态 |
|--------|------|----------|-------------|
| 14 | China Used Car Exports to Africa in 2026 | 2026-04-21 | ❌ 缺失 |
| 15 | Geely Coolray, VW T-Roc, Skoda Tharu XR & Jetta VS5 | 2026-04-22 | ❌ 缺失 |

**建议操作**:
```xml
<!-- 添加到 sitemap.xml -->
<url>
  <loc>https://www.global-ucars.com/blog-post.html?id=14</loc>
  <lastmod>2026-04-21</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.8</priority>
</url>
<url>
  <loc>https://www.global-ucars.com/blog-post.html?id=15</loc>
  <lastmod>2026-04-22</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.8</priority>
</url>
```

### 2. 🟡 过去14天无新内容发布

分析周期内（4月24日-5月8日）:
- ✅ sitemap 最后更新为 2026-04-21（已有18天未更新）
- ⚠️ 没有新文章在检查周期内发布并提交 sitemap
- 建议保持每周至少1篇博客更新节奏

---

## 📈 周期对比总结

| 指标 | 上次 (04-07~04-21) | 本次 (04-24~05-08) | 变化趋势 |
|------|-------------------|---------------------|---------|
| sitemap URL数 | 21 | 26 | ⬆️ +5 |
| 博客收录文章数 | 8 | 13 | ⬆️ +5 |
| robots.txt | ✅ 正常 | ✅ 正常 | → 稳定 |
| 产品页加载 | ❌ 异常 | ✅ 已修复 | ⬆️ 修复 |
| 新文章缺失 | 无 | id=14, id=15 | ⚠️ 新问题 |

---

## ✅ 已解决的问题

| 问题 | 状态 | 备注 |
|------|------|------|
| products.html 加载失败 | ✅ 已修复 | 产品列表现已正常显示 |
| robots.txt 404 | ✅ 已修复 | 2026-04-13发现，04-21确认修复 |

---

## ✅ robots.txt 配置

```
User-agent: *
Allow: /
Sitemap: https://www.global-ucars.com/sitemap.xml
```

配置正常，无抓取限制。

---

## 📌 后续行动清单

### 🔴 高优先级 (本周内完成)

- [ ] **更新 sitemap.xml** — 添加 id=14 和 id=15 的博客文章URL
- [ ] **登录 GSC 重新提交 sitemap** — https://search.google.com/search-console
- [ ] **手动请求编入索引** — 通过 URL Inspection 工具提交 id=14, id=15

### 🟡 中优先级 (本周内完成)

- [ ] **发布本周新博客** — 建议周四发布整车主题文章
- [ ] **更新 sitemap lastmod** — 提交 sitemap 后确保 Google 识别新变化
- [ ] **手动查看 GSC 性能数据** — 登录 Console 查看实际点击/展示/排名数据

### 📋 每月例行任务

- [ ] 每周四发布博客后同步更新 sitemap
- [ ] 每月检查一次 sitemap.xml 完整性
- [ ] 监控 Google 收录页面数量变化

---

## 🔗 相关链接

- Google Search Console: https://search.google.com/search-console
- Sitemap: https://www.global-ucars.com/sitemap.xml
- Robots.txt: https://www.global-ucars.com/robots.txt

---

## 📋 GSC 性能数据手动查看指引

由于自动化无法获取 GSC 认证数据，请手动查看以下指标：

1. **点击数 / 展示数**: 性能报告 → 过去28天
2. **平均排名**: 性能报告 → 平均排名列
3. **索引覆盖率**: 索引 → 覆盖率报告
4. **抓取统计**: 设置 → 抓取统计

---

*报告生成时间: 2026-05-08 14:58*
*由自动化任务 google-3 生成 | 检查周期: 过去14天*
