# GitHub Trending Bot

基于纯 Serverless 架构的 GitHub 趋势自动化追踪与分析推送系统。
本项目通过 GitHub Actions 驱动，自动抓取每日 GitHub Trending 榜单，利用大语言模型（LLM）对开源项目进行摘要提纯，并通过 Telegram 机器人进行精准投递。

## ⚙️ 系统架构与执行链路

本系统采用无状态（Stateless）设计，通过 GitHub Gist 实现轻量级状态持久化与数据去重。数据流向严格遵循单向线性原则：

1. **触发 (Trigger)**：GitHub Actions Cron 定时唤醒云端容器。
2. **捞取 (Ingestion)**：定向抓取 GitHub Trending 榜单前 20 名候选项目。
3. **过滤 (Deduplication)**：通过 Gist API 读取历史推送集合，进行差集计算，顺位截取 3 个全新增量项目。
4. **认知 (Processing)**：拉取增量项目的 README 原文，调用 Google Gemini API 提取结构化核心特征（技术栈、受众、爆火原因）。
5. **投递 (Delivery)**：组装 Markdown 格式报告，通过 HTTP POST 推送至 Telegram 终端。
6. **落盘 (Persistence)**：投递成功后，将新增项目名称追加至 Gist，并执行定长（容量 100）的 FIFO 队列裁剪。

## 🗂️ 核心模块职责矩阵

| 模块文件 | 核心职责 | 脆弱性评估 / 潜在故障点 |
| :--- | :--- | :--- |
| `main.py` | 任务调度、全局异常捕获、降级告警分发。 | **核心枢纽**。若语法错误，系统告警机制将失效。 |
| `src/crawler.py` | HTML DOM 解析、网络请求、超时控制。 | **高风险**。强依赖 GitHub 前端结构。若 DOM 变更，需同步更新解析逻辑。 |
| `src/llm_service.py` | 鉴权懒加载、Prompt 构造、强制 JSON 输出。 | 中风险。依赖 Google API 稳定性及账号配额状态。 |
| `src/storage.py` | Gist REST API 交互、集合去重、容量裁剪。 | 低风险。依赖 GitHub API 稳定性及 Token 有效期。 |
| `src/notifier.py` | Telegram Bot API 交互、Markdown 转义。 | 低风险。注意单条消息不可超过 4096 字符限制。 |

## 🔑 环境变量与凭证配置

部署此项目前，**必须**在本地 `.env` 文件及 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 中配置以下 5 个关键环境变量：

| 变量名 (Secret Name) | 用途说明 | 来源 / 权限要求 |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | 驱动大模型进行文本提纯与总结。 | [Google AI Studio](https://aistudio.google.com/) |
| `TG_BOT_TOKEN` | 授权机器人向外发送 HTTP 请求。 | Telegram `@BotFather` |
| `TG_CHAT_ID` | 指定消息投递的精确目标物理设备/账号。 | Telegram `@userinfobot` (纯数字 ID) |
| `GIST_TOKEN` | 授权脚本读写云端持久化状态文件。 | GitHub PAT (仅需勾选 `gist` 权限) |
| `GIST_ID` | 定位具体存储数据的 JSON 文件物理地址。 | GitHub Gist (URL 中的 32 位 Hash 字符串) |

## 🚨 故障排查与灾备指南 (SOP)

当接收到 Telegram `[系统告警]` 或观察到 GitHub Actions 构建失败时，请按以下路径排查：

**定位入口：** 登录 GitHub 仓库 -> `Actions` -> 点击失败的 Workflow run -> 展开 `Execute Main Pipeline` 步骤查看标准错误输出 (stderr)。

**典型异常对照表：**

* `RuntimeError: 爬虫返回空数据...`
    * **诊断**：GitHub 更改了 Trending 页面的 HTML 结构，反爬策略升级。
    * **修复**：重新审查网页源码，更新 `src/crawler.py` 中的 BeautifulSoup 选择器。
* `401 Unauthorized` (指向 Gist 或 Telegram)
    * **诊断**：对应的 API Token 过期、被撤销或配置名称拼写错误。
    * **修复**：重新生成对应 Token 并覆盖 GitHub Secrets，保持一致性。
* `429 Too Many Requests` (指向 Google API)
    * **诊断**：并发过高或免费配额耗尽。
    * **修复**：检查 `main.py` 中的 `SLEEP_INTERVAL` 是否正常触发，或更换 API Key。
* `JSONDecodeError`
    * **诊断**：大模型未按规范输出 JSON 格式。
    * **修复**：检查 `src/llm_service.py` 中的 `temperature` 设置，或微调 Prompt 强化格式约束。