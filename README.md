# AI Radar · AI 情报决策台

> 个人自用的 AI 领域资讯聚合与情报决策服务：自动采集全球 AI 新闻与开源项目动态，经过去重、AI 相关性过滤、热度归一化、LLM 中文提炼与事实核查、五维评分后，通过**网页**与**飞书推送**两种方式呈现。每天几分钟，知道「发生了什么、为什么重要、是否与你相关、哪些值得进一步验证」。

---

## 最近迭代（v2.1.0）升级能力

本次迭代聚焦「信息时效收敛 + 历史可回溯 + 精简 Brief」，新增/升级能力如下：

### 1. 首页与推送收敛到「当天 + 前一天」
首页各信息流模块（今日 Briefing / 必须知道 / 与我相关 / 趋势升温 / 模型发布雷达 / 热门项目）与飞书推送统一只展示 `published_at` 在「当天 + 前一天」时间窗口内的信息，消除非当天旧闻；「我的收藏」不限日期。

### 2. 历史信息查询页
新增 `/history` 页面，首页顶栏「历史」入口直达；支持按日期精确查询、分类筛选与分页（每页 50）。

### 3. 新增 ~50 字 Brief 字段
数据模型新增 `brief` 字段（约 50 字一句话简述），飞书推送与网页卡片摘要优先展示 brief（为空回退 summary_zh）。LLM 在同一次提炼调用中一并产出，零额外调用成本；存量数据不回填。

---

## v2.0.0 升级能力（历史）

本次迭代将产品从「新闻聚合器」正式升级为「AI 情报决策台」，围绕**判断与决策**组织信息。新增/升级能力如下：

### 1. 五维评分系统
每条信息计算 5 个分数，加权得出综合优先级，作为首页排序与「必须知道」的选取依据。

| 分数 | 实现方式 | 考量维度 |
|---|---|---|
| 相关性分数 | 规则（关注主题关键词 + 权重） | 与用户关注方向的相关程度 |
| 可信度分数 | 规则（来源层级映射） | 官方 > 学术/媒体 > 社区 > 匿名 |
| 重要性分数 | LLM（合并 1 次调用） | 能力突破 / 多源确认 / 影响面 / 格局变化 |
| 新颖性分数 | LLM（同上合并调用） | 真新能力 / 小优化 / 重包装 / 宣传 / 重复 |
| 行动价值分数 | LLM（同上合并调用） | 立即体验 / 观察 / 精读 / 机会 / 忽略 |

**综合优先级**：`重要性×30% + 相关性×30% + 可信度×20% + 新颖性×10% + 行动价值×10%`

> 降本设计：相关性/可信度用**规则**（零 LLM 成本），重要性/新颖性/行动价值用 **1 次合并 LLM 调用**产出。

### 2. 主题分类
规则关键词分类，12 个主主题标签（Agent / 多模态 / 端侧模型 / AI 硬件 / 语音 / Memory / MCP 工具 / 模型成本 / 产品商业化 / 商业政策 / 论文 / 开源项目），每条信息打 1 个主主题，供首页筛选。

### 3. 今日 AI Briefing
每天定时流水线结束后，取综合分 top 资讯，LLM 生成「今日简报」：一句「今日一句话」头条 + 逐条「一句话结论 + 为什么重要」，首页首屏展示并随飞书推送发送。

### 4. 收藏与已读
每条信息支持「已读 / 收藏」标记，本地 SQLite 持久化，首页按状态筛选。

### 5. 模型发布雷达
从 GitHub Releases + 新闻流中识别「模型发布/更新」事件，单列展示最新模型动态。

### 6. 每周总结
每周生成周报：本周最重要变化 / 升温趋势 / 营销噪声判断 / 行动建议，通过飞书推送。

### 7. 首页 MVP 重构
六区域决策台布局（今日 Briefing / 必须知道 / 与我相关 / 趋势升温 / 模型发布雷达 / 热门项目 / 收藏·待验证），信息卡片 20 秒可读完。

### 8. 数据模型升级
新增 9 个字段（`category` + 五维评分 + `final_score` + `is_read` + `is_starred`），采用**轻量迁移**（`ALTER TABLE ADD COLUMN`）为旧库补齐列，**保留既有数据、不重建表**。

### 9. 飞书推送增强
推送卡片每条新增「综合分 + 主题分类」展示。

---

## 核心链路

