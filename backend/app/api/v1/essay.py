# app/api/v1/essay.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
from app.services.llm_client import llm_generate, llm_chat, llm_chat_stream

router = APIRouter(prefix="/essay", tags=["Essay"])


# ===============================
# 输入结构
# ===============================
class EssayRequest(BaseModel):
    essay_type: str  # "personal_statement", "statement_of_purpose", "cv", "cover_letter" 等
    student_background: str  # 学生背景信息
    target_university: Optional[str] = None  # 目标学校
    target_program: Optional[str] = None  # 目标专业/项目
    additional_requirements: Optional[str] = None  # 额外要求或提示
    word_limit: Optional[int] = None  # 字数限制
    language: str = "中文"  # 输出语言


# ===============================
# 输出结构
# ===============================
class EssayResponse(BaseModel):
    essay_content: str
    essay_type: str
    word_count: int


# ===============================
# 文书类型映射和提示词
# ===============================
ESSAY_PROMPTS = {
    "personal_statement": """你是一名专业的留学文书写作专家。请根据以下信息，撰写一篇优秀的Personal Statement（个人陈述）。

学生背景：
{student_background}

目标学校：{target_university}
目标专业/项目：{target_program}
{additional_info}

要求：
1. 突出学生的学术兴趣和动机
2. 展示学生的相关经历和能力
3. 说明为什么选择这个学校和专业
4. 体现学生的个性和独特性
5. 语言流畅、逻辑清晰、有说服力
{word_limit_info}

请用{language}撰写完整的Personal Statement。""",

    "statement_of_purpose": """你是一名专业的留学文书写作专家。请根据以下信息，撰写一篇优秀的Statement of Purpose（目的陈述）。

学生背景：
{student_background}

目标学校：{target_university}
目标专业/项目：{target_program}
{additional_info}

要求：
1. 明确说明学术和职业目标
2. 解释为什么这个项目符合你的目标
3. 展示你为这个项目所做的准备
4. 说明你能为项目带来什么价值
5. 语言专业、逻辑严密、目标明确
{word_limit_info}

请用{language}撰写完整的Statement of Purpose。""",

    "cv": """你是一名专业的留学文书写作专家。请根据以下信息，为学生撰写一份专业的Curriculum Vitae（简历）。

学生背景：
{student_background}

目标学校：{target_university}
目标专业/项目：{target_program}
{additional_info}

要求：
1. 格式专业、清晰、易读
2. 突出教育背景、学术成就、研究经历
3. 包含实习、工作、项目经验
4. 列出相关技能和语言能力
5. 根据目标专业调整内容重点
{word_limit_info}

请用{language}撰写完整的CV。""",

    "cover_letter": """你是一名专业的留学文书写作专家。请根据以下信息，撰写一封专业的Cover Letter（求职信/申请信）。

学生背景：
{student_background}

目标学校：{target_university}
目标专业/项目：{target_program}
{additional_info}

要求：
1. 开头说明申请意图
2. 突出与项目相关的经验和能力
3. 表达对该项目的兴趣和热情
4. 说明为什么你是合适的候选人
5. 结尾礼貌、专业、有说服力
{word_limit_info}

请用{language}撰写完整的Cover Letter。"""
}


