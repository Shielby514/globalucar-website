# OE 库服务器 24 小时发布 —— 部署与交接文档

> 版本：2026-10-26 ｜ 站点：`https://www.global-ucars.com`
> 目标：**服务器全年无休运行**，每天自动「补数据 → 出页 → 发布 → 推送」。
>
> 本文档自成一体。拿到服务器后从「一、速览」读到「三、部署」即可开工，
> 无需翻阅历史对话。

---

## 一、速览

### 为什么做这件事

2026-10-26 实测发现 OE 库真正的瓶颈不是收录，而是**页面本身没有可承接的查询词**：

| 指标 | 实测值 |
|---|---|
| OE 页单页产出 | **3.26 曝光 / 月**（blog 是 33.04，差 10 倍）|
| 真实收录率 | 50%（另 42.8% 卡在"Discovered - not indexed"）|
| 母库 fitment 覆盖率 | **0.23%** |
| 母库 images 覆盖率 | 0.17% |
| 零件名形态 | 工厂缩写：`Ring ASSY Sunroof Re`、`Bolt`、`RING SNAP` |

根因：**页面上的文字不是买家会输入的文字**。
没人搜 "WIRING ASSY MAIN"，也没人靠搜 "Bolt" 找汽配。

### 突破口

母库 **221,663 条（93.7%）自带 `ref_url`**，指向 hyundaipartsdeal 的详情页。
页面内嵌 JSON-LD Product，含**完整零件名 + 适配车型年份 + 图片 + 价格**。

实测 16 条：

| 项目 | 获取率 |
|---|---:|
| 完整零件名（含母库回退） | **100%** |
| 适配车型 + 年份 | 94% |
| 图片 URL | 100% |
| 价格（MSRP） | 100% |

缩写被还原成买家语言：

| 母库旧名 | 数据源完整名 | 适配 |
|---|---|---|
| `Ring ASSY Sunroof Re` | Sunroof Reinforcement Ring Assembly | 1991-1995 Hyundai Elantra |
| `Panel ASSY Front Door Trim RH` | Front Door Trim Panel Assembly Right Hand | 2024-2026 Hyundai Sonata |
| `Lamp ASSY O Head Con` | Overhead Console Lamp Assembly | 2008-2014 Hyundai Genesis |

**→ 零件名映射表不用人工建了，数据源直接给。**
但数据要一条条抓，共 22 万条 —— 这正是需要服务器 24 小时跑的原因。

### 分工（重要）

| 任务 | 跑在哪 | 原因 |
|---|---|---|
| 数据补强 / 出页 / 发布 / IndexNow | **服务器** | 无需 Google API，境内服务器配代理即可 |
| 收录率周测 / GSC 周报 / sitemap 提交 | **本机** | 依赖 Google OAuth 凭据与本地代理 |

**不要两边同时跑发布线**，会重复发布。服务器上线的同时，
把本机的 `automation-1792049617751`（每 2 天 600 页发布线）改为 PAUSED。

---

## 二、架构

```
                   ┌──────────────────────────────────────┐
   每天 01:00       │  服务器（cron → deploy/oe_pipeline.sh）│
   ───────────────>│                                       │
                   │  1. enrich：抓 hyundaipartsdeal 补数据 │
                   │     → .workbuddy/data/oe-enriched.jsonl│
                   │  2. 护栏：2 天内发过就跳过             │
                   │  3. release → generate → hubs         │
                   │  4. 健康检查（不通过则中止）           │
                   │  5. git push + IndexNow 推送          │
                   └──────────────────────────────────────┘
                                    │
                                    ▼
                        GitHub → Cloudflare Pages
                                    │
   周二 09:30（本机）               ▼
   收录率周测 ───────────────>   Google 抓取收录

```

---

## 三、部署（6 步）

### 步骤 1：装基础环境

```bash
apt-get update && apt-get install -y git python3 python3-pip curl
python3 -m pip install --upgrade requests
```

### 步骤 2：拉仓库

```bash
git clone <仓库地址> ~/ucars
cd ~/ucars
```

### 步骤 3：⚠️ 同步 `.workbuddy` 目录（最容易漏的一步）

`.workbuddy` 在 `.gitignore` 第 88 行被排除，**clone 是不会带下来的**，
但所有 Python 脚本和 70MB 母库都在里面。必须单独同步：