```
信息采集 → 去重与聚类 → 重要性判断 → 个性化关联 → 人工阅读与收藏 → 形成长期认知
```

## 信息源

| 分类 | 来源 |
|---|---|
| 官方/技术博客 RSS | OpenAI、Anthropic、Google DeepMind、Hugging Face、NVIDIA 等 |
| 被墙博客 RSS | Meta / Microsoft / Google / xAI（默认关闭，需代理） |
| 国内科技媒体 RSS | 机器之心、量子位、新智元 |
| Reddit | r/MachineLearning、r/LocalLLaMA、r/artificial、r/singularity |
| Hacker News | 官方 API top stories |
| GitHub | 25 个活跃 AI 项目的 Releases + 每日 Trending |

## 技术栈

- **Python 3.12** / FastAPI / Uvicorn
- SQLAlchemy 2.0 + SQLite（`data/news.db`）
- APScheduler（每日定时调度）
- DeepSeek（经阿里百炼 DashScope 兼容接口）做 LLM 提炼、评分、简报
- Jinja2 模板（服务端渲染首页）
- 飞书自建应用机器人（推送）

## 目录结构

```
app/
├── collectors/        # 数据采集器（HN / Reddit / GitHub / RSS）
├── pipeline/          # 处理流水线
│   ├── dedup.py       # URL + 标题相似度去重
│   ├── filter.py      # AI 相关性过滤
│   ├── llm.py         # LLM 提炼 + 事实核查自检
│   ├── scoring.py     # 热度归一化
│   ├── classify.py    # 主题分类（v2.0.0）
│   ├── rating.py      # 五维评分（v2.0.0）
│   ├── radar.py       # 模型发布雷达（v2.0.0）
│   └── briefing.py    # 今日 Briefing / 每周总结（v2.0.0）
├── main.py            # FastAPI 应用 + API 路由
├── models.py          # 数据模型
├── database.py        # 连接 + 轻量迁移
├── scheduler.py       # 每日流水线调度
├── feishu.py          # 飞书推送
├── config.py          # 配置
└── templates/         # 首页 + 历史页模板
docs/PRD.md            # 产品需求文档（唯一权威来源）
```

## 快速开始

```bash
# 1. 创建虚拟环境并安装依赖
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. 配置环境变量（复制模板后填写）
cp .env.example .env
#   必填：DASHSCOPE_API_KEY
#   可选：飞书推送、GitHub Token、代理与被墙源开关

# 3. 启动
./run.sh
#   本机访问 http://127.0.0.1:8000
```

首次启动自动建库并执行轻量迁移。

## 配置项（.env）

| 配置 | 说明 | 默认 |
|---|---|---|
| `DASHSCOPE_API_KEY` | 阿里百炼 API Key（必填） | 空 |
| `DASHSCOPE_MODEL` | LLM 模型 | `deepseek-v4-pro` |
| `UPDATE_HOUR` / `UPDATE_MINUTE` | 每日更新时刻 | `8` / `0` |
| `DATABASE_URL` | 数据库路径 | `sqlite:///data/news.db` |
| `FEISHU_*` | 飞书推送（留空则关闭） | 空 |
| `ENABLE_BLOCKED_SOURCES` | 被墙源开关 | `false` |
| `HTTP_PROXY` / `HTTPS_PROXY` | 本地代理 | 空 |

## API 路由

| 路由 | 方法 | 说明 |
|---|---|---|
| `/` | GET | 首页（分页） |
| `/history` | GET | 历史信息查询页（按日期/分类查询、分页） |
| `/update` | POST | 手动触发一次完整流水线 |
| `/api/articles` | GET | 文章列表（分类/状态筛选、日期窗口 `since`/`date`/`days`、排序、分页） |
| `/api/articles/{id}/read` | POST | 标记已读 |
| `/api/articles/{id}/star` | POST | 切换收藏 |
| `/api/briefing` | GET | 即时生成今日 Briefing |
| `/api/radar` | GET | 模型发布雷达 |
| `/api/weekly` | POST | 生成过去 7 天周报 |

## 部署

- macOS 常驻：通过 launchd 开机自启 + 崩溃自动拉起，服务名 `com.omo.ai-news-aggregator`（见 `deploy/com.omo.ai-news-aggregator.plist`）。
- 敏感凭证仅存 `.env`，不入库；`.env` / 数据库 / 虚拟环境 / 缓存均由 `.gitignore` 忽略。

## 许可证

个人项目，仅供自用。
