import sys
import os
import time
import json
import random
from dotenv import load_dotenv
from openai import OpenAI

# ================================================
# 路径设置：让 Python 能正确 import app.*
# ================================================
CURRENT_FILE = os.path.abspath(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_FILE, "../../.."))
ROOT_DIR = BACKEND_DIR
sys.path.append(ROOT_DIR)

print(">> ROOT_DIR added:", ROOT_DIR)

# ================================================
# 读取环境变量
# ================================================
ENV_PATH = os.path.join(ROOT_DIR, ".env")
print(">> Loading .env from:", ENV_PATH)
load_dotenv(ENV_PATH)

# ================================================
# 导入 Supabase & Config
# ================================================
from app.config import settings
from app.services.supabase_client import supabase

client = OpenAI(api_key=settings.OPENAI_API_KEY)


# =====================================================
# 工具：转换 embedding 格式（避免 numpy.float32）
# =====================================================
def normalize_embedding(arr):
    return [float(x) for x in arr]


# =====================================================
# 工具：安全 embedding（带指数退避重试）
# =====================================================
def safe_embed(text):
    for attempt in range(6):  # 最多重试 6 次
        try:
            res = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return normalize_embedding(res.data[0].embedding)
        except Exception as e:
            wait = (2 ** attempt) + random.random()
            print(f"⚠️ Embedding failed ({text}), retry {attempt+1}/6, wait {wait:.2f}s")
            time.sleep(wait)
    return None


# =====================================================
# 批量处理工具
# =====================================================
def chunks(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i+size]


# =====================================================
# 主函数：批量 embedding
# =====================================================
def update_program_embeddings(batch_size=50):
    print(">> Fetching programs from Supabase...")

    programs = (
        supabase.table("programs")
        .select("*")
        .execute()
        .data
    )

    print(f"🎯 Total programs: {len(programs)}")

    # 只处理 program_embedding_cn 为空的（断点续跑）
    programs_to_process = [p for p in programs if not p.get("program_embedding_cn")]

    print(f"➡️ Programs needing embedding: {len(programs_to_process)}")

    # 记录失败日志
    error_log = open("embedding_errors.log", "a", encoding="utf-8")

    for batch in chunks(programs_to_process, batch_size):
        cn_texts = [p["program_cn_name"] or "" for p in batch]
        en_texts = [p["program_en_name"] or "" for p in batch]

        # ---- 批量生成 CN embedding ----
        try:
            cn_res = client.embeddings.create(
                model="text-embedding-3-small",
                input=cn_texts
            )
            cn_embeddings = [normalize_embedding(e.embedding) for e in cn_res.data]
        except Exception as e:
            print("❌ CN batch embedding failed:", e)
            # fallback: 单条重试
            cn_embeddings = [safe_embed(t) for t in cn_texts]

        # ---- 批量生成 EN embedding ----
        try:
            en_res = client.embeddings.create(
                model="text-embedding-3-small",
                input=en_texts
            )
            en_embeddings = [normalize_embedding(e.embedding) for e in en_res.data]
        except Exception as e:
            print("❌ EN batch embedding failed:", e)
            en_embeddings = [safe_embed(t) for t in en_texts]

        # ---- 保存到 Supabase ----
        for p, emb_cn, emb_en in zip(batch, cn_embeddings, en_embeddings):
            try:
                supabase.table("programs").update({
                    "program_embedding_cn": emb_cn,
                    "program_embedding_en": emb_en
                }).eq("id", p["id"]).execute()

                print(f"✓ Updated {p['program_cn_name']}")
            except Exception as e:
                print(f"❌ Failed saving {p['program_cn_name']}", e)
                error_log.write(json.dumps({
                    "id": p["id"],
                    "name": p["program_cn_name"],
                    "error": str(e)
                }, ensure_ascii=False) + "\n")

        # ---- 防止 Rate Limit ----
        time.sleep(0.5)

    error_log.close()
    print("\n🎉 All embeddings updated successfully!")


# =====================================================
# 入口
# =====================================================
if __name__ == "__main__":
    update_program_embeddings(batch_size=50)
