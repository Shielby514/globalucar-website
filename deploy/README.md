# OE 库服务器 24 小时发布 —— 部署与交接文档

> 版本：2026-10-26 ｜ 站点：`https://www.global-ucars.com`
> 部署环境：**境内公司局域网**（本节所有代理配置为此而设）
> 目标：**服务器全年无休运行**，每天自动「补数据 → 出页 → 发布 → 推送」。
>
> 本文档自成一体。拿到服务器后按顺序读：
> 「一、速览」→ **「二、境内部网专项」**（别跳）→「四、部署」。
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

## 二、境内部网专项（部署前必读）

> 本部署环境：**境内公司局域网**。这一节的所有内容都和境外 VPS 不同，
> 跳过会直接卡住。先花 5 分钟判断自己属于哪种出口情形。

### 2.1 先判断：你的服务器能不能出境

在服务器上跑这三条，看结果：

```bash
# ① 能不能到数据源（要 200）
curl -s -o /dev/null -w "%{http_code}\n" --max-time 20 \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://www.hyundaipartsdeal.com/genuine/hyundai-cover-rr-seat-mtg~89137-2e001-z9.html"

# ② 能不能到 GitHub（200 或 401 都算通，000 才算不通）
curl -s -o /dev/null -w "%{http_code}\n" --max-time 20 https://api.github.com

# ③ 有没有现成代理
env | grep -iE 'https?_proxy' || echo "无全局代理变量"
```

> ⚠️ 第 ① 条**必须带完整浏览器 UA**。数据源有 UA 反爬，
> 短 UA `Mozilla/5.0` 会被判 **403**，看起来像"被墙"，实际是反爬。
> 这个坑让自检误报过一次。

### 2.2 三种情形，三条路

| 情形 | 表现 | 部署方式 |
|---|---|---|
| **A. 有公司统一出口代理** | 直连失败，`curl -x proxy` 成功 | 最理想。`ENRICH_PROXY` + `GIT_PROXY` 都填代理地址，其余照本文档走 |
| **B. 局域内有可出网机器** | 服务器不能出网，但同网段某台机器能 | 在那台机器装 squid/privoxy 做正向代理，服务器指过去。等价于情形 A |
| **C. 全网不能出境** | 加代理也不行，白名单锁死 | 走"本机抓取 + rsync 同步"，见 2.5。**服务器退化为纯出页机器** |

**先跑 `deploy/env_check.sh`，它会直接告诉你落在哪种情形**，
不用自己判断。

### 2.3 情形 A/B：代理怎么填

```bash
# 无认证
ENRICH_PROXY=http://10.0.0.5:8080
GIT_PROXY=http://10.0.0.5:8080

# 有认证（用户名/密码含特殊字符必须 URL 编码）
ENRICH_PROXY=http://user:p%40ssw0rd@10.0.0.5:8080
```

三个必检点：

1. **代理端口不一定是 8080**。公司常见 8080/3128/8000/1080（socks5 需写 `socks5://`）
2. **域名白名单**。公司代理常只放行常见站点，`hyundaipartsdeal.com` 和
   `github.com` 要单独申请加白。env_check 会分别测这两个域名，缺哪个补哪个
3. **`GIT_PROXY` 必须单独设**。git 不总是继承 `HTTPS_PROXY`，流水线用
   `-c http.proxy=` 显式传，最稳

验证代理真的能出去（不是"端口开着"）：

```bash
curl -x $ENRICH_PROXY -o /dev/null -w "%{http_code}\n" -A "$UA" "https://www.hyundaipartsdeal.com/..."
curl -x $GIT_PROXY    -o /dev/null -w "%{http_code}\n" https://api.github.com
```

**内置的省时机制**：`enrich_oe_from_hpd.py` 启动时会先抓一条做预检，
代理不通立刻 `exit 1` 并打印三种处置建议，**不会白跑 45 分钟**再报错。
流水线收到非 0 退出码会直接中止本轮，不会带着坏网络去发布。

### 2.4 境内特有故障模式

