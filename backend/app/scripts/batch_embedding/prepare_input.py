# prepare_input.py (完整修复版)

import os, sys, json
from dotenv import load_dotenv

# ===== 修复路径 =====
CURRENT = os.path.abspath(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT, "../../../.."))
APP_DIR = os.path.join(BACKEND_DIR, "app")

print(">> BACKEND_DIR:", BACKEND_DIR)
sys.path.append(BACKEND_DIR)

# ===== 读取 .env =====
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

# ===== 导入依赖 =====
from app.services.supabase_client import supabase


def run():
    print(">> Fetching programs...")

    rows = (
        supabase.table("programs")
        .select("id, program_cn_name, program_en_name")
        .execute()
        .data
    )

    print(f"Total programs: {len(rows)}")

    out_path = "programs_batch_input.jsonl"
    f = open(out_path, "w", encoding="utf-8")

    for p in rows:
        pid = p["id"]
        cn = p.get("program_cn_name") or ""
        en = p.get("program_en_name") or ""

        # 中文 embedding - 使用正确的 OpenAI Batch API 格式
        if cn.strip():  # 只处理非空文本
            f.write(json.dumps({
                "custom_id": f"cn_{pid}",
                "method": "POST",
                "url": "/v1/embeddings",
                "body": {
                    "model": "text-embedding-3-small",
                    "input": cn,
                    "encoding_format": "float"
                }
            }, ensure_ascii=False) + "\n")

        # 英文 embedding
        if en.strip():  # 只处理非空文本
            f.write(json.dumps({
                "custom_id": f"en_{pid}",
                "method": "POST",
                "url": "/v1/embeddings",
                "body": {
                    "model": "text-embedding-3-small",
                    "input": en,
                    "encoding_format": "float"
                }
            }, ensure_ascii=False) + "\n")

    f.close()
    
    # 计算实际写入的行数
    actual_lines = sum(1 for _ in open(out_path, 'r', encoding='utf-8'))
    print(f"✔ programs_batch_input.jsonl generated! ({actual_lines} lines)")


if __name__ == "__main__":
    run()