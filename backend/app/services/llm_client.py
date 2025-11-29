from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ===========================
# 非流式 API（推荐用这个）
# ===========================
def llm_generate(prompt: str) -> str:
    """
    调用 OpenAI GPT-4o-mini，返回完整字符串（推荐理由生成用）
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "你是一名资深留学顾问，需要给出专业分析、项目理解和申请建议。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6
    )

    return response.choices[0].message.content


# ===========================
# 流式 API（你以后做前端 streaming 再用）
# ===========================
def llm_stream(prompt: str):
    """
    以流式方式生成推荐理由（用于 future 前端流式展示）
    """
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "你是一名资深留学顾问，需要给出专业分析、项目理解和申请建议。"},
            {"role": "user", "content": prompt}
        ],
        stream=True,
        temperature=0.6,
    )

    for event in stream:
        delta = event.choices[0].delta
        if delta and delta.content:
            yield delta.content


# ===========================
# 对话式 API（用于聊天）
# ===========================
def llm_chat(messages: list, system_prompt: str = None) -> str:
    """
    对话式LLM调用，支持消息历史
    messages: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    """
    msg_list = []
    if system_prompt:
        msg_list.append({"role": "system", "content": system_prompt})
    msg_list.extend(messages)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=msg_list,
        temperature=0.7
    )
    
    return response.choices[0].message.content


# ===========================
# 流式对话式 API（用于聊天流式输出）
# ===========================
def llm_chat_stream(messages: list, system_prompt: str = None):
    """
    流式对话式LLM调用，支持消息历史
    messages: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    """
    msg_list = []
    if system_prompt:
        msg_list.append({"role": "system", "content": system_prompt})
    msg_list.extend(messages)
    
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=msg_list,
        stream=True,
        temperature=0.7
    )
    
    for event in stream:
        delta = event.choices[0].delta
        if delta and delta.content:
            yield delta.content