| 现象 | 真实原因 | 处理 |
|---|---|---|
| 数据源 403，但浏览器能打开 | **UA 反爬**，不是墙 | curl 要带完整 Chrome UA；脚本已内置 |
| 代理端口能 telnet 通，请求却 000 | 代理只放行 80/443 白名单 | 申请把两个域名加白 |
| 白天正常，01:00 全失败 | 公司夜间断网/切换出口 | 把流水线改到 08:30（crontab 改 `30 8 * * *`） |
| push 超时但 `git ls-remote` 正常 | credential helper 挂起 | 必须 `git -c credential.helper= push`（脚本已带） |
| 补强很慢（>2s/条） | 代理带宽被办公流量挤占 | `ENRICH_WORKERS=2`、`ENRICH_DELAY=2.0`，或改夜间跑 |
| 大批 `SSL: CERTIFICATE_VERIFY_FAILED` | 公司做了 SSL 中间人解密 | 让 IT 提供公司根证书，或换一台不走解密的机器 |

### 2.5 情形 C：全网不能出境怎么办

这是境内部网的真实常见情况。分工改成"本机抓、服务器发"：

```
本机（能出境）                     服务器（不能出境）
─────────────────                ─────────────────
enrich 抓数据                     读 oe-enriched.jsonl
      │                                  │
      └── rsync oe-enriched.jsonl ──────>┘
                                         │
                                   release + 出页 + 健康检查
                                         │
                                   git commit（只在本地）
                                         │
         <──── rsync 页面回来 ────────────┘
      │
      └── git push（本机推）
```

落地方式：

```bash
# 本机：每天抓完推过去
python .workbuddy/scripts/enrich_oe_from_hpd.py --limit 3000 --workers 4
rsync -avz .workbuddy/data/oe-enriched.jsonl server:~/ucars/.workbuddy/data/

# 服务器：流水线去掉 enrich 和 push 两步（设两个开关）
ENRICH_LIMIT=0 GIT_PUSH=0 bash deploy/oe_pipeline.sh

# 本机：拉回页面并推送
rsync -avz server:~/ucars/oe/ ./oe/
git -c credential.helper= push origin main
```

> 情形 C 下服务器价值打折（只剩出页），但仍有意义：出页是 CPU/IO 密集，
> 放服务器不影响本机使用。若嫌麻烦，也可以全程只在本机跑，
> 代价是本机不能关机。

### 2.6 境内部网的数据安全边界（别忽略）

服务器在公司内网，意味着：

- `.workbuddy/data/` 里有母库与补强数据（含竞品 MSRP）→ **不要开公网访问**，
  只允许 SSH 进来
- `git remote` URL 内嵌 PAT（明文）→ 服务器若多人共用，改用
  `git config credential.helper store` + 单独的 deploy key，别把 PAT 写在 URL 里
- 公司安全策略常扫出网流量。补强是每天 3000 次境外 HTTPS 请求，
  **上线前跟 IT 报备一声**，避免被当成异常外联掐掉

---

## 三、架构

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

## 四、部署（6 步）

> 境内部网请先读完第二节，确认自己在情形 A/B 还是 C。

### 步骤 0：先确定两件事

```bash
# ① 时区（01:00 按服务器本地时间触发）
sudo timedatectl set-timezone Asia/Shanghai
timedatectl

# ② 代理变量（情形 A/B 必填，情形 C 跳过）
export ENRICH_PROXY=http://10.0.0.5:8080
export GIT_PROXY=http://10.0.0.5:8080
```

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

# 境内：把代理写进仓库配置（流水线还会用 GIT_PROXY 显式覆盖，双保险）
git config http.proxy  "$GIT_PROXY"
git config https.proxy "$GIT_PROXY"

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

## 五、文件清单

| 路径 | 作用 |
|---|---|
| `deploy/README.md` | 本文档 |
| `deploy/env_check.sh` | 环境自检：**直连与代理双测**、DNS、NTP、cron 状态、推送能力（部署前必跑） |
| `deploy/oe_pipeline.sh` | 每日流水线主脚本（含预检失败即停、`ENRICH_LIMIT=0`/`GIT_PUSH=0` 情形 C 开关） |
| `deploy/crontab.example` | crontab 模板（境内版，代理已预留） |
| `.workbuddy/scripts/enrich_oe_from_hpd.py` | **新增**：B 层数据补强（断点续传） |
| `.workbuddy/data/oe-enriched.jsonl` | **新增**：补强产出，一行一条，增量追加 |
| `.workbuddy/data/oe-enrich-progress.json` | 补强进度统计 |

