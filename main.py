import time
from src.crawler import get_trending_repos, get_readme
from src.llm_service import analyze_repo
from src.notifier import send_telegram_message

# ==========================================
# 优先级 高：全局调度配置
# ==========================================
TARGET_REPO_COUNT = 3  # 每次抓取并分析的项目数量 (建议 3-5 个，防止超出 Telegram 单条消息 4096 字符限制)
SLEEP_INTERVAL = 5  # 每次大模型调用后的强制休眠时间（秒），防止触发 API 并发限流


def format_markdown_message(repo_data: dict, ai_analysis: dict) -> str:
    """
    将原始数据和 AI 分析结果组装为 Telegram 支持的 Markdown 格式。
    """
    msg = f"📦 *项目*: `{repo_data['repo_name']}`\n"
    msg += f"🔗 *链接*: [点击直达 GitHub]({repo_data['url']})\n\n"

    # 如果 AI 分析成功，注入 AI 提取的核心特征
    if ai_analysis:
        msg += f"💡 *核心概念*: {ai_analysis.get('core_concept', '未提取出核心概念')}\n"
        tech_stack = ", ".join(ai_analysis.get("tech_stack", []))
        msg += f"🛠️ *技术栈*: {tech_stack}\n"
        msg += f"👥 *目标受众*: {ai_analysis.get('target_audience', '未明')}\n"
        msg += f"🔥 *爆火推测*: {ai_analysis.get('why_trending', '未明')}\n"
    else:
        # LLM 熔断时的降级策略：回退到 GitHub 原生简介
        msg += f"⚠️ *AI 分析失败，原生简介*: {repo_data['description']}\n"

    msg += "—" * 20 + "\n"
    return msg


def main():
    print(">>> 启动 GitHub 趋势自动抓取与分析流水线 <<<")

    # 1. 获取榜单
    repos = get_trending_repos(limit=TARGET_REPO_COUNT)
    if not repos:
        print("致命错误：无法获取榜单数据，主程序终止。")
        return

    final_messages = ["📊 *今日 GitHub Trending 核心摘要* 📊\n\n"]

    # 2. 遍历处理
    for index, repo in enumerate(repos):
        print(f"\n[{index+1}/{len(repos)}] 正在处理: {repo['repo_name']}")

        # 抓取生肉
        readme_text = get_readme(repo["repo_name"])

        # 认知处理
        ai_result = None
        if readme_text:
            ai_result = analyze_repo(
                repo["repo_name"], repo["description"], readme_text
            )
        else:
            print("警告：缺少 README，跳过 AI 分析阶段。")

        # 格式化组装
        repo_msg = format_markdown_message(repo, ai_result)
        final_messages.append(repo_msg)

        # 强制延时（如果是最后一个项目则跳过延时）
        if index < len(repos) - 1:
            print(f"进入强制休眠 {SLEEP_INTERVAL} 秒...")
            time.sleep(SLEEP_INTERVAL)

    # 3. 聚合投递
    # 将列表中的字符串拼接为一个完整的长字符串
    daily_digest = "".join(final_messages)

    print("\n>>> 流水线处理完毕，准备执行终端投递 <<<")
    success = send_telegram_message(daily_digest)

    if success:
        print("流水线正常结束。")
    else:
        print("流水线异常：投递节点失败。")


if __name__ == "__main__":
    main()
