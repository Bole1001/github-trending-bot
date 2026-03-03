import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 优先级 高：移除顶层拦截，改为单例懒加载
# ==========================================
_client = None


def _get_client():
    """
    单例模式获取 Gemini Client。
    将鉴权异常的抛出时机推迟到业务运行期，以确保外层 main.py 能够捕获。
    """
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("严重错误: 环境变量中缺失 GEMINI_API_KEY。")
        _client = genai.Client(api_key=api_key)
    return _client


def analyze_repo(repo_name: str, description: str, readme_text: str) -> dict | None:
    """
    调用 Google Gemini 模型提取 GitHub 项目的结构化信息。
    """
    print(f"执行大模型分析: {repo_name} ...")

    # 延迟触发校验
    client = _get_client()

    safe_readme = readme_text[:30000] if len(readme_text) > 30000 else readme_text

    prompt = f"""
    你是一个开源技术专家。请分析以下 GitHub 项目信息：
    
    【输入信息】
    项目名称: {repo_name}
    项目简介: {description}
    README 内容: {safe_readme}
    
    【任务要求】
    严格按照以下 JSON 格式返回，不要包含任何额外的解释性文字或 Markdown 代码块标记：
    {{
        "core_concept": "用1到2句话概括这个项目的核心功能和解决的痛点",
        "tech_stack": ["技术栈1", "技术栈2", "语言等..."],
        "target_audience": "该项目主要面向哪类开发者或用户",
        "why_trending": "根据你的经验，一句话推测它近期爆火的原因"
    }}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        return json.loads(response.text)

    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        print(f"异常返回内容: {response.text}")
        return None
    except Exception as e:
        print(f"API 调用异常: {e}")
        return None
