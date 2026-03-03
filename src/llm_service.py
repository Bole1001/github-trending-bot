import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ==========================================
# 优先级 高：环境配置与鉴权拦截
# ==========================================
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("严重错误: 环境变量中缺失 GEMINI_API_KEY。")

client = genai.Client(api_key=GEMINI_API_KEY)


def analyze_repo(repo_name: str, description: str, readme_text: str) -> dict | None:
    """
    调用 Google Gemini 模型提取 GitHub 项目的结构化信息。
    """
    print(f"执行大模型分析: {repo_name} ...")

    # ==========================================
    # 优先级 中：防御性截断
    # 解释：即使模型支持百万上下文，物理截断超出必要长度的文本可降低无意义的 Token 消耗和网络延迟。
    # ==========================================
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
        # ==========================================
        # 优先级 高：模型调用与强制结构化输出
        # ==========================================
        response = client.models.generate_content(
            model="gemini-2.5-flash",  # 若依然报 429 降级为 'gemini-2.0-flash-lite'
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,  # 降低随机性，确保 JSON 结构稳定
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


if __name__ == "__main__":
    # ==========================================
    # 优先级 低：本地单元测试模块
    # ==========================================
    mock_repo_name = "test/awesome-ai-tool"
    mock_desc = "一个极简的 AI 工具箱"
    mock_readme = """
    # Awesome AI Tool
    This is a backend service built with FastAPI and Python 3.10. 
    It uses Redis for caching and integrates with OpenAI API.
    Perfect for backend developers to quickly deploy AI features.
    """

    result = analyze_repo(mock_repo_name, mock_desc, mock_readme)

    if result:
        print("结构化数据提取结果：")
        print(json.dumps(result, indent=4, ensure_ascii=False))
