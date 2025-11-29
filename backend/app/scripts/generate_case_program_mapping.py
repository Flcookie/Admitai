# backend/app/scripts/generate_case_program_mapping.py

import sys
import os
import time
import json
import random
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

# ===========================================================
# 修复路径
# ===========================================================
CURRENT_FILE = os.path.abspath(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_FILE, "../../.."))
ROOT_DIR = BACKEND_DIR
sys.path.append(ROOT_DIR)

# 加载 env
load_dotenv(os.path.join(ROOT_DIR, ".env"))

from app.config import settings
from app.services.supabase_client import supabase

client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ===========================================================
# 工具函数
# ===========================================================
def cosine(a, b):
    a, b = np.array(a), np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def normalize(v):
    return [float(x) for x in v]


# ===========================================================
# 安全版批量 embedding，带 retry + 限速
# ===========================================================
def safe_batch_embed(texts, batch_id=""):
    """
    texts: list[str]
    return: list[list[float] or None]
    """
    try:
        res = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [normalize(e.embedding) for e in res.data]
    except Exception as e:
        print(f"⚠️ Batch {batch_id} failed → retrying individually...", e)

    # fallback 单条重试
    final = []
    for t in texts:
        final.append(safe_single_embed(t))
    return final


def safe_single_embed(text):
    for attempt in range(6):
        try:
            res = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return normalize(res.data[0].embedding)
        except Exception as e:
            wait = (2 ** attempt) + random.random()
            print(f"⚠️ Single embed retry {attempt+1}/6 wait={wait:.2f}s ({text})")
            time.sleep(wait)
    return None


# ===========================================================
# 载入全部 program（含 embedding）
# ===========================================================
def load_programs():
    print("Loading programs...")
    rows = supabase.table("programs").select("*").execute().data

    programs = []
    for r in rows:
        emb = r.get("program_embedding")
        if isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except:
                emb = None

        programs.append({
            "id": r["id"],
            "university": r["chinese_name"],
            "name": r["program_cn_name"],
            "embedding": emb
        })

    print(f"Loaded {len(programs)} programs")
    return programs


# ===========================================================
# 主逻辑：案例 → 项目匹配
# ===========================================================
def match_cases(batch_size=80, threshold=0.70):
    print("Loading cases...")
    cases = supabase.table("cases").select("*").execute().data
    print(f"Total cases = {len(cases)}")

    programs = load_programs()

    # 需要更新的 cases（避免重复运行）
    todo = [c for c in cases if not c.get("program_id")]
    print(f"Need processing = {len(todo)}")

    # logging
    log_fail = open("case_mapping_fail.log", "a", encoding="utf-8")

    # 批处理
    for i in range(0, len(todo), batch_size):
        batch = todo[i:i + batch_size]
        names = [c["applied_program"] for c in batch]

        print(f"\n=== Batch {i//batch_size+1} ({len(batch)}) ===")

        # 批量 embedding
        embeddings = safe_batch_embed(names, batch_id=i)

        # 对每个 case 做匹配
        for case, case_emb in zip(batch, embeddings):

            if case_emb is None:
                log_fail.write(json.dumps(
                    {"id": case["id"], "reason": "embedding failed"}, ensure_ascii=False) + "\n")
                continue

            best = None
            best_score = 0

            for p in programs:
                if not p["embedding"]:
                    continue
                s = cosine(case_emb, p["embedding"])
                if s > best_score:
                    best_score = s
                    best = p

            # 判断是否匹配成功
            if best and best_score >= threshold:
                print(f"✓ {case['applied_program']} → {best['name']}  ({best_score:.3f})")

                supabase.table("cases").update({
                    "program_id": best["id"],
                    "matched_program_name": best["name"],
                    "matched_university": best["university"],
                    "match_score": best_score
                }).eq("id", case["id"]).execute()
            else:
                print(f"✗ No match: {case['applied_program']} (best={best_score:.3f})")
                log_fail.write(json.dumps(
                    {"id": case["id"], "program": case["applied_program"], "score": best_score},
                    ensure_ascii=False
                ) + "\n")

        # 限速：每处理一批休眠 1 秒
        time.sleep(1)

    log_fail.close()
    print("\n🎉 All cases matched successfully!")


# run
if __name__ == "__main__":
    print("=== Start Case → Program Matching ===")
    match_cases(batch_size=80, threshold=0.70)
    print("=== Completed ===")
