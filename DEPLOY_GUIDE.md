# Globalucar 网站 GitHub Pages 完整发布指南

> 域名：**www.global-ucars.com** | 发布日期：2026-04-03

---

## 目录

1. [发布前检查清单](#1-发布前检查清单)
2. [需要准备的账号](#2-需要准备的账号)
3. [第一步：注册 Formspree 表单 ID](#3-第一步注册-formspree-表单-id)
4. [第二步：准备 Logo 文件](#4-第二步准备-logo-文件)
5. [第三步：整理发布文件（过滤开发垃圾）](#5-第三步整理发布文件过滤开发垃圾)
6. [第四步：创建 GitHub 仓库](#6-第四步创建-github-仓库)
7. [第五步：初始化 Git 并推送代码](#7-第五步初始化-git-并推送代码)
8. [第六步：开启 GitHub Pages](#8-第六步开启-github-pages)
9. [第七步：配置自定义域名](#9-第七步配置自定义域名)
10. [第八步：提交 Google Search Console](#10-第八步提交-google-search-console)
11. [后续维护：日常更新流程](#11-后续维护日常更新流程)
12. [故障排查](#12-故障排查)

---

## 1. 发布前检查清单

在开始之前，确认以下全部完成：

| 项目 | 状态 | 备注 |
|------|------|------|
| 全站 14 个页面 SEO TDK | ✅ 完成 | Title/Description/Keywords |
| Twitter Card / Open Graph | ✅ 完成 | 14/14 页面全覆盖 |
| FAQPage JSON-LD | ✅ 完成 | services.html(25条) + parts-finder(48条) |
| BreadcrumbList JSON-LD | ✅ 完成 | 10个页面 |
| 202款产品 meta_title/meta_desc/alt_text | ✅ 完成 | 100% 覆盖 |
| sitemap.xml | ✅ 完成 | 位于根目录 |
| robots.txt | ✅ 完成 | 位于根目录 |
| Formspree 表单 ID | ⏳ **待填入** | 见第三步 |
| Logo 图片文件 | ⏳ **待上传** | 见第四步 |

---

## 2. 需要准备的账号

| 平台 | 用途 | 注册地址 |
|------|------|---------|
| **GitHub** | 代码托管 + 免费静态托管 | https://github.com |
| **Formspree** | 邮件表单接收 | https://formspree.io |
| **Google Search Console** | 提交 sitemap，监控收录 | https://search.google.com/search-console |
| **Cloudflare**（可选） | DNS 管理 + HTTPS 加速 | https://cloudflare.com |

---

## 3. 第一步：注册 Formspree 表单 ID

> 目的：让 Contact 页面的询盘表单真实发送邮件到双方邮箱

### 3.1 注册账号并创建表单

1. 打开 https://formspree.io → **Sign Up Free**（免费账号，每月 50 次提交）
2. 登录后点击 **+ New Form**

**创建第一个表单（Globalucar Vehicle）：**
- Form Name：`Globalucar Vehicle Inquiry`
- Email：`ucars@global-ucars.com`
- 点击 Create → 复制表单 ID（格式如 `xpzgkqrb`）

**创建第二个表单（Kingmay Auto Parts）：**
- Form Name：`Kingmay Parts Inquiry`
- Email：`ku@kingmay-autoparts.com`
- 点击 Create → 复制表单 ID

### 3.2 填入 script.js

打开 `C:\Users\123\WorkBuddy\20260324111450\script.js`，找到第 124-125 行：

```javascript
const FORMSPREE_VEHICLE = 'XXXXXXXX'; // ← 替换为 Globalucar 表单 ID
const FORMSPREE_PARTS   = 'YYYYYYYY'; // ← 替换为 Kingmay 表单 ID
```

将 `XXXXXXXX` 和 `YYYYYYYY` 分别替换为你刚刚复制的两个表单 ID，例如：

```javascript
const FORMSPREE_VEHICLE = 'xpzgkqrb';
const FORMSPREE_PARTS   = 'mqwabcde';
```

**保存文件后验证：**
- 打开 `contact.html` → 填写测试询盘 → 提交
- 检查 `ucars@global-ucars.com` 是否收到邮件

---

## 4. 第二步：准备 Logo 文件

> 目前页面导航引用了两个 Logo，需要确保文件存在

### 需要的文件

| 文件名 | 路径 | 尺寸建议 |
|--------|------|----------|
| `logo-vehicle.jpg` 或 `logo-vehicle.png` | `assets/logo-vehicle.jpg` | 200×60 px（横版） |
| `logo-Kingmay.png` | `assets/logo-Kingmay.png` | 200×60 px（横版） |

### 如果暂时没有 Logo

可以用文字版 Logo 作为临时方案 —— 导航栏目前已有 CSS 文字 fallback，不影响上线。

---

## 5. 第三步：整理发布文件（过滤开发垃圾）

> 工作目录里有大量 `.py` 脚本、临时文件，**不应**上传到 GitHub

### 5.1 需要上传的文件（白名单）

```
根目录：
  index.html
  about.html
  products.html
  product-detail.html
  services.html
  contact.html
  kingmay.html
  parts-finder.html
  parts-engine.html
  parts-cooling.html
  parts-suspension.html
  parts-electrical.html
  blog.html
  blog-post.html
  gx-content-studio.html   ← 后台编辑器（可选，建议保留）
  script.js
  styles.css
  products-inline.js       ← 核心产品数据（~600KB，必须！）
  sitemap.xml
  robots.txt

assets/ 目录：
  assets/products/         ← 整车图片（必须）
  assets/parts/            ← 汽配图片（必须）
  assets/brands/           ← 品牌 Logo（必须）
  assets/hero-*.jpg        ← Hero 背景图（如有）
  assets/logo-vehicle.jpg  ← 主品牌 Logo
  assets/logo-Kingmay.png  ← Kingmay Logo
```

### 5.2 创建 .gitignore 文件

在工作目录创建 `.gitignore`，内容如下：

```
# Python 脚本（仅用于本地开发）
*.py
__pycache__/
*.pyc

# 临时文件 / 日志
*.txt
*.log
generation_log.txt
remaining_generation_log.txt

# 备份文件
*.backup
*.backup3
*.bak
*.seo_backup
*.seo_backup2
*.security_backup

# 开发用临时 HTML 预览
hero-preview*.html
_cards_*.html
parts_listing_*.html

# 源数据（products-data.json 不必要公开，产品数据在 products-inline.js 中）
products-data.json
products-data.json.*
source_cars.json
*.json.backup*

# 开发报告
security_audit_report.md
security_fix_report.md
final_security_verification.md

# 图片原料
*.png
b7.png
bingyue01.png
fcb003.png
haisi001.png
jt001.png
jt002.png
pld001.png

# scripts 备份目录
scripts_backup/

# 系统文件
.DS_Store
Thumbs.db
desktop.ini

# WorkBuddy 工作目录（不上传！）
.workbuddy/
```

> ⚠️ **注意**：`.gitignore` 是全局规则文件，`.py` 写在里面会忽略所有 Python 脚本，不影响 HTML/JS/CSS 的上传。

---

## 6. 第四步：创建 GitHub 仓库

1. 登录 GitHub → 右上角 **+** → **New repository**

2. 填写信息：
   - Repository name：`globalucar-website`（或任意名称）
   - Description：`Globalucar Group — China Vehicle Export & Kingmay Auto Parts`
   - **Visibility**：⚠️ 选 **Public**（GitHub Pages 免费版只支持公开仓库）
   - **不要**勾选 Initialize with README（因为本地已有文件）

3. 点击 **Create repository**

4. 记录仓库地址，格式为：
   ```
   https://github.com/你的用户名/globalucar-website.git
   ```

---

## 7. 第五步：初始化 Git 并推送代码

> 在 PowerShell 或 Git Bash 中执行以下命令

### 7.1 安装 Git（如未安装）

下载地址：https://git-scm.com/download/win → 一路默认安装

验证安装：
```powershell
git --version
# 输出类似：git version 2.44.0.windows.1
```

### 7.2 配置 Git 身份

```powershell
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"
```

### 7.3 进入项目目录

```powershell
cd "C:\Users\123\WorkBuddy\20260324111450"
```

### 7.4 初始化仓库并提交

```powershell
# 初始化 Git 仓库
git init

# 确认 .gitignore 已创建（非常重要！）
Get-Content .gitignore | Select-Object -First 5

# 将所有文件添加到暂存区（.gitignore 会自动过滤不需要的文件）
git add .

# 查看将要提交的文件列表（建议核查一遍）
git status

# 提交
git commit -m "Initial commit: Globalucar Group website v1.0"
```

### 7.5 连接远程仓库并推送

```powershell
# 替换下面的 URL 为你的仓库地址
git remote add origin https://github.com/你的用户名/globalucar-website.git

# 设置主分支为 main 并推送
git branch -M main
git push -u origin main
```

> 第一次推送时，会弹出 GitHub 登录窗口（或要求输入用户名+密码/Token），按提示操作即可。

---

## 8. 第六步：开启 GitHub Pages

1. 打开你的 GitHub 仓库页面
2. 点击顶部 **Settings**（设置）
3. 左侧菜单找到 **Pages**
4. 在 **Build and deployment** 中：
   - Source：选 **Deploy from a branch**
   - Branch：选 **main** → 目录选 **/ (root)**
5. 点击 **Save**

等待 1-3 分钟，页面顶部会出现：
```
Your site is live at https://你的用户名.github.io/globalucar-website/
```

**先用这个临时地址测试网站是否正常运行！**

---

## 9. 第七步：配置自定义域名

> 目标：将 `www.global-ucars.com` 指向 GitHub Pages

### 9.1 在 GitHub 添加自定义域名

1. 仍在仓库 **Settings → Pages**
2. Custom domain 一栏输入：`www.global-ucars.com`
3. 点击 **Save**
4. GitHub 会自动在仓库根目录创建 `CNAME` 文件（内容为 `www.global-ucars.com`）

### 9.2 在域名注册商配置 DNS

> 登录你购买 `global-ucars.com` 的域名注册商（阿里云/腾讯云/GoDaddy 等）

**方案 A（推荐）：使用 CNAME 记录**

| 记录类型 | 主机名 | 目标值 |
|---------|--------|--------|
| `CNAME` | `www` | `你的用户名.github.io` |

**方案 B：同时支持裸域名（不带 www）**

额外添加 4 条 A 记录（GitHub Pages IP）：

| 记录类型 | 主机名 | IP 地址 |
|---------|--------|---------|
| `A` | `@` | `185.199.108.153` |
| `A` | `@` | `185.199.109.153` |
| `A` | `@` | `185.199.110.153` |
| `A` | `@` | `185.199.111.153` |

> DNS 生效时间通常 10 分钟 ~ 48 小时，耐心等待。

### 9.3 启用 HTTPS

DNS 生效后，回到 GitHub Pages 设置页面：
- 勾选 **Enforce HTTPS** ✅

此后访问 `http://` 会自动跳转到 `https://`。

---

## 10. 第八步：提交 Google Search Console

> 告诉 Google 你的网站上线了，加速收录

### 10.1 添加站点

1. 打开 https://search.google.com/search-console
2. 点击 **Add property** → 选 **URL prefix**
3. 输入：`https://www.global-ucars.com/`

### 10.2 验证所有权

推荐方法：**HTML 文件验证**
1. Google 会让你下载一个 `googleXXXXXXXX.html` 文件
2. 将该文件上传到项目根目录
3. `git add googleXXXXXXXX.html && git commit -m "Add Google Search Console verification" && git push`
4. 回到 Search Console 点击 **Verify**

### 10.3 提交 Sitemap

验证成功后：
1. 左侧菜单 → **Sitemaps**
2. 输入：`sitemap.xml`
3. 点击 **Submit**

Google 会在几天内开始爬取并收录你的页面。

---

## 11. 后续维护：日常更新流程

网站上线后，每次更新内容的标准流程：

```powershell
# 1. 进入项目目录
cd "C:\Users\123\WorkBuddy\20260324111450"

# 2. 确认修改了哪些文件
git status

# 3. 添加修改的文件
git add index.html products-inline.js  # 或用 git add . 添加全部

# 4. 提交，写清楚改了什么
git commit -m "Update: 新增3款BYD车型产品数据"

# 5. 推送到 GitHub（自动触发重新部署）
git push
```

推送后 GitHub Pages 通常 **30 秒 ~ 2 分钟** 内自动更新。

---

## 12. 故障排查

### 问题：网站打开但样式全没了

**原因**：CSS 或 JS 路径不对（相对路径在子目录失效）

**检查**：打开浏览器开发者工具 → Console 标签 → 看报错的路径

**确认**：所有 HTML 页面引用的 CSS/JS 路径为相对路径：
```html
<link rel="stylesheet" href="styles.css">  <!-- 正确 ✅ -->
<script src="products-inline.js"></script>  <!-- 正确 ✅ -->
```

---

### 问题：产品数据不显示（202款产品空白）

**原因**：`products-inline.js` 没有上传（文件 ~600KB，较大）

**检查**：GitHub 仓库里是否有 `products-inline.js`

**解决**：
```powershell
git add products-inline.js
git commit -m "Add products-inline.js"
git push
```

---

### 问题：自定义域名一直显示 404

**原因**：CNAME 文件丢失（每次重新开启 Pages 可能被删除）

**解决**：在仓库根目录手动创建 `CNAME` 文件，内容只写一行：
```
www.global-ucars.com
```

```powershell
echo "www.global-ucars.com" > CNAME
git add CNAME
git commit -m "Restore CNAME for custom domain"
git push
```

---

### 问题：表单提交没有收到邮件

**检查顺序**：
1. `script.js` 第 124-125 行的 Formspree ID 是否已替换（不是 XXXXXXXX）
2. 登录 https://formspree.io 后台，查看 Submissions 是否有记录
3. 检查 `ucars@global-ucars.com` 的垃圾邮件文件夹

---

### 问题：HTTPS 证书一直显示 Not yet issued

**原因**：DNS 未生效（等待中）或域名配置有误

**等待**：DNS 生效最长需要 48 小时，先用 `http://` 临时访问

**检查 DNS**：
```powershell
nslookup www.global-ucars.com
# 应该返回 GitHub Pages 的 IP 或 CNAME 指向
```

---

## 附录：快速命令速查

```powershell
# 查看 Git 状态
git status

# 撤销未提交的修改
git restore 文件名.html

# 查看提交历史
git log --oneline -10

# 强制同步本地与远程（⚠️ 会覆盖本地未提交修改）
git fetch origin && git reset --hard origin/main
```

---

> **写于**：2026-04-03 | Globalucar Group 官网项目
> 
> 如有疑问，联系开发协助：WorkBuddy AI Assistant