> `deploy/` 在仓库内（会入库，clone 即得）；
> `.workbuddy/` 不入库（需单独同步）。

---

## 六、三阶段路线（不要跳步）

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

## 七、日常运维

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

## 八、故障排查

| 现象 | 原因 / 处理 |
|---|---|
| 流水线没跑 | 查 `crontab -e` 里环境变量是否写了（cron 不加载 profile）；看 `/var/log/cron` |
| push 卡住不动 | 脚本里必须用 `git -c credential.helper= push`。若仍卡，`timeout 600` 会兜底杀掉 |
| 大批 `http403` / `http429` | 数据源限流。调大 `ENRICH_DELAY`（→2.0）或减小 `ENRICH_WORKERS`（→2） |
| `no_ld` 增多 | 数据源改版或返回反爬页。先 curl 一条看 HTML；必要时暂停并修 `parse_ld` |
| 健康检查不通过 | 流水线会**自动中止推送**并 exit 1，等人工处理。不要注释掉这一步 |
| 磁盘涨得快 | OE 页量大。定期清理 `.workbuddy/logs`（crontab 已配 30 天轮转） |
| **预检就失败，日志只有三行** | 代理不通。这是内置保护：宁可 10 秒退出，不白跑 45 分钟。按日志里的三条建议逐一试 |
| **数据源 403** | 先排除 UA 反爬（用完整 Chrome UA 重试），再怀疑墙 |
| **补强速度突然降到 >2s/条** | 代理带宽被办公流量挤占。`ENRICH_WORKERS=2` 或改夜间 |
| **SSL CERTIFICATE_VERIFY_FAILED** | 公司 SSL 中间人解密。找 IT 要根证书，或换不走解密的机器 |
| **01:00 全失败，白天手工跑正常** | 公司夜间断网。crontab 改 `30 8 * * *` |

### 已知陷阱（别踩）

1. **`release_next_oe.py` 没有 argparse，加 `--help` 会被当成正常参数直接触发 release**
   （2026-10-15 实测误触发过）。确认参数只能读源码，别试探。
2. 它一旦跑了，DB 里那批就标记为 released，**必须立刻接出页步骤**，否则永久漏发。
3. `.workbuddy` 不入库，换服务器必须单独同步（步骤 3）。

---

## 九、合规与护栏

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

## 十、上线检查清单

**通用**

- [ ] `deploy/env_check.sh` 全部通过（0 FAIL）
- [ ] `.workbuddy` 已同步（母库 70MB 到位）
- [ ] `git -c credential.helper= push` 实测通过
- [ ] `DRY=1` 空跑命令序列无误
- [ ] 小批量（10 条）真跑成功
- [ ] crontab 已安装，次日 01:00 的日志正常生成

**境内局域网专项**

- [ ] 已判定出口情形（A 有代理 / B 跳板机 / C 全网不出境）
- [ ] `ENRICH_PROXY` 实测能取到数据源 200
- [ ] `GIT_PROXY` 实测能到 api.github.com
- [ ] 两个域名已申请加入公司代理白名单
- [ ] 时区为 `Asia/Shanghai`，NTP 已同步（时间漂移会让证书校验失败）
- [ ] `systemctl is-enabled cron` 为 enabled（断电恢复后才会继续跑）
- [ ] 已向 IT 报备每日 3000 次境外 HTTPS 请求
- [ ] 情形 C 的话：`ENRICH_LIMIT=0 GIT_PUSH=0` 已写进 crontab，rsync 链路已通
- [ ] 服务器未开公网访问（`.workbuddy/data` 含竞品价格数据）

**收尾**

- [ ] **本机发布线自动化已改 PAUSED**（`automation-1792049617751`，避免两边重复发布）
- [ ] 本机周二 09:30 收录率周测仍在跑（这是判断成效的北极星）