```bash
# 从工作站同步（Windows 侧用 scp / rsync / rclone 都行）
rsync -avz --progress \
   user@workstation:/c/Users/123/WorkBuddy/20260324111450/.workbuddy/ \
   ~/ucars/.workbuddy/

# 或先打个包再传（70MB+，含母库）
tar czf workbuddy.tar.gz .workbuddy
```

必须确认以下存在：

- `.workbuddy/scripts/`（含 `enrich_oe_from_hpd.py`、`release_next_oe.py` 等）
- `.workbuddy/data/oe-master-db.json`（母库）
- `.workbuddy/data/` 下的历史 `oe-release-*-allowlist.json`（护栏靠它判断）

### 步骤 4：验证 git 推送能用

```bash
# remote URL 内嵌 PAT。确认可见：
git remote -v
# 实测推送能力（ls-remote 通就基本没问题）
git -c credential.helper= ls-remote origin
```

> **推送务必用 `git -c credential.helper= push origin main`。**
> 不加这个参数，credential helper 会让 push 永久挂起（本机踩过：卡死需手动杀）。
> 流水线脚本里已经写好了这个参数。

### 步骤 5：跑环境自检

```bash
REPO=~/ucars PY=/usr/bin/python3 bash deploy/env_check.sh
```

逐项看输出，按提示补齐。重点关注：

- 数据源可达性（决定要不要配 `ENRICH_PROXY`）
- GitHub 可达性（境内服务器需 `git config http.proxy`）
- GSC API 可达性（不可达没关系，GSC 任务本来留在本机）

### 步骤 6：手动跑一遍 + 装 crontab

```bash
# 先空跑看命令序列对不对
DRY=1 REPO=~/ucars bash deploy/oe_pipeline.sh

# 真跑一次小批量（10 条，验证链路）
REPO=~/ucars ENRICH_LIMIT=10 ENRICH_MODE=released bash deploy/oe_pipeline.sh

# 没问题后装 crontab
crontab -e   # 粘贴 deploy/crontab.example 的内容
```

---

## 四、文件清单

| 路径 | 作用 |
|---|---|
| `deploy/README.md` | 本文档 |
| `deploy/env_check.sh` | 服务器环境自检（部署前必跑） |
| `deploy/oe_pipeline.sh` | 每日流水线主脚本 |
| `deploy/crontab.example` | crontab 模板 |
| `.workbuddy/scripts/enrich_oe_from_hpd.py` | **新增**：B 层数据补强（断点续传） |
| `.workbuddy/data/oe-enriched.jsonl` | **新增**：补强产出，一行一条，增量追加 |
| `.workbuddy/data/oe-enrich-progress.json` | 补强进度统计 |

> `deploy/` 在仓库内（会入库，clone 即得）；
> `.workbuddy/` 不入库（需单独同步）。

---

## 五、三阶段路线（不要跳步）

### 阶段 1 · 存数据（立即启动，零风险）

服务器 24 小时跑 `enrich`，把 22 万条的结构化数据抓回来。
纯数据采集，断点续传，不碰任何线上页面，**失败也没有副作用**。

```bash
# 前 2 周：只补已发布的 14,772 条（补完能立刻重出页见效）
ENRICH_MODE=released ENRICH_LIMIT=3000 ENRICH_WORKERS=4 bash deploy/oe_pipeline.sh
```

耗时估算（实测 0.91s/条）：

| 范围 | 单线程 | 4 线程 |
|---|---:|---:|
| 已发布 14,772 条 | 3.7 小时 | **1 小时** |
| 全量 221,663 条 | 56 小时 | **14 小时** |

### 阶段 2 · 消费数据（需改代码，风险中等）

让 `generate_oe_pages.py` 读取 `oe-enriched.jsonl`，把 fitment 与完整名写进页面。
**这一步必须先在小批量上验证 + 跑健康检查门禁，再全量。**

改动点为 OE 页模板：

- 标题 / H1：`{完整零件名} {OE号} for {车型} {年份}`（现在是缩写）
- 正文新增适配车型区块：`Fits 2009-2015 Hyundai Tucson`
- JSON-LD 补 `Product` 的 `mpn`、可补 `ItemList`（适配车型列表）

### 阶段 3 · 重出存量页（规模大，最后做）

已发布的 14,772 页用新数据重新出页。
**建议分批做**（每批 1000-2000 页），每批跑一次健康检查，避免一次性全量重写。

---

## 六、日常运维

