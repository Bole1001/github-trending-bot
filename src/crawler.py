import requests
from bs4 import BeautifulSoup

# 配置全局请求头，伪装成真实浏览器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_trending_repos(limit=5):
    """
    抓取 GitHub Trending 榜单前 N 个项目的基本信息
    """
    print(f"🌍 开始抓取 GitHub Trending 榜单前 {limit} 名...")
    url = "https://github.com/trending"

    try:
        # ⚠️ 方案3核心：把 timeout 从 10 秒放宽到 30 秒
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ 抓取榜单失败: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    repo_articles = soup.find_all("article", class_="Box-row")

    repos = []
    for article in repo_articles[:limit]:
        # 1. 解析项目名和链接
        h2_tag = article.find("h2", class_="h3 lh-condensed")
        if not h2_tag:
            continue

        repo_path = h2_tag.find("a")["href"]
        repo_name = repo_path.lstrip("/")
        full_url = f"https://github.com{repo_path}"

        # 2. 解析项目原生简介 (可能为空)
        p_tag = article.find("p", class_="col-9 color-fg-muted my-1 pr-4")
        description = p_tag.text.strip() if p_tag else "暂无描述"

        repos.append(
            {"repo_name": repo_name, "url": full_url, "description": description}
        )

    return repos


def get_readme(repo_name):
    """
    获取指定项目的 README.md 纯文本
    尝试 main 和 master 两个常见主分支
    """
    print(f"  📄 正在拉取 {repo_name} 的 README...")
    branches = ["main", "master"]

    for branch in branches:
        # 核心技巧：直接访问 raw 内容服务器，无需解析 HTML
        raw_url = f"https://raw.githubusercontent.com/{repo_name}/refs/heads/{branch}/README.md"

        try:
            # ⚠️ 方案3核心：README抓取也放宽到 30 秒
            response = requests.get(raw_url, timeout=30)
            if response.status_code == 200:
                return response.text
        except requests.RequestException:
            pass  # 网络异常直接忽略，尝试下一个分支

    print(f"  ⚠️ 警告: 未能找到 {repo_name} 的 README")
    return ""


if __name__ == "__main__":
    print("--- 爬虫模块本地测试 ---")
    test_repos = get_trending_repos(limit=3)

    for repo in test_repos:
        print(f"\n📦 项目: {repo['repo_name']}")
        print(f"🔗 链接: {repo['url']}")
        print(f"💡 简介: {repo['description']}")

        readme_text = get_readme(repo["repo_name"])
        if readme_text:
            print(f"✅ README 抓取成功，总长度: {len(readme_text)} 字符")
            print(f"✂️  预览前100字符: {readme_text[:100].replace(chr(10), ' ')}...")
