# app/services/canonical/llm_match.py
"""
LLM语义匹配模块
使用GPT-4o-mini进行语义匹配
"""
from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def llm_semantic_match(a: str, b: str) -> bool:
    """
    使用LLM判断两个项目名称是否指向同一个项目
    
    Args:
        a: 第一个项目名称
        b: 第二个项目名称
        
    Returns:
        是否匹配
    """
    if not a or not b:
        return False
    
    try:
        prompt = f"""Do these two program names refer to the same postgraduate programme? A: {a} B: {b}. Reply yes or no."""
        
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        
        reply = res.choices[0].message.content.strip().lower()
        return reply == "yes"
    except Exception as e:
        # 如果LLM调用失败，返回False
        return False