# ===============================
# API 端点：生成文书
# ===============================
@router.post("/generate", response_model=EssayResponse)
def generate_essay(request: EssayRequest):
    """
    根据学生背景和目标信息，AI生成留学文书
    """
    # 获取对应的提示词模板
    essay_type = request.essay_type
    if essay_type not in ESSAY_PROMPTS:
        raise ValueError(f"不支持的文书类型: {essay_type}")

    prompt_template = ESSAY_PROMPTS[essay_type]

    # 构建提示词
    additional_info = ""
    if request.additional_requirements:
        additional_info = f"\n额外要求：{request.additional_requirements}"

    word_limit_info = ""
    if request.word_limit:
        word_limit_info = f"\n6. 字数控制在约{request.word_limit}字左右"

    prompt = prompt_template.format(
        student_background=request.student_background,
        target_university=request.target_university or "未指定",
        target_program=request.target_program or "未指定",
        additional_info=additional_info,
        word_limit_info=word_limit_info,
        language=request.language
    )

    # 调用LLM生成文书
    try:
        essay_content = llm_generate(prompt)
        word_count = len(essay_content)

        return EssayResponse(
            essay_content=essay_content,
            essay_type=essay_type,
            word_count=word_count
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文书生成失败: {str(e)}")


# ===============================
# API 端点：获取支持的文书类型
# ===============================
@router.get("/types")
def get_essay_types():
    """
    返回支持的文书类型列表
    """
    return {
        "types": [
            {
                "value": "personal_statement",
                "label": "Personal Statement (个人陈述)",
                "description": "用于展示个人背景、兴趣和动机"
            },
            {
                "value": "statement_of_purpose",
                "label": "Statement of Purpose (目的陈述)",
                "description": "重点说明学术和职业目标"
            },
            {
                "value": "cv",
                "label": "CV/Resume (简历)",
                "description": "学术和工作经历汇总"
            },
            {
                "value": "cover_letter",
                "label": "Cover Letter (求职信)",
                "description": "用于申请工作或项目的信件"
            }
        ]
    }


# ===============================
# 聊天式文书生成
# ===============================
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class EssayChatRequest(BaseModel):
    essay_type: str  # 文书类型
    messages: List[ChatMessage]  # 对话历史
    student_background: Optional[str] = None  # 学生背景（首次对话需要）
    target_university: Optional[str] = None  # 目标学校
    target_program: Optional[str] = None  # 目标专业/项目
    language: str = "中文"  # 输出语言
    current_essay: Optional[str] = None  # 当前的文书内容（用于修改）


class EssayChatResponse(BaseModel):
    message: str  # AI回复
    essay_content: Optional[str] = None  # 如果有生成/更新文书，包含文书内容
    word_count: Optional[int] = None


def build_system_prompt(essay_type: str, student_background: str, target_university: str, 
                       target_program: str, language: str) -> str:
    """构建系统提示词"""
    essay_type_descriptions = {
        "personal_statement": "Personal Statement（个人陈述），用于展示个人背景、兴趣和动机",
        "statement_of_purpose": "Statement of Purpose（目的陈述），重点说明学术和职业目标",
        "cv": "CV/Resume（简历），学术和工作经历汇总",
        "cover_letter": "Cover Letter（求职信），用于申请工作或项目的信件"
    }
    
    essay_desc = essay_type_descriptions.get(essay_type, "留学文书")
    
    return f"""你是一名专业的留学文书写作专家，正在帮助学生撰写{essay_desc}。

学生背景信息：
{student_background}

目标学校：{target_university or "未指定"}
目标专业/项目：{target_program or "未指定"}

你的任务：
1. 根据学生的对话需求，生成或修改文书内容
2. 如果学生要求生成新文书，提供完整的文书内容
3. 如果学生要求修改特定部分，只提供修改后的完整文书内容
4. 如果学生询问问题，提供专业建议和指导
5. 始终保持专业、友好、有帮助的态度
6. 用{language}回复

在回复时：
- 如果是生成或修改文书，请在回复的最后单独一行写上 "---ESSAY_START---" 然后换行，接着是完整的文书内容，最后换行写上 "---ESSAY_END---"
- 如果没有文书内容，直接回复对话即可
"""


@router.post("/chat", response_model=EssayChatResponse)
def chat_essay(request: EssayChatRequest):
    """
    聊天式文书生成和修改API
    """
    # 验证文书类型
    if request.essay_type not in ESSAY_PROMPTS:
        raise HTTPException(status_code=400, detail=f"不支持的文书类型: {request.essay_type}")
    
    # 如果是第一次对话，需要学生背景信息
    if len(request.messages) == 0 and not request.student_background:
        raise HTTPException(status_code=400, detail="首次对话需要提供学生背景信息")
    
    # 构建消息列表
    messages = []
    
    # 如果是首次对话（消息为空），添加一个初始用户消息
    if len(request.messages) == 0:
        messages.append({
            "role": "user",
            "content": "你好，我想开始撰写文书。请告诉我如何开始，或者直接为我生成一份初稿。"
        })
    else:
        # 添加历史消息
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})
    
    # 构建系统提示词
    if request.student_background:
        system_prompt = build_system_prompt(
            request.essay_type,
            request.student_background,
            request.target_university or "",
            request.target_program or "",
            request.language
        )
    else:
        system_prompt = "你是一名专业的留学文书写作专家，正在帮助学生撰写和修改文书。"
    
    # 如果有当前文书内容，添加到系统提示中
    if request.current_essay:
        system_prompt += f"\n\n当前文书内容：\n{request.current_essay}\n\n如果学生要求修改，请提供修改后的完整文书内容，并在回复最后用 ---ESSAY_START--- 和 ---ESSAY_END--- 标记。"
    
    # 调用LLM
    try:
        response_content = llm_chat(messages, system_prompt=system_prompt)
        
        # 解析回复，检查是否包含文书内容
        essay_content = None
        word_count = None
        message = response_content
        
        if "---ESSAY_START---" in response_content and "---ESSAY_END---" in response_content:
            # 提取文书内容
            parts = response_content.split("---ESSAY_START---")
            if len(parts) > 1:
                essay_part = parts[1].split("---ESSAY_END---")[0].strip()
                message_part = parts[0].strip()
                
                # 如果有文书内容之前的消息，保留它
                if message_part:
                    message = message_part
                else:
                    message = "我已经为你生成了文书内容，请查看下方。"
                
                essay_content = essay_part
                word_count = len(essay_content)
        
        return EssayChatResponse(
            message=message,
            essay_content=essay_content,
            word_count=word_count
        )
        
    except HTTPException:
        # 重新抛出HTTPException
        raise
    except Exception as e:
        # 其他异常转换为HTTPException
        error_msg = str(e)
        raise HTTPException(status_code=500, detail=f"文书生成失败: {error_msg}")


