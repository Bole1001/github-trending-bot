import time
import traceback
from src.crawler import get_trending_repos, get_readme
from src.llm_service import analyze_repo
from src.notifier import send_telegram_message

# ==========================================
# 优先级 高：全局调度配置
# ==========================================
TARGET_REPO_COUNT = 3
SLEEP_INTERVAL = 5


def format_markdown_message(repo_data: dict, ai_analysis: dict) -> str:
    """
    将原始数据和 AI 分析结果组装为 Telegram 支持的 Markdown 格式。
    """
    msg = f"📦 *项目*: `{repo_data['repo_name']}`\n"
    msg += f"🔗 *链接*: [点击直达 GitHub]({repo_data['url']})\n\n"

    if ai_analysis:
        msg += f"💡 *核心概念*: {ai_analysis.get('core_concept', '未提取出核心概念')}\n"
        tech_stack = ", ".join(ai_analysis.get("tech_stack", []))
        msg += f"🛠️ *技术栈*: {tech_stack}\n"
        msg += f"👥 *目标受众*: {ai_analysis.get('target_audience', '未明')}\n"
        msg += f"🔥 *爆火推测*: {ai_analysis.get('why_trending', '未明')}\n"
    else:
        msg += f"⚠️ *AI 分析失败，原生简介*: {repo_data['description']}\n"

    msg += "—" * 20 + "\n"
    return msg


def execute_pipeline():
    """
    执行核心流水线。
    职责：仅处理业务流转，遇到致命错误主动抛出异常 (raise)。
    """
    repos = get_trending_repos(limit=TARGET_REPO_COUNT)
    if not repos:
        # 业务逻辑阻断：主动抛出异常以触发外层告警
        raise RuntimeError(
            "爬虫模块返回空数据，GitHub Trending 页面结构可能已变更或遭遇反爬拦截。"
        )

    final_messages = ["📊 *今日 GitHub Trending 核心摘要* 📊\n\n"]

    for index, repo in enumerate(repos):
        print(f"\n[{index+1}/{len(repos)}] 正在处理: {repo['repo_name']}")

        readme_text = get_readme(repo["repo_name"])

        ai_result = None
        if readme_text:
            ai_result = analyze_repo(
                repo["repo_name"], repo["description"], readme_text
            )
        else:
            print("警告：缺少 README，跳过 AI 分析阶段。")

        repo_msg = format_markdown_message(repo, ai_result)
        final_messages.append(repo_msg)

        if index < len(repos) - 1:
            print(f"进入强制休眠 {SLEEP_INTERVAL} 秒...")
            time.sleep(SLEEP_INTERVAL)

    daily_digest = "".join(final_messages)

    print("\n>>> 流水线处理完毕，准备执行终端投递 <<<")
    success = send_telegram_message(daily_digest)

    if not success:
        raise RuntimeError("Telegram 推送接口调用失败，请检查网络或配置。")


def main():
    """
    主控入口。
    职责：全局错误捕获与系统级告警分发。
    """
    print(">>> 启动 GitHub 趋势自动抓取与分析流水线 <<<")
    try:
        execute_pipeline()
        print("流水线正常结束。")
    except Exception as e:
        # 优先级 极高：拦截崩溃并执行降级通信
        error_details = traceback.format_exc()
        print(f"发生致命错误:\n{error_details}")

        # 构造 Telegram 告警结构
        alert_msg = (
            "🚨 *[系统告警] GitHub 趋势机器人运行异常* 🚨\n\n"
            f"**错误类型**: `{type(e).__name__}`\n"
            f"**错误原因**: `{str(e)}`\n\n"
            "⚠️ *请立即登录 GitHub Actions 控制台查看完整运行日志。*"
        )

        # 尝试发送告警。若此处再次失败，则物理机/容器彻底失联。
        send_telegram_message(alert_msg)


if __name__ == "__main__":
    main()