```bash
# 看今天流水线跑了什么
tail -f ~/ucars/.workbuddy/logs/pipeline-$(date +%F).log

# 看补强累计进度
cat ~/ucars/.workbuddy/data/oe-enrich-progress.json

# 抽查补强出来的数据
head -5 ~/ucars/.workbuddy/data/oe-enriched.jsonl | python3 -c \
  "import sys,json;[print(json.loads(l)['oe'], json.loads(l).get('name_clean'), json.loads(l).get('fitment')) for l in sys.stdin]"

# 手动补一批（临时加量）
REPO=~/ucars ENRICH_LIMIT=10000 ENRICH_MODE=new bash deploy/oe_pipeline.sh

# 检查服务器磁盘（OE 页每千页约 100-200MB）
df -h ~/ucars
```

### 切阶段

阶段 1 把已发布页补完后，改 crontab 的 `ENRICH_MODE`：

```
ENRICH_MODE=released   →   前 2 周（先补已上线页面）
ENRICH_MODE=new        →   之后（为后续发布备数据）
```

---

## 七、故障排查

| 现象 | 原因 / 处理 |
|---|---|
| 流水线没跑 | 查 `crontab -e` 里环境变量是否写了（cron 不加载 profile）；看 `/var/log/cron` |
| push 卡住不动 | 脚本里必须用 `git -c credential.helper= push`。若仍卡，`timeout 600` 会兜底杀掉 |
| 大批 `http403` / `http429` | 数据源限流。调大 `ENRICH_DELAY`（→2.0）或减小 `ENRICH_WORKERS`（→2） |
| `no_ld` 增多 | 数据源改版或返回反爬页。先 curl 一条看 HTML；必要时暂停并修 `parse_ld` |
| 健康检查不通过 | 流水线会**自动中止推送**并 exit 1，等人工处理。不要注释掉这一步 |
| 磁盘涨得快 | OE 页量大。定期清理 `.workbuddy/logs`（crontab 已配 30 天轮转） |

### 已知陷阱（别踩）

1. **`release_next_oe.py` 没有 argparse，加 `--help` 会被当成正常参数直接触发 release**
   （2026-10-15 实测误触发过）。确认参数只能读源码，别试探。
2. 它一旦跑了，DB 里那批就标记为 released，**必须立刻接出页步骤**，否则永久漏发。
3. `.workbuddy` 不入库，换服务器必须单独同步（步骤 3）。

---

## 八、合规与护栏

### 数据使用边界（铁律）

| 数据 | 可否使用 | 说明 |
|---|---|---|
| fitment（车型 + 年份） | ✅ 直接可用 | 事实性数据，不受版权保护 |
| 完整零件名 | ✅ 可用 | 脚本已自动脱敏：去品牌前缀、去内嵌 OE 号 |
| 图片 URL | ⚠️ **只归档，不下载不上架** | 项目铁律：竞品图永不直接上架，仅作 AI 重生成参考 |
| 价格 MSRP | ⚠️ 仅存档参考 | 是竞品零售价，**不得显示为本站报价**（规范：不编造 price） |

`enrich_oe_from_hpd.py` 已按此实现：`ref_imgs` 只存 URL，不下载。

### 发布护栏（脚本内已实现）

- **每 2 天 600 页**：流水线检查 2 天内是否有发布记录，有则跳过
- **健康检查门禁**：`seo_health_monitor.py` 不通过则中止推送
- **防重入**：lock 文件 + pid 检查，上一轮没跑完不启动下一轮
- **循环速率**：`ENRICH_DELAY` 默认 1.0s，`ENRICH_WORKERS` 默认 4

### 关于"发布节奏能不能伪装成人工"

**不能，也不必。** Google 判定 Scaled Content Abuse 看的是**页面有没有独立价值**，
不是发布曲线；算法侧不存在"发布速度方差"信号。每天 210 页、月产 6300 页，
在 210–300 之间抖动仍是清晰批量模式。

真正的提升路径是**让页面有独立价值**（补 fitment、给完整名、配图），
这正是这套流水线在做的事 —— 而不是在曲线上做伪装。

---

## 九、上线检查清单

- [ ] `deploy/env_check.sh` 全部通过
- [ ] `.workbuddy` 已同步（母库 70MB 到位）
- [ ] `git -c credential.helper= push` 实测通过
- [ ] `DRY=1` 空跑命令序列无误
- [ ] 小批量（10 条）真跑成功
- [ ] crontab 已安装，次日 01:00 的日志正常生成
- [ ] **本机发布线自动化已改 PAUSED**（避免两边重复发布）
- [ ] 本机周二 09:30 收录率周测仍在跑（这是判断成效的北极星）
