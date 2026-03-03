import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 优先级 高：环境配置拦截
# ==========================================
GIST_TOKEN = os.getenv("GIST_TOKEN")
GIST_ID = os.getenv("GIST_ID")
GIST_FILENAME = "trending_history.json"

if not GIST_TOKEN or not GIST_ID:
    raise ValueError("严重错误: 环境变量中缺失 GIST_TOKEN 或 GIST_ID。")

# Gist API 的标准请求头
HEADERS = {
    "Authorization": f"Bearer {GIST_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def fetch_pushed_history() -> list:
    """
    读取云端 Gist 中的历史推送记录。
    """
    url = f"https://api.github.com/gists/{GIST_ID}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        files = response.json().get("files", {})
        if GIST_FILENAME in files:
            content = files[GIST_FILENAME]["content"]
            # 若为空内容，返回空列表
            if not content.strip():
                return []
            return json.loads(content)
        return []
    except requests.RequestException as e:
        print(f"读取 Gist 网络异常: {e}")
        return []
    except json.JSONDecodeError:
        print("Gist 内容 JSON 解析失败，返回空列表。")
        return []


def update_pushed_history(new_repos: list, max_records: int = 100) -> bool:
    """
    将今日推送的新项目追加到云端 Gist，并执行容量裁剪。
    :param new_repos: 今日新推送的 repo_name 列表
    :param max_records: 历史队列的最大允许长度
    """
    if not new_repos:
        return True

    # 1. 获取现有数据
    current_history = fetch_pushed_history()

    # 2. 追加新数据
    current_history.extend(new_repos)

    # 3. 去重并保持顺序（保留最新的记录）
    seen = set()
    dedup_history = []
    for repo in reversed(current_history):
        if repo not in seen:
            seen.add(repo)
            dedup_history.insert(0, repo)

    # 4. 容量裁剪 (FIFO)
    if len(dedup_history) > max_records:
        dedup_history = dedup_history[-max_records:]

    # 5. 回写云端
    url = f"https://api.github.com/gists/{GIST_ID}"
    payload = {"files": {GIST_FILENAME: {"content": json.dumps(dedup_history)}}}

    try:
        response = requests.patch(url, headers=HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        print(f"Gist 状态更新成功。当前记忆库容量: {len(dedup_history)}/{max_records}")
        return True
    except requests.RequestException as e:
        # 状态更新失败属于业务缺陷，但不应阻断主进程
        print(f"写入 Gist 网络异常: {e}")
        return False