# ===============================
# 流式聊天式文书生成
# ===============================
def generate_stream_response(request: EssayChatRequest):
    """
    生成流式响应的生成器
    """
    try:
        # 验证文书类型
        if request.essay_type not in ESSAY_PROMPTS:
            yield f"data: {json.dumps({'type': 'error', 'content': f'不支持的文书类型: {request.essay_type}'}, ensure_ascii=False)}\n\n"
            return
        
        # 如果是第一次对话，需要学生背景信息
        if len(request.messages) == 0 and not request.student_background:
            yield f"data: {json.dumps({'type': 'error', 'content': '首次对话需要提供学生背景信息'}, ensure_ascii=False)}\n\n"
            return
        
        # 构建消息列表
        messages = []
        
        # 如果是首次对话（消息为空），添加一个初始用户消息
        if len(request.messages) == 0:
            messages.append({
                "role": "user",
                "content": "你好，我想开始撰写文书。请告诉我如何开始，或者直接为我生成一份初稿。"
            })
        else:
            # 添加历史消息
            for msg in request.messages:
                messages.append({"role": msg.role, "content": msg.content})
        
        # 构建系统提示词
        if request.student_background:
            system_prompt = build_system_prompt(
                request.essay_type,
                request.student_background,
                request.target_university or "",
                request.target_program or "",
                request.language
            )
        else:
            system_prompt = "你是一名专业的留学文书写作专家，正在帮助学生撰写和修改文书。"
        
        # 如果有当前文书内容，添加到系统提示中
        if request.current_essay:
            system_prompt += f"\n\n当前文书内容：\n{request.current_essay}\n\n如果学生要求修改，请提供修改后的完整文书内容，并在回复最后用 ---ESSAY_START--- 和 ---ESSAY_END--- 标记。"
        
        # 流式调用LLM
        full_content = ""
        for chunk in llm_chat_stream(messages, system_prompt=system_prompt):
            full_content += chunk
            # 发送文本块
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk}, ensure_ascii=False)}\n\n"
        
        # 检查是否包含文书内容
        essay_content = None
        word_count = None
        message = full_content
        
        if "---ESSAY_START---" in full_content and "---ESSAY_END---" in full_content:
            # 提取文书内容
            parts = full_content.split("---ESSAY_START---")
            if len(parts) > 1:
                essay_part = parts[1].split("---ESSAY_END---")[0].strip()
                message_part = parts[0].strip()
                
                if message_part:
                    message = message_part
                else:
                    message = "我已经为你生成了文书内容，请查看下方。"
                
                essay_content = essay_part
                word_count = len(essay_content)
                
                # 发送文书内容
                yield f"data: {json.dumps({'type': 'essay', 'content': essay_content, 'word_count': word_count}, ensure_ascii=False)}\n\n"
        
        # 发送完成信号
        yield f"data: {json.dumps({'type': 'done', 'message': message}, ensure_ascii=False)}\n\n"
        
    except Exception as e:
        error_msg = str(e)
        yield f"data: {json.dumps({'type': 'error', 'content': f'文书生成失败: {error_msg}'}, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
def chat_essay_stream(request: EssayChatRequest):
    """
    流式聊天式文书生成和修改API（Server-Sent Events）
    """
    return StreamingResponse(
        generate_stream_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

