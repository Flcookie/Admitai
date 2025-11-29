# postprocess_output.py (修复版)

import os
import sys
import json
from dotenv import load_dotenv

# ============================
# 动态路径
# ============================
CURRENT_FILE = os.path.abspath(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_FILE, "../../../.."))
APP_DIR = os.path.join(BACKEND_DIR, "app")

sys.path.append(BACKEND_DIR)
sys.path.append(APP_DIR)

ENV_PATH = os.path.join(BACKEND_DIR, ".env")
load_dotenv(ENV_PATH)

from app.config import settings
from app.services.supabase_client import supabase


def main():
    output_file = "batch_output.jsonl"

    if not os.path.exists(output_file):
        raise FileNotFoundError("❌ 请先运行 download_output.py 下载 batch_output.jsonl")

    print(">> Reading:", output_file)

    # 处理输出
    updated_cn = 0
    updated_en = 0
    errors = 0

    with open(output_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                obj = json.loads(line)
                
                # 检查是否有错误
                if obj.get("error"):
                    print(f"⚠️  Line {line_num} 有错误: {obj['error']}")
                    errors += 1
                    continue
                
                custom_id = obj["custom_id"]
                
                # 从 custom_id 中提取 program_id
                # custom_id 格式: "cn_{pid}" 或 "en_{pid}"
                lang, pid = custom_id.split("_", 1)
                program_id = int(pid)
                
                # 获取 embedding 向量
                response_body = obj["response"]["body"]
                embedding = response_body["data"][0]["embedding"]
                
                # 确保是浮点数列表
                embedding = [float(x) for x in embedding]
                
                # 根据语言决定更新哪个字段
                if lang == "cn":
                    field = "program_embedding_cn"
                    updated_cn += 1
                elif lang == "en":
                    field = "program_embedding_en"
                    updated_en += 1
                else:
                    print(f"⚠️  未知的语言前缀: {lang}")
                    continue
                
                # 写回 Supabase
                result = supabase.table("programs").update({
                    field: embedding
                }).eq("id", program_id).execute()
                
                if line_num % 100 == 0:
                    print(f">> 已处理 {line_num} 行...")
                    
            except Exception as e:
                print(f"❌ Line {line_num} 处理失败: {e}")
                print(f"   内容: {line[:100]}...")
                errors += 1
                continue

    print("\n" + "="*50)
    print(f"🎉 处理完成!")
    print(f"   中文 embeddings: {updated_cn}")
    print(f"   英文 embeddings: {updated_en}")
    print(f"   总计更新: {updated_cn + updated_en}")
    if errors > 0:
        print(f"   ⚠️  错误数: {errors}")
    print("="*50)


if __name__ == "__main__":
    main()