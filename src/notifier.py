import os
import requests
from dotenv import load_dotenv

# ==========================================
# 优先级 高：环境配置与拦截
# ==========================================
load_dotenv()
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

if not TG_BOT_TOKEN or not TG_CHAT_ID:
    raise ValueError("严重错误: 环境变量中缺失 TG_BOT_TOKEN 或 TG_CHAT_ID。")


def send_telegram_message(text: str) -> bool:
    """
    通过 Telegram Bot API 发送 Markdown 格式的消息。
    """
    if not text:
        print("警告: 尝试发送空消息，已拦截。")
        return False

    # Telegram SendMessage API 端点
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"

    # 构造请求体，指定 parse_mode 为 Markdown 以支持加粗和链接
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,  # 禁用网页预览，保持消息界面整洁
    }

    try:
        # ==========================================
        # 优先级 高：网络请求与容错
        # 设置 timeout 防止网络阻塞挂起整个服务
        # ==========================================
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()
        if result.get("ok"):
            print("消息投递成功。")
            return True
        else:
            print(f"投递失败，Telegram API 返回: {result}")
            return False

    except requests.RequestException as e:
        print(f"推送通道网络异常: {e}")
        return False


if __name__ == "__main__":
    # ==========================================
    # 优先级 低：本地单元测试模块
    # ==========================================
    test_message = """
    *GitHub 趋势日报测试*
    
    📦 项目: `test/awesome-ai`
    💡 概念: 这是一个极简的测试项目。
    🛠️ 技术栈: Python, FastAPI
    
    [🔗 点击查看项目](https://github.com)
    """

    success = send_telegram_message(test_message)
    if not success:
        print("本地测试未通过，请检查网络连通性或 Token/ChatID 的正确性。")